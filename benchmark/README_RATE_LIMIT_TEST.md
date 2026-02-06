# Rate Limiting Test Guide

## Overview

Test script ini digunakan untuk memverifikasi konfigurasi rate limiting pada Smart Geo Inventory application. Ada dua versi:
- **Bash version**: `test_rate_limit.sh` (lebih simple, tidak perlu dependencies)
- **Python version**: `test_rate_limit.py` (lebih detail dengan statistik)

## Cara Menggunakan

### Opsi 1: Menggunakan Bash Script (Recommended)

```bash
# Masuk ke directory benchmark
cd /app/Smart-Geo-Inventory/benchmark

# Jalankan test
./test_rate_limit.sh
```

### Opsi 2: Menggunakan Python Script

```bash
# Install requirements (jika belum)
pip3 install requests

# Jalankan test
cd /app/Smart-Geo-Inventory/benchmark
python3 test_rate_limit.py
```

### Opsi 3: Custom Configuration

```bash
# Custom host
HOST=http://172.30.95.251:5000 ./test_rate_limit.sh

# Custom credentials
LOGIN_EMAIL=admin@smartgeo.com LOGIN_PASSWORD=admin123 ./test_rate_limit.sh
```

## Test yang Dilakukan

### Test 1: Login
- Mencoba login ke aplikasi
- Mendapatkan session cookie untuk test berikutnya

### Test 2: Burst Requests (100 requests)
- Mengirim 100 requests sekaligus tanpa delay
- Menguji apakah burst requests memicu rate limiting
- **Expected**: Seharusnya **TIDAK** kena rate limit (karena limit sudah dinaikkan)

### Test 3: Sustained Load (60 requests selama 60 detik)
- Mengirim 60 requests dengan interval 1 detik
- Menguji sustained load selama 1 menit
- **Expected**: Seharusnya **TIDAK** kena rate limit (1 req/sec = 60 req/minit, di bawah 1000/hour)

### Test 4: Public Endpoint (50 requests)
- Menguji endpoint publik (`/home`) tanpa authentication
- **Expected**: Tidak ada rate limiting (public endpoint)

### Test 5: Login Endpoint Rate Limit (20 requests)
- Menguji rate limiting pada login endpoint
- Mengirim 20 login attempts dengan password salah
- **Expected**: Seharusnya kena rate limit setelah beberapa attempts

## Hasil yang Diharapkan

### Konfigurasi Saat Ini
- **Default**: 10000 per day, 1000 per hour
- **API Auth**: 10 per minute, 20 per hour

### Expected Results

| Test | Total Requests | Expected 429 | Description |
|------|---------------|--------------|-------------|
| Test 2: Burst | 100 | 0 | Limit cukup tinggi |
| Test 3: Sustained | 60 | 0 | 1 req/sec < 1000/hour |
| Test 4: Public | 50 | 0 | Public endpoint no limit |
| Test 5: Login | 20 | ±5-10 | Login has strict limit |

### Interpretasi Hasil

#### ✅ Skenario Ideal (Rate Limit Bekerja dengan Benar)
```
Test 2: 0/100 rate limited ✅
Test 3: 0/60 rate limited ✅
Test 4: 0/50 rate limited ✅
Test 5: 5-10/20 rate limited ✅

Rate limiting bekerja dengan baik untuk endpoint yang ketat (login),
tidak mengganggu normal usage untuk endpoint lain.
```

#### ⚠️ Skenario Semua Test Lolos (Rate Limit Tidak Aktif)
```
Test 2: 0/100 rate limited
Test 3: 0/60 rate limited
Test 4: 0/50 rate limited
Test 5: 0/20 rate limited

Kemungkinan:
- Rate limit tidak aktif
- Limit terlalu tinggi
- Konfigurasi salah
```

#### ❌ Skenario Banyak 429 (Rate Limit Terlalu Ketat)
```
Test 2: 50+/100 rate limited
Test 3: 30+/60 rate limited

Rate limiting terlalu ketat untuk benchmarking.
Solusi: NAIKKAN limit di app/__init__.py
```

## Troubleshooting

### Error: command not found: python3
```bash
# Install Python dan requests
apt-get update
apt-get install -y python3 python3-pip
pip3 install requests
```

### Error: Permission denied
```bash
# Make script executable
chmod +x test_rate_limit.sh
```

### Error: Connection refused
```bash
# Cek apakah aplikasi running
curl -k https://172.30.95.249/home

# Atau gunakan HTTP direct
HOST=http://172.30.95.251:5000 ./test_rate_limit.sh
```

### Login gagal
```bash
# Pastikan admin user ada
cd /app/Smart-Geo-Inventory
python3 seed_admin_user.py
```

## Output Example

```
========================================
TEST 1: Login untuk mendapatkan session
========================================

✅ Login berhasil
ℹ️  User: Administrator

========================================
TEST 2: Burst Requests (100 requests sekaligus)
========================================

Progress: 100/100

ℹ️  Hasil Burst Test:
  ✅ Successful (200): 100/100
  🚫 Rate Limited (429): 0/100
  ❌ Other Errors: 0/100
  ⏱️  Total time: 15.23 seconds
  ⚡ Average response time: 152.30ms

✅ Semua requests berhasil (tidak ada rate limiting pada burst test)

========================================
SUMMARY
========================================

ℹ️  Konfigurasi Rate Limit Saat Ini:
  • Default: 10000 per day, 1000 per hour
  • API Auth: 10 per minute, 20 per hour

ℹ️  Hasil Test:
  1. Burst Test (100 req): 0 rate limited
  2. Sustained Load (60 req): 0 rate limited
  3. Public Endpoint (50 req): 0 rate limited
  4. Login Endpoint (20 req): 8 rate limited

✅ Rate limiting bekerja dengan baik (8 requests ditolak dari 230 total)

ℹ️  Rekomendasi:
  ✅ Untuk benchmarking: 10000/day, 1000/hour (sudah dikonfigurasi)
  ✅ Untuk production: 1000/day, 100/hour (lebih ketat)
  ✅ Login endpoint: 10/minute, 20/hour (sudah sesuai)

✅ Rate limiting test selesai!
```

## Best Practices

### Untuk Benchmarking
- Rate limit harus dinaikkan: `10000/day, 1000/hour`
- Agar benchmark tidak terganggu oleh rate limiting

### Untuk Production
- Rate limit lebih ketat: `1000/day, 100/hour`
- Mencegah abuse dan DDoS

### Untuk Sensitive Endpoints (Login)
- Rate limit sangat ketat: `10/minute, 20/hour`
- Mencegah brute force attacks

## Files

- `test_rate_limit.sh` - Bash version (simple, no dependencies)
- `test_rate_limit.py` - Python version (advanced, with statistics)
- `README_RATE_LIMIT_TEST.md` - Documentation ini
