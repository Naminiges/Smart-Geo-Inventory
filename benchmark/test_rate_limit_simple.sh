#!/bin/bash

# Simple Rate Limiting Test Script (NO LOGIN REQUIRED)
# Tests rate limiting on public endpoints only

set -e

# Configuration
HOST=${HOST:-https://172.30.95.249}
CURL_OPTS=${CURL_OPTS:--k}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Test 1: Homepage - Burst Test
print_header "TEST 1: Homepage - Burst Test (100 requests)"

print_info "Mengirim 100 requests ke /home (public endpoint, no auth)"
print_info "Test apakah public endpoint memiliki rate limiting"

success_count=0
rate_limited=0
failed=0
start_time=$(date +%s)

for i in {1..100}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" "$HOST/home" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi

    if [ $((i % 20)) -eq 0 ]; then
        echo -n "."
    fi
done

end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo ""
print_info "Hasil Homepage Burst Test:"
echo "  ✅ Successful (200): $success_count/100"
echo "  🚫 Rate Limited (429): $rate_limited/100"
echo "  ❌ Other Errors: $failed/100"
echo "  ⏱️  Duration: ${duration} seconds"

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting terdeteksi pada public endpoint!"
else
    print_success "Public endpoint tidak memiliki rate limiting (normal)"
fi

echo ""

# Test 2: Sustained Load - Homepage
print_header "TEST 2: Homepage - Sustained Load (60 requests selama 60 detik)"

print_info "Mengirim 60 requests selama 60 detik (1 req/detik)"
print_info "Test apakah sustained load memicu rate limiting"

success_count=0
rate_limited=0
failed=0

for i in {1..60}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" "$HOST/home" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi

    echo -n "."
    sleep 1
done

echo ""
echo ""
print_info "Hasil Homepage Sustained Load Test:"
echo "  ✅ Successful (200): $success_count/60"
echo "  🚫 Rate Limited (429): $rate_limited/60"
echo "  ❌ Other Errors: $failed/60"

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting terdeteksi pada sustained load!"
else
    print_success "Semua requests berhasil pada sustained load"
fi

echo ""

# Test 3: Test API Auth Login Endpoint (tanpa login)
print_header "TEST 3: API Auth Login Endpoint (Rate Limit Test)"

print_info "Test rate limiting pada /api/benchmark/login"
print_info "Mengirim 20 login attempts dengan password salah"

login_success=0
rate_limited=0
unauthorized=0
other_error=0

for i in {1..20}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"wrong"}' \
        "$HOST/api/benchmark/login" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        login_success=$((login_success + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    elif [ "$response" = "401" ]; then
        unauthorized=$((unauthorized + 1))
    else
        other_error=$((other_error + 1))
    fi

    echo -n "."
    sleep 0.1
done

echo ""
echo ""
print_info "Hasil Login Endpoint Test:"
echo "  ✅ Successful (200): $login_success/20"
echo "  🚫 Rate Limited (429): $rate_limited/20"
echo "  🔒 Unauthorized (401): $unauthorized/20"
echo "  ❌ Other Errors: $other_error/20"

if [ $rate_limited -gt 0 ]; then
    print_success "Rate limiting bekerja pada login endpoint! ($rate_limited/20 ditolak)"
elif [ $unauthorized -eq 20 ]; then
    print_warning "Tidak ada rate limiting (semua request gagal dengan 401)"
else
    print_warning "Hasil mixed - perlu investigasi lebih lanjut"
fi

echo ""

# Test 4: Multiple Endpoints Concurrent Test
print_header "TEST 4: Concurrent Requests to Multiple Endpoints"

print_info "Test 50 requests concurrent ke berbagai endpoints"
print_info "Endpoint: /home, /, /api/dashboard/stats"

success_count=0
rate_limited=0
failed=0

for i in {1..50}; do
    # Random endpoint
    rand=$((RANDOM % 3))
    if [ $rand -eq 0 ]; then
        endpoint="/home"
    elif [ $rand -eq 1 ]; then
        endpoint="/"
    else
        endpoint="/api/dashboard/stats"
    fi

    response=$(curl -s $CURL_OPTS -w "%{http_code}" "$HOST$endpoint" -o /dev/null 2>&1)

    if [ "$response" = "200" ] || [ "$response" = "302" ]; then
        success_count=$((success_count + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        failed=$((failed + 1))
    fi
done

echo ""
print_info "Hasil Concurrent Test:"
echo "  ✅ Successful: $success_count/50"
echo "  🚫 Rate Limited (429): $rate_limited/50"
echo "  ❌ Other Errors: $failed/50"

if [ $rate_limited -gt 0 ]; then
    print_warning "Rate limiting terdeteksi pada concurrent requests!"
else
    print_success "Concurrent requests tidak kena rate limit"
fi

echo ""

# Summary
print_header "SUMMARY"

print_info "Konfigurasi Rate Limit (di app/__init__.py):"
echo "  • Default: 10000 per day, 1000 per hour"
echo "  • API Auth: 10 per minute, 20 per hour"
echo ""

print_info "Interpretasi Hasil:"
echo ""
echo "  ✅ IDEAL (Rate Limit Bekerja):"
echo "     - Homepage: 0/100 rate limited (public should be open)"
echo "     - Login endpoint: 5-10/20 rate limited (strict protection)"
echo ""
echo "  ⚠️  TIDAK IDEAL (Rate Limit Terlalu Ketat):"
echo "     - Homepage: >20/100 rate limited"
echo "     - Sustained: >10/60 rate limited"
echo "     → Solusi: NAIKKAN limit di app/__init__.py"
echo ""
echo "  ⚠️  TIDAK IDEAL (Rate Limit Tidak Aktif):"
echo "     - Login endpoint: 0/20 rate limited (harusnya ada)"
echo "     → Solusi: CEK konfigurasi Flask-Limiter"
echo ""

print_success "Rate limiting test selesai!"
echo ""
print_info "Note: Test ini TIDAK memerlukan login"
echo "      Hanya test public endpoints dan login rate limit"
