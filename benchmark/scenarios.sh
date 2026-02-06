#!/bin/bash

# Benchmark scenarios for Smart Geo Inventory
# This script runs different benchmark scenarios using wrk

set -e

# Configuration
WRK_BIN=${WRK_BIN:-wrk}
# Akses melalui reverse proxy (rev-proxy: 172.30.95.249)
HOST=${HOST:-https://172.30.95.249}
# Alternatif: akses langsung ke apps (172.30.95.251:5000)
# HOST=${HOST:-http://172.30.95.251:5000}
# Options untuk curl (misal: -k untuk self-signed certificates)
CURL_OPTS=${CURL_OPTS:--k}
DURATION=${DURATION:-30s}
THREADS=${THREADS:-4}
CONNECTIONS=${CONNECTIONS:-100}
RESULTS_DIR=${RESULTS_DIR:-./benchmark/results}
COOKIE_FILE=${COOKIE_FILE:-./benchmark/.cookies.txt}

# Login credentials (default admin user)
LOGIN_EMAIL=${LOGIN_EMAIL:-admin@smartgeo.com}
LOGIN_PASSWORD=${LOGIN_PASSWORD:-admin123}

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

# Function to login and save session
login_and_save_session() {
    print_info "Logging in to get session cookie..."

    # Step 1: Get login page and CSRF token
    print_info "Fetching CSRF token from login page..."
    local login_page=$(curl -s $CURL_OPTS -c "$COOKIE_FILE" "$HOST/auth/login" 2>&1)

    # Extract CSRF token from HTML
    local csrf_token=$(echo "$login_page" | grep -o 'name="csrf_token".*value="[^"]*"' | sed 's/.*value="\([^"]*\)".*/\1/')

    if [ -z "$csrf_token" ]; then
        print_warning "Could not extract CSRF token from login page"
        print_warning "Trying login without CSRF token..."
    else
        print_info "✅ CSRF token extracted: ${csrf_token:0:20}..."
    fi

    # Step 2: Perform login with CSRF token
    print_info "Attempting login..."
    local login_data="email=$LOGIN_EMAIL&password=$LOGIN_PASSWORD"
    if [ -n "$csrf_token" ]; then
        login_data="$login_data&csrf_token=$csrf_token"
    fi

    local login_response=$(curl -i -s $CURL_OPTS -b "$COOKIE_FILE" -c "$COOKIE_FILE" -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "$login_data" \
        "$HOST/auth/login" 2>&1)

    # Check if login successful (302 redirect or Location header)
    if echo "$login_response" | grep -q "302\|Found\|Location:"; then
        print_info "✅ Login successful! Session saved to $COOKIE_FILE"

        # Show cookie info
        if [ -f "$COOKIE_FILE" ]; then
            print_info "Cookie file created:"
            cat "$COOKIE_FILE" | head -5
        fi
        return 0
    else
        print_error "❌ Login failed!"
        echo ""
        echo "Login response:"
        echo "$login_response" | head -30
        echo ""
        echo "Please check:"
        echo "  1. Application is running at $HOST"
        echo "  2. Login credentials are correct"
        echo "  3. Admin user exists (run: python3 seed_admin_user.py)"
        echo ""
        echo "Current credentials:"
        echo "  Email: $LOGIN_EMAIL"
        echo "  Password: $LOGIN_PASSWORD"
        echo ""
        echo "Debug info:"
        echo "  CSRF token: ${csrf_token:-none}"
        return 1
    fi
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

    # Determine if using HTTPS
    if [[ $HOST == https://* ]]; then
        print_warning "HTTPS detected - using curl for basic benchmarking"
        print_warning "For full benchmarking, use HTTP endpoint (direct to apps container)"

        # Check if cookie file exists for authenticated endpoints
        local use_auth=false
        if [[ $path == /api/* ]] || [[ $path == /dashboard* ]]; then
            use_auth=true
            if [ ! -f "$COOKIE_FILE" ]; then
                print_error "Cookie file not found: $COOKIE_FILE"
                print_error "Please login first (script should do this automatically)"
                return 1
            fi
        fi

        # Simple curl-based benchmark for HTTPS
        {
            echo "=== Benchmark: $name ==="
            echo "Path: $path"
            echo "Method: $method"
            echo "Duration: $duration"
            echo "Threads: $threads"
            echo "Connections: $connections"
            echo "Authentication: $use_auth"
            echo ""
            echo "Test started at: $(date)"
            echo ""

            local duration_sec=$(echo $duration | sed 's/s//')
            local end_time=$(($(date +%s) + duration_sec))

            local total_requests=0
            local successful=0
            local failed=0
            local unauthorized=0
            declare -a response_times

            while [ $(date +%s) -lt $end_time ]; do
                for ((i=1; i<=connections; i++)); do
                    local start_time=$(date +%s.%N 2>/dev/null || date +%s)

                    # Add cookie if authentication needed
                    local curl_cmd="curl -s -w '%{http_code}' -o /dev/null $CURL_OPTS"
                    if [ "$use_auth" = true ]; then
                        curl_cmd="$curl_cmd -b $COOKIE_FILE"
                    fi
                    curl_cmd="$curl_cmd '$HOST$path'"

                    local response=$(eval $curl_cmd 2>&1)
                    local end_time_req=$(date +%s.%N 2>/dev/null || date +%s)
                    local elapsed=$(awk "BEGIN {print $end_time_req - $start_time}")

                    total_requests=$((total_requests + 1))
                    response_times+=("$elapsed")

                    if [ "$response" = "200" ] || [ "$response" = "302" ]; then
                        successful=$((successful + 1))
                    elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
                        unauthorized=$((unauthorized + 1))
                        failed=$((failed + 1))
                    else
                        failed=$((failed + 1))
                    fi
                done
            done

            echo "Test completed at: $(date)"
            echo ""
            echo "=== Results ==="
            echo "Total requests: $total_requests"
            echo "Successful: $successful"
            echo "Failed: $failed"
            if [ $unauthorized -gt 0 ]; then
                echo "Unauthorized (401/403): $unauthorized"
            fi
            echo ""

            # Calculate average response time
            if [ ${#response_times[@]} -gt 0 ]; then
                # Use awk for all calculations
                local stats=$(printf "%s\n" "${response_times[@]}" | awk '
                {
                    sum += $1
                    if (NR == 1) {
                        min = max = $1
                    } else {
                        if ($1 < min) min = $1
                        if ($1 > max) max = $1
                    }
                }
                END {
                    avg = sum / NR
                    printf "%.3f %.3f %.3f", avg, min, max
                }')

                local avg=$(echo $stats | awk '{print $1}')
                local min=$(echo $stats | awk '{print $2}')
                local max=$(echo $stats | awk '{print $3}')

                echo "Average response time: ${avg}s"
                echo "Min response time: ${min}s"
                echo "Max response time: ${max}s"
            fi

            echo ""
            echo "Note: This is a basic curl-based benchmark for HTTPS endpoints."
            echo "For production-grade benchmarking, consider:"
            echo "  1. Using wrk with HTTP (direct to apps container at http://172.30.95.251:5000)"
            echo "  2. Setting up stunnel to proxy HTTPS to HTTP for wrk"
            echo "  3. Using alternative tools like hey (https://github.com/rakyll/hey)"
            echo "     or vegeta (https://github.com/tsenart/vegeta)"
        } | tee "$output_file"

    else
        # Use wrk for HTTP
        local cmd="$WRK_BIN -t$threads -c$connections -d$duration"

        if [ -n "$body" ]; then
            cmd="$cmd -s wrk.lua $HOST$path --path $path --method $method --body '$body'"
        else
            cmd="$cmd -s wrk.lua $HOST$path --path $path --method $method"
        fi

        # Run the benchmark
        eval $cmd | tee "$output_file"
    fi

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
        if curl -s -f $CURL_OPTS "$HOST/home" > /dev/null 2>&1; then
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

    # Login to get session cookie
    if ! login_and_save_session; then
        print_error "Failed to login. Exiting..."
        exit 1
    fi
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
    run_benchmark "04_api_items" "/api/items/" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 5: API endpoints - Dashboard stats
    print_info "=== Scenario 5: API - Dashboard Stats ==="
    run_benchmark "05_api_dashboard_stats" "/api/dashboard/stats" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 6: API endpoints - Map warehouses
    print_info "=== Scenario 6: API - Map Warehouses ==="
    run_benchmark "06_api_map_warehouses" "/api/map/warehouses" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 7: API endpoints - Dashboard main page
    print_info "=== Scenario 7: Dashboard Page ==="
    run_benchmark "07_dashboard_page" "/dashboard/" "GET" "" "4" "50" "30s"
    echo ""

    # Scenario 8: Stress test - Sustained load
    print_info "=== Scenario 8: Stress Test - Sustained Load ==="
    run_benchmark "08_stress_sustained" "/home" "GET" "" "12" "500" "120s"
    echo ""

    # Scenario 9: Spike test - Sudden load
    print_info "=== Scenario 9: Spike Test - Sudden Load ==="
    run_benchmark "09_spike_test" "/home" "GET" "" "16" "1000" "30s"
    echo ""

    print_info "=== All benchmarks completed! ==="
    print_info "Results are saved in: $RESULTS_DIR"
}

# Run main function
main "$@"
