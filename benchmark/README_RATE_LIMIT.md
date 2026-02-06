# Rate Limiting Test

## Cara Menggunakan

```bash
cd /app/Smart-Geo-Inventory/benchmark

# Jalankan test (TIDAK perlu login!)
./test_rate_limit.sh
```

## Test yang Dilakukan

| Test | Requests | Description |
|------|----------|-------------|
| 1. Burst | 100 sekaligus | Test burst load ke `/home` |
| 2. Sustained | 60 (1 req/detik) | Test sustained load selama 60 detik |
| 3. Login Protection | 20 | Test rate limiting pada login endpoint |
| 4. Multiple Endpoints | 50 random | Test ke berbagai endpoints |

## Hasil yang Diharapkan

Dengan konfigurasi saat ini (`10000/day, 1000/hour`):

- ✅ **Homepage Burst**: 0/100 rate limited (public endpoint)
- ✅ **Sustained Load**: 0/60 rate limited (1 req/sec < 1000/hour)
- ⚠️ **Login Endpoint**: ±5-10/20 rate limited (protection aktif)

## Interpretasi

**Tidak ada rate limiting pada public endpoints?** ✅ **NORMAL!**
- Rate limit sudah dinaikkan untuk benchmarking
- Public endpoints memang seharusnya tidak dibatasi

**Rate limiting aktif pada login endpoint?** ✅ **BAGUS!**
- Login endpoint memiliki rate limit yang lebih ketat
- Melindungi dari brute force attacks

## Troubleshooting

### Error: Connection refused
```bash
# Cek koneksi
curl -k https://172.30.95.249/home
```

### Rate limiting terlalu ketat (banyak 429)
```bash
# Cek konfigurasi di app/__init__.py
# Pastikan: default_limits=["10000 per day", "1000 per hour"]
```

## Files

- `test_rate_limit.sh` - Test script (langsung jalan, no dependencies)
