# Rate Limiting Test Guide

## Overview

Test script ini digunakan untuk memverifikasi konfigurasi rate limiting pada Smart Geo Inventory application.

**4 Versi Tersedia:**

| Script | Login Required | Dependencies | Best For |
|--------|---------------|--------------|----------|
| `test_rate_limit_simple.sh` | ❌ NO | None (only curl) | **Quick test** (Recommended!) |
| `test_rate_limit_fallback.sh` | ⚠️ Auto-detect | None (only curl) | **Best choice** - tries all methods |
| `test_rate_limit.sh` | ❌ NO | None | Comprehensive test |
| `test_rate_limit.py` | ✅ YES | Python + requests | Advanced statistics |

## Cara Menggunakan

### ⭐ Opsi 0: Fallback Version (BEST - Auto-detect)

```bash
# Jalankan test yang mencoba semua method
./test_rate_limit_fallback.sh
```

**Keuntungan:**
- ✅ **Auto-detect** - coba semua login method
- ✅ **Graceful fallback** - lanjut tanpa auth jika login gagal
- ✅ **Universal** - jalan di semua situasi
- ✅ **Informative** - kasih tahu apa yang terjadi

### ✅ Opsi 1: Simple Version (TANPA Login - Recommended)

```bash
# Masuk ke directory benchmark
cd /app/Smart-Geo-Inventory/benchmark

# Jalankan test (TIDAK perlu login!)
./test_rate_limit_simple.sh
```

**Keuntungan:**
- ✅ **Tidak perlu login** - langsung jalan
- ✅ **Tidak perlu dependencies** - hanya butuh curl
- ✅ **Cepat** - selesai dalam ~1 menit
- ✅ **Simple** - mudah dimengerti

### Opsi 2: Comprehensive Bash Version

```bash
# Jalankan test lengkap
./test_rate_limit.sh
```

### Opsi 3: Python Version (Perlu Login)

```bash
# Install requirements
pip3 install requests

# Jalankan test
python3 test_rate_limit.py
```

### Opsi 4: Custom Configuration

```bash
# Custom host
HOST=http://172.30.95.251:5000 ./test_rate_limit_simple.sh
```

## Test yang Dilakukan

### Simple Version (`test_rate_limit_simple.sh`):

| Test | Requests | Endpoint | Purpose | Expected 429 |
|------|----------|----------|---------|--------------|
| 1. Homepage Burst | 100 sekaligus | `/home` | Public endpoint burst | 0 |
| 2. Homepage Sustained | 60 selama 60s | `/home` | 1 req/sec load | 0 |
| 3. Login Rate Limit | 20 | `/api/benchmark/login` | Login protection | ±5-10 |
| 4. Concurrent | 50 | Multiple endpoints | Concurrent load | 0-5 |

### Comprehensive Version (`test_rate_limit.sh`):

Test yang sama tapi dengan statistik lebih detail.

### Python Version (`test_rate_limit.py`):

Test yang sama **TAPI memerlukan login** untuk test authenticated endpoints.

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

- `test_rate_limit_simple.sh` - Simple version (no login, no dependencies)
- `test_rate_limit_fallback.sh` - Fallback version (auto-detect login)
- `test_rate_limit.sh` - Comprehensive version (detailed statistics)
- `test_rate_limit.py` - Python version (advanced, with statistics)
- `README_RATE_LIMIT_TEST.md` - Documentation ini

## ⚠️ PENTING: Jika Login Gagal

### Gejala:
- Script return 404 saat login
- Error "Benchmark API endpoint tidak tersedia"
- Python script error saat mencoba login

### Solusi: **RESTART APLIKASI**

Setelah menambahkan endpoint `/api/benchmark/login`, aplikasi **HARUS di-restart**:

```bash
# Cek apakah endpoint tersedia
curl -k https://172.30.95.249/api/benchmark/login

# Jika return 404, restart aplikasi:
docker restart <container_name>
# ATAU
systemctl restart smart-geo-inventory

# Setelah restart, test lagi
curl -k https://172.30.95.249/api/benchmark/login
# Harus return: Method Not Allowed (bukan 404)
```

### Verification:

```bash
# Test endpoint manual
curl -k https://172.30.95.249/api/benchmark/login

# Response yang diharapkan:
# {"message":"The method is not allowed..."}  ← Endpoint ada tapi method salah (NORMAL!)
#
# BUKAN:
# {"error":"Not Found"}  ← Endpoint tidak ada (perlu restart!)
```

### Alternative: Gunakan Script Fallback

Jika tidak mau restart, gunakan `test_rate_limit_fallback.sh`:

```bash
./test_rate_limit_fallback.sh
```

Script ini akan:
1. Coba login dulu
2. Jika gagal, lanjut test public endpoints saja
3. Tetap bisa test rate limiting dengan baik
