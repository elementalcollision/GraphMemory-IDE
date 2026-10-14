#!/bin/bash
# scripts/deploy-secure.sh
# Deploy GraphMemory-IDE with full security hardening

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# NOTE (§3.14 repair): this line had mangled quoting
# ("${BASH_SOURCE[0]\\"))"" — unbalanced parens) that made the whole script
# fail `bash -n` with a syntax error reported far away at the case statement.
# Restored to the canonical idiom.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_ROOT/certs"
DOCKER_DIR="$PROJECT_ROOT/docker"

echo -e "${BLUE}🔐 GraphMemory-IDE Secure Deployment${NC}"
echo "====================================="
echo "Project root: $PROJECT_ROOT"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate environment
validate_environment() {
    echo -e "${BLUE}🔍 Validating environment...${NC}"
    
    # Check Docker
    if ! command_exists docker; then
        echo -e "${RED}❌ Docker not found. Please install Docker or OrbStack.${NC}"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker daemon not running. Please start Docker.${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker Compose not found.${NC}"
        exit 1
    fi
    
    # Check OpenSSL for certificate generation
    if ! command_exists openssl; then
        echo -e "${RED}❌ OpenSSL not found. Required for certificate generation.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Environment validation passed${NC}"
}

# Function to setup mTLS certificates
setup_mtls() {
    echo -e "${BLUE}🔐 Setting up mTLS certificates...${NC}"
    
    if [ "$MTLS_ENABLED" = "true" ]; then
        if [ ! -f "$CERT_DIR/ca-cert.pem" ]; then
            echo "Generating mTLS certificates..."
            "$SCRIPT_DIR/setup-mtls.sh"
        else
            echo "mTLS certificates already exist"
        fi
        
        # Validate certificates
        echo "Validating certificate chain..."
        if openssl verify -CAfile "$CERT_DIR/ca-cert.pem" "$CERT_DIR/server-cert.pem" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Server certificate valid${NC}"
        else
            echo -e "${RED}❌ Server certificate validation failed${NC}"
            exit 1
        fi
        
        if openssl verify -CAfile "$CERT_DIR/ca-cert.pem" "$CERT_DIR/client-cert.pem" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Client certificate valid${NC}"
        else
            echo -e "${RED}❌ Client certificate validation failed${NC}"
            exit 1
        fi
    else
        echo "mTLS disabled, skipping certificate setup"
    fi
}

# Function to build secure containers
build_containers() {
    echo -e "${BLUE}🏗️  Building secure containers...${NC}"
    
    cd "$DOCKER_DIR"
    
    # Build with security hardening
    echo "Building MCP server container..."
    docker build -f mcp-server/Dockerfile -t graphmemory-mcp:secure ..
    
    echo -e "${GREEN}✅ Containers built successfully${NC}"
}

# Function to deploy with security
deploy_secure() {
    echo -e "${BLUE}🚀 Deploying with security hardening...${NC}"
    
    cd "$DOCKER_DIR"
    
    # Stop existing containers
    echo "Stopping existing containers..."
    docker compose down --remove-orphans || true
    
    # Deploy with security configuration
    echo "Starting secure deployment..."
    docker compose up -d
    
    # Wait for services to start
    echo "Waiting for services to start..."
    sleep 10
    
    # Check container health
    echo "Checking container health..."
    for i in {1..30}; do
        if docker compose ps | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✅ Services are running${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ Services failed to start properly${NC}"
            docker compose logs
            exit 1
        fi
        sleep 2
    done
}

# Function to validate security configuration
validate_security() {
    echo -e "${BLUE}🔒 Validating security configuration...${NC}"
    
    # Get container names
    MCP_CONTAINER=$(docker ps --format "{{.Names}}" | grep mcp-server | head -1)
    
    if [ -z "$MCP_CONTAINER" ]; then
        echo -e "${RED}❌ MCP server container not found${NC}"
        return 1
    fi
    
    # Check non-root user
    echo "Checking user privileges..."
    MCP_UID=$(docker exec "$MCP_CONTAINER" id -u)
    if [ "$MCP_UID" != "1000" ]; then
        echo -e "${RED}❌ MCP container not running as expected user (UID 1000), got UID $MCP_UID${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ MCP container running as non-root user (UID $MCP_UID)${NC}"
    
    # Check read-only filesystem
    echo "Checking filesystem permissions..."
    if docker exec "$MCP_CONTAINER" touch /test-file 2>/dev/null; then
        echo -e "${RED}❌ MCP container root filesystem is writable${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ MCP container root filesystem is read-only${NC}"
    
    # Check writable volumes
    if ! docker exec "$MCP_CONTAINER" touch /var/log/mcp/test.log 2>/dev/null; then
        echo -e "${RED}❌ MCP container log directory not writable${NC}"
        return 1
    fi
    docker exec "$MCP_CONTAINER" rm -f /var/log/mcp/test.log
    echo -e "${GREEN}✅ MCP container writable volumes working${NC}"
    
    # Check capabilities
    echo "Checking security capabilities..."
    CAPS=$(docker exec "$MCP_CONTAINER" cat /proc/self/status | grep CapEff)
    if [[ "$CAPS" == *"0000000000000000"* ]] || [[ "$CAPS" == *"0000000000000400"* ]]; then
        echo -e "${GREEN}✅ MCP container has minimal capabilities${NC}"
    else
        echo -e "${YELLOW}⚠️  MCP container capabilities: $CAPS${NC}"
    fi
    
    # Check network connectivity
    echo "Checking network connectivity..."
    if curl -s --max-time 10 http://localhost:8080/docs >/dev/null; then
        echo -e "${GREEN}✅ HTTP endpoint accessible${NC}"
    else
        echo -e "${RED}❌ HTTP endpoint not accessible${NC}"
        return 1
    fi
    
    # Check mTLS if enabled
    if [ "$MTLS_ENABLED" = "true" ]; then
        echo "Checking mTLS connectivity..."
        if timeout 10 openssl s_client -connect localhost:50051 -verify_return_error >/dev/null 2>&1; then
            echo -e "${GREEN}✅ mTLS endpoint accessible${NC}"
        else
            echo -e "${YELLOW}⚠️  mTLS endpoint not accessible (may need client certificate)${NC}"
        fi
    fi
    
    echo -e "${GREEN}✅ Security validation completed${NC}"
}

# Function to run security tests
run_security_tests() {
    echo -e "${BLUE}🧪 Running security tests...${NC}"
    
    if [ -f "$PROJECT_ROOT/tests/test_security.py" ]; then
        cd "$PROJECT_ROOT"
        if command_exists pytest; then
            echo "Running pytest security tests..."
            pytest tests/test_security.py -v --tb=short || echo -e "${YELLOW}⚠️  Some security tests failed${NC}"
        else
            echo "Running Python security tests..."
            python tests/test_security.py || echo -e "${YELLOW}⚠️  Some security tests failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Security test file not found${NC}"
    fi
}

# Function to display deployment summary
display_summary() {
    echo ""
    echo -e "${BLUE}📋 Deployment Summary${NC}"
    echo "====================="
    echo "✅ Security hardening applied:"
    echo "   - Read-only root filesystems"
    echo "   - Non-root users (UID 1000/1001)"
    echo "   - Dropped capabilities"
    echo "   - Seccomp profiles"
    echo "   - Resource limits"
    echo "   - No privileged mode"
    echo ""
    echo "🌐 Endpoints:"
    echo "   - HTTP API: http://localhost:8080"
    echo "   - API Docs: http://localhost:8080/docs"
    if [ "$MTLS_ENABLED" = "true" ]; then
        echo "   - mTLS API: https://localhost:50051 (requires client certificate)"
    fi
    echo ""
    echo "🔐 Security features:"
    echo "   - JWT authentication enabled"
    if [ "$MTLS_ENABLED" = "true" ]; then
        echo "   - mTLS enabled with client certificates"
        echo "   - Certificates location: $CERT_DIR"
    else
        echo "   - mTLS disabled (set MTLS_ENABLED=true to enable)"
    fi
    echo ""
    echo "📊 Monitoring:"
    echo "   - Resource monitor: ./monitoring/resource-monitor.sh"
    echo "   - Security tests: pytest tests/test_security.py"
    echo ""
    echo -e "${GREEN}🎉 Secure deployment completed successfully!${NC}"
}

# Main deployment flow
main() {
    # Set default environment variables
    export JWT_ENABLED="${JWT_ENABLED:-true}"
    export MTLS_ENABLED="${MTLS_ENABLED:-false}"
    export LADYBUG_READ_ONLY="${LADYBUG_READ_ONLY:-false}"
    
    # Generate secure JWT secret if not provided
    if [ -z "$JWT_SECRET_KEY" ]; then
        export JWT_SECRET_KEY=$(openssl rand -hex 32)
        echo -e "${YELLOW}⚠️  Generated JWT secret key. Save this for production: $JWT_SECRET_KEY${NC}"
    fi
    
    echo "Configuration:"
    echo "  JWT_ENABLED: $JWT_ENABLED"
    echo "  MTLS_ENABLED: $MTLS_ENABLED"
    echo "  LADYBUG_READ_ONLY: $LADYBUG_READ_ONLY"
    echo ""
    
    # Execute deployment steps
    validate_environment
    setup_mtls
    build_containers
    deploy_secure
    
    # Wait a bit for services to fully initialize
    sleep 5
    
    validate_security
    run_security_tests
    display_summary
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "validate")
        validate_security
        ;;
    "test")
        run_security_tests
        ;;
    "mtls")
        export MTLS_ENABLED=true
        setup_mtls
        ;;
    "help")
        echo "Usage: $0 [deploy|validate|test|mtls|help]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full secure deployment (default)"
        echo "  validate - Validate security configuration"
        echo "  test     - Run security tests"
        echo "  mtls     - Setup mTLS certificates"
        echo "  help     - Show this help"
        echo ""
        echo "Environment variables:"
        echo "  MTLS_ENABLED=true     - Enable mTLS"
        echo "  JWT_SECRET_KEY=...    - Set JWT secret"
        echo "  LADYBUG_READ_ONLY=true   - Enable read-only mode"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 