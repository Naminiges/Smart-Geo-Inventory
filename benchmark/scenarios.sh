#!/bin/bash

# Benchmark scenarios for Smart Geo Inventory
# This script runs different benchmark scenarios using wrk

set -e

# Configuration
WRK_BIN=${WRK_BIN:-wrk}
# Akses melalui reverse proxy (rev-proxy: 172.30.95.249)
HOST=${HOST:-http://172.30.95.249}
# Alternatif: akses langsung ke apps (172.30.95.251:5000)
# HOST=${HOST:-http://172.30.95.251:5000}
DURATION=${DURATION:-30s}
THREADS=${THREADS:-4}
CONNECTIONS=${CONNECTIONS:-100}
RESULTS_DIR=${RESULTS_DIR:-./benchmark/results}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$RESULTS_DIR"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run benchmark
run_benchmark() {
    local name=$1
    local path=$2
    local method=${3:-GET}
    local body=${4:-""}
    local threads=${5:-$THREADS}
    local connections=${6:-$CONNECTIONS}
    local duration=${7:-$DURATION}

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_file="$RESULTS_DIR/${name}_${timestamp}.txt"

    print_info "Running benchmark: $name"
    print_info "  Path: $path"
    print_info "  Method: $method"
    print_info "  Threads: $threads"
    print_info "  Connections: $connections"
    print_info "  Duration: $duration"
    echo ""

    local cmd="$WRK_BIN -t$threads -c$connections -d$duration"

    if [ -n "$body" ]; then
        cmd="$cmd -s wrk.lua $HOST$path --path $path --method $method --body '$body'"
    else
        cmd="$cmd -s wrk.lua $HOST$path --path $path --method $method"
    fi

    # Run the benchmark
    eval $cmd | tee "$output_file"

    echo ""
    print_info "Results saved to: $output_file"
    echo ""
}

# Function to check if service is ready
wait_for_service() {
    local max_attempts=30
    local attempt=1

    print_info "Waiting for service at $HOST to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$HOST/home" > /dev/null 2>&1 || curl -s -f "http://172.30.95.249/home" > /dev/null 2>&1; then
            print_info "Service is ready!"
            return 0
        fi

        print_warning "Attempt $attempt/$max_attempts: Service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "Service failed to start within expected time"
    return 1
}

# Main execution
main() {
    print_info "Starting Smart Geo Inventory Benchmark"
    print_info "Target: $HOST"
    print_info "Results directory: $RESULTS_DIR"
    echo ""

    # Wait for service to be ready
    wait_for_service
    echo ""

    # Scenario 1: Light load - Homepage
    print_info "=== Scenario 1: Light Load - Homepage ==="
    run_benchmark "01_homepage_light" "/home" "GET" "" "2" "10" "10s"
    echo ""

    # Scenario 2: Medium load - Homepage
    print_info "=== Scenario 2: Medium Load - Homepage ==="
    run_benchmark "02_homepage_medium" "/home" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 3: Heavy load - Homepage
    print_info "=== Scenario 3: Heavy Load - Homepage ==="
    run_benchmark "03_homepage_heavy" "/home" "GET" "" "8" "200" "60s"
    echo ""

    # Scenario 4: API endpoints - Items list
    print_info "=== Scenario 4: API - Items List ==="
    run_benchmark "04_api_items" "/api/items" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 5: API endpoints - Dashboard data
    print_info "=== Scenario 5: API - Dashboard ==="
    run_benchmark "05_api_dashboard" "/api/dashboard/data" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 6: API endpoints - Map data
    print_info "=== Scenario 6: API - Map Data ==="
    run_benchmark "06_api_map" "/api/map/markers" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 7: Stress test - Sustained load
    print_info "=== Scenario 7: Stress Test - Sustained Load ==="
    run_benchmark "07_stress_sustained" "/home" "GET" "" "12" "500" "120s"
    echo ""

    # Scenario 8: Spike test - Sudden load
    print_info "=== Scenario 8: Spike Test - Sudden Load ==="
    run_benchmark "08_spike_test" "/home" "GET" "" "16" "1000" "30s"
    echo ""

    print_info "=== All benchmarks completed! ==="
    print_info "Results are saved in: $RESULTS_DIR"
}

# Run main function
main "$@"
