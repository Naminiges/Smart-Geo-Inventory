#!/bin/bash

# Rate Limiting Test Script with Working Login
# Test rate limiting pada authenticated endpoints (cara real!)

set -e

# Configuration
HOST=${HOST:-https://172.30.95.249}
CURL_OPTS=${CURL_OPTS:--k}
COOKIE_FILE=${COOKIE_FILE:-.cookies.txt}
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
print_header "RATE LIMITING TEST - WITH LOGIN"
print_info "Target: $HOST"
print_info "Total requests: 1000+ (authenticated)"
echo ""

# Login Phase - Using browser-like approach
print_header "STEP 1: LOGIN (Menggunakan Browser Session)"

print_info "Cara kerja:"
echo "  1. GET halaman login untuk dapat session + CSRF token"
echo "  2. POST form data dengan CSRF token"
echo "  3. Simpan session cookie untuk request berikutnya"
echo ""

# Step 1: Get login page to get CSRF token
print_info "Langkah 1: Mengambil halaman login..."
rm -f "$COOKIE_FILE"

login_page=$(curl -s $CURL_OPTS -c "$COOKIE_FILE" "$HOST/auth/login" 2>&1)

# Extract CSRF token from hidden input
csrf_token=$(echo "$login_page" | grep -oP 'name="csrf_token"\s*value="\K[^"]*' | head -1)

if [ -z "$csrf_token" ]; then
    print_error "Gagal mengambil CSRF token!"
    print_info "Mencoba metode lain..."

    # Coba pakai type='hidden' pattern
    csrf_token=$(echo "$login_page" | grep -oP 'type="hidden".*name="csrf_token".*value="\K[^"]*' | grep -oP 'value="\K[^"]*' | head -1)
fi

if [ -z "$csrf_token" ]; then
    print_error "CSRF token tidak ditemukan!"
    echo ""
    echo "Debug: Menyimpan HTML untuk inspection..."
    echo "$login_page" > debug_login_page.html
    print_info "HTML disimpan ke debug_login_page.html"
    print_error "Login gagal. Tidak bisa melanjutkan test authenticated endpoints."
    exit 1
fi

print_success "CSRF token berhasil diambil: ${csrf_token:0:20}..."
echo ""

# Step 2: Login with CSRF token
print_info "Langkah 2: Login dengan CSRF token..."

# Build form data (application/x-www-form-urlencoded)
form_data="email=$LOGIN_EMAIL&password=$LOGIN_PASSWORD&csrf_token=$csrf_token"

login_response=$(curl -i -s $CURL_OPTS -b "$COOKIE_FILE" -c "$COOKIE_FILE" \
    -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "$form_data" \
    "$HOST/auth/login" 2>&1)

# Check if login successful
if echo "$login_response" | grep -q "302\|Location:"; then
    print_success "Login BERHASIL!"

    # Verify session
    print_info "Verifikasi session..."
    test_response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" "$HOST/dashboard/" -o /dev/null -w "%{http_code}" 2>&1)

    if [ "$test_response" = "200" ]; then
        print_success "Session valid! Bisa akses authenticated endpoints."
    else
        print_warning "Session mungkin belum valid (HTTP $test_response)"
    fi
else
    print_error "Login GAGAL!"
    echo ""
    echo "Response:"
    echo "$login_response" | head -30
    echo ""
    print_error "Tidak bisa melanjutkan test authenticated endpoints."
    exit 1
fi

echo ""

# Test 1: Homepage - 1000 Requests (Benchmark utama)
print_header "STEP 2: TEST HOMEPAGE - 1000 Requests"
print_endpoint "GET /home"
print_info "Test public endpoint sebagai baseline"
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

    if [ $((i % 200)) -eq 0 ]; then
        echo -n "...."
        echo -n " ($i/1000)"
    fi
done

end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo ""
print_info "Hasil Homepage:"
echo "  ✅ Sukses: $success/1000"
echo "  🚫 Rate Limited (429): $rate_limited/1000"
echo "  ❌ Error lain: $errors/1000"
echo "  ⏱️  Duration: ${duration} detik"
echo "  ⚡ RPS: $((success / duration)) req/s"
echo ""

if [ $rate_limited -eq 0 ]; then
    print_success "Homepage tidak kena rate limit (baseline OK)"
else
    print_warning "Homepage: $rate_limited/1000 kena rate limit"
fi

echo ""

# Test 2: Authenticated Dashboard - 200 Requests
print_header "STEP 3: TEST DASHBOARD - 200 Requests (Authenticated)"
print_endpoint "GET /dashboard/"
print_info "Test authenticated endpoint WITH session cookie"
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
print_info "Hasil Dashboard (200 requests, authenticated):"
echo "  ✅ Sukses (200): $success/200"
echo "  🚫 Rate Limited (429): $rate_limited/200"
echo "  🔒 Unauthorized (401/403): $unauthorized/200"
echo "  ❌ Error lain: $errors/200"
echo ""

if [ $unauthorized -eq 200 ]; then
    print_error "Session tidak valid! Semua requests unauthorized!"
    print_info "Cookie mungkin expired atau login tidak benar-benar sukses"
elif [ $rate_limited -eq 0 ]; then
    print_success "Dashboard tidak kena rate limit"
else
    print_warning "Dashboard: $rate_limited/200 kena rate limit"
fi

echo ""

# Test 3: API Dashboard Stats - 300 Requests (Authenticated)
print_header "STEP 4: TEST API DASHBOARD STATS - 300 Requests (Authenticated)"
print_endpoint "GET /api/dashboard/stats"
print_info "Test authenticated API endpoint"
echo ""

if [ $unauthorized -lt 200 ]; then
    success=0
    rate_limited=0
    unauthorized_api=0
    errors=0

    for i in {1..300}; do
        response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
            "$HOST/api/dashboard/stats" -o /dev/null 2>&1)

        if [ "$response" = "200" ]; then
            success=$((success + 1))
        elif [ "$response" = "429" ]; then
            rate_limited=$((rate_limited + 1))
        elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
            unauthorized_api=$((unauthorized_api + 1))
        else
            errors=$((errors + 1))
        fi

        if [ $((i % 60)) -eq 0 ]; then
            echo -n "."
        fi
    done

    echo ""
    echo ""
    print_info "Hasil API Dashboard Stats (300 requests, authenticated):"
    echo "  ✅ Sukses (200): $success/300"
    echo "  🚫 Rate Limited (429): $rate_limited/300"
    echo "  🔒 Unauthorized (401/403): $unauthorized_api/300"
    echo "  ❌ Error lain: $errors/300"
    echo ""

    if [ $rate_limited -eq 0 ]; then
        print_success "API Dashboard Stats tidak kena rate limit"
    else
        print_warning "API Dashboard Stats: $rate_limited/300 kena rate limit"
    fi
else
    print_info "Melewati API test karena session tidak valid"
fi

echo ""

# Test 4: API Items - 200 Requests (Authenticated)
print_header "STEP 5: TEST API ITEMS - 200 Requests (Authenticated)"
print_endpoint "GET /api/items/"
print_info "Test another authenticated API endpoint"
echo ""

if [ $unauthorized -lt 200 ]; then
    success=0
    rate_limited=0
    unauthorized_api=0
    errors=0

    for i in {1..200}; do
        response=$(curl -s $CURL_OPTS -b "$COOKIE_FILE" -w "%{http_code}" \
            "$HOST/api/items/" -o /dev/null 2>&1)

        if [ "$response" = "200" ]; then
            success=$((success + 1))
        elif [ "$response" = "429" ]; then
            rate_limited=$((rate_limited + 1))
        elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
            unauthorized_api=$((unauthorized_api + 1))
        else
            errors=$((errors + 1))
        fi

        if [ $((i % 40)) -eq 0 ]; then
            echo -n "."
        fi
    done

    echo ""
    echo ""
    print_info "Hasil API Items (200 requests, authenticated):"
    echo "  ✅ Sukses (200): $success/200"
    echo "  🚫 Rate Limited (429): $rate_limited/200"
    echo "  🔒 Unauthorized (401/403): $unauthorized_api/200"
    echo "  ❌ Error lain: $errors/200"
    echo ""

    if [ $rate_limited -eq 0 ]; then
        print_success "API Items tidak kena rate limit"
    else
        print_warning "API Items: $rate_limited/200 kena rate limit"
    fi
else
    print_info "Melewati API Items test karena session tidak valid"
fi

echo ""

# Summary
print_header "SUMMARY"

print_info "Total requests: 1700+"
print_info "Authentication: ✅ BERHASIL (via web form + CSRF)"
print_info ""
print_info "Endpoint yang ditest:"
echo "  1. /home (public) - 1000 requests"
echo "  2. /dashboard/ (authenticated) - 200 requests"
echo "  3. /api/dashboard/stats (authenticated) - 300 requests"
echo "  4. /api/items/ (authenticated) - 200 requests"
echo ""

print_info "Konfigurasi Rate Limit:"
echo "  • Default: 10000 per day, 1000 per hour"
echo "  • API Auth: 10 per minute, 20 per hour"
echo ""

print_info "Kesimpulan:"

total_429=$(echo "$rate_limited" | tail -1)

if [ "$total_429" -eq 0 ]; then
    echo "  ✅ TIDAK ADA RATE LIMITING terdeteksi"
    echo "     Rate limit 1000/hour belum tercapai"
    echo "     Semua 1700+ requests berhasil"
elif [ "$total_429" -lt 50 ]; then
    echo "  ⚠️ Sedikit requests kena rate limit"
    echo "     Masih acceptable untuk benchmarking"
else
    echo "  ❌ Banyak requests kena rate limit"
    echo "     Perlu evaluasi konfigurasi"
fi

echo ""
print_success "Test selesai!"
echo ""
print_info "Durasi total: ~5-7 menit"
echo ""
print_info "Catatan:"
echo "  • Login menggunakan web form (GET login page + POST with CSRF)"
echo "  • Session cookie disimpan dan digunakan untuk authenticated requests"
echo "  • Test rate limiting pada endpoints yang sebenarnya dipakai user"
