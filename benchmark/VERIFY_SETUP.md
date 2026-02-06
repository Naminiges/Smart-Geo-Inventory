# Verification Guide - Benchmark Setup

## Setup Verification

Check that all components are properly configured for rate limiting tests with login.

## 1. Check Application Configuration

Verify rate limiting is configured correctly in `app/__init__.py`:

```bash
# From the project root
grep -A 5 "limiter = Limiter" app/__init__.py
```

Expected output should show:
```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10000 per day", "1000 per hour"],  # Increased for benchmarking
    storage_uri="memory://"
)
```

## 2. Verify Admin User Exists

```bash
# From the project root
python3 seed_admin_user.py
```

Expected output:
```
Admin user exists or created successfully!
Email: admin@smartgeo.com
Password: admin123
```

## 3. Test Connection to Application

```bash
# Test HTTPS with self-signed cert
curl -k https://172.30.95.249/home

# Test login page
curl -k https://172.30.95.249/auth/login
```

Expected: Should return HTML content (not connection errors)

## 4. Verify Benchmark Scripts

```bash
cd benchmark

# Make scripts executable
chmod +x *.sh

# List all scripts
ls -lh *.sh
```

Expected files:
- `run_benchmark.sh` - Quick 1-minute benchmark
- `scenarios.sh` - Full benchmark with multiple scenarios
- `test_rate_limit.sh` - Rate limiting test with login

## 5. Quick Test (No Login Required)

```bash
cd benchmark

# Test rate limiting on public endpoint (1000 requests, ~2-3 minutes)
./test_rate_limit.sh
```

This will:
1. ✅ Attempt login via web form (CSRF-based)
2. ✅ Test homepage with 1000 requests
3. ✅ Test authenticated endpoints (Dashboard, APIs)
4. ✅ Total: 1700+ requests in ~5-7 minutes

## Expected Results

### Successful Login
```
STEP 1: LOGIN (Menggunakan Browser Session)
✅ CSRF token berhasil diambil
✅ Login BERHASIL!
✅ Session valid! Bisa akses authenticated endpoints.
```

### Rate Limit Test Results

**With 1000/hour limit:**
- Homepage (1000 req): 0-50 requests should hit rate limit (429)
- Dashboard (200 req): 0 rate limited (below threshold)
- API Stats (300 req): 0 rate limited
- API Items (200 req): 0 rate limited

**Total 429 responses:** 0-50 (acceptable for benchmarking)

## Troubleshooting

### Login Fails (CSRF token not found)
```bash
# Check if login page is accessible
curl -k https://172.30.95.249/auth/login | grep csrf_token

# Should show: <input type="hidden" name="csrf_token" value="..." />
```

### All Requests Unauthorized (401/403)
```bash
# Session may be invalid. Check cookie file:
cat .cookies.txt

# Should show session cookie with valid value
```

### Rate Limit Too Strict
```bash
# Check current limits in app/__init__.py
grep "default_limits" app/__init__.py

# Should be: ["10000 per day", "1000 per hour"]
```

### Connection Refused
```bash
# Verify application is running
docker ps | grep smart-geo

# Or check if service is active
systemctl status smart-geo-inventory
```

## Next Steps After Verification

Once everything is verified:

1. **Run Quick Benchmark** (1 minute):
   ```bash
   ./run_benchmark.sh
   ```

2. **Run Full Benchmark** (5-10 minutes):
   ```bash
   ./scenarios.sh
   ```

3. **Run Rate Limit Test** (5-7 minutes):
   ```bash
   ./test_rate_limit.sh
   ```

4. **View Results**:
   ```bash
   cat results/*.txt
   ```

## Configuration Reference

Default credentials:
- Email: `admin@smartgeo.com`
- Password: `admin123`

Default targets:
- HTTPS (via rev-proxy): `https://172.30.95.249`
- HTTP (direct to apps): `http://172.30.95.251:5000`

Rate limits:
- Default: 10000 per day, 1000 per hour
- API Auth: 10 per minute, 20 per hour
