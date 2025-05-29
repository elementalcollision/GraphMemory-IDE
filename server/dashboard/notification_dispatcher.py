"""
Notification Dispatcher - Multi-channel notification delivery system.

This module provides the central NotificationDispatcher that:
- Delivers notifications across multiple channels (WebSocket, email, webhook, Slack)
- Manages background queue processing for reliable delivery
- Handles notification templates and formatting
- Provides delivery tracking and retry logic

Created as part of Step 8 Phase 2: Real-time Alerting & Notification System
Research foundation: Exa + Context7 + Sequential Thinking
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Set, Any, Callable
from uuid import UUID, uuid4
from collections import defaultdict, deque
from dataclasses import dataclass
from email.utils import formataddr

# Optional imports for enhanced functionality
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None

from server.dashboard.models.alert_models import (
    Alert, AlertEvent, NotificationConfig, NotificationDelivery, 
    NotificationChannel, NotificationTemplate, AlertSeverity
)
from server.dashboard.cache_manager import get_cache_manager, CacheManager
from server.dashboard.enhanced_circuit_breaker import get_circuit_breaker_manager, CircuitBreakerManager

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DeliveryContext:
    """Context for notification delivery"""
    alert: Alert
    config: NotificationConfig
    template: Optional[NotificationTemplate] = None
    retry_count: int = 0
    scheduled_at: Optional[datetime] = None
    user_context: Optional[Dict[str, Any]] = None


class WebSocketManager:
    """Manages WebSocket connections for real-time alerts"""
    
    def __init__(self):
        self.connections: Dict[str, Set[Any]] = defaultdict(set)  # user_id -> connections
        self.alert_subscriptions: Dict[str, Set[AlertSeverity]] = {}  # user_id -> severities
        self.connection_metadata: Dict[Any, Dict[str, Any]] = {}  # connection -> metadata
    
    def add_connection(self, connection: Any, user_id: str, 
                      severities: Optional[List[AlertSeverity]] = None):
        """Add a WebSocket connection"""
        self.connections[user_id].add(connection)
        if severities:
            self.alert_subscriptions[user_id] = set(severities)
        else:
            # Convert enum class to set of all enum values
            self.alert_subscriptions[user_id] = set(AlertSeverity.__members__.values())
        
        self.connection_metadata[connection] = {
            'user_id': user_id,
            'connected_at': datetime.utcnow(),
            'alert_count': 0
        }
        
        logger.info(f"Added WebSocket connection for user {user_id}")
    
    def remove_connection(self, connection: Any):
        """Remove a WebSocket connection"""
        if connection in self.connection_metadata:
            user_id = self.connection_metadata[connection]['user_id']
            self.connections[user_id].discard(connection)
            
            if not self.connections[user_id]:
                del self.connections[user_id]
                if user_id in self.alert_subscriptions:
                    del self.alert_subscriptions[user_id]
            
            del self.connection_metadata[connection]
            logger.info(f"Removed WebSocket connection for user {user_id}")
    
    async def broadcast_alert(self, alert: Alert, user_filter: Optional[Callable[[str], bool]] = None):
        """Broadcast alert to connected WebSocket clients"""
        event = AlertEvent(
            event_type="alert_created",
            alert=alert,
            timestamp=alert.triggered_at
        )
        
        message = json.dumps(event.dict(), default=str)
        disconnected_connections = set()
        
        for user_id, connections in self.connections.items():
            # Check user filter
            if user_filter and not user_filter(user_id):
                continue
            
            # Check severity subscription
            if (user_id in self.alert_subscriptions and 
                alert.severity not in self.alert_subscriptions[user_id]):
                continue
            
            # Send to all user connections
            for connection in connections.copy():
                try:
                    if hasattr(connection, 'send_text'):
                        await connection.send_text(message)
                    elif hasattr(connection, 'send'):
                        await connection.send(message)
                    
                    # Update connection metadata
                    if connection in self.connection_metadata:
                        self.connection_metadata[connection]['alert_count'] += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to send alert to WebSocket connection: {e}")
                    disconnected_connections.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.remove_connection(connection)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        total_connections = sum(len(conns) for conns in self.connections.values())
        
        return {
            'total_connections': total_connections,
            'unique_users': len(self.connections),
            'subscriptions': dict(self.alert_subscriptions),
            'average_alerts_per_connection': (
                sum(meta['alert_count'] for meta in self.connection_metadata.values()) / 
                max(total_connections, 1)
            )
        }


class EmailNotifier:
    """SMTP email notification handler"""
    
    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 587,
                 smtp_user: Optional[str] = None, smtp_password: Optional[str] = None,
                 use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_email = smtp_user or "alerts@graphmemory-ide.com"
        self.from_name = "GraphMemory-IDE Alerts"
    
    async def send_notification(self, context: DeliveryContext) -> bool:
        """Send email notification"""
        try:
            # Format the notification
            subject = self._format_subject(context)
            body = self._format_body(context)
            html_body = self._format_html_body(context)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = ', '.join(context.config.email_addresses)
            
            # Add text and HTML parts
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_smtp, msg, context.config.email_addresses
            )
            
            logger.info(f"Email notification sent for alert {context.alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_smtp(self, msg: MIMEMultipart, recipients: List[str]):
        """Send email via SMTP (blocking operation)"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.send_message(msg, to_addrs=recipients)
    
    def _format_subject(self, context: DeliveryContext) -> str:
        """Format email subject"""
        if context.template and context.template.subject_template:
            return context.template.subject_template.format(alert=context.alert)
        
        return f"[{context.alert.severity.value.upper()}] {context.alert.title}"
    
    def _format_body(self, context: DeliveryContext) -> str:
        """Format email body (text)"""
        if context.template and context.template.body_template:
            return context.template.body_template.format(alert=context.alert)
        
        return f"""
Alert Details:
Title: {context.alert.title}
Severity: {context.alert.severity.value.upper()}
Category: {context.alert.category.value}
Status: {context.alert.status.value}

Description:
{context.alert.description}

Metrics:
{self._format_metrics(context.alert)}

Alert ID: {context.alert.id}
Triggered: {context.alert.triggered_at}
Rule: {context.alert.rule_name}
        """.strip()
    
    def _format_html_body(self, context: DeliveryContext) -> str:
        """Format email body (HTML)"""
        if context.template and context.template.html_template:
            return context.template.html_template.format(alert=context.alert)
        
        severity_color = {
            'critical': '#dc2626',
            'high': '#ea580c',
            'medium': '#ca8a04',
            'low': '#65a30d',
            'info': '#2563eb'
        }.get(context.alert.severity.value, '#6b7280')
        
        return f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .alert-header {{ background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px; }}
                    .alert-content {{ padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }}
                    .metric-item {{ margin: 5px 0; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="alert-header">
                    <h2>{context.alert.title}</h2>
                    <p>Severity: {context.alert.severity.value.upper()} | Category: {context.alert.category.value}</p>
                </div>
                
                <div class="alert-content">
                    <h3>Description</h3>
                    <p>{context.alert.description}</p>
                    
                    <h3>Metrics</h3>
                    {self._format_metrics_html(context.alert)}
                    
                    <h3>Alert Information</h3>
                    <div class="metric-item"><strong>Alert ID:</strong> {context.alert.id}</div>
                    <div class="metric-item"><strong>Triggered:</strong> {context.alert.triggered_at}</div>
                    <div class="metric-item"><strong>Rule:</strong> {context.alert.rule_name}</div>
                    <div class="metric-item"><strong>Status:</strong> {context.alert.status.value}</div>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from GraphMemory-IDE Analytics System.</p>
                </div>
            </body>
        </html>
        """
    
    def _format_metrics(self, alert: Alert) -> str:
        """Format metrics for text display"""
        if not alert.metric_values:
            return "No metrics data available"
        
        lines = []
        for metric, value in alert.metric_values.items():
            lines.append(f"- {metric}: {value}")
        
        return "\n".join(lines)
    
    def _format_metrics_html(self, alert: Alert) -> str:
        """Format metrics for HTML display"""
        if not alert.metric_values:
            return "<p>No metrics data available</p>"
        
        items = []
        for metric, value in alert.metric_values.items():
            items.append(f'<div class="metric-item"><strong>{metric}:</strong> {value}</div>')
        
        return "\n".join(items)


class WebhookNotifier:
    """HTTP webhook notification handler"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[Any] = None  # aiohttp.ClientSession when available
        self.available = HAS_AIOHTTP
        
        if not self.available:
            logger.warning("aiohttp not available, webhook notifications disabled")
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.available:
            return
            
        if not self.session and aiohttp:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def shutdown(self):
        """Shutdown HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def send_notification(self, context: DeliveryContext) -> bool:
        """Send webhook notification"""
        if not self.available:
            logger.error("aiohttp not available, cannot send webhook notification")
            return False
            
        if not context.config.webhook_url:
            logger.error("Webhook URL not configured")
            return False
        
        try:
            await self.initialize()
            
            if not self.session:
                logger.error("Failed to initialize HTTP session")
                return False
            
            # Prepare payload
            payload = self._prepare_payload(context)
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'GraphMemory-IDE-Alerts/1.0'
            }
            
            # Send webhook with retries
            for attempt in range(self.max_retries + 1):
                try:
                    async with self.session.post(
                        context.config.webhook_url,
                        json=payload,
                        headers=headers
                    ) as response:
                        if response.status < 400:
                            logger.info(f"Webhook notification sent for alert {context.alert.id}")
                            return True
                        else:
                            logger.warning(f"Webhook returned status {response.status}: {await response.text()}")
                
                except Exception as e:
                    logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    def _prepare_payload(self, context: DeliveryContext) -> Dict[str, Any]:
        """Prepare webhook payload"""
        return {
            'event_type': 'alert_notification',
            'timestamp': datetime.utcnow().isoformat(),
            'alert': {
                'id': str(context.alert.id),
                'title': context.alert.title,
                'description': context.alert.description,
                'severity': context.alert.severity.value,
                'category': context.alert.category.value,
                'status': context.alert.status.value,
                'triggered_at': context.alert.triggered_at.isoformat(),
                'rule_name': context.alert.rule_name,
                'rule_id': str(context.alert.rule_id),
                'metric_values': context.alert.metric_values,
                'threshold_breached': context.alert.threshold_breached,
                'actual_value': context.alert.actual_value,
                'source_host': context.alert.source_host,
                'source_component': context.alert.source_component,
                'tags': context.alert.tags
            },
            'notification_config': {
                'id': str(context.config.id),
                'name': context.config.name,
                'channel': context.config.channel.value
            }
        }


class SlackNotifier:
    """Slack webhook notification handler"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[Any] = None  # aiohttp.ClientSession when available
        self.available = HAS_AIOHTTP
        
        if not self.available:
            logger.warning("aiohttp not available, Slack notifications disabled")
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.available:
            return
            
        if not self.session and aiohttp:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def shutdown(self):
        """Shutdown HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def send_notification(self, context: DeliveryContext) -> bool:
        """Send Slack notification"""
        if not self.available:
            logger.error("aiohttp not available, cannot send Slack notification")
            return False
            
        if not context.config.slack_webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        try:
            await self.initialize()
            
            if not self.session:
                logger.error("Failed to initialize HTTP session")
                return False
            
            # Prepare Slack message
            payload = self._prepare_slack_payload(context)
            
            async with self.session.post(
                context.config.slack_webhook_url,
                json=payload
            ) as response:
                if response.status == 200:
                    logger.info(f"Slack notification sent for alert {context.alert.id}")
                    return True
                else:
                    logger.error(f"Slack webhook failed with status {response.status}")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def _prepare_slack_payload(self, context: DeliveryContext) -> Dict[str, Any]:
        """Prepare Slack message payload"""
        severity_colors = {
            'critical': '#dc2626',
            'high': '#ea580c', 
            'medium': '#ca8a04',
            'low': '#65a30d',
            'info': '#2563eb'
        }
        
        color = severity_colors.get(context.alert.severity.value, '#6b7280')
        
        # Create fields for alert details
        fields = [
            {
                'title': 'Severity',
                'value': context.alert.severity.value.upper(),
                'short': True
            },
            {
                'title': 'Category',
                'value': context.alert.category.value,
                'short': True
            },
            {
                'title': 'Rule',
                'value': context.alert.rule_name,
                'short': True
            },
            {
                'title': 'Triggered',
                'value': context.alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'short': True
            }
        ]
        
        # Add metric fields
        if context.alert.metric_values:
            for metric, value in list(context.alert.metric_values.items())[:3]:  # Limit to 3 metrics
                fields.append({
                    'title': metric.replace('_', ' ').title(),
                    'value': str(value),
                    'short': True
                })
        
        attachment = {
            'color': color,
            'title': context.alert.title,
            'text': context.alert.description,
            'fields': fields,
            'footer': 'GraphMemory-IDE Alerts',
            'footer_icon': 'https://example.com/favicon.ico',
            'ts': int(context.alert.triggered_at.timestamp())
        }
        
        # Add channel if specified
        payload: Dict[str, Any] = {
            'attachments': [attachment]
        }
        
        if context.config.slack_channel:
            payload['channel'] = context.config.slack_channel
        
        return payload


class NotificationQueue:
    """Background queue processor for notifications"""
    
    def __init__(self, max_workers: int = 5, max_queue_size: int = 1000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self.metrics = {
            'queued': 0,
            'processed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
    
    async def start(self):
        """Start queue processing workers"""
        if self.is_running:
            return
        
        self.is_running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
        
        logger.info(f"Started notification queue with {self.max_workers} workers")
    
    async def stop(self):
        """Stop queue processing"""
        self.is_running = False
        
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Stopped notification queue")
    
    async def enqueue(self, delivery_fn: Callable, context: DeliveryContext, 
                     priority: int = 0) -> bool:
        """Enqueue notification for delivery"""
        try:
            item = {
                'delivery_fn': delivery_fn,
                'context': context,
                'priority': priority,
                'enqueued_at': datetime.utcnow()
            }
            
            await self.queue.put(item)
            self.metrics['queued'] += 1
            
            logger.debug(f"Enqueued notification for alert {context.alert.id}")
            return True
            
        except asyncio.QueueFull:
            logger.error("Notification queue is full")
            return False
        except Exception as e:
            logger.error(f"Failed to enqueue notification: {e}")
            return False
    
    async def _worker(self, worker_name: str):
        """Queue worker process"""
        logger.info(f"Notification worker {worker_name} started")
        
        while self.is_running:
            try:
                # Get item from queue with timeout
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process notification
                success = await self._process_notification(item)
                
                # Update metrics
                self.metrics['processed'] += 1
                if not success:
                    self.metrics['failed'] += 1
                
                # Update success rate
                if self.metrics['processed'] > 0:
                    self.metrics['success_rate'] = (
                        (self.metrics['processed'] - self.metrics['failed']) / 
                        self.metrics['processed'] * 100
                    )
                
                # Mark task done
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Notification worker {worker_name} stopped")
    
    async def _process_notification(self, item: Dict[str, Any]) -> bool:
        """Process a single notification"""
        try:
            delivery_fn = item['delivery_fn']
            context = item['context']
            
            # Execute delivery function
            return await delivery_fn(context)
            
        except Exception as e:
            logger.error(f"Failed to process notification: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        return {
            **self.metrics,
            'queue_size': self.queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'workers': len(self.workers),
            'is_running': self.is_running
        }


class NotificationDispatcher:
    """Central notification dispatcher with multi-channel support"""
    
    def __init__(self, max_workers: int = 5, queue_size: int = 1000):
        # Channel handlers
        self.websocket_manager = WebSocketManager()
        self.email_notifier = EmailNotifier()
        self.webhook_notifier = WebhookNotifier()
        self.slack_notifier = SlackNotifier()
        
        # Queue processing
        self.queue = NotificationQueue(max_workers, queue_size)
        
        # External dependencies
        self.cache_manager: Optional[CacheManager] = None
        self.circuit_breaker_manager: Optional[CircuitBreakerManager] = None
        
        # Delivery tracking
        self.delivery_history: deque = deque(maxlen=1000)
        self.active_deliveries: Dict[UUID, NotificationDelivery] = {}
        
        # Configuration
        self.notification_configs: Dict[UUID, NotificationConfig] = {}
        
        logger.info("NotificationDispatcher initialized")
    
    async def initialize(self):
        """Initialize the notification dispatcher"""
        try:
            # Get external dependencies
            self.cache_manager = await get_cache_manager()
            self.circuit_breaker_manager = get_circuit_breaker_manager()
            
            # Initialize channel handlers
            await self.webhook_notifier.initialize()
            await self.slack_notifier.initialize()
            
            # Start queue processing
            await self.queue.start()
            
            logger.info("NotificationDispatcher initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NotificationDispatcher: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the notification dispatcher"""
        try:
            # Stop queue processing
            await self.queue.stop()
            
            # Shutdown channel handlers
            await self.webhook_notifier.shutdown()
            await self.slack_notifier.shutdown()
            
            logger.info("NotificationDispatcher shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during NotificationDispatcher shutdown: {e}")
    
    async def dispatch_alert(self, alert: Alert) -> List[NotificationDelivery]:
        """Dispatch alert to all configured notification channels"""
        deliveries = []
        
        try:
            # Get notification configurations for this alert
            configs = await self._get_applicable_configs(alert)
            
            for config in configs:
                # Create delivery record
                delivery = NotificationDelivery(
                    alert_id=alert.id,
                    config_id=config.id,
                    channel=config.channel,
                    subject=self._generate_subject(alert, config),
                    body=self._generate_body(alert, config),
                    recipients=self._get_recipients(config)
                )
                
                # Store delivery record
                self.active_deliveries[delivery.id] = delivery
                deliveries.append(delivery)
                
                # Dispatch based on channel
                if config.channel == NotificationChannel.WEBSOCKET:
                    await self._dispatch_websocket(alert, config, delivery)
                else:
                    # Queue other notifications for background processing
                    await self._queue_notification(alert, config, delivery)
            
            logger.info(f"Dispatched alert {alert.id} to {len(deliveries)} channels")
            
        except Exception as e:
            logger.error(f"Failed to dispatch alert {alert.id}: {e}")
        
        return deliveries
    
    async def _get_applicable_configs(self, alert: Alert) -> List[NotificationConfig]:
        """Get notification configurations applicable to this alert"""
        applicable_configs = []
        
        for config in self.notification_configs.values():
            if not config.enabled:
                continue
            
            # Check severity filter
            if (config.severity_filter and 
                alert.severity not in config.severity_filter):
                continue
            
            # Check category filter
            if (config.category_filter and 
                alert.category not in config.category_filter):
                continue
            
            # Check tag filters
            if config.tag_filters:
                match = True
                for tag_key, tag_value in config.tag_filters.items():
                    if alert.tags.get(tag_key) != tag_value:
                        match = False
                        break
                if not match:
                    continue
            
            applicable_configs.append(config)
        
        return applicable_configs
    
    async def _dispatch_websocket(self, alert: Alert, config: NotificationConfig, 
                                delivery: NotificationDelivery):
        """Dispatch alert via WebSocket"""
        try:
            # Broadcast to WebSocket connections
            await self.websocket_manager.broadcast_alert(alert)
            
            # Update delivery status
            delivery.status = "sent"
            delivery.sent_at = datetime.utcnow()
            delivery.delivered_at = datetime.utcnow()
            
            logger.info(f"WebSocket notification sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"WebSocket notification failed for alert {alert.id}: {e}")
            delivery.status = "failed"
            delivery.failed_at = datetime.utcnow()
            delivery.error_message = str(e)
    
    async def _queue_notification(self, alert: Alert, config: NotificationConfig,
                                delivery: NotificationDelivery):
        """Queue notification for background processing"""
        context = DeliveryContext(
            alert=alert,
            config=config,
            template=config.template
        )
        
        # Select delivery function based on channel
        if config.channel == NotificationChannel.EMAIL:
            delivery_fn = self.email_notifier.send_notification
        elif config.channel == NotificationChannel.WEBHOOK:
            delivery_fn = self.webhook_notifier.send_notification
        elif config.channel == NotificationChannel.SLACK:
            delivery_fn = self.slack_notifier.send_notification
        else:
            logger.error(f"Unsupported notification channel: {config.channel}")
            delivery.status = "failed"
            delivery.error_message = f"Unsupported channel: {config.channel}"
            return
        
        # Enqueue with wrapped delivery function
        async def wrapped_delivery(ctx: DeliveryContext) -> bool:
            try:
                # Update delivery status
                delivery.status = "pending"
                
                # Attempt delivery
                success = await delivery_fn(ctx)
                
                # Update delivery record
                if success:
                    delivery.status = "sent"
                    delivery.sent_at = datetime.utcnow()
                    delivery.delivered_at = datetime.utcnow()
                else:
                    delivery.status = "failed"
                    delivery.failed_at = datetime.utcnow()
                    delivery.error_message = "Delivery function returned False"
                
                return success
                
            except Exception as e:
                delivery.status = "failed"
                delivery.failed_at = datetime.utcnow()
                delivery.error_message = str(e)
                return False
            finally:
                # Move to history and remove from active
                self.delivery_history.append(delivery.dict())
                if delivery.id in self.active_deliveries:
                    del self.active_deliveries[delivery.id]
        
        # Calculate priority based on severity
        priority = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3,
            'info': 4
        }.get(alert.severity.value, 5)
        
        await self.queue.enqueue(wrapped_delivery, context, priority)
    
    def _generate_subject(self, alert: Alert, config: NotificationConfig) -> str:
        """Generate notification subject"""
        if config.template and config.template.subject_template:
            return config.template.subject_template.format(alert=alert)
        
        return f"[{alert.severity.value.upper()}] {alert.title}"
    
    def _generate_body(self, alert: Alert, config: NotificationConfig) -> str:
        """Generate notification body"""
        if config.template and config.template.body_template:
            return config.template.body_template.format(alert=alert)
        
        return f"""
Alert: {alert.title}
Severity: {alert.severity.value.upper()}
Description: {alert.description}
Triggered: {alert.triggered_at}
Alert ID: {alert.id}
        """.strip()
    
    def _get_recipients(self, config: NotificationConfig) -> List[str]:
        """Get recipients for notification"""
        if config.channel == NotificationChannel.EMAIL:
            return config.email_addresses
        elif config.channel == NotificationChannel.SLACK and config.slack_channel:
            return [config.slack_channel]
        else:
            return []
    
    # Public API methods
    
    def add_websocket_connection(self, connection: Any, user_id: str,
                               severities: Optional[List[AlertSeverity]] = None):
        """Add WebSocket connection for real-time alerts"""
        self.websocket_manager.add_connection(connection, user_id, severities)
    
    def remove_websocket_connection(self, connection: Any):
        """Remove WebSocket connection"""
        self.websocket_manager.remove_connection(connection)
    
    async def add_notification_config(self, config: NotificationConfig) -> bool:
        """Add notification configuration"""
        try:
            self.notification_configs[config.id] = config
            
            # Cache the config
            if self.cache_manager:
                cache_key = f"notification_config:{config.id}"
                await self.cache_manager.set(cache_key, config.dict(), ttl=3600)
            
            logger.info(f"Added notification config: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add notification config: {e}")
            return False
    
    async def remove_notification_config(self, config_id: UUID) -> bool:
        """Remove notification configuration"""
        try:
            if config_id in self.notification_configs:
                config = self.notification_configs[config_id]
                del self.notification_configs[config_id]
                
                # Remove from cache
                if self.cache_manager:
                    cache_key = f"notification_config:{config_id}"
                    await self.cache_manager.delete(cache_key)
                
                logger.info(f"Removed notification config: {config.name}")
                return True
            
            logger.warning(f"Notification config {config_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove notification config: {e}")
            return False
    
    def get_delivery_metrics(self) -> Dict[str, Any]:
        """Get notification delivery metrics"""
        queue_metrics = self.queue.get_metrics()
        websocket_stats = self.websocket_manager.get_connection_stats()
        
        # Calculate delivery success rates by channel
        channel_stats = defaultdict(lambda: {'sent': 0, 'failed': 0})
        
        for delivery_dict in self.delivery_history:
            channel = delivery_dict['channel']
            status = delivery_dict['status']
            
            if status == 'sent':
                channel_stats[channel]['sent'] += 1
            elif status == 'failed':
                channel_stats[channel]['failed'] += 1
        
        return {
            'queue': queue_metrics,
            'websocket': websocket_stats,
            'channels': dict(channel_stats),
            'active_deliveries': len(self.active_deliveries),
            'total_deliveries': len(self.delivery_history),
            'configurations': len(self.notification_configs)
        }
    
    def get_notification_configs(self) -> List[NotificationConfig]:
        """Get all notification configurations"""
        return list(self.notification_configs.values())


# Global notification dispatcher instance
_notification_dispatcher: Optional[NotificationDispatcher] = None


async def get_notification_dispatcher() -> NotificationDispatcher:
    """Get the global notification dispatcher instance"""
    global _notification_dispatcher
    
    if _notification_dispatcher is None:
        _notification_dispatcher = NotificationDispatcher()
        await _notification_dispatcher.initialize()
    
    return _notification_dispatcher


async def initialize_notification_dispatcher(max_workers: int = 5, 
                                           queue_size: int = 1000) -> NotificationDispatcher:
    """Initialize the global notification dispatcher"""
    global _notification_dispatcher
    
    if _notification_dispatcher is not None:
        await _notification_dispatcher.shutdown()
    
    _notification_dispatcher = NotificationDispatcher(max_workers, queue_size)
    await _notification_dispatcher.initialize()
    
    return _notification_dispatcher


async def shutdown_notification_dispatcher():
    """Shutdown the global notification dispatcher"""
    global _notification_dispatcher
    
    if _notification_dispatcher is not None:
        await _notification_dispatcher.shutdown()
        _notification_dispatcher = None


# Export main classes and functions
__all__ = [
    'NotificationDispatcher',
    'WebSocketManager',
    'EmailNotifier',
    'WebhookNotifier', 
    'SlackNotifier',
    'NotificationQueue',
    'DeliveryContext',
    'get_notification_dispatcher',
    'initialize_notification_dispatcher',
    'shutdown_notification_dispatcher'
] 