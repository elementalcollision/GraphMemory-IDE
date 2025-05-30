local kp = (import 'kube-prometheus/main.libsonnet') +
           (import 'kube-prometheus/addons/anti-affinity.libsonnet') +
           (import 'kube-prometheus/addons/all-namespaces.libsonnet') + {
  values+:: {
    common+: {
      namespace: 'monitoring-production',
      ruleLabels: {
        role: 'alert-rules',
        prometheus: 'kube-prometheus',
        part_of: 'graphmemory-ide',
      },
    },
    
    // Prometheus configuration optimized for production
    prometheus+: {
      namespaces: ['graphmemory-production', 'graphmemory-staging', 'monitoring-production', 'kube-system', 'default'],
      retention: '30d',
      retentionSize: '100GB',
      replicas: 2,
      resources: {
        requests: {
          cpu: '500m',
          memory: '2Gi',
        },
        limits: {
          cpu: '2000m',
          memory: '8Gi',
        },
      },
      storage: {
        volumeClaimTemplate: {
          spec: {
            storageClassName: 'fast-ssd',
            accessModes: ['ReadWriteOnce'],
            resources: {
              requests: {
                storage: '200Gi',
              },
            },
          },
        },
      },
      externalLabels: {
        cluster: 'graphmemory-production',
        environment: 'production',
        region: 'us-west-2',
      },
      // Remote write configuration for long-term storage
      remoteWrite: [
        {
          url: 'https://prometheus-remote-write.monitoring.svc.cluster.local:9090/api/v1/write',
          queueConfig: {
            capacity: 2500,
            batchSendDeadline: '5s',
            maxSamplesPerSend: 1000,
          },
        },
      ],
      // Alerting configuration
      alerting: {
        alertmanagers: [
          {
            namespace: 'monitoring-production',
            name: 'alertmanager-main',
            port: 'web',
          },
        ],
      },
    },
    
    // Alertmanager configuration with PagerDuty/Slack integration
    alertmanager+: {
      replicas: 2,
      resources: {
        requests: {
          cpu: '100m',
          memory: '200Mi',
        },
        limits: {
          cpu: '500m',
          memory: '1Gi',
        },
      },
      storage: {
        volumeClaimTemplate: {
          spec: {
            storageClassName: 'standard',
            accessModes: ['ReadWriteOnce'],
            resources: {
              requests: {
                storage: '10Gi',
              },
            },
          },
        },
      },
      config: |||
        global:
          resolve_timeout: 5m
          slack_api_url: '$SLACK_API_URL'
          
        templates:
          - '/etc/alertmanager/config/*.tmpl'
          
        route:
          group_by: ['alertname', 'cluster', 'service']
          group_wait: 10s
          group_interval: 10s
          repeat_interval: 1h
          receiver: 'web.hook'
          routes:
          # Critical alerts go to PagerDuty
          - match:
              severity: critical
            receiver: 'pagerduty-critical'
            group_wait: 1s
            group_interval: 1s
            repeat_interval: 2m
          # High severity alerts go to Slack
          - match:
              severity: warning
            receiver: 'slack-warnings'
            group_wait: 30s
            group_interval: 5m
            repeat_interval: 12h
          # GraphMemory-IDE specific alerts
          - match:
              service: graphmemory
            receiver: 'graphmemory-alerts'
            group_wait: 10s
            repeat_interval: 1h
          # Watchdog alerts (silenced)
          - match:
              alertname: Watchdog
            receiver: 'null'
            
        receivers:
        - name: 'null'
        
        - name: 'web.hook'
          webhook_configs:
          - url: 'http://alertmanager-webhook:8080/webhook'
            
        - name: 'pagerduty-critical'
          pagerduty_configs:
          - service_key: '$PAGERDUTY_SERVICE_KEY'
            description: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
            details:
              cluster: '{{ .GroupLabels.cluster }}'
              environment: '{{ .GroupLabels.environment }}'
              firing: '{{ .Alerts.Firing | len }}'
              resolved: '{{ .Alerts.Resolved | len }}'
              
        - name: 'slack-warnings'
          slack_configs:
          - channel: '#alerts-warning'
            title: 'GraphMemory-IDE Alert'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
            send_resolved: true
            
        - name: 'graphmemory-alerts'
          slack_configs:
          - channel: '#graphmemory-alerts'
            title: 'GraphMemory-IDE Service Alert'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
            send_resolved: true
            actions:
            - type: button
              text: 'Runbook'
              url: '{{ (index .Alerts 0).Annotations.runbook_url }}'
            - type: button
              text: 'Query'
              url: '{{ (index .Alerts 0).GeneratorURL }}'
        
        inhibit_rules:
        - source_match:
            severity: 'critical'
          target_match:
            severity: 'warning'
          equal: ['alertname', 'cluster', 'service']
      |||,
    },
    
    // Grafana configuration with custom dashboards
    grafana+: {
      resources: {
        requests: {
          cpu: '200m',
          memory: '512Mi',
        },
        limits: {
          cpu: '1000m',
          memory: '2Gi',
        },
      },
      config: {
        sections: {
          'auth.anonymous': {
            enabled: false,
          },
          security: {
            admin_user: 'admin',
            admin_password: '$GRAFANA_ADMIN_PASSWORD',
            secret_key: '$GRAFANA_SECRET_KEY',
          },
          server: {
            root_url: 'https://grafana.graphmemory.dev',
            serve_from_sub_path: false,
          },
          database: {
            type: 'postgres',
            host: 'postgres.monitoring.svc.cluster.local:5432',
            name: 'grafana',
            user: 'grafana',
            password: '$GRAFANA_DB_PASSWORD',
          },
          'auth.oauth': {
            enabled: true,
            name: 'OAuth',
            allow_sign_up: true,
            client_id: '$OAUTH_CLIENT_ID',
            client_secret: '$OAUTH_CLIENT_SECRET',
            scopes: 'openid profile email',
            auth_url: 'https://auth.graphmemory.dev/oauth/authorize',
            token_url: 'https://auth.graphmemory.dev/oauth/token',
            api_url: 'https://auth.graphmemory.dev/oauth/userinfo',
          },
          smtp: {
            enabled: true,
            host: 'smtp.gmail.com:587',
            user: '$SMTP_USER',
            password: '$SMTP_PASSWORD',
            from_address: 'alerts@graphmemory.dev',
            from_name: 'GraphMemory-IDE Monitoring',
          },
          alerting: {
            enabled: true,
            execute_alerts: true,
          },
          'unified_alerting': {
            enabled: true,
          },
        },
      },
      dashboards+:: {
        'graphmemory-overview.json': (import 'dashboards/graphmemory-overview.json'),
        'graphmemory-performance.json': (import 'dashboards/graphmemory-performance.json'),
        'graphmemory-memory-analytics.json': (import 'dashboards/graphmemory-memory-analytics.json'),
        'graphmemory-api-metrics.json': (import 'dashboards/graphmemory-api-metrics.json'),
        'graphmemory-infrastructure.json': (import 'dashboards/graphmemory-infrastructure.json'),
      },
    },
    
    // Node Exporter configuration
    nodeExporter+: {
      resources: {
        requests: {
          cpu: '100m',
          memory: '128Mi',
        },
        limits: {
          cpu: '200m',
          memory: '256Mi',
        },
      },
    },
    
    // Kube State Metrics configuration
    kubeStateMetrics+: {
      resources: {
        requests: {
          cpu: '100m',
          memory: '150Mi',
        },
        limits: {
          cpu: '500m',
          memory: '512Mi',
        },
      },
      // Increase resource allocation for large clusters
      baseCPU: '150m',
      cpuPerNode: '3m',
      baseMemory: '200Mi',
      memoryPerNode: '40Mi',
    },
    
    // Prometheus Operator configuration
    prometheusOperator+: {
      resources: {
        requests: {
          cpu: '100m',
          memory: '128Mi',
        },
        limits: {
          cpu: '500m',
          memory: '512Mi',
        },
      },
    },
  },
  
  // Custom PrometheusRules for GraphMemory-IDE
  kubePrometheus+: {
    prometheusRule+: {
      spec+: {
        groups+: [
          {
            name: 'graphmemory-ide.rules',
            interval: '30s',
            rules: [
              // SLI: API Success Rate
              {
                record: 'graphmemory:api_success_rate',
                expr: |||
                  sum(rate(http_requests_total{job="fastapi-backend", status!~"5.."}[5m])) /
                  sum(rate(http_requests_total{job="fastapi-backend"}[5m]))
                |||,
              },
              // SLI: API Response Time P95
              {
                record: 'graphmemory:api_response_time_p95',
                expr: |||
                  histogram_quantile(0.95,
                    sum(rate(http_request_duration_seconds_bucket{job="fastapi-backend"}[5m])) by (le)
                  )
                |||,
              },
              // SLI: Memory Operations Success Rate
              {
                record: 'graphmemory:memory_operations_success_rate',
                expr: |||
                  sum(rate(memory_operations_total{job="fastapi-backend", status="success"}[5m])) /
                  sum(rate(memory_operations_total{job="fastapi-backend"}[5m]))
                |||,
              },
              // SLI: Database Connection Health
              {
                record: 'graphmemory:database_health',
                expr: |||
                  sum(up{job="postgres-exporter"}) /
                  count(up{job="postgres-exporter"})
                |||,
              },
              // Application availability
              {
                record: 'graphmemory:application_availability',
                expr: |||
                  sum(up{job=~"fastapi-backend|streamlit-dashboard"}) /
                  count(up{job=~"fastapi-backend|streamlit-dashboard"})
                |||,
              },
            ],
          },
          {
            name: 'graphmemory-ide.alerts',
            rules: [
              // Critical: Application Down
              {
                alert: 'GraphMemoryApplicationDown',
                expr: 'graphmemory:application_availability < 0.5',
                'for': '1m',
                labels: {
                  severity: 'critical',
                  service: 'graphmemory',
                },
                annotations: {
                  summary: 'GraphMemory-IDE application is down',
                  description: 'Less than 50% of GraphMemory-IDE application instances are running',
                  runbook_url: 'https://docs.graphmemory.dev/runbooks/application-down',
                },
              },
              // Warning: High API Response Time
              {
                alert: 'GraphMemoryHighResponseTime',
                expr: 'graphmemory:api_response_time_p95 > 2',
                'for': '5m',
                labels: {
                  severity: 'warning',
                  service: 'graphmemory',
                },
                annotations: {
                  summary: 'GraphMemory-IDE API response time is high',
                  description: 'API P95 response time is {{ $value }}s, above 2s threshold',
                  runbook_url: 'https://docs.graphmemory.dev/runbooks/high-response-time',
                },
              },
              // Warning: Low API Success Rate
              {
                alert: 'GraphMemoryLowSuccessRate',
                expr: 'graphmemory:api_success_rate < 0.99',
                'for': '5m',
                labels: {
                  severity: 'warning',
                  service: 'graphmemory',
                },
                annotations: {
                  summary: 'GraphMemory-IDE API success rate is low',
                  description: 'API success rate is {{ $value }}, below 99% SLO',
                  runbook_url: 'https://docs.graphmemory.dev/runbooks/low-success-rate',
                },
              },
              // Critical: Database Unavailable
              {
                alert: 'GraphMemoryDatabaseDown',
                expr: 'graphmemory:database_health < 1',
                'for': '1m',
                labels: {
                  severity: 'critical',
                  service: 'graphmemory',
                },
                annotations: {
                  summary: 'GraphMemory-IDE database is unavailable',
                  description: 'Database connectivity issues detected',
                  runbook_url: 'https://docs.graphmemory.dev/runbooks/database-down',
                },
              },
              // Warning: Memory Operations Failing
              {
                alert: 'GraphMemoryOperationsFailing',
                expr: 'graphmemory:memory_operations_success_rate < 0.95',
                'for': '10m',
                labels: {
                  severity: 'warning',
                  service: 'graphmemory',
                },
                annotations: {
                  summary: 'GraphMemory-IDE memory operations failing',
                  description: 'Memory operations success rate is {{ $value }}, below 95% threshold',
                  runbook_url: 'https://docs.graphmemory.dev/runbooks/memory-operations-failing',
                },
              },
            ],
          },
        ],
      },
    },
  },
};

// Generate manifests for all components
{ ['00namespace-' + name]: kp.kubePrometheus[name] for name in std.objectFields(kp.kubePrometheus) } +
{ ['0prometheus-operator-' + name]: kp.prometheusOperator[name] for name in std.objectFields(kp.prometheusOperator) } +
{ ['node-exporter-' + name]: kp.nodeExporter[name] for name in std.objectFields(kp.nodeExporter) } +
{ ['kube-state-metrics-' + name]: kp.kubeStateMetrics[name] for name in std.objectFields(kp.kubeStateMetrics) } +
{ ['alertmanager-' + name]: kp.alertmanager[name] for name in std.objectFields(kp.alertmanager) } +
{ ['prometheus-' + name]: kp.prometheus[name] for name in std.objectFields(kp.prometheus) } +
{ ['grafana-' + name]: kp.grafana[name] for name in std.objectFields(kp.grafana) } 