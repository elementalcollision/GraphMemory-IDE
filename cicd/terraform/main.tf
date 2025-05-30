terraform {
  required_version = ">= 1.6"
  
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
  
  backend "s3" {
    # Backend configuration will be provided via backend config files
    # terraform init -backend-config=environments/{env}/backend.conf
  }
}

# Provider configurations
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "GraphMemory-IDE"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner_team
      CostCenter  = var.cost_center
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Local values
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner_team
    CostCenter  = var.cost_center
  }
  
  # Availability zones
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# Data sources
data "aws_availability_zones" "available" {
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

data "aws_caller_identity" "current" {}

# Random password for database
resource "random_password" "database_password" {
  length  = 32
  special = true
}

# KMS key for encryption
resource "aws_kms_key" "graphmemory" {
  description             = "KMS key for GraphMemory-IDE ${var.environment} encryption"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  enable_key_rotation     = true
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-kms-key"
  })
}

resource "aws_kms_alias" "graphmemory" {
  name          = "alias/${local.name_prefix}-key"
  target_key_id = aws_kms_key.graphmemory.key_id
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  name_prefix = local.name_prefix
  cidr        = var.vpc_cidr
  azs         = local.azs
  
  # Public subnets for ALB
  public_subnets = [
    cidrsubnet(var.vpc_cidr, 8, 1),
    cidrsubnet(var.vpc_cidr, 8, 2),
    cidrsubnet(var.vpc_cidr, 8, 3)
  ]
  
  # Private subnets for EKS nodes
  private_subnets = [
    cidrsubnet(var.vpc_cidr, 8, 10),
    cidrsubnet(var.vpc_cidr, 8, 11),
    cidrsubnet(var.vpc_cidr, 8, 12)
  ]
  
  # Database subnets
  database_subnets = [
    cidrsubnet(var.vpc_cidr, 8, 20),
    cidrsubnet(var.vpc_cidr, 8, 21),
    cidrsubnet(var.vpc_cidr, 8, 22)
  ]
  
  enable_nat_gateway     = true
  single_nat_gateway     = var.environment != "production"
  enable_vpn_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true
  
  # Flow logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_retention_in_days           = var.environment == "production" ? 90 : 30
  
  tags = local.common_tags
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"
  
  cluster_name    = "${local.name_prefix}-cluster"
  cluster_version = var.kubernetes_version
  
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  
  # Cluster endpoint configuration
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = var.environment == "production" ? false : true
  cluster_endpoint_public_access_cidrs = var.environment == "production" ? [] : ["0.0.0.0/0"]
  
  # Encryption
  cluster_encryption_config = [{
    provider_key_arn = aws_kms_key.graphmemory.arn
    resources        = ["secrets"]
  }]
  
  # CloudWatch logging
  cluster_enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]
  cloudwatch_log_group_retention_in_days = var.environment == "production" ? 90 : 30
  
  # Node groups
  node_groups = {
    system = {
      desired_capacity = 2
      max_capacity     = 4
      min_capacity     = 2
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      
      k8s_labels = {
        role = "system"
      }
      
      taints = [{
        key    = "system"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
    
    application = {
      desired_capacity = var.environment == "production" ? 3 : 2
      max_capacity     = var.environment == "production" ? 10 : 5
      min_capacity     = var.environment == "production" ? 3 : 1
      
      instance_types = var.environment == "production" ? ["t3.large", "t3.xlarge"] : ["t3.medium"]
      capacity_type  = "SPOT"
      
      k8s_labels = {
        role = "application"
      }
    }
    
    monitoring = {
      desired_capacity = 1
      max_capacity     = 2
      min_capacity     = 1
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      
      k8s_labels = {
        role = "monitoring"
      }
    }
  }
  
  tags = local.common_tags
}

# RDS Database Module
module "rds" {
  source = "./modules/rds"
  
  identifier = "${local.name_prefix}-postgres"
  
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = var.environment == "production" ? "db.t3.medium" : "db.t3.micro"
  
  allocated_storage     = var.environment == "production" ? 100 : 20
  max_allocated_storage = var.environment == "production" ? 1000 : 100
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.graphmemory.arn
  
  db_name  = "graphmemory"
  username = "graphmemory"
  password = random_password.database_password.result
  
  vpc_security_group_ids = [module.vpc.database_security_group_id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  
  backup_retention_period = var.environment == "production" ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  deletion_protection = var.environment == "production"
  skip_final_snapshot = var.environment != "production"
  
  # Monitoring
  monitoring_interval = var.environment == "production" ? 60 : 0
  monitoring_role_arn = var.environment == "production" ? aws_iam_role.rds_enhanced_monitoring[0].arn : null
  
  # Performance Insights
  performance_insights_enabled = var.environment == "production"
  performance_insights_kms_key_id = var.environment == "production" ? aws_kms_key.graphmemory.arn : null
  
  tags = local.common_tags
}

# ElastiCache Redis Module
module "elasticache" {
  source = "./modules/elasticache"
  
  cluster_id = "${local.name_prefix}-redis"
  
  node_type           = var.environment == "production" ? "cache.t3.medium" : "cache.t3.micro"
  num_cache_nodes     = 1
  parameter_group_name = "default.redis7"
  port                = 6379
  
  subnet_group_name  = module.vpc.elasticache_subnet_group_name
  security_group_ids = [module.vpc.elasticache_security_group_id]
  
  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.database_password.result
  
  # Backups
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window         = "03:00-05:00"
  
  tags = local.common_tags
}

# S3 Buckets Module
module "s3" {
  source = "./modules/s3"
  
  name_prefix = local.name_prefix
  
  # Application data bucket
  create_data_bucket = true
  data_bucket_name   = "${local.name_prefix}-data"
  
  # Backup bucket
  create_backup_bucket = true
  backup_bucket_name   = "${local.name_prefix}-backups"
  
  # Assets bucket
  create_assets_bucket = true
  assets_bucket_name   = "${local.name_prefix}-assets"
  
  # Encryption
  kms_key_id = aws_kms_key.graphmemory.arn
  
  # Lifecycle policies
  enable_lifecycle_rules = true
  
  tags = local.common_tags
}

# Application Load Balancer Module
module "alb" {
  source = "./modules/alb"
  
  name_prefix = local.name_prefix
  
  vpc_id          = module.vpc.vpc_id
  public_subnets  = module.vpc.public_subnets
  security_groups = [module.vpc.alb_security_group_id]
  
  # SSL Certificate
  certificate_arn = var.ssl_certificate_arn
  
  # Default action
  default_action_type = "fixed-response"
  default_action_fixed_response = {
    content_type = "text/plain"
    message_body = "GraphMemory-IDE - Service Unavailable"
    status_code  = "503"
  }
  
  # Access logs
  enable_access_logs = true
  access_logs_bucket = module.s3.access_logs_bucket_id
  
  tags = local.common_tags
}

# IAM roles for enhanced monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.environment == "production" ? 1 : 0
  
  name = "${local.name_prefix}-rds-monitoring-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  count = var.environment == "production" ? 1 : 0
  
  role       = aws_iam_role.rds_enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Kubernetes namespaces
resource "kubernetes_namespace" "graphmemory" {
  metadata {
    name = "graphmemory-${var.environment}"
    
    labels = {
      "app.kubernetes.io/name"       = "graphmemory"
      "app.kubernetes.io/environment" = var.environment
      "app.kubernetes.io/managed-by"  = "terraform"
    }
    
    annotations = {
      "terraform.io/managed" = "true"
    }
  }
  
  depends_on = [module.eks]
}

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring-${var.environment}"
    
    labels = {
      "app.kubernetes.io/name"       = "monitoring"
      "app.kubernetes.io/environment" = var.environment
      "app.kubernetes.io/managed-by"  = "terraform"
    }
    
    annotations = {
      "terraform.io/managed" = "true"
    }
  }
  
  depends_on = [module.eks]
}

# Kubernetes secrets
resource "kubernetes_secret" "database_credentials" {
  metadata {
    name      = "database-credentials"
    namespace = kubernetes_namespace.graphmemory.metadata[0].name
  }
  
  type = "Opaque"
  
  data = {
    host     = module.rds.db_instance_endpoint
    port     = tostring(module.rds.db_instance_port)
    database = module.rds.db_instance_name
    username = module.rds.db_instance_username
    password = random_password.database_password.result
    url      = "postgresql://${module.rds.db_instance_username}:${random_password.database_password.result}@${module.rds.db_instance_endpoint}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  }
}

resource "kubernetes_secret" "redis_credentials" {
  metadata {
    name      = "redis-credentials"
    namespace = kubernetes_namespace.graphmemory.metadata[0].name
  }
  
  type = "Opaque"
  
  data = {
    host     = module.elasticache.cache_nodes[0].address
    port     = tostring(module.elasticache.cache_nodes[0].port)
    password = random_password.database_password.result
    url      = "redis://:${random_password.database_password.result}@${module.elasticache.cache_nodes[0].address}:${module.elasticache.cache_nodes[0].port}"
  }
} 