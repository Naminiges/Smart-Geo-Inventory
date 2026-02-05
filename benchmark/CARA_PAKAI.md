# CARA PAKAI - BENCHMARK SMART GEO INVENTORY

## Environment Setup

Aplikasi berjalan di container dengan konfigurasi:
- **apps**: 172.30.95.251 (Flask application)
- **db**: 172.30.95.250 (Database)
- **rev-proxy**: 172.30.95.249 (Reverse Proxy - nginx/apache)

**Benchmark akan dijalankan ke rev-proxy (172.30.95.249)**

---

## SETELAH PULL DARI GIT

### 1. Install wrk di Container

```bash
# Cek apakah wrk sudah terinstall
wrk --version

# Jika belum, install wrk
# Untuk Ubuntu/Debian:
sudo apt-get update
sudo apt-get install -y wrk

# Jika package tidak tersedia, build dari source:
cd /tmp
git clone https://github.com/wg/wrk.git
cd wrk
make
sudo cp wrk /usr/local/bin/
```

### 2. Pindah ke Directory Benchmark

```bash
cd /path/to/Smart-Geo-Inventory/benchmark
```

### 3. Test Connection ke Aplikasi

```bash
# Test koneksi ke rev-proxy (default)
curl http://172.30.95.249/home

# Atau test langsung ke apps (opsional)
curl http://172.30.95.251:5000/home
```

Jika berhasil, akan muncul HTML dari halaman home.

### 4. Jalankan Benchmark

#### Opsi A: Quick Test (Cepat - 1 menit)

```bash
# Pastikan script executable
chmod +x *.sh

# Jalankan quick test
./run_benchmark.sh
```

Hasil disimpan di: `results/quick_run.txt`

#### Opsi B: Full Benchmark Scenarios (Lengkap - 5-10 menit)

```bash
# Jalankan semua scenario
./scenarios.sh
```

Hasil disimpan di: `results/` dengan nama file timestamped

---

## SCENARIO YANG DIUJI

1. **Light Load** - Homepage (2 threads, 10 connections, 10s)
2. **Medium Load** - Homepage (4 threads, 50 connections, 30s)
3. **Heavy Load** - Homepage (8 threads, 200 connections, 60s)
4. **API - Items List** (4 threads, 50 connections, 30s)
5. **API - Dashboard** (4 threads, 50 connections, 30s)
6. **API - Map Data** (4 threads, 50 connections, 30s)
7. **Stress Test** - Sustained load (12 threads, 500 connections, 120s)
8. **Spike Test** - Sudden load (16 threads, 1000 connections, 30s)

---

## KONFIGURASI OPSIONAL

### Mengganti Target Host

Default: rev-proxy (172.30.95.249)

Untuk akses langsung ke apps (tanpa proxy):

```bash
# Edit file scenarios.sh atau run_benchmark.sh
# Uncomment baris ini:
HOST=${HOST:-http://172.30.95.251:5000}
```

Atau set dari command line:

```bash
HOST=http://172.30.95.251:5000 ./scenarios.sh
```

### Mengganti Durasi/Threads/Connections

```bash
# Set custom duration
DURATION=60s ./scenarios.sh

# Set custom threads dan connections
THREADS=8 CONNECTIONS=200 ./scenarios.sh

# Combine all
HOST=http://172.30.95.249 DURATION=60s THREADS=8 CONNECTIONS=200 ./scenarios.sh
```

---

## MELIHAT HASIL

```bash
# Lihat semua file hasil
ls -lh results/

# Lihat hasil tertentu
cat results/02_homepage_medium_20241205_143022.txt

# Lihat hasil terbaru
ls -lt results/ | head -2

# Monitoring real-time (jika menjalankan di terminal terpisah)
watch -n 1 'ls -lh results/'
```

---

## CONTOH OUTPUT

```
=== BENCHMARK RESULTS ===
Path tested: /home
Method: GET

Status Code Distribution:
  200: 5000 (100.00%)

Latency Statistics:
  Min: 5.23ms
  Max: 156.78ms
  Mean: 23.45ms
  Std Dev: 12.34ms

Percentile Distribution:
  P50.0: 21.34ms
  P75.0: 28.90ms
  P90.0: 35.67ms
  P95.0: 42.12ms
  P99.0: 78.45ms
  P99.9: 134.56ms

Request Statistics:
  Total requests: 5000
  Successful: 5000
  Errors: 0

Throughput:
  Requests/sec: 166.67
  Bytes transferred: 12.45 MB
  Bytes/sec: 0.42 MB/s
```

---

## TROUBLESHOOTING

### Error: wrk: command not found

**Solusi**: Install wrk (lihat langkah 1 di atas)

### Error: Permission denied

**Solusi**:
```bash
chmod +x *.sh
```

### Error: Connection refused

**Solusi**:
```bash
# Test koneksi
curl http://172.30.95.249/home
curl http://172.30.95.251:5000/home

# Cek status container
# (sesuaikan dengan command di environment Anda)

# Ping IP addresses
ping -c 3 172.30.95.249
ping -c 3 172.30.95.251
```

### Error: Bad Argument

**Solusi**:
```bash
# Pastikan di directory benchmark
pwd  # Harus: .../Smart-Geo-Inventory/benchmark

# Cek file ada
ls wrk.lua scenarios.sh
```

### High Error Rate / Banyak Request Gagal

**Kemungkinan penyebab**:
1. Container kelebihan load (CPU/RAM)
2. Network issue antar container
3. Database connection limit
4. Flask workers tidak cukup

**Solusi**:
```bash
# Cek resources
htop
# atau
top

# Cek network
netstat -tlnp | grep 5000

# Kurangi threads/connections
THREADS=2 CONNECTIONS=50 ./scenarios.sh
```

---

## TIPS & BEST PRACTICES

1. **Jalankan quick test dulu** sebelum full benchmark
2. **Pastikan tidak ada traffic lain** saat benchmark (user tidak sedang pakai)
3. **Monitor resources** selama benchmark dengan `htop` di terminal lain
4. **Ulangi 2-3 kali** untuk hasil yang lebih akurat
5. **Simpan hasil** dengan copy folder `results/` sebelum dihapus
6. **Test di waktu sepi** untuk hasil yang lebih bersih

---

## FLOW LENGKAP (CHECKLIST)

```bash
✅ 1. Pull dari git
   git pull origin main

✅ 2. Install wrk (jika belum)
   sudo apt-get install -y wrk

✅ 3. Pindah directory
   cd benchmark

✅ 4. Test connection
   curl http://172.30.95.249/home

✅ 5. Jalankan benchmark
   chmod +x *.sh
   ./run_benchmark.sh          # Quick test
   # atau
   ./scenarios.sh              # Full benchmark

✅ 6. Lihat hasil
   ls results/
   cat results/*.txt
```

**Total waktu: 10-20 menit (untuk full benchmark)**

---

## FILE YANG DIBUTUHKAN

Minimal, pastikan file-file ini ada di directory `benchmark/`:

```
✅ wrk.lua              - Script utama wrk (WAJIB)
✅ scenarios.sh         - Script scenario lengkap (WAJIB)
✅ run_benchmark.sh     - Script quick test (OPSIONAL)
✅ CARA_PAKAI.md        - Panduan ini (OPSIONAL)
```

---

## QUESTIONS?

Jika ada masalah atau pertanyaan, hubungi tim development Smart Geo Inventory.
