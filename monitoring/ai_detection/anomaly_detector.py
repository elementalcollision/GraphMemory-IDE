"""
AI-Powered Anomaly Detection Engine for GraphMemory-IDE
Dynamic baseline learning with multi-model ensemble approach
"""

import logging
import asyncio
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pickle
import json

from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA

# Type checking imports for optional dependencies
if TYPE_CHECKING:
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        TensorFlowModel = Sequential
    except ImportError:
        TensorFlowModel = type(None)

# Optional TensorFlow import with robust fallback
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    HAS_TENSORFLOW = True
    TensorFlowModel = Sequential
except ImportError:
    tf = None
    Sequential = None
    LSTM = Dense = Dropout = None
    HAS_TENSORFLOW = False
    TensorFlowModel = type(None)

from prometheus_client.parser import text_string_to_metric_families
import httpx

logger = logging.getLogger(__name__)

@dataclass
class AnomalyAlert:
    """Anomaly detection alert data structure."""
    timestamp: datetime
    metric_name: str
    value: float
    baseline: float
    anomaly_score: float
    severity: str  # low, medium, high, critical
    confidence: float
    context: Dict[str, Any]
    model_type: str
    recommendations: List[str] = field(default_factory=list)

@dataclass
class ModelPerformance:
    """Model performance tracking."""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    last_trained: datetime
    training_samples: int

class GraphMemoryAnomalyPatterns:
    """GraphMemory-specific anomaly pattern definitions."""
    
    @staticmethod
    def detect_node_creation_anomalies(data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect unusual node creation patterns."""
        anomalies = []
        
        if 'graphmemory_node_operations_total' in data.columns:
            node_ops = data['graphmemory_node_operations_total']
            
            # Calculate rolling statistics
            rolling_mean = node_ops.rolling(window=20).mean()
            rolling_std = node_ops.rolling(window=20).std()
            
            # Detect spikes (> 3 standard deviations)
            spikes = node_ops > (rolling_mean + 3 * rolling_std)
            
            for idx in spikes[spikes].index:
                anomalies.append({
                    'type': 'node_creation_spike',
                    'timestamp': data.loc[idx, 'timestamp'],
                    'value': node_ops.loc[idx],
                    'baseline': rolling_mean.loc[idx],
                    'severity': 'high' if node_ops.loc[idx] > (rolling_mean.loc[idx] + 5 * rolling_std.loc[idx]) else 'medium',
                    'description': f"Unusual spike in node creation: {node_ops.loc[idx]:.0f} vs baseline {rolling_mean.loc[idx]:.0f}"
                })
        
        return anomalies
    
    @staticmethod
    def detect_search_anomalies(data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect unusual search patterns."""
        anomalies = []
        
        if 'graphmemory_search_operations_total' in data.columns:
            search_ops = data['graphmemory_search_operations_total']
            
            # Detect search floods (unusually high frequency)
            search_rate = search_ops.diff().fillna(0)
            rate_threshold = search_rate.quantile(0.95)
            
            floods = search_rate > rate_threshold * 2
            
            for idx in floods[floods].index:
                anomalies.append({
                    'type': 'search_flood',
                    'timestamp': data.loc[idx, 'timestamp'],
                    'value': search_rate.loc[idx],
                    'threshold': rate_threshold,
                    'severity': 'high',
                    'description': f"Search flood detected: {search_rate.loc[idx]:.0f} searches/sec vs normal {rate_threshold:.0f}"
                })
        
        return anomalies
    
    @staticmethod
    def detect_memory_growth_anomalies(data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect unusual memory growth patterns."""
        anomalies = []
        
        if 'graphmemory_total_nodes' in data.columns:
            node_count = data['graphmemory_total_nodes']
            
            # Calculate growth rate
            growth_rate = node_count.pct_change().fillna(0)
            
            # Detect exponential growth (> 10% per measurement)
            exponential_growth = growth_rate > 0.1
            
            for idx in exponential_growth[exponential_growth].index:
                anomalies.append({
                    'type': 'memory_growth_anomaly',
                    'timestamp': data.loc[idx, 'timestamp'],
                    'growth_rate': growth_rate.loc[idx],
                    'severity': 'critical' if growth_rate.loc[idx] > 0.2 else 'high',
                    'description': f"Exponential memory growth: {growth_rate.loc[idx]:.1%} increase"
                })
        
        return anomalies

class EnsembleAnomalyDetector:
    """
    Advanced ensemble anomaly detector using multiple ML models.
    
    Combines isolation forest, one-class SVM, and LSTM for comprehensive detection.
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        lstm_sequence_length: int = 50,
        model_weights: Optional[Dict[str, float]] = None
    ) -> None:
        self.contamination = contamination
        self.lstm_sequence_length = lstm_sequence_length
        self.model_weights = model_weights or {
            'isolation_forest': 0.5,
            'one_class_svm': 0.5,
            'lstm': 0.0 if not HAS_TENSORFLOW else 0.3
        }
        
        # Adjust weights if TensorFlow is not available
        if not HAS_TENSORFLOW:
            total_weight = self.model_weights['isolation_forest'] + self.model_weights['one_class_svm']
            self.model_weights['isolation_forest'] = 0.6
            self.model_weights['one_class_svm'] = 0.4
            self.model_weights['lstm'] = 0.0
            logger.warning("TensorFlow not available - LSTM model disabled, adjusting ensemble weights")
        
        # Initialize models with proper typing
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        self.one_class_svm = OneClassSVM(
            nu=contamination,
            kernel='rbf',
            gamma='scale'
        )
        
        self.lstm_model: Optional[TensorFlowModel] = None
        self.scaler = RobustScaler()
        
        # Training data storage with proper typing
        self.training_data: pd.DataFrame = pd.DataFrame()
        self.is_trained = False
        self.last_training: Optional[datetime] = None
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
    
    def _build_lstm_model(self, input_shape: Tuple[int, int]) -> Optional[TensorFlowModel]:
        """Build LSTM model for time series anomaly detection."""
        if not HAS_TENSORFLOW or tf is None:
            logger.warning("TensorFlow not available, LSTM model disabled")
            return None
            
        try:
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=input_shape),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            
            return model
        except Exception as e:
            logger.error(f"Failed to build LSTM model: {e}")
            return None
    
    def prepare_data(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare data for anomaly detection."""
        try:
            # Select numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            
            # Handle missing values
            data_clean = data[numeric_cols].fillna(method='ffill').fillna(0)
            
            # Scale data
            if not hasattr(self.scaler, 'scale_'):
                scaled_data = self.scaler.fit_transform(data_clean)
            else:
                scaled_data = self.scaler.transform(data_clean)
            
            return scaled_data
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return np.array([])
    
    def prepare_lstm_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for LSTM training."""
        X, y = [], []
        
        try:
            for i in range(self.lstm_sequence_length, len(data)):
                X.append(data[i-self.lstm_sequence_length:i])
                y.append(data[i])
            
            return np.array(X), np.array(y)
        except Exception as e:
            logger.error(f"Error preparing LSTM sequences: {e}")
            return np.array([]), np.array([])
    
    def train(self, data: pd.DataFrame, retrain: bool = False) -> None:
        """Train all models in the ensemble."""
        if self.is_trained and not retrain:
            logger.info("Models already trained. Use retrain=True to force retraining.")
            return
        
        logger.info("Training anomaly detection ensemble...")
        
        try:
            # Prepare data
            scaled_data = self.prepare_data(data)
            
            if len(scaled_data) == 0:
                logger.error("No data available for training")
                return
            
            # Train Isolation Forest
            logger.info("Training Isolation Forest...")
            self.isolation_forest.fit(scaled_data)
            
            # Train One-Class SVM
            logger.info("Training One-Class SVM...")
            self.one_class_svm.fit(scaled_data)
            
            # Train LSTM (if available)
            if HAS_TENSORFLOW and tf is not None and len(scaled_data) > self.lstm_sequence_length:
                logger.info("Training LSTM...")
                X_lstm, y_lstm = self.prepare_lstm_sequences(scaled_data)
                
                if len(X_lstm) > 0:
                    if self.lstm_model is None:
                        self.lstm_model = self._build_lstm_model((X_lstm.shape[1], X_lstm.shape[2]))
                    
                    if self.lstm_model is not None:
                        # Train with early stopping
                        early_stopping = tf.keras.callbacks.EarlyStopping(
                            monitor='loss',
                            patience=10,
                            restore_best_weights=True
                        )
                        
                        self.lstm_model.fit(
                            X_lstm, y_lstm,
                            epochs=50,
                            batch_size=32,
                            validation_split=0.2,
                            callbacks=[early_stopping],
                            verbose=0
                        )
            
            self.is_trained = True
            self.last_training = datetime.now()
            self.training_data = data.copy()
            
            logger.info("Ensemble training completed successfully")
            
        except Exception as e:
            logger.error(f"Error during training: {e}")
            raise
    
    def detect_anomalies(self, data: pd.DataFrame) -> List[AnomalyAlert]:
        """Detect anomalies using ensemble approach."""
        if not self.is_trained:
            raise ValueError("Models must be trained before detecting anomalies")
        
        alerts = []
        
        try:
            scaled_data = self.prepare_data(data)
            
            if len(scaled_data) == 0:
                logger.warning("No data available for anomaly detection")
                return alerts
            
            # Get predictions from each model
            if_scores = self.isolation_forest.decision_function(scaled_data)
            svm_scores = self.one_class_svm.decision_function(scaled_data)
            
            lstm_scores = np.zeros(len(scaled_data))
            if HAS_TENSORFLOW and self.lstm_model and len(scaled_data) > self.lstm_sequence_length:
                try:
                    X_lstm, _ = self.prepare_lstm_sequences(scaled_data)
                    if len(X_lstm) > 0:
                        lstm_predictions = self.lstm_model.predict(X_lstm, verbose=0)
                        lstm_reconstruction_error = np.mean(np.square(X_lstm[:, -1, :] - lstm_predictions), axis=1)
                        
                        # Pad with zeros for sequence length
                        lstm_scores = np.concatenate([
                            np.zeros(self.lstm_sequence_length),
                            lstm_reconstruction_error
                        ])
                except Exception as e:
                    logger.warning(f"LSTM prediction failed: {e}")
            
            # Combine scores using weighted average
            ensemble_scores = (
                self.model_weights['isolation_forest'] * self._normalize_scores(if_scores) +
                self.model_weights['one_class_svm'] * self._normalize_scores(svm_scores) +
                self.model_weights['lstm'] * self._normalize_scores(lstm_scores)
            )
            
            # Detect anomalies based on threshold
            threshold = float(np.percentile(ensemble_scores, (1 - self.contamination) * 100))
            anomaly_indices = np.where(ensemble_scores > threshold)[0]
            
            # Create alerts for anomalies
            for idx in anomaly_indices:
                try:
                    severity = self._calculate_severity(float(ensemble_scores[idx]), threshold)
                    confidence = min(float(ensemble_scores[idx]) / threshold, 1.0)
                    
                    alert = AnomalyAlert(
                        timestamp=data.iloc[idx]['timestamp'] if 'timestamp' in data.columns else datetime.now(),
                        metric_name='ensemble_anomaly',
                        value=float(ensemble_scores[idx]),
                        baseline=threshold,
                        anomaly_score=float(ensemble_scores[idx]),
                        severity=severity,
                        confidence=confidence,
                        context={
                            'isolation_forest_score': float(if_scores[idx]),
                            'svm_score': float(svm_scores[idx]),
                            'lstm_score': float(lstm_scores[idx]) if idx < len(lstm_scores) else 0.0,
                            'ensemble_score': float(ensemble_scores[idx])
                        },
                        model_type='ensemble',
                        recommendations=self._generate_recommendations(float(ensemble_scores[idx]), severity)
                    )
                    
                    alerts.append(alert)
                except Exception as e:
                    logger.error(f"Error creating alert for index {idx}: {e}")
        
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
        
        return alerts
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize scores to [0, 1] range."""
        if len(scores) == 0:
            return scores
        
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        if max_score == min_score:
            return np.ones_like(scores)
        
        return (scores - min_score) / (max_score - min_score)
    
    def _calculate_severity(self, score: float, threshold: float) -> str:
        """Calculate anomaly severity based on score."""
        ratio = score / threshold if threshold > 0 else 1.0
        
        if ratio >= 3.0:
            return 'critical'
        elif ratio >= 2.0:
            return 'high'
        elif ratio >= 1.5:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(self, score: float, severity: str) -> List[str]:
        """Generate actionable recommendations based on anomaly."""
        recommendations = []
        
        if severity == 'critical':
            recommendations.extend([
                "Immediate investigation required",
                "Consider scaling resources",
                "Check for security incidents",
                "Review recent deployments"
            ])
        elif severity == 'high':
            recommendations.extend([
                "Monitor closely for escalation",
                "Review system performance",
                "Check application logs"
            ])
        elif severity == 'medium':
            recommendations.extend([
                "Track for patterns",
                "Review if this becomes recurring"
            ])
        else:
            recommendations.append("Monitor for trend development")
        
        return recommendations

class RealTimeAnomalyMonitor:
    """
    Real-time anomaly monitoring system with streaming analysis.
    
    Continuously monitors Prometheus metrics and detects anomalies
    using the ensemble detector.
    """
    
    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        check_interval: int = 60,
        detector: Optional[EnsembleAnomalyDetector] = None
    ) -> None:
        self.prometheus_url = prometheus_url
        self.check_interval = check_interval
        self.detector = detector or EnsembleAnomalyDetector()
        
        # Monitoring state with proper typing
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task[None]] = None
        self.alert_handlers: List[Any] = []
        
        # Data storage with proper typing
        self.metric_history = pd.DataFrame()
        self.alert_history: List[AnomalyAlert] = []
        
        # Performance metrics
        self.metrics_processed = 0
        self.alerts_generated = 0
        self.last_check: Optional[datetime] = None
    
    async def start_monitoring(self) -> None:
        """Start real-time anomaly monitoring."""
        if self.is_running:
            logger.warning("Monitoring already running")
            return
        
        logger.info("Starting real-time anomaly monitoring...")
        self.is_running = True
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start training if detector is not trained
        if not self.detector.is_trained:
            await self._initial_training()
    
    async def stop_monitoring(self) -> None:
        """Stop real-time anomaly monitoring."""
        logger.info("Stopping anomaly monitoring...")
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Fetch metrics from Prometheus
                metrics_data = await self._fetch_metrics()
                
                if not metrics_data.empty:
                    # Detect anomalies
                    anomalies = self.detector.detect_anomalies(metrics_data)
                    
                    # Process alerts
                    for anomaly in anomalies:
                        await self._handle_anomaly(anomaly)
                    
                    # Update statistics
                    self.metrics_processed += len(metrics_data)
                    self.alerts_generated += len(anomalies)
                    self.last_check = datetime.now()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _fetch_metrics(self) -> pd.DataFrame:
        """Fetch metrics from Prometheus."""
        try:
            async with httpx.AsyncClient() as client:
                # Fetch GraphMemory-specific metrics
                metrics_queries = [
                    'graphmemory_node_operations_total',
                    'graphmemory_search_operations_total',
                    'graphmemory_total_nodes',
                    'graphmemory_active_sessions',
                    'graphmemory_http_request_duration_seconds',
                    'graphmemory_operation_duration_seconds'
                ]
                
                metrics_data = []
                timestamp = datetime.now()
                
                for query in metrics_queries:
                    response = await client.get(f"{self.prometheus_url}/api/v1/query", params={
                        'query': query
                    })
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data['status'] == 'success' and data['data']['result']:
                            for result in data['data']['result']:
                                value = float(result['value'][1])
                                metrics_data.append({
                                    'timestamp': timestamp,
                                    'metric': query,
                                    'value': value,
                                    'labels': result.get('metric', {})
                                })
                
                # Convert to DataFrame
                if metrics_data:
                    df = pd.DataFrame(metrics_data)
                    # Pivot to get metrics as columns
                    pivot_df = df.pivot_table(
                        index='timestamp',
                        columns='metric',
                        values='value',
                        aggfunc='mean'
                    ).reset_index()
                    
                    # Update history
                    self.metric_history = pd.concat([self.metric_history, pivot_df]).tail(1000)
                    
                    return pivot_df
                
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
        
        return pd.DataFrame()
    
    async def _initial_training(self) -> None:
        """Perform initial training with historical data."""
        logger.info("Performing initial training with historical data...")
        
        try:
            # Fetch historical data for training
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)  # Use last 7 days for training
            
            historical_data = await self._fetch_historical_metrics(start_time, end_time)
            
            if not historical_data.empty and len(historical_data) > 50:
                # Train detector in background thread
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    await loop.run_in_executor(
                        executor,
                        self.detector.train,
                        historical_data
                    )
                
                logger.info("Initial training completed successfully")
            else:
                logger.warning("Insufficient historical data for training")
                
        except Exception as e:
            logger.error(f"Error in initial training: {e}")
    
    async def _fetch_historical_metrics(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Fetch historical metrics for training."""
        # This would typically query Prometheus range endpoint
        # For now, return empty DataFrame
        return pd.DataFrame()
    
    async def _handle_anomaly(self, anomaly: AnomalyAlert) -> None:
        """Handle detected anomaly."""
        # Add to history
        self.alert_history.append(anomaly)
        
        # Keep history bounded
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                await handler(anomaly)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        logger.warning(f"Anomaly detected: {anomaly.metric_name} - {anomaly.severity}")
    
    def add_alert_handler(self, handler) -> None:
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'is_running': self.is_running,
            'metrics_processed': self.metrics_processed,
            'alerts_generated': self.alerts_generated,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'detector_trained': self.detector.is_trained,
            'alert_history_size': len(self.alert_history),
            'metric_history_size': len(self.metric_history),
            'tensorflow_available': HAS_TENSORFLOW
        }

# Global monitor instance
_anomaly_monitor: Optional[RealTimeAnomalyMonitor] = None

def get_anomaly_monitor() -> RealTimeAnomalyMonitor:
    """Get or create global anomaly monitor."""
    global _anomaly_monitor
    
    if _anomaly_monitor is None:
        _anomaly_monitor = RealTimeAnomalyMonitor()
    
    return _anomaly_monitor

async def initialize_anomaly_detection(
    prometheus_url: str = "http://localhost:9090",
    check_interval: int = 60
) -> RealTimeAnomalyMonitor:
    """Initialize and start anomaly detection system."""
    global _anomaly_monitor
    
    _anomaly_monitor = RealTimeAnomalyMonitor(
        prometheus_url=prometheus_url,
        check_interval=check_interval
    )
    
    await _anomaly_monitor.start_monitoring()
    
    logger.info("Anomaly detection system initialized and started")
    return _anomaly_monitor 