#!/bin/bash
# monitoring/resource-monitor.sh
# Monitor container resource usage and security metrics

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ALERT_MEMORY_THRESHOLD=80  # Alert if memory usage > 80%
ALERT_CPU_THRESHOLD=80     # Alert if CPU usage > 80%
LOG_FILE="/tmp/resource-monitor.log"

echo -e "${BLUE}🔍 GraphMemory-IDE Resource Monitor${NC}"
echo "=================================================="
echo "Timestamp: $(date)"
echo ""

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to format bytes to human readable
format_bytes() {
    local bytes=$1
    if [ "$bytes" -ge 1073741824 ]; then
        echo "$(echo "scale=2; $bytes/1073741824" | bc)GB"
    elif [ "$bytes" -ge 1048576 ]; then
        echo "$(echo "scale=2; $bytes/1048576" | bc)MB"
    elif [ "$bytes" -ge 1024 ]; then
        echo "$(echo "scale=2; $bytes/1024" | bc)KB"
    else
        echo "${bytes}B"
    fi
}

# Check Docker availability
if ! command_exists docker; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker daemon not running${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker daemon is running${NC}"
echo ""

# Container Resource Usage
echo -e "${BLUE}📊 Container Resource Usage${NC}"
echo "=============================="

# Check if containers are running
CONTAINERS=$(docker ps --format "{{.Names}}" | grep -E "(mcp-server|kestra)" || true)

if [ -z "$CONTAINERS" ]; then
    echo -e "${YELLOW}⚠️  No GraphMemory-IDE containers running${NC}"
else
    # Get detailed stats
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}" | \
    while IFS= read -r line; do
        if [[ "$line" == *"CONTAINER"* ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ "$line" == *"mcp-server"* ]] || [[ "$line" == *"kestra"* ]]; then
            # Extract memory percentage
            MEM_PERC=$(echo "$line" | awk '{print $4}' | sed 's/%//')
            CPU_PERC=$(echo "$line" | awk '{print $2}' | sed 's/%//')
            
            # Check thresholds
            if (( $(echo "$MEM_PERC > $ALERT_MEMORY_THRESHOLD" | bc -l) )); then
                echo -e "${RED}$line${NC}"
                log_message "ALERT: High memory usage detected: $line"
            elif (( $(echo "$CPU_PERC > $ALERT_CPU_THRESHOLD" | bc -l) )); then
                echo -e "${YELLOW}$line${NC}"
                log_message "WARNING: High CPU usage detected: $line"
            else
                echo -e "${GREEN}$line${NC}"
            fi
        else
            echo "$line"
        fi
    done
fi

echo ""

# Container Security Status
echo -e "${BLUE}🔒 Container Security Status${NC}"
echo "============================="

for container in $CONTAINERS; do
    echo -e "${BLUE}Container: $container${NC}"
    
    # Check if running as root
    USER_ID=$(docker exec "$container" id -u 2>/dev/null || echo "unknown")
    if [ "$USER_ID" = "0" ]; then
        echo -e "  ${RED}❌ Running as root (UID: $USER_ID)${NC}"
        log_message "SECURITY: Container $container running as root"
    elif [ "$USER_ID" != "unknown" ]; then
        echo -e "  ${GREEN}✅ Running as non-root (UID: $USER_ID)${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Cannot determine user ID${NC}"
    fi
    
    # Check read-only filesystem
    RO_CHECK=$(docker inspect "$container" --format '{{.HostConfig.ReadonlyRootfs}}' 2>/dev/null || echo "false")
    if [ "$RO_CHECK" = "true" ]; then
        echo -e "  ${GREEN}✅ Read-only root filesystem${NC}"
    else
        echo -e "  ${RED}❌ Writable root filesystem${NC}"
        log_message "SECURITY: Container $container has writable root filesystem"
    fi
    
    # Check capabilities
    CAPS=$(docker inspect "$container" --format '{{.HostConfig.CapDrop}}' 2>/dev/null || echo "[]")
    if [[ "$CAPS" == *"ALL"* ]]; then
        echo -e "  ${GREEN}✅ All capabilities dropped${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Not all capabilities dropped${NC}"
        log_message "SECURITY: Container $container may have unnecessary capabilities"
    fi
    
    # Check seccomp profile
    SECCOMP=$(docker inspect "$container" --format '{{.HostConfig.SecurityOpt}}' 2>/dev/null || echo "[]")
    if [[ "$SECCOMP" == *"seccomp"* ]]; then
        echo -e "  ${GREEN}✅ Seccomp profile applied${NC}"
    else
        echo -e "  ${YELLOW}⚠️  No seccomp profile detected${NC}"
    fi
    
    echo ""
done

# OrbStack Resource Usage (if available)
if command_exists orb; then
    echo -e "${BLUE}🚀 OrbStack Resource Usage${NC}"
    echo "=========================="
    
    # Get OrbStack info
    ORB_INFO=$(orb info 2>/dev/null || echo "OrbStack info not available")
    if [[ "$ORB_INFO" != *"not available"* ]]; then
        echo "$ORB_INFO" | grep -E "(Memory|CPU|Disk)" || echo "Resource info not found"
    else
        echo -e "${YELLOW}⚠️  OrbStack info not available${NC}"
    fi
    echo ""
fi

# Volume Usage
echo -e "${BLUE}💾 Volume Usage${NC}"
echo "==============="

# Docker system df
echo "Docker System Usage:"
docker system df

echo ""
echo "Volume Details:"
docker volume ls --format "table {{.Driver}}\t{{.Name}}\t{{.Size}}" | \
while IFS= read -r line; do
    if [[ "$line" == *"DRIVER"* ]]; then
        echo -e "${BLUE}$line${NC}"
    elif [[ "$line" == *"kuzu-data"* ]] || [[ "$line" == *"kestra-data"* ]] || [[ "$line" == *"mcp-"* ]]; then
        echo -e "${GREEN}$line${NC}"
    else
        echo "$line"
    fi
done

echo ""

# Network Usage
echo -e "${BLUE}🌐 Network Status${NC}"
echo "=================="

# Check network connectivity
echo "Network Connectivity:"
if curl -s --max-time 5 http://localhost:8080/docs >/dev/null; then
    echo -e "  ${GREEN}✅ MCP Server (HTTP:8080) - Accessible${NC}"
else
    echo -e "  ${RED}❌ MCP Server (HTTP:8080) - Not accessible${NC}"
    log_message "ALERT: MCP Server HTTP endpoint not accessible"
fi

if command_exists openssl; then
    if timeout 5 openssl s_client -connect localhost:50051 -verify_return_error >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ MCP Server (mTLS:50051) - Accessible${NC}"
    else
        echo -e "  ${YELLOW}⚠️  MCP Server (mTLS:50051) - Not accessible (may be disabled)${NC}"
    fi
fi

if curl -s --max-time 5 http://localhost:8081/ >/dev/null; then
    echo -e "  ${GREEN}✅ Kestra (HTTP:8081) - Accessible${NC}"
else
    echo -e "  ${RED}❌ Kestra (HTTP:8081) - Not accessible${NC}"
    log_message "ALERT: Kestra endpoint not accessible"
fi

echo ""

# Process Information
echo -e "${BLUE}⚙️  Process Information${NC}"
echo "======================"

for container in $CONTAINERS; do
    echo -e "${BLUE}Container: $container${NC}"
    PROCESSES=$(docker exec "$container" ps aux 2>/dev/null | head -10 || echo "Cannot access process list")
    echo "$PROCESSES"
    echo ""
done

# Log Summary
echo -e "${BLUE}📝 Monitoring Summary${NC}"
echo "===================="
echo "Log file: $LOG_FILE"
echo "Last 5 log entries:"
if [ -f "$LOG_FILE" ]; then
    tail -5 "$LOG_FILE" | while IFS= read -r line; do
        if [[ "$line" == *"ALERT"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ "$line" == *"WARNING"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        else
            echo "$line"
        fi
    done
else
    echo "No log entries found"
fi

echo ""
echo -e "${GREEN}✅ Resource monitoring complete${NC}"
echo "Run with 'watch -n 30 ./monitoring/resource-monitor.sh' for continuous monitoring" 