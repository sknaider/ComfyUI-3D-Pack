#!/bin/bash
# Health check script for ComfyUI-3D-Pack
# Usage: ./scripts/health-check.sh [host] [port]

set -e

# Configuration
HOST="${1:-localhost}"
PORT="${2:-8188}"
BASE_URL="http://${HOST}:${PORT}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_code="${3:-200}"

    echo -n "Testing $name... "

    response=$(curl -s -w "%{http_code}" -o /tmp/response.txt "$BASE_URL$endpoint")

    if [ "$response" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $response)${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to test health endpoint
test_health() {
    echo -n "Testing health endpoint... "

    response=$(curl -s "$BASE_URL/health")

    if echo "$response" | grep -q "healthy"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))

        # Check CUDA availability
        if echo "$response" | grep -q '"cuda_available":true'; then
            echo "  - CUDA: Available"
        else
            echo -e "  - CUDA: ${YELLOW}Not Available${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi

        # Check GPU count
        gpu_count=$(echo "$response" | grep -o '"cuda_devices":[0-9]*' | cut -d':' -f2)
        if [ -n "$gpu_count" ] && [ "$gpu_count" -gt 0 ]; then
            echo "  - GPUs: $gpu_count"
        else
            echo -e "  - GPUs: ${YELLOW}0${NC}"
        fi
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Function to test metrics endpoint
test_metrics() {
    echo -n "Testing metrics endpoint... "

    response=$(curl -s "$BASE_URL/metrics")

    if echo "$response" | grep -q "cuda_available"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))

        # Parse some metrics
        cuda_available=$(echo "$response" | grep "cuda_available" | tail -1 | awk '{print $2}')
        echo "  - CUDA Available: $cuda_available"
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Function to test authenticated endpoint (if auth enabled)
test_auth() {
    echo -n "Testing authentication... "

    # Try without auth
    response=$(curl -s -w "%{http_code}" -o /dev/null "$BASE_URL/viewfile?filepath=/test")

    if [ "$response" -eq 401 ] || [ "$response" -eq 403 ]; then
        echo -e "${GREEN}✓ PASSED (Auth required)${NC}"
        PASSED=$((PASSED + 1))
    elif [ "$response" -eq 400 ]; then
        echo -e "${YELLOW}⚠ WARNING (Auth not enabled)${NC}"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${RED}✗ FAILED (Unexpected response: $response)${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Function to show summary
show_summary() {
    echo ""
    echo "========================================="
    echo "Health Check Summary"
    echo "========================================="
    echo -e "Passed:   ${GREEN}$PASSED${NC}"
    echo -e "Failed:   ${RED}$FAILED${NC}"
    echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
    echo "========================================="

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}Overall Status: HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}Overall Status: UNHEALTHY${NC}"
        return 1
    fi
}

# Main function
main() {
    echo "ComfyUI-3D-Pack Health Check"
    echo "Testing: $BASE_URL"
    echo ""

    # Test basic connectivity
    if ! curl -s --connect-timeout 5 "$BASE_URL" &> /dev/null; then
        echo -e "${RED}Error: Cannot connect to $BASE_URL${NC}"
        exit 1
    fi

    # Run tests
    test_health
    test_metrics
    test_auth

    # Show summary
    show_summary
}

# Run main function
main
