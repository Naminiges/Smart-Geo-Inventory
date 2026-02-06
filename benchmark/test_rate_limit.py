#!/usr/bin/env python3
"""
Rate Limiting Test Script for Smart Geo Inventory
Tests rate limiting configuration with detailed statistics
"""

import requests
import time
import json
from collections import defaultdict
from datetime import datetime, timedelta

# Configuration
HOST = "https://172.30.95.249"
LOGIN_EMAIL = "admin@smartgeo.com"
LOGIN_PASSWORD = "admin123"
VERIFY_SSL = False  # Set to False for self-signed certs

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(title):
    print(f"\n{Colors.BLUE}{'='*50}{Colors.NC}")
    print(f"{Colors.BLUE}{title}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}\n")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.NC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")

def login():
    """Login and get session cookie"""
    print_header("TEST 1: Login untuk mendapatkan session")

    url = f"{HOST}/api/benchmark/login"
    payload = {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }

    try:
        response = requests.post(url, json=payload, verify=VERIFY_SSL)

        if response.status_code == 200 and response.json().get('success'):
            print_success("Login berhasil")
            print_info(f"User: {response.json().get('user', {}).get('name', 'Unknown')}")
            return response.cookies
        else:
            print_error(f"Login gagal: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Exception during login: {str(e)}")
        return None

def test_burst_requests(cookies):
    """Test burst requests (many requests at once)"""
    print_header("TEST 2: Burst Requests (100 requests sekaligus)")

    print_info("Mengirim 100 requests sekaligus...")
    print_info("Jika rate limit aktif, sebagian request akan gagal dengan 429")

    url = f"{HOST}/api/dashboard/stats"
    results = defaultdict(int)
    response_times = []

    start_time = time.time()

    for i in range(100):
        try:
            req_start = time.time()
            response = requests.get(url, cookies=cookies, verify=VERIFY_SSL)
            req_end = time.time()

            response_times.append(req_end - req_start)
            results[response.status_code] += 1

        except Exception as e:
            print_error(f"Request {i+1} failed: {str(e)}")
            results['error'] += 1

        if (i + 1) % 20 == 0:
            print(f"Progress: {i+1}/100", end='\r')

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n{' ' * 50}")  # Clear progress line
    print_info("Hasil Burst Test:")
    print(f"  ✅ Successful (200): {results.get(200, 0)}/100")
    print(f"  🚫 Rate Limited (429): {results.get(429, 0)}/100")
    print(f"  ❌ Other Errors: {sum(results.values()) - results.get(200, 0) - results.get(429, 0)}/100")
    print(f"  ⏱️  Total time: {total_time:.2f} seconds")
    print(f"  ⚡ Average response time: {sum(response_times)/len(response_times)*1000:.2f}ms")

    if results.get(429, 0) > 0:
        print_warning(f"Rate limiting terdeteksi! {results.get(429, 0)} requests ditolak")
    else:
        print_success("Semua requests berhasil (tidak ada rate limiting pada burst test)")

    return results

def test_sustained_load(cookies):
    """Test sustained load (requests over time)"""
    print_header("TEST 3: Sustained Load (60 requests selama 60 detik)")

    print_info("Mengirim 60 requests selama 60 detik (1 req/detik)")
    print_info("Test apakah sustained load memicu rate limiting")

    url = f"{HOST}/api/dashboard/stats"
    results = defaultdict(int)
    response_times = []

    start_time = time.time()

    for i in range(60):
        try:
            req_start = time.time()
            response = requests.get(url, cookies=cookies, verify=VERIFY_SSL)
            req_end = time.time()

            response_times.append(req_end - req_start)
            results[response.status_code] += 1

        except Exception as e:
            results['error'] += 1

        print(f"Progress: {i+1}/60", end='\r')
        time.sleep(1)  # 1 request per second

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n{' ' * 50}")  # Clear progress line
    print_info("Hasil Sustained Load Test:")
    print(f"  ✅ Successful (200): {results.get(200, 0)}/60")
    print(f"  🚫 Rate Limited (429): {results.get(429, 0)}/60")
    print(f"  ❌ Other Errors: {sum(results.values()) - results.get(200, 0) - results.get(429, 0)}/60")
    print(f"  ⏱️  Total time: {total_time:.2f} seconds")
    print(f"  ⚡ Average response time: {sum(response_times)/len(response_times)*1000:.2f}ms")

    if results.get(429, 0) > 0:
        print_warning(f"Rate limiting terdeteksi pada sustained load!")
    else:
        print_success("Semua requests berhasil pada sustained load")

    return results

def test_public_endpoint():
    """Test public endpoint rate limiting"""
    print_header("TEST 4: Public Endpoint - Homepage")

    print_info("Test rate limiting pada public endpoint (tanpa authentication)")

    url = f"{HOST}/home"
    results = defaultdict(int)
    response_times = []

    for i in range(50):
        try:
            req_start = time.time()
            response = requests.get(url, verify=VERIFY_SSL)
            req_end = time.time()

            response_times.append(req_end - req_start)
            results[response.status_code] += 1

        except Exception as e:
            results['error'] += 1

        print(f"Progress: {i+1}/50", end='\r')

    print(f"\n{' ' * 50}")  # Clear progress line
    print_info("Hasil Public Endpoint Test:")
    print(f"  ✅ Successful (200): {results.get(200, 0)}/50")
    print(f"  🚫 Rate Limited (429): {results.get(429, 0)}/50")
    print(f"  ❌ Other Errors: {sum(results.values()) - results.get(200, 0) - results.get(429, 0)}/50")
    print(f"  ⚡ Average response time: {sum(response_times)/len(response_times)*1000:.2f}ms")

    if results.get(429, 0) > 0:
        print_warning("Rate limiting aktif pada public endpoint")
    else:
        print_success("Public endpoint tidak memiliki rate limiting (expected)")

    return results

def test_login_rate_limit():
    """Test login endpoint rate limiting"""
    print_header("TEST 5: API Login Endpoint (Strict Rate Limit)")

    print_info("Test rate limiting pada /api/benchmark/login")
    print_info("Harusnya memiliki rate limit yang lebih ketat")

    url = f"{HOST}/api/benchmark/login"
    results = defaultdict(int)

    for i in range(20):
        try:
            payload = {
                "email": "test@test.com",
                "password": "wrongpassword"
            }
            response = requests.post(url, json=payload, verify=VERIFY_SSL)
            results[response.status_code] += 1

        except Exception as e:
            results['error'] += 1

        print(f"Progress: {i+1}/20", end='\r')
        time.sleep(0.1)  # Small delay

    print(f"\n{' ' * 50}")  # Clear progress line
    print_info("Hasil Login Endpoint Test (20 attempts):")
    print(f"  ✅ Successful (200): {results.get(200, 0)}/20")
    print(f"  🚫 Rate Limited (429): {results.get(429, 0)}/20")
    print(f"  ❌ Unauthorized (401): {results.get(401, 0)}/20")
    print(f"  ❌ Other Errors: {sum(results.values()) - results.get(200, 0) - results.get(429, 0) - results.get(401, 0)}/20")

    if results.get(429, 0) > 0:
        print_warning(f"Rate limiting aktif pada login endpoint (bagus!)")
    else:
        print_warning("Rate limiting tidak terdeteksi pada login endpoint")

    return results

def main():
    """Main test function"""
    print_header("RATE LIMITING TEST - SMART GEO INVENTORY")
    print_info(f"Target: {HOST}")
    print_info(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Rate Limit Config: 10000/day, 1000/hour (default)")

    # Test 1: Login
    cookies = login()
    if not cookies:
        print_error("Gagal login. Exiting...")
        return

    # Test 2: Burst requests
    burst_results = test_burst_requests(cookies)
    time.sleep(2)

    # Test 3: Sustained load
    sustained_results = test_sustained_load(cookies)
    time.sleep(2)

    # Test 4: Public endpoint
    public_results = test_public_endpoint()
    time.sleep(2)

    # Test 5: Login rate limit
    login_results = test_login_rate_limit()

    # Summary
    print_header("SUMMARY")

    print_info("Konfigurasi Rate Limit Saat Ini:")
    print("  • Default: 10000 per day, 1000 per hour")
    print("  • API Auth: 10 per minute, 20 per hour")
    print()

    print_info "Hasil Test:"
    print(f"  1. Burst Test (100 req): {burst_results.get(429, 0)} rate limited")
    print(f"  2. Sustained Load (60 req): {sustained_results.get(429, 0)} rate limited")
    print(f"  3. Public Endpoint (50 req): {public_results.get(429, 0)} rate limited")
    print(f"  4. Login Endpoint (20 req): {login_results.get(429, 0)} rate limited")
    print()

    total_429 = (burst_results.get(429, 0) + sustained_results.get(429, 0) +
                 public_results.get(429, 0) + login_results.get(429, 0))

    if total_429 == 0:
        print_warning("Rate limiting tidak terdeteksi pada semua test!")
        print_info("Kemungkinan:")
        print("  1. Rate limit tidak aktif/enabled")
        print("  2. Limit terlalu tinggi")
        print("  3. Konfigurasi tidak benar")
    elif total_429 > 50:
        print_error("Rate limiting terlalu ketat! Banyak requests yang ditolak.")
        print_info("Pertimbangkan untuk menaikkan limit untuk benchmarking.")
    else:
        print_success(f"Rate limiting bekerja dengan baik ({total_429} requests ditolak dari 230 total)")

    print()
    print_info "Rekomendasi:"
    print("  ✅ Untuk benchmarking: 10000/day, 1000/hour (sudah dikonfigurasi)")
    print("  ✅ Untuk production: 1000/day, 100/hour (lebih ketat)")
    print("  ✅ Login endpoint: 10/minute, 20/hour (sudah sesuai)")
    print()

    print_success("Rate limiting test selesai!")

if __name__ == "__main__":
    main()
