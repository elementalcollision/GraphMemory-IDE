# Hybrid CPython/Condon Deployment Strategy

This directory contains the comprehensive deployment strategy for the hybrid CPython/Condon architecture, including containerization, orchestration, service discovery, and production-ready deployment patterns.

## Architecture Overview

The hybrid architecture combines CPython services for general-purpose web applications with Condon-compiled services for performance-critical components:

### Service Types

#### CPython Services
- **Auth Service**: User authentication and authorization
- **Dashboard Service**: Web interface and user management
- **Streaming Service**: Real-time data streaming

#### Condon Services
- **Analytics Service**: High-performance data analytics
- **AI Detection Service**: Machine learning inference
- **Monitoring Service**: System monitoring and alerting

### Infrastructure Components

- **Kubernetes**: Container orchestration
- **Istio**: Service mesh for traffic management
- **OpenTelemetry**: Observability and monitoring
- **Horizontal Pod Autoscaler**: Automatic scaling
- **Network Policies**: Security and traffic control

## Directory Structure

```
deploy/
├── hybrid-deployment-strategy.yaml    # Complete deployment configuration
├── scripts/
│   ├── deploy-hybrid.sh              # Deployment script
│   └── disaster-recovery.sh          # Disaster recovery script
├── docker/
│   ├── cpython-service.Dockerfile    # CPython service containerization
│   └── condon-service.Dockerfile     # Condon service containerization
└── README.md                         # This documentation
```

## Prerequisites

### Required Tools
- `kubectl` - Kubernetes command-line tool
- `docker` - Container runtime
- `istioctl` - Istio command-line tool (optional)

### Required Infrastructure
- Kubernetes cluster (v1.24+)
- Istio service mesh
- Container registry
- Monitoring stack (Prometheus, Grafana, Jaeger)

### Required Permissions
- Cluster admin access for initial setup
- Namespace admin access for deployment

## Quick Start

### 1. Deploy the Hybrid Architecture

```bash
# Navigate to deployment directory
cd deploy

# Deploy the complete hybrid architecture
./scripts/deploy-hybrid.sh deploy
```

### 2. Verify Deployment

```bash
# Check deployment status
./scripts/deploy-hybrid.sh verify

# Perform health checks
./scripts/deploy-hybrid.sh health
```

### 3. Monitor Services

```bash
# Check service status
kubectl get pods -n graphmemory

# View service logs
kubectl logs -f deployment/auth-service -n graphmemory
kubectl logs -f deployment/analytics-service -n graphmemory
```

## Deployment Configuration

### Service Configuration

Each service is configured with:

- **Resource Limits**: CPU and memory constraints
- **Health Checks**: Liveness and readiness probes
- **Scaling**: Horizontal Pod Autoscaler configuration
- **Security**: Network policies and RBAC
- **Monitoring**: OpenTelemetry instrumentation

### Traffic Management

- **Istio Virtual Service**: Routes external traffic to appropriate services
- **Destination Rules**: Configure load balancing and circuit breakers
- **Gateway**: External traffic ingress point

### Observability

- **OpenTelemetry Collector**: Centralized telemetry collection
- **Metrics**: Prometheus integration
- **Traces**: Jaeger distributed tracing
- **Logs**: Centralized logging

## Containerization Strategy

### CPython Services

```dockerfile
# Multi-stage build with security hardening
FROM python:3.11-slim as builder
# ... build dependencies

FROM python:3.11-slim as production
# ... runtime configuration
USER app  # Non-root user
```

### Condon Services

```dockerfile
# Multi-stage build with performance optimization
FROM condaforge/mambaforge:latest as builder
# ... Condon compilation

FROM debian:bullseye-slim as production
# ... minimal runtime
```

## Scaling and Performance

### Horizontal Scaling
- **CPython Services**: 2-10 replicas based on CPU/memory usage
- **Condon Services**: 2-6 replicas based on computational load
- **Auto-scaling**: Triggered at 70% CPU or 80% memory utilization

### Performance Optimization
- **Resource Requests**: Guaranteed resource allocation
- **Resource Limits**: Prevent resource exhaustion
- **Connection Pooling**: Optimized for service mesh
- **Circuit Breakers**: Automatic failure detection

## Security Configuration

### Network Policies
- **Ingress**: Allow traffic from ingress controllers
- **Egress**: Restrict outbound traffic to required services
- **Service-to-Service**: Internal communication policies

### Secrets Management
- **Database Credentials**: External secret management
- **JWT Secrets**: Secure token signing
- **API Keys**: Encrypted storage

## Monitoring and Observability

### Metrics Collection
```yaml
# OpenTelemetry configuration
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
```

### Service Instrumentation
```python
# CPython service instrumentation
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracing and metrics
trace.set_tracer_provider(TracerProvider())
metrics.set_meter_provider(MeterProvider())
```

## Disaster Recovery

### Automated Recovery
```bash
# Start disaster recovery
./scripts/disaster-recovery.sh recover

# Check system health
./scripts/disaster-recovery.sh check

# Scale services for recovery
./scripts/disaster-recovery.sh scale
```

### Recovery Procedures
1. **Health Check**: Verify cluster and service status
2. **Service Restart**: Restart failed services
3. **Scaling**: Scale up healthy services
4. **Backup Restoration**: Restore from latest backup if needed
5. **Verification**: Confirm recovery success

## Troubleshooting

### Common Issues

#### Service Not Starting
```bash
# Check pod status
kubectl get pods -n graphmemory

# View pod logs
kubectl logs <pod-name> -n graphmemory

# Check events
kubectl get events -n graphmemory --sort-by='.lastTimestamp'
```

#### Service Mesh Issues
```bash
# Check Istio proxy status
kubectl get pods -n graphmemory -l istio.io/rev

# View proxy logs
kubectl logs <pod-name> -c istio-proxy -n graphmemory
```

#### Scaling Issues
```bash
# Check HPA status
kubectl get hpa -n graphmemory

# View HPA events
kubectl describe hpa <hpa-name> -n graphmemory
```

### Performance Issues

#### High Resource Usage
```bash
# Check resource usage
kubectl top pods -n graphmemory

# View resource metrics
kubectl get pods -n graphmemory -o custom-columns=NAME:.metadata.name,CPU:.spec.containers[0].resources.requests.cpu,MEMORY:.spec.containers[0].resources.requests.memory
```

#### Slow Response Times
```bash
# Check service endpoints
kubectl get endpoints -n graphmemory

# Test service connectivity
kubectl exec -it <pod-name> -n graphmemory -- curl <service-url>
```

## Maintenance

### Regular Maintenance Tasks

#### Backup Creation
```bash
# Create deployment backup
kubectl get deployments -n graphmemory -o yaml > backups/deployments_$(date +%Y%m%d_%H%M%S).yaml
```

#### Log Rotation
```bash
# Configure log rotation in Kubernetes
kubectl patch deployment <deployment-name> -n graphmemory -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","env":[{"name":"LOG_LEVEL","value":"INFO"}]}]}}}}'
```

#### Security Updates
```bash
# Update container images
kubectl set image deployment/<deployment-name> <container-name>=<new-image> -n graphmemory
```

### Monitoring Alerts

Configure alerts for:
- **Service Availability**: < 99.9% uptime
- **Response Time**: > 100ms average
- **Error Rate**: > 0.1% error rate
- **Resource Usage**: > 80% utilization

## Best Practices

### Deployment
1. **Blue-Green Deployment**: Zero-downtime deployments
2. **Canary Releases**: Gradual traffic shifting
3. **Rollback Strategy**: Quick rollback procedures
4. **Health Checks**: Comprehensive monitoring

### Security
1. **Principle of Least Privilege**: Minimal required permissions
2. **Network Segmentation**: Isolated service communication
3. **Secret Management**: External secret storage
4. **Regular Updates**: Security patch management

### Performance
1. **Resource Planning**: Proper resource allocation
2. **Auto-scaling**: Dynamic resource management
3. **Caching**: Optimize data access patterns
4. **Monitoring**: Proactive performance tracking

## Support

### Getting Help
- **Documentation**: Check this README and inline comments
- **Logs**: Review service and system logs
- **Metrics**: Monitor performance metrics
- **Community**: Reach out to the development team

### Emergency Contacts
- **DevOps Team**: For infrastructure issues
- **Architecture Team**: For design and scaling issues
- **Security Team**: For security-related concerns

## Changelog

### Version 1.0.0
- Initial hybrid deployment strategy
- CPython and Condon service containerization
- Istio service mesh integration
- OpenTelemetry observability
- Automated disaster recovery
- Comprehensive monitoring and alerting

---

**Note**: This deployment strategy is designed for production use and includes comprehensive error handling, monitoring, and disaster recovery procedures. Always test in a staging environment before deploying to production. 