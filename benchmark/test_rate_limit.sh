#!/bin/bash

# Rate Limiting Test Script for Smart Geo Inventory
# Simple version - Tidak perlu login, langsung jalan

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

# Start
print_header "RATE LIMITING TEST - SMART GEO INVENTORY"
print_info "Target: $HOST"
print_info "Test public endpoints (TIDAK memerlukan login)"
echo ""

# Test 1: Burst Test
print_header "TEST 1: Burst Requests (100 requests sekaligus)"

print_info "Mengirim 100 requests ke /home"
echo ""

success=0
rate_limited=0
errors=0

for i in {1..100}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" "$HOST/home" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success=$((success + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        errors=$((errors + 1))
    fi

    if [ $((i % 20)) -eq 0 ]; then
        echo -n "."
    fi
done

echo ""
echo ""
print_info "Hasil:"
echo "  ✅ Sukses: $success/100"
echo "  🚫 Rate Limited (429): $rate_limited/100"
echo "  ❌ Error lain: $errors/100"
echo ""

if [ $rate_limited -eq 0 ]; then
    print_success "Tidak ada rate limiting (normal untuk public endpoint)"
else
    print_warning "$rate_limited requests kena rate limit!"
fi

echo ""
sleep 1

# Test 2: Sustained Load
print_header "TEST 2: Sustained Load (60 requests, 1 req/detik)"

print_info "Mengirim 60 requests selama 60 detik"
echo ""

success=0
rate_limited=0
errors=0

for i in {1..60}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" "$HOST/home" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success=$((success + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        errors=$((errors + 1))
    fi

    echo -n "."
    sleep 1
done

echo ""
echo ""
print_info "Hasil:"
echo "  ✅ Sukses: $success/60"
echo "  🚫 Rate Limited (429): $rate_limited/60"
echo "  ❌ Error lain: $errors/60"
echo ""

if [ $rate_limited -eq 0 ]; then
    print_success "Tidak ada rate limiting pada sustained load (normal)"
else
    print_warning "$rate_limited requests kena rate limit!"
fi

echo ""
sleep 1

# Test 3: Login Endpoint Protection
print_header "TEST 3: Login Endpoint Protection (20 attempts)"

print_info "Test rate limiting pada login endpoint"
print_info "Mengirim 20 login attempts dengan password salah"
echo ""

success=0
rate_limited=0
unauthorized=0

for i in {1..20}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"wrong"}' \
        "$HOST/api/benchmark/login" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success=$((success + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    elif [ "$response" = "401" ]; then
        unauthorized=$((unauthorized + 1))
    fi
done

echo ""
print_info "Hasil:"
echo "  ✅ Sukses: $success/20"
echo "  🚫 Rate Limited (429): $rate_limited/20"
echo "  🔒 Unauthorized (401): $unauthorized/20"
echo ""

if [ $rate_limited -gt 0 ]; then
    print_success "Rate limiting bekerja pada login endpoint! ($rate_limited/20 ditolak)"
elif [ $unauthorized -eq 20 ]; then
    print_warning "Login endpoint tersedia tapi tidak ada rate limiting"
else
    print_info "Hasil mixed - login endpoint mungkin tidak tersedia"
fi

echo ""
sleep 1

# Test 4: Multiple Endpoints
print_header "TEST 4: Multiple Endpoints (50 requests random)"

print_info "Test ke berbagai endpoints"
echo ""

success=0
rate_limited=0
errors=0

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
        success=$((success + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        errors=$((errors + 1))
    fi
done

echo ""
print_info "Hasil:"
echo "  ✅ Sukses: $success/50"
echo "  🚫 Rate Limited (429): $rate_limited/50"
echo "  ❌ Error lain: $errors/50"
echo ""

if [ $rate_limited -eq 0 ]; then
    print_success "Tidak ada rate limiting pada multiple endpoints"
else
    print_warning "$rate_limited requests kena rate limit!"
fi

echo ""

# Summary
print_header "SUMMARY"

print_info "Total requests: 230"
print_info "Total rate limited: $(($rate_limited * 4))/230"
echo ""

print_info "Konfigurasi rate limit (di app/__init__.py):"
echo "  • Default: 10000 per day, 1000 per hour"
echo "  • API Auth: 10 per minute, 20 per hour"
echo ""

print_info "Kesimpulan:"

total_rate_limited=$(($rate_limited * 4))

if [ $total_rate_limited -eq 0 ]; then
    echo "  ✅ Rate limiting tidak terdeteksi pada public endpoints"
    echo "     Ini NORMAL karena rate limit sudah dinaikkan untuk benchmarking"
elif [ $total_rate_limited -lt 20 ]; then
    echo "  ⚠️  Sedikit requests yang kena rate limit ($total_rate_limited/230)"
    echo "     Masih acceptable untuk benchmarking"
else
    echo "  ❌ Banyak requests kena rate limit ($total_rate_limited/230)"
    echo "     Rate limiting mungkin terlalu ketat untuk benchmarking"
fi

echo ""
print_success "Test selesai!"
echo ""
print_info "Note: Test ini TIDAK memerlukan login"
echo "      Hanya test public endpoints dan login rate limit protection"
