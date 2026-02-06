#!/bin/bash

# Rate Limiting Test Script for Smart Geo Inventory
# Comprehensive version - Test 1000+ requests

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
MAGENTA='\033[0;35m'
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

print_endpoint() {
    echo -e "${MAGENTA}🔗 $1${NC}"
}

# Start
print_header "COMPREHENSIVE RATE LIMITING TEST"
print_info "Target: $HOST"
print_info "Total requests: 1000+"
print_info "Endpoints: Public & Authenticated"
echo ""

# Try login first
print_header "LOGIN PHASE"

print_info "Mencoba login untuk test authenticated endpoints..."
print_info "Email: $LOGIN_EMAIL"
print_info "Password: $LOGIN_PASSWORD"

# Method 1: Try benchmark API (new endpoint, CSRF-exempt)
print_info "Method 1: Benchmark API endpoint..."
json_payload="{\"email\":\"$LOGIN_EMAIL\",\"password\":\"$LOGIN_PASSWORD\"}"
login_response=$(curl -i -s $CURL_OPTS -c "$COOKIE_FILE" -X POST \
    -H "Content-Type: application/json" \
    -d "$json_payload" \
    "$HOST/api/benchmark/login" 2>&1)

if echo "$login_response" | grep -q "success.*true"; then
    print_success "Login berhasil via Benchmark API!"
    HAS_AUTH=1
    echo ""
    # Show user info
    user_name=$(echo "$login_response" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    print_info "Logged in as: $user_name"
else
    print_warning "Benchmark API tidak tersedia (mungkin perlu restart aplikasi)"

    # Method 2: Try regular API auth (might have CSRF issue, but try anyway)
    print_info "Method 2: Regular API Auth endpoint..."
    login_response2=$(curl -i -s $CURL_OPTS -c "$COOKIE_FILE" -X POST \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        "$HOST/api/auth/login" 2>&1)

    if echo "$login_response2" | grep -q "success.*true"; then
        print_success "Login berhasil via Regular API!"
        HAS_AUTH=1
        echo ""
        user_name=$(echo "$login_response2" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        print_info "Logged in as: $user_name"
    else
        print_error "Login gagal via semua method"
        echo ""
        print_info "Melanjutkan TANPA authentication (public endpoints only)"
        HAS_AUTH=0
    fi
fi

echo ""

# Test 1: Homepage - 1000 Requests (The Main Test!)
print_header "TEST 1: Homepage - 1000 Requests (BENCHMARK)"
print_endpoint "GET /home"
print_info "Mengirim 1000 requests untuk test rate limit 1000/hour"
echo ""

success=0
rate_limited=0
errors=0
start_time=$(date +%s)

for i in {1..1000}; do
    response=$(curl -s $CURL_OPTS -w "%{http_code}" "$HOST/home" -o /dev/null 2>&1)

    if [ "$response" = "200" ]; then
        success=$((success + 1))
    elif [ "$response" = "429" ]; then
        rate_limited=$((rate_limited + 1))
    else
        errors=$((errors + 1))
    fi

    if [ $((i % 100)) -eq 0 ]; then
        echo -n "."
    fi
done

end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo ""
print_info "Hasil Homepage Test (1000 requests):"
echo "  ✅ Sukses (200): $success/1000"
echo "  🚫 Rate Limited (429): $rate_limited/1000"
echo "  ❌ Error lain: $errors/1000"
echo "  ⏱️  Duration: ${duration} detik"
echo ""

if [ $rate_limited -eq 0 ]; then
    print_success "TIDAK ada rate limiting (normal - limit 1000/hour)"
elif [ $rate_limited -lt 50 ]; then
    print_warning "Sedikit rate limited ($rate_limited/1000) - masih OK"
else
    print_error "Banyak kena rate limit ($rate_limited/1000) - terlalu ketat!"
fi

echo ""

# Test 2: Authenticated Dashboard (if logged in)
if [ $HAS_AUTH -eq 1 ]; then
    print_header "TEST 2: Authenticated Dashboard - 200 Requests"
    print_endpoint "GET /dashboard/"
    print_info "Mengirim 200 requests ke authenticated endpoint"
    echo ""

    success=0
    rate_limited=0
    unauthorized=0
    errors=0

    for i in {1..200}; do
        response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
            "$HOST/dashboard/" -o /dev/null 2>&1)

        if [ "$response" = "200" ]; then
            success=$((success + 1))
        elif [ "$response" = "429" ]; then
            rate_limited=$((rate_limited + 1))
        elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
            unauthorized=$((unauthorized + 1))
        else
            errors=$((errors + 1))
        fi

        if [ $((i % 40)) -eq 0 ]; then
            echo -n "."
        fi
    done

    echo ""
    echo ""
    print_info "Hasil Dashboard Test (200 requests):"
    echo "  ✅ Sukses (200): $success/200"
    echo "  🚫 Rate Limited (429): $rate_limited/200"
    echo "  🔒 Unauthorized (401/403): $unauthorized/200"
    echo "  ❌ Error lain: $errors/200"
    echo ""

    if [ $rate_limited -eq 0 ]; then
        print_success "Dashboard tidak kena rate limit"
    else
        print_warning "Dashboard terkena rate limit ($rate_limited/200)"
    fi

    echo ""
fi

# Test 3: API Dashboard Stats (if logged in)
if [ $HAS_AUTH -eq 1 ]; then
    print_header "TEST 3: API Dashboard Stats - 300 Requests"
    print_endpoint "GET /api/dashboard/stats"
    print_info "Mengirim 300 requests ke authenticated API endpoint"
    echo ""

    success=0
    rate_limited=0
    unauthorized=0
    errors=0

    for i in {1..300}; do
        response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
            "$HOST/api/dashboard/stats" -o /dev/null 2>&1)

        if [ "$response" = "200" ]; then
            success=$((success + 1))
        elif [ "$response" = "429" ]; then
            rate_limited=$((rate_limited + 1))
        elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
            unauthorized=$((unauthorized + 1))
        else
            errors=$((errors + 1))
        fi

        if [ $((i % 50)) -eq 0 ]; then
            echo -n "."
        fi
    done

    echo ""
    echo ""
    print_info "Hasil API Dashboard Stats (300 requests):"
    echo "  ✅ Sukses (200): $success/300"
    echo "  🚫 Rate Limited (429): $rate_limited/300"
    echo "  🔒 Unauthorized (401/403): $unauthorized/300"
    echo "  ❌ Error lain: $errors/300"
    echo ""

    if [ $rate_limited -eq 0 ]; then
        print_success "API Dashboard Stats tidak kena rate limit"
    else
        print_warning "API Dashboard Stats terkena rate limit ($rate_limited/300)"
    fi

    echo ""
fi

# Test 4: API Items (if logged in)
if [ $HAS_AUTH -eq 1 ]; then
    print_header "TEST 4: API Items - 200 Requests"
    print_endpoint "GET /api/items/"
    print_info "Mengirim 200 requests ke items API"
    echo ""

    success=0
    rate_limited=0
    unauthorized=0
    errors=0

    for i in {1..200}; do
        response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
            "$HOST/api/items/" -o /dev/null 2>&1)

        if [ "$response" = "200" ]; then
            success=$((success + 1))
        elif [ "$response" = "429" ]; then
            rate_limited=$((rate_limited + 1))
        elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
            unauthorized=$((unauthorized + 1))
        else
            errors=$((errors + 1))
        fi

        if [ $((i % 40)) -eq 0 ]; then
            echo -n "."
        fi
    done

    echo ""
    echo ""
    print_info "Hasil API Items (200 requests):"
    echo "  ✅ Sukses (200): $success/200"
    echo "  🚫 Rate Limited (429): $rate_limited/200"
    echo "  🔒 Unauthorized (401/403): $unauthorized/200"
    echo "  ❌ Error lain: $errors/200"
    echo ""

    if [ $rate_limited -eq 0 ]; then
        print_success "API Items tidak kena rate limit"
    else
        print_warning "API Items terkena rate limit ($rate_limited/200)"
    fi

    echo ""
fi

# Test 5: Login Endpoint Protection
print_header "TEST 5: Login Endpoint Protection - 100 Attempts"
print_endpoint "POST /api/benchmark/login"
print_info "Test rate limiting pada login endpoint (brute force protection)"
echo ""

success=0
rate_limited=0
unauthorized=0
errors=0

for i in {1..100}; do
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
    else
        errors=$((errors + 1))
    fi

    if [ $((i % 20)) -eq 0 ]; then
        echo -n "."
    fi
done

echo ""
echo ""
print_info "Hasil Login Endpoint (100 attempts):"
echo "  ✅ Sukses (200): $success/100"
echo "  🚫 Rate Limited (429): $rate_limited/100"
echo "  🔒 Unauthorized (401): $unauthorized/100"
echo "  ❌ Error lain: $errors/100"
echo ""

if [ $rate_limited -gt 50 ]; then
    print_success "Rate limiting bekerja BAIK pada login! ($rate_limited/100 ditolak)"
elif [ $rate_limited -gt 10 ]; then
    print_success "Rate limiting bekerja pada login ($rate_limited/100 ditolak)"
else
    print_warning "Rate limiting kurang ketat pada login ($rate_limited/100 ditolak)"
fi

echo ""

# Summary
print_header "SUMMARY"

# Calculate totals
if [ $HAS_AUTH -eq 1 ]; then
    total_requests=1800
    print_info "Authentication: ✅ BERHASIL"
    print_info "Endpoint yang ditest:"
    echo "  1. /home (public)"
    echo "  2. /dashboard/ (authenticated)"
    echo "  3. /api/dashboard/stats (authenticated API)"
    echo "  4. /api/items/ (authenticated API)"
    echo "  5. /api/benchmark/login (login protection)"
else
    total_requests=1100
    print_info "Authentication: ❌ GAGAL"
    print_info "Endpoint yang ditest:"
    echo "  1. /home (public)"
    echo "  2. /api/benchmark/login (login protection)"
fi

echo ""
print_info "Konfigurasi Rate Limit (app/__init__.py):"
echo "  • Default: 10000 per day, 1000 per hour"
echo "  • API Auth: 10 per minute, 20 per hour"
echo ""

print_info "Kesimpulan:"

if [ $rate_limited_429 -eq 0 ]; then
    echo "  ✅ TIDAK ada rate limiting terdeteksi"
    echo "     Rate limit (1000/hour) sudah cukup longgar untuk benchmarking"
elif [ $rate_limited_429 -lt 100 ]; then
    echo "  ⚠️  Sedikit requests kena rate limit"
    echo "     Masih acceptable untuk benchmarking"
else
    echo "  ❌ Banyak requests kena rate limit"
    echo "     Pertimbangkan menaikkan limit untuk benchmarking"
fi

echo ""
print_success "Test selesai!"
echo ""
if [ $HAS_AUTH -eq 0 ]; then
    print_warning "Login tidak berhasil - hanya test public endpoints"
    print_info "Untuk test lengkap, pastikan:"
    echo "  1. Aplikasi sudah di-restart"
    echo "  2. Admin user sudah dibuat (python3 seed_admin_user.py)"
fi

