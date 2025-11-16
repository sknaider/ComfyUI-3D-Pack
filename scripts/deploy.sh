#!/bin/bash
# Deployment script for ComfyUI-3D-Pack
# Usage: ./scripts/deploy.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"

echo -e "${GREEN}ComfyUI-3D-Pack Deployment Script${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi

    # Check .env file
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${RED}Error: .env file not found${NC}"
        echo "Please create .env from .env.example"
        exit 1
    fi

    echo -e "${GREEN}✓ Prerequisites check passed${NC}"
}

# Function to validate environment configuration
validate_config() {
    echo "Validating configuration..."

    # Check critical environment variables
    source "$PROJECT_ROOT/.env"

    if [ "$ENABLE_AUTH" = "true" ] && [ -z "$API_KEYS" ]; then
        echo -e "${RED}Error: AUTH enabled but API_KEYS not set${NC}"
        exit 1
    fi

    if [ -z "$HUGGINGFACE_TOKEN" ]; then
        echo -e "${YELLOW}Warning: HUGGINGFACE_TOKEN not set${NC}"
    fi

    echo -e "${GREEN}✓ Configuration validated${NC}"
}

# Function to build Docker image
build_image() {
    echo "Building Docker image..."

    cd "$PROJECT_ROOT"
    docker build -f Dockerfile.enterprise -t comfyui-3d-pack:latest -t "comfyui-3d-pack:$ENVIRONMENT" .

    echo -e "${GREEN}✓ Docker image built${NC}"
}

# Function to run tests
run_tests() {
    echo "Running tests..."

    # Run tests in a temporary container
    docker run --rm \
        -v "$PROJECT_ROOT:/app" \
        comfyui-3d-pack:latest \
        python -m pytest tests/unit/ -v || {
        echo -e "${RED}Error: Tests failed${NC}"
        exit 1
    }

    echo -e "${GREEN}✓ Tests passed${NC}"
}

# Function to stop existing containers
stop_containers() {
    echo "Stopping existing containers..."

    cd "$PROJECT_ROOT"
    docker-compose down || true

    echo -e "${GREEN}✓ Containers stopped${NC}"
}

# Function to start containers
start_containers() {
    echo "Starting containers..."

    cd "$PROJECT_ROOT"

    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose up -d
    elif [ "$ENVIRONMENT" = "staging" ]; then
        docker-compose -f docker-compose.yml up -d
    else
        echo -e "${RED}Error: Unknown environment: $ENVIRONMENT${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Containers started${NC}"
}

# Function to wait for health check
wait_for_health() {
    echo "Waiting for service to be healthy..."

    MAX_ATTEMPTS=30
    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl -f http://localhost:8188/health &> /dev/null; then
            echo -e "${GREEN}✓ Service is healthy${NC}"
            return 0
        fi

        ATTEMPT=$((ATTEMPT + 1))
        echo "Attempt $ATTEMPT/$MAX_ATTEMPTS..."
        sleep 2
    done

    echo -e "${RED}Error: Service health check failed${NC}"
    docker-compose logs
    exit 1
}

# Function to run smoke tests
smoke_tests() {
    echo "Running smoke tests..."

    # Test health endpoint
    HEALTH=$(curl -s http://localhost:8188/health)
    if echo "$HEALTH" | grep -q "healthy"; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${RED}Error: Health check failed${NC}"
        exit 1
    fi

    # Test metrics endpoint
    if curl -f http://localhost:8188/metrics &> /dev/null; then
        echo -e "${GREEN}✓ Metrics endpoint accessible${NC}"
    else
        echo -e "${YELLOW}Warning: Metrics endpoint not accessible${NC}"
    fi
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Environment: $ENVIRONMENT"
    echo "Service URL: http://localhost:8188"
    echo "Health Check: http://localhost:8188/health"
    echo "Metrics: http://localhost:8188/metrics"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "To stop services:"
    echo "  docker-compose down"
    echo ""
}

# Main deployment flow
main() {
    check_prerequisites
    validate_config
    build_image

    # Skip tests in production (run in CI/CD instead)
    if [ "$ENVIRONMENT" != "production" ]; then
        run_tests
    fi

    stop_containers
    start_containers
    wait_for_health
    smoke_tests
    show_summary
}

# Run main function
main
