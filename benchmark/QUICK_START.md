# QUICK START - BENCHMARK

## Langkah Cepat (Di Container)

```bash
# 1. Install wrk
sudo apt-get update && sudo apt-get install -y wrk

# 2. Pindah ke directory benchmark
cd benchmark

# 3. Test koneksi (HTTPS dengan self-signed certificate)
curl -k https://172.30.95.249/home

# 4. Jalankan quick test (1 menit)
chmod +x *.sh
./run_benchmark.sh

# 5. Lihat hasil
cat results/quick_run.txt
```

## Full Benchmark (5-10 menit)

```bash
# Jalankan semua scenario
./scenarios.sh

# Lihat semua hasil
ls -lh results/
```

## Test Rate Limiting (2 menit)

```bash
# Cek apakah rate limiting bekerja dengan benar
./test_rate_limit.sh

# Atau gunakan Python version (lebih detail)
python3 test_rate_limit.py
```

Lihat `README_RATE_LIMIT_TEST.md` untuk detail tentang rate limiting test.

## IP Address Reference

- **rev-proxy**: 172.30.95.249 (default target)
- **apps**: 172.30.95.251:5000 (opsional - direct access)
- **db**: 172.30.95.250 (database)

## Konfigurasi Cepat

```bash
# Ganti target ke apps (tanpa proxy)
HOST=http://172.30.95.251:5000 ./scenarios.sh

# Ganti target ke HTTPS (self-signed cert)
HOST=https://172.30.95.249 CURL_OPTS="-k" ./scenarios.sh

# Custom load
THREADS=8 CONNECTIONS=200 DURATION=60s ./scenarios.sh
```

Lihat `CARA_PAKAI.md` untuk dokumentasi lengkap.
