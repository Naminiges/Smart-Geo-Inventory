# Panduan Penggunaan Helper Konfirmasi

## Pendahuluan

Helper konfirmasi (`confirm.js`) digunakan untuk menampilkan dialog konfirmasi sebelum menjalankan aksi krusial seperti delete, approve, reject, dll.

## Cara Penggunaan Otomatis

### 1. Logout (Otomatis)
Tombol logout sudah otomatis memiliki konfirmasi. Cukup tambahkan class `logout-btn`:
```html
<a href="/logout" class="logout-btn">Keluar</a>
```

### 2. Delete (Otomatis)
Untuk tombol hapus, gunakan class `btn-delete` atau `delete-btn`:
```html
<a href="/items/5/delete" class="btn-delete" data-item-name="Laptop Dell">Hapus</a>
<a href="/items/5/hapus" class="delete-btn">Hapus</a>
```

### 3. Form dengan Konfirmasi
Gunakan atribut `data-confirm` pada form:
```html
<form action="/submit" method="POST" data-confirm="submit" data-form-name="Form Peminjaman">
    <!-- form fields -->
    <button type="submit">Kirim</button>
</form>
```

## Cara Penggunaan Manual

### Method yang Tersedia

```javascript
// 1. Logout
confirmAction.logout().then(confirmed => {
    if (confirmed) { /* lakukan sesuatu */ }
});

// 2. Delete
confirmAction.delete('Laptop Dell').then(confirmed => {
    if (confirmed) { /* hapus data */ }
});

// 3. Approve
confirmAction.approve('permohonan barang').then(confirmed => {
    if (confirmed) { /* setujui */ }
});

// 4. Reject
confirmAction.reject('permohonan').then(confirmed => {
    if (confirmed) { /* tolak */ }
});

// 5. Complete
confirmAction.complete('pemasangan').then(confirmed => {
    if (confirmed) { /* selesaikan */ }
});

// 6. Cancel
confirmAction.cancel('pengiriman').then(confirmed => {
    if (confirmed) { /* batalkan */ }
});

// 7. Submit
confirmAction.submit('Form Permohonan').then(confirmed => {
    if (confirmed) { /* kirim */ }
});

// 8. Distribute
confirmAction.distribute('10 unit komputer').then(confirmed => {
    if (confirmed) { /* kirim barang */ }
});

// 9. Return
confirmAction.returnItem('barang').then(confirmed => {
    if (confirmed) { /* kembalikan ke gudang */ }
});

// 10. Verify
confirmAction.verify('permohonan').then(confirmed => {
    if (confirmed) { /* verifikasi */ }
});

// 11. Receive
confirmAction.receive('barang').then(confirmed => {
    if (confirmed) { /* terima barang */ }
});

// 12. Custom
confirmAction.custom('Judul', 'Pesan konfirmasi', {
    confirmButtonText: 'Oke',
    confirmButtonClass: 'bg-green-600 text-white'
}).then(confirmed => {
    if (confirmed) { /* ... */ }
});
```

## Contoh Implementasi di Template

### Contoh 1: Tombol Delete
```html
<a href="{{ url_for('items.delete', id=item.id) }}"
   class="btn-delete px-3 py-2 bg-red-600 text-white rounded-lg"
   data-item-name="{{ item.name }}">
    <i class="fas fa-trash"></i> Hapus
</a>
```

### Contoh 2: Tombol Approve dengan Inline JavaScript
```html
<a href="{{ url_for('asset_requests.approve', id=request.id) }}"
   class="px-3 py-2 bg-green-600 text-white rounded-lg"
   onclick="confirmAction.approve('permohonan {{ request.id }}').then(c => c && (window.location.href = this.href)); return false;">
    <i class="fas fa-check"></i> Setujui
</a>
```

### Contoh 3: Form Submit dengan Konfirmasi
```html
<form action="{{ url_for('procurement.create') }}" method="POST"
      data-confirm="procurement" data-item-name="Permohonan Pembelian Barang">
    {{ form.hidden_tag() }}

    <!-- Form fields -->

    <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg">
        Ajukan Permohonan
    </button>
</form>
```

### Contoh 4: Multiple Action Buttons
```html
<div class="flex gap-2">
    <!-- Approve -->
    <a href="{{ url_for('venue_loans.approve', id=loan.id) }}"
       onclick="confirmAction.approve('peminjaman {{ loan.event_name }}').then(c => c && (window.location.href = this.href)); return false;"
       class="px-3 py-2 bg-green-600 text-white rounded-lg">
        <i class="fas fa-check"></i> Setujui
    </a>

    <!-- Reject -->
    <a href="{{ url_for('venue_loans.reject', id=loan.id) }}"
       onclick="confirmAction.reject('peminjaman {{ loan.event_name }}').then(c => c && (window.location.href = this.href)); return false;"
       class="px-3 py-2 bg-red-600 text-white rounded-lg">
        <i class="fas fa-times"></i> Tolak
    </a>

    <!-- Delete -->
    <a href="{{ url_for('venue_loans.delete', id=loan.id) }}"
       onclick="confirmAction.delete('peminjaman {{ loan.event_name }}').then(c => c && (window.location.href = this.href)); return false;"
       class="px-3 py-2 bg-red-600 text-white rounded-lg">
        <i class="fas fa-trash"></i> Hapus
    </a>
</div>
```

## Contoh Implementasi yang Perlu Ditambahkan

Berikut adalah contoh implementasi yang perlu ditambahkan di berbagai template:

### 1. Asset Requests (Approve/Reject)
```html
<!-- Di asset_requests/index.html atau detail.html -->
<a href="{{ url_for('asset_requests.verify', id=req.id) }}"
   onclick="confirmAction.verify('Permohonan #{{ req.id }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-green-600 text-white rounded-lg">
    <i class="fas fa-check-circle"></i> Verifikasi
</a>

<a href="{{ url_for('asset_requests.reject', id=req.id) }}"
   onclick="confirmAction.reject('Permohonan #{{ req.id }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-red-600 text-white rounded-lg">
    <i class="fas fa-times-circle"></i> Tolak
</a>
```

### 2. Procurement (Approve/Reject)
```html
<!-- Di procurement/detail.html -->
<a href="{{ url_for('procurement.approve', id=proc.id) }}"
   onclick="confirmAction.approve('Pengadaan #{{ proc.id }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-green-600 text-white rounded-lg">
    <i class="fas fa-thumbs-up"></i> Setujui
</a>

<a href="{{ url_for('procurement.reject', id=proc.id) }}"
   onclick="confirmAction.reject('Pengadaan #{{ proc.id }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-red-600 text-white rounded-lg">
    <i class="fas fa-thumbs-down"></i> Tolak
</a>
```

### 3. Venue Loans (Approve/Reject/Complete)
```html
<!-- Di venue_loans/admin/detail.html -->
<a href="{{ url_for('venue_loans.approve', id=loan.id) }}"
   onclick="confirmAction.approve('Peminjaman {{ loan.event_name }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-green-600 text-white rounded-lg">
    <i class="fas fa-check"></i> Setujui
</a>

<a href="{{ url_for('venue_loans.complete', id=loan.id) }}"
   onclick="confirmAction.complete('Peminjaman {{ loan.event_name }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-blue-600 text-white rounded-lg">
    <i class="fas fa-check-double"></i> Selesaikan
</a>

<a href="{{ url_for('venue_loans.reject', id=loan.id) }}"
   onclick="confirmAction.reject('Peminjaman {{ loan.event_name }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-red-600 text-white rounded-lg">
    <i class="fas fa-times"></i> Tolak
</a>
```

### 4. Distributions (Verify/Ship)
```html
<!-- Di installations/batch_detail.html -->
<a href="{{ url_for('installations.verify_batch', id=batch.id) }}"
   onclick="confirmAction.verify('Draft pengiriman #{{ batch.id }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-green-600 text-white rounded-lg">
    <i class="fas fa-check-circle"></i> Verifikasi
</a>

<a href="{{ url_for('installations.ship_batch', id=batch.id) }}"
   onclick="confirmAction.distribute('Draft pengiriman #{{ batch.id }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-blue-600 text-white rounded-lg">
    <i class="fas fa-truck"></i> Kirim Barang
</a>
```

### 5. Returns (Verify)
```html
<!-- Di returns/detail.html -->
<a href="{{ url_for('returns.verify', id=batch.id) }}"
   onclick="confirmAction.verify('Retur #{{ batch.batch_code }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-green-600 text-white rounded-lg">
    <i class="fas fa-check-circle"></i> Verifikasi
</a>
```

### 6. Items (Delete)
```html
<!-- Di items/details.html -->
<a href="{{ url_for('items.delete', id=item.id) }}"
   onclick="confirmAction.delete('{{ item.name }}').then(c => c && (window.location.href = this.href)); return false;"
   class="px-3 py-2 bg-red-600 text-white rounded-lg">
    <i class="fas fa-trash"></i> Hapus
</a>
```

### 7. Forms (General Submit)
```html
<!-- Form dengan konfirmasi submit -->
<form action="{{ url_for('something.create') }}" method="POST"
      data-confirm="submit" data-form-name="Data Baru">
    {{ form.hidden_tag() }}

    <!-- form fields -->

    <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg">
        Simpan
    </button>
</form>
```

## Show Toast/Pesan Sukses

```javascript
// Menampilkan pesan sukses
showToast('Data berhasil disimpan!', 'success');

// Menampilkan pesan error
showToast('Terjadi kesalahan!', 'error');

// Menampilkan pesan peringatan
showToast('Perhatian: Stok menipis!', 'warning');

// Menampilkan pesan info
showToast('Data sedang diproses...', 'info');
```

## Notes

- Pastikan file `confirm.js` sudah diload di `base.html`
- Semua tombol logout otomatis memiliki konfirmasi dengan class `logout-btn`
- Tombol delete otomatis terdeteksi dengan class `btn-delete` atau `delete-btn`
- Gunakan `return false;` setelah inline JavaScript onclick untuk mencegah double-execution
- Modal konfirmasi otomatis tertutup dengan tombol ESC
