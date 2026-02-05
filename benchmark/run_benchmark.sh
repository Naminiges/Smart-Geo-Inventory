#!/bin/bash

# Quick run script for Smart Geo Inventory benchmarking
# Untuk environment container dengan rev-proxy

set -e

# Configuration
# Default: akses melalui reverse proxy (rev-proxy: 172.30.95.249)
HOST=${HOST:-https://172.30.95.249}
# Alternatif: akses langsung ke apps (172.30.95.251:5000)
# HOST=${HOST:-http://172.30.95.251:5000}
# Options untuk curl (misal: -k untuk self-signed certificates)
CURL_OPTS=${CURL_OPTS:--k}

# Check if wrk is installed
if ! command -v wrk &> /dev/null; then
    echo "Error: wrk is not installed"
    echo "Install wrk:"
    echo "  Ubuntu/Debian: sudo apt-get install wrk"
    echo ""
    echo "Atau build dari source:"
    echo "  git clone https://github.com/wg/wrk.git"
    echo "  cd wrk && make"
    echo "  sudo cp wrk /usr/local/bin/"
    exit 1
fi

# Check if app is running
if ! curl -s -f $CURL_OPTS "$HOST/home" > /dev/null 2>&1; then
    echo "Error: Application is not running at $HOST"
    echo ""
    echo "Pastikan:"
    echo "  1. Apps container sudah running (172.30.95.251)"
    echo "  2. Reverse proxy sudah running (172.30.95.249)"
    echo "  3. Network antar container sudah OK"
    echo ""
    echo "Test connection:"
    echo "  curl $CURL_OPTS $HOST/home"
    exit 1
fi

# Create results directory
mkdir -p results

# Run simple benchmark
echo "Running quick benchmark on homepage..."
echo "Target: $HOST/home"
echo ""

# Determine if using HTTPS
if [[ $HOST == https://* ]]; then
    echo "Note: Using HTTPS with self-signed certificate"
    echo "wrk does not support HTTPS natively. Using curl for basic test instead."
    echo ""

    # Use curl for basic load testing with HTTPS
    echo "Running HTTP load test with curl..."
    for i in {1..10}; do
        curl -s -w "@-" -o /dev/null $CURL_OPTS "$HOST/home" <<< 'time_total: %{time_total}s\n' >> results/quick_run.txt
    done

    # Calculate average
    echo "" >> results/quick_run.txt
    echo "For full HTTPS benchmarking, consider:" >> results/quick_run.txt
    echo "1. Using wrk with HTTP (direct to apps container)" >> results/quick_run.txt
    echo "2. Setting up stunnel to proxy HTTPS to HTTP" >> results/quick_run.txt
    echo "3. Using alternative tools like hey or vegeta" >> results/quick_run.txt
else
    wrk -t4 -c50 -d30s \
        -s wrk.lua \
        "$HOST/home" \
        --path /home \
        --method GET | tee results/quick_run.txt
fi

echo ""
echo "Results saved to: results/quick_run.txt"
