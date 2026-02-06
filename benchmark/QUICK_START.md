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

## Test Rate Limiting

### Basic Test (2-3 menit)

```bash
# Test dengan login - 1700 requests
./test_rate_limit.sh
```

### Comprehensive Test untuk Laporan (8-10 menit) ⭐

```bash
# 4 scenarios yang menunjukkan efek rate limiting dengan jelas
./test_rate_limit_comprehensive.sh
```

** scenarios:**
1. **Baseline** (100 req) - Traffic rendah
2. **Half Limit** (500 req) - Traffic sedang (50% batas)
3. **At Limit** (1200 req) - Traffic tinggi (melebihi batas) ⭐
4. **Authenticated** (500 req) - Test endpoints dengan login

**Recommended untuk laporan:** Gunakan `test_rate_limit_comprehensive.sh`

Lihat `SCENARIO_LAPORAN.md` untuk dokumentasi lengkap tentang scenarios dan interpretasi hasil.

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
