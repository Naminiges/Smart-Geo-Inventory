# Rate Limiting Test

## Cara Menggunakan

```bash
cd /app/Smart-Geo-Inventory/benchmark

# Jalankan test (Otomatis coba login)
./test_rate_limit.sh
```

## Test yang Dilakukan (Total: 1000-1800 requests)

| # | Test | Requests | Endpoint | Auth Required |
|---|------|----------|----------|---------------|
| 1 | Homepage Benchmark | **1000** | `/home` | ❌ No |
| 2 | Dashboard | 200 | `/dashboard/` | ✅ Yes |
| 3 | API Dashboard Stats | 300 | `/api/dashboard/stats` | ✅ Yes |
| 4 | API Items | 200 | `/api/items/` | ✅ Yes |
| 5 | Login Protection | 100 | `/api/benchmark/login` | ❌ No |

## Hasil yang Diharapkan

### Dengan Konfigurasi Saat Ini:
- **Default**: 10000 per day, **1000 per hour** ⚠️
- **API Auth**: 10 per minute, 20 per hour

### Expected Results:

| Test | Expected 429 | Description |
|------|--------------|-------------|
| Homepage (1000) | **0-50** | Mungkin kena rate limit jika mendekati 1000/hour |
| Dashboard (200) | 0 | Seharusnya tidak kena (amount kecil) |
| API Stats (300) | 0 | Seharusnya tidak kena |
| API Items (200) | 0 | Seharusnya tidak kena |
| Login (100) | **10-50+** | **Harus kena rate limit** (protection aktif) |

## Interpretasi Hasil

### Scenario 1: Homepage 0/1000 Limited
✅ **IDEAL** - Rate limit bekerja, belum kena batas 1000/hour

### Scenario 2: Homepage 100-500/1000 Limited
⚠️ **NORMAL** - Rate limit aktif, mendekati batas 1000/hour

### Scenario 3: Homepage >500/1000 Limited
❌ **TERLALU KETAT** - Perlu naikkan limit untuk benchmarking

### Scenario 4: Login 0/100 Limited
⚠️ **KURANG KETAT** - Login protection kurang aktif

### Scenario 5: Login 10-50/100 Limited
✅ **BAGUS** - Rate limiting bekerja pada login endpoint

## Catatan Penting

### Jika Login Gagal:
Script akan otomatis lanjut test public endpoints saja:
- ✅ Homepage 1000 requests
- ✅ Login protection test
- ❌ Tidak test authenticated endpoints

### Untuk Test Lengkap:
1. Pastikan aplikasi sudah di-restart
2. Pastikan admin user ada: `python3 seed_admin_user.py`
3. Script akan auto-login jika endpoint tersedia

## Troubleshooting

### Homepage banyak kena rate limit?
```bash
# Cek konfigurasi di app/__init__.py
# Pastikan: default_limits=["10000 per day", "1000 per hour"]
```

### Login gagal (404)?
```bash
# Restart aplikasi untuk load endpoint baru
docker restart <container>
# ATAU
systemctl restart smart-geo-inventory
```

## Duration

- **Tanpa login**: ~2-3 menit (1100 requests)
- **Dengan login**: ~5-7 menit (1800 requests)
