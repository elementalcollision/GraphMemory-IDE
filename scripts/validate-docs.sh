#!/bin/bash

# Documentation Validation Script
# Validates that all documentation links work and services are accessible

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}GraphMemory-IDE Documentation Validation${NC}"
echo "=========================================="
echo

# Function to check if file exists
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file (NOT FOUND)"
        return 1
    fi
}

# Function to check if directory exists
check_directory() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $description: $dir"
        return 0
    else
        echo -e "${RED}✗${NC} $description: $dir (NOT FOUND)"
        return 1
    fi
}

# Function to check if service is running
check_service() {
    local url=$1
    local service=$2
    
    if curl -s -f "$url" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service: $url"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $service: $url (NOT ACCESSIBLE - may not be running)"
        return 1
    fi
}

# Function to validate API endpoint
validate_api() {
    local endpoint=$1
    local method=${2:-GET}
    local description=$3
    
    if [ "$method" = "GET" ]; then
        if curl -s -f "http://localhost:8080$endpoint" >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} API $description: $method $endpoint"
            return 0
        else
            echo -e "${YELLOW}⚠${NC} API $description: $method $endpoint (NOT ACCESSIBLE)"
            return 1
        fi
    else
        echo -e "${BLUE}ℹ${NC} API $description: $method $endpoint (requires manual testing)"
        return 0
    fi
}

echo -e "${BLUE}1. Core Documentation Files${NC}"
echo "----------------------------"

# Check main documentation files
check_file "README.md" "Main README"
check_file "DOCUMENTATION.md" "Documentation Index"
check_file "PRD - GraphMemory-IDE - Combined.md" "Product Requirements"

echo

echo -e "${BLUE}2. Server Documentation${NC}"
echo "------------------------"

# Check server documentation
check_file "server/README.md" "Server Documentation"
check_file "server/main.py" "Server Main Module"
check_file "server/models.py" "Server Models"
check_file "server/test_main.py" "Server Tests"

echo

echo -e "${BLUE}3. Docker Documentation${NC}"
echo "------------------------"

# Check Docker documentation
check_file "docker/README.md" "Docker Documentation"
check_file "docker/docker-compose.yml" "Docker Compose Config"
check_file "docker/mcp-server/Dockerfile" "MCP Server Dockerfile"
check_file "docker/backup-volumes.sh" "Backup Script"
check_file "docker/VOLUME_MANAGEMENT.md" "Volume Management Guide"
check_file "docker/VOLUME_RESEARCH_SUMMARY.md" "Volume Research Summary"

echo

echo -e "${BLUE}4. Configuration Files${NC}"
echo "-----------------------"

# Check configuration files
check_file "requirements.txt" "Python Requirements (locked)"
check_file "requirements.in" "Python Requirements (direct)"
check_file "package.json" "Node.js Package Config"
check_file "kestra.yml" "Kestra Configuration"

echo

echo -e "${BLUE}5. Project Structure${NC}"
echo "---------------------"

# Check project directories
check_file ".context/README.md" "Context Framework Documentation"
check_file ".context/AI_INSTRUCTIONS.md" "AI Framework Instructions"
check_directory "data" "Database Directory"

echo

echo -e "${BLUE}6. Service Accessibility${NC}"
echo "---------------------------"

# Check if services are running
check_service "http://localhost:8080/docs" "MCP Server (Swagger UI)"
check_service "http://localhost:8080/openapi.json" "MCP Server (OpenAPI)"
check_service "http://localhost:8081/" "Kestra CI/CD"

echo

echo -e "${BLUE}7. API Endpoints${NC}"
echo "-----------------"

# Validate API endpoints
validate_api "/docs" "GET" "Documentation"
validate_api "/openapi.json" "GET" "OpenAPI Spec"
validate_api "/telemetry/list" "GET" "List Telemetry"
validate_api "/telemetry/query" "GET" "Query Telemetry"
validate_api "/telemetry/ingest" "POST" "Ingest Telemetry"
validate_api "/tools/topk" "POST" "Vector Search"

echo

echo -e "${BLUE}8. Docker Environment${NC}"
echo "----------------------"

# Check Docker environment
if command -v docker >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is installed"
    
    if docker compose version >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker Compose is available"
    else
        echo -e "${RED}✗${NC} Docker Compose is not available"
    fi
    
    # Check if volumes exist
    if docker volume ls | grep -q "docker_kuzu-data"; then
        echo -e "${GREEN}✓${NC} Kuzu data volume exists"
    else
        echo -e "${YELLOW}⚠${NC} Kuzu data volume not found (may not be created yet)"
    fi
    
    if docker volume ls | grep -q "docker_kestra-data"; then
        echo -e "${GREEN}✓${NC} Kestra data volume exists"
    else
        echo -e "${YELLOW}⚠${NC} Kestra data volume not found (may not be created yet)"
    fi
    
else
    echo -e "${RED}✗${NC} Docker is not installed"
fi

echo

echo -e "${BLUE}9. Python Environment${NC}"
echo "----------------------"

# Check Python environment
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓${NC} Python virtual environment exists"
    
    if [ -f ".venv/bin/activate" ]; then
        echo -e "${GREEN}✓${NC} Virtual environment activation script found"
    else
        echo -e "${RED}✗${NC} Virtual environment activation script not found"
    fi
else
    echo -e "${YELLOW}⚠${NC} Python virtual environment not found"
fi

# Check if requirements are installed (if venv is activated)
if [ -n "$VIRTUAL_ENV" ]; then
    if python -c "import kuzu" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Kuzu package is installed"
    else
        echo -e "${RED}✗${NC} Kuzu package is not installed"
    fi
    
    if python -c "import fastapi" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} FastAPI package is installed"
    else
        echo -e "${RED}✗${NC} FastAPI package is not installed"
    fi
else
    echo -e "${BLUE}ℹ${NC} Virtual environment not activated - skipping package checks"
fi

echo

echo -e "${BLUE}10. Documentation Links Validation${NC}"
echo "------------------------------------"

# This would require a more sophisticated link checker
# For now, we'll just check that key files reference each other correctly
if grep -q "DOCUMENTATION.md" README.md; then
    echo -e "${GREEN}✓${NC} Main README references documentation index"
else
    echo -e "${RED}✗${NC} Main README does not reference documentation index"
fi

if grep -q "server/README.md" README.md; then
    echo -e "${GREEN}✓${NC} Main README references server documentation"
else
    echo -e "${RED}✗${NC} Main README does not reference server documentation"
fi

if grep -q "docker/README.md" README.md; then
    echo -e "${GREEN}✓${NC} Main README references Docker documentation"
else
    echo -e "${RED}✗${NC} Main README does not reference Docker documentation"
fi

echo

echo -e "${BLUE}Validation Summary${NC}"
echo "=================="
echo
echo -e "${GREEN}✓${NC} = Available/Working"
echo -e "${YELLOW}⚠${NC} = Warning/Not Running"
echo -e "${RED}✗${NC} = Missing/Error"
echo -e "${BLUE}ℹ${NC} = Information/Manual Check Required"
echo
echo "To start services for full validation:"
echo "  cd docker && docker compose up -d"
echo
echo "To setup Python environment:"
echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
echo
echo "For complete documentation, see: DOCUMENTATION.md" 