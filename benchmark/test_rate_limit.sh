#!/bin/bash

# Rate Limiting Test Script for Smart Geo Inventory
# This script tests whether rate limiting is properly configured

set -e

# Configuration
HOST=${HOST:-https://172.30.95.249}
CURL_OPTS=${CURL_OPTS:--k}
COOKIE_FILE=${COOKIE_FILE:-./benchmark/.cookies.txt}
LOGIN_EMAIL=${LOGIN_EMAIL:-admin@smartgeo.com}
LOGIN_PASSWORD=${LOGIN_PASSWORD:-admin123}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Test 1: Login First
print_header "TEST 1: Login untuk mendapatkan session"

json_payload="{\"email\":\"$LOGIN_EMAIL\",\"password\":\"$LOGIN_PASSWORD\"}"
login_response=$(curl -s $CURL_OPTS -c "$COOKIE_FILE" -X POST \
    -H "Content-Type: application/json" \
    -d "$json_payload" \
    "$HOST/api/benchmark/login" 2>&1)

if echo "$login_response" | grep -q "success.*true"; then
    print_success "Login berhasil"
else
    print_error "Login gagal"
    echo "Response: $login_response"
    exit 1
fi

echo ""

# Test 2: Rate Limit Test - Burst Requests
print_header "TEST 2: Burst Requests (100 requests seketika)"

print_info "Mengirim 100 requests sekaligus..."
print_info "Jika rate limit aktif, sebagian request akan gagal dengan 429"

success_count=0
rate_limited=0
failed=0

for i in {1..100}; do
    response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
        "$HOST/api/dashboard/stats" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi

    # Progress indicator
    if [ $((i % 20)) -eq 0 ]; then
        echo -n "."
    fi
done

echo ""
echo ""
print_info "Hasil Burst Test:"
echo "  ✅ Successful: $success_count/100"
echo "  🚫 Rate Limited (429): $rate_limited/100"
echo "  ❌ Other Errors: $failed/100"
echo ""

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting terdeteksi! $rate_limited requests ditolak dengan 429"
else
    print_success "Semua requests berhasil (tidak ada rate limiting pada burst test)"
fi

echo ""

# Test 3: Sustained Load Test
print_header "TEST 3: Sustained Load (60 requests per menit)"

print_info "Mengirim 60 requests selama 60 detik (1 req/detik)"
print_info "Test apakah sustained load memicu rate limiting"

success_count=0
rate_limited=0
failed=0

for i in {1..60}; do
    response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
        "$HOST/api/dashboard/stats" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi

    # Wait 1 second between requests
    sleep 1

    # Progress indicator
    echo -n "."
done

echo ""
echo ""
print_info "Hasil Sustained Load Test:"
echo "  ✅ Successful: $success_count/60"
echo "  🚫 Rate Limited (429): $rate_limited/60"
echo "  ❌ Other Errors: $failed/60"
echo ""

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting terdeteksi pada sustained load!"
else
    print_success "Semua requests berhasil pada sustained load"
fi

echo ""

# Test 4: Public Endpoint (No Auth)
print_header "TEST 4: Public Endpoint - Homepage"

print_info "Test rate limiting pada public endpoint (tanpa authentication)"

success_count=0
rate_limited=0
failed=0

for i in {1..50}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" \
        "$HOST/home" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi
done

echo ""
print_info "Hasil Public Endpoint Test:"
echo "  ✅ Successful: $success_count/50"
echo "  🚫 Rate Limited (429): $rate_limited/50"
echo "  ❌ Other Errors: $failed/50"
echo ""

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting aktif pada public endpoint"
else
    print_success "Public endpoint tidak memiliki rate limiting (expected)"
fi

echo ""

# Test 5: API Login Endpoint
print_header "TEST 5: API Login Endpoint (Strict Rate Limit)"

print_info "Test rate limiting pada /api/benchmark/login"
print_info "Harusnya memiliki rate limit yang lebih ketat"

# Delete cookie first to test fresh login
rm -f "$COOKIE_FILE"

login_attempts=0
success_count=0
rate_limited=0
failed=0

for i in {1..20}; do
    json_payload="{\"email\":\"test@test.com\",\"password\":\"wrongpassword\"}"
    response=$(curl -s $CURL_OPTS -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        "$HOST/api/benchmark/login" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi
done

echo ""
print_info "Hasil Login Endpoint Test (20 attempts):"
echo "  ✅ Successful: $success_count/20"
echo "  🚫 Rate Limited (429): $rate_limited/20"
echo "  ❌ Other Errors (401, dll): $failed/20"
echo ""

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting aktif pada login endpoint (bagus!)"
else
    print_warning "Rate limiting tidak terdeteksi pada login endpoint"
fi

echo ""

# Summary
print_header "SUMMARY"

print_info "Konfigurasi Rate Limit Saat Ini:"
echo "  Default: 10000 per day, 1000 per hour"
echo "  API Auth: 10 per minute, 20 per hour"
echo ""

print_info "Rekomendasi:"
echo "  ✅ Burst test harusnya tidak kena rate limit (sesuai config)"
echo "  ✅ Sustained load harusnya tidak kena rate limit (1000/hour cukup)"
echo "  ✅ Public endpoint tidak perlu rate limit (opsional)"
echo "  ⚠️  Login endpoint sebaiknya memiliki rate limit yang lebih ketat"
echo ""

print_success "Rate limiting test selesai!"
echo ""
print_info "Catatan:"
echo "  - Jika semua test lolos tanpa 429, rate limit mungkin tidak aktif"
echo "  - Jika banyak 429, rate limit bekerja tapi mungkin terlalu ketat"
echo "  - Untuk benchmark, rate limit sudah dinaikkan ke 10000/day, 1000/hour"
echo ""
