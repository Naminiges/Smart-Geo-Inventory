/**
 * Helper Functions untuk Konfirmasi dan Alert
 * Digunakan untuk tombol-tombol krusial yang memerlukan konfirmasi sebelum aksi
 */

// Tampilkan pesan konfirmasi dengan SweetAlert2 style
function showConfirm(options) {
    return new Promise((resolve) => {
        // Default options
        const defaults = {
            title: 'Apakah Anda yakin?',
            text: 'Aksi ini tidak dapat dibatalkan!',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3B82F6', // blue-500
            cancelButtonColor: '#EF4444', // red-500
            confirmButtonText: 'Ya, lanjutkan',
            cancelButtonText: 'Batal'
        };

        // Merge with user options
        const settings = {...defaults, ...options};

        // Create modal HTML
        const modalHtml = `
            <div class="fixed inset-0 z-50 flex items-center justify-center p-4" id="confirmModal">
                <div class="absolute inset-0 bg-black opacity-50"></div>
                <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-auto relative z-10 transform transition-all">
                    <div class="p-6">
                        <div class="flex items-start mb-4">
                            <div class="flex-shrink-0 mr-4">
                                ${settings.icon === 'warning' ? '<i class="fas fa-exclamation-triangle text-yellow-500 text-4xl"></i>' : ''}
                                ${settings.icon === 'danger' ? '<i class="fas fa-times-circle text-red-500 text-4xl"></i>' : ''}
                                ${settings.icon === 'success' ? '<i class="fas fa-check-circle text-green-500 text-4xl"></i>' : ''}
                                ${settings.icon === 'info' ? '<i class="fas fa-info-circle text-blue-500 text-4xl"></i>' : ''}
                            </div>
                            <div class="flex-1">
                                <h3 class="text-lg font-bold text-gray-900 mb-2">${settings.title}</h3>
                                <p class="text-sm text-gray-600">${settings.text}</p>
                                ${settings.details ? `<p class="text-xs text-gray-500 mt-2">${settings.details}</p>` : ''}
                            </div>
                        </div>
                        <div class="flex gap-3 justify-end">
                            <button type="button" id="confirmCancelBtn"
                                class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-semibold text-sm">
                                ${settings.cancelButtonText}
                            </button>
                            <button type="button" id="confirmOkBtn"
                                class="px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${settings.confirmButtonClass || 'bg-blue-600 text-white hover:bg-blue-700'}">
                                ${settings.confirmButtonText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Get modal elements
        const modal = document.getElementById('confirmModal');
        const cancelBtn = document.getElementById('confirmCancelBtn');
        const okBtn = document.getElementById('confirmOkBtn');

        // Handle cancel
        const closeModal = () => {
            modal.remove();
            resolve(false);
        };

        cancelBtn.addEventListener('click', closeModal);
        modal.querySelector('.bg-black.opacity-50').addEventListener('click', closeModal);

        // Handle confirm
        okBtn.addEventListener('click', () => {
            modal.remove();
            resolve(true);
        });

        // Close on ESC key
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
    });
}

// Tampilkan toast/sukses pesan
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg transform transition-all duration-300 translate-y-full opacity-0`;

    const colors = {
        success: 'bg-green-600 text-white',
        error: 'bg-red-600 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-600 text-white'
    };

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.classList.add(...colors[type].split(' '));
    toast.innerHTML = `
        <div class="flex items-center">
            <i class="fas ${icons[type]} mr-3"></i>
            <span class="font-semibold">${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-y-full', 'opacity-0');
    }, 100);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('translate-y-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Konfirmasi untuk aksi krusial
const confirmAction = {
    // Logout
    logout: function() {
        return showConfirm({
            title: 'Keluar dari Aplikasi?',
            text: 'Anda harus login kembali untuk mengakses sistem.',
            icon: 'warning'
        });
    },

    // Delete/Hapus
    delete: function(itemName = 'item') {
        return showConfirm({
            title: 'Hapus Data?',
            text: `Data "${itemName}" akan dihapus secara permanen dan tidak dapat dikembalikan.`,
            icon: 'danger',
            confirmButtonText: 'Ya, Hapus',
            confirmButtonClass: 'px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold text-sm'
        });
    },

    // Approve/Setujui
    approve: function(itemName = 'permohonan') {
        return showConfirm({
            title: 'Setujui Permohonan?',
            text: `Anda akan menyetujui ${itemName}. Aksi ini akan melanjutkan proses ke tahap berikutnya.`,
            icon: 'info',
            confirmButtonText: 'Ya, Setujui',
            confirmButtonClass: 'px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold text-sm'
        });
    },

    // Reject/Tolak
    reject: function(itemName = 'permohonan') {
        return showConfirm({
            title: 'Tolak Permohonan?',
            text: `Anda akan menolak ${itemName}. Pastikan Anda memiliki alasan yang jelas.`,
            icon: 'danger',
            confirmButtonText: 'Ya, Tolak',
            confirmButtonClass: 'px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold text-sm'
        });
    },

    // Complete/Selesaikan
    complete: function(itemName = 'tugas') {
        return showConfirm({
            title: 'Selesaikan Tugas?',
            text: `Tandai ${itemName} sebagai selesai? Pastikan semua pekerjaan sudah benar-benar selesai.`,
            icon: 'success',
            confirmButtonText: 'Ya, Selesaikan',
            confirmButtonClass: 'px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold text-sm'
        });
    },

    // Cancel/Batalkan
    cancel: function(itemName = 'permohonan') {
        return showConfirm({
            title: 'Batalkan Permohonan?',
            text: `Anda akan membatalkan ${itemName}. Aksi ini tidak dapat diurungkan.`,
            icon: 'warning',
            confirmButtonText: 'Ya, Batalkan',
            confirmButtonClass: 'px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 font-semibold text-sm'
        });
    },

    // Submit/Kirim
    submit: function(formName = 'form') {
        return showConfirm({
            title: 'Kirim Data?',
            text: `Pastikan semua data yang Anda masukkan sudah benar sebelum mengirim ${formName}.`,
            icon: 'info',
            confirmButtonText: 'Ya, Kirim',
            confirmButtonClass: 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm'
        });
    },

    // Distribute/Kirim Barang
    distribute: function(itemName = 'barang') {
        return showConfirm({
            title: 'Kirim Barang?',
            text: `Anda akan mengirim ${itemName} ke unit. Pastikan data sudah benar.`,
            icon: 'info',
            details: 'Barang yang sudah dikirim tidak dapat ditarik kembali kecuali melalui proses retur.',
            confirmButtonText: 'Ya, Kirim',
            confirmButtonClass: 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm'
        });
    },

    // Return/Kembalikan
    returnItem: function(itemName = 'barang') {
        return showConfirm({
            title: 'Kembalikan Barang ke Gudang?',
            text: `Anda akan mengembalikan ${itemName} ke gudang. Status barang akan kembali menjadi tersedia.`,
            icon: 'warning',
            confirmButtonText: 'Ya, Kembalikan',
            confirmButtonClass: 'px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 font-semibold text-sm'
        });
    },

    // Edit
    edit: function(itemName = 'data') {
        return showConfirm({
            title: 'Edit Data?',
            text: `Anda akan mengedit ${itemName}. Pastikan perubahan yang dilakukan sudah benar.`,
            icon: 'info',
            confirmButtonText: 'Ya, Edit',
            confirmButtonClass: 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm'
        });
    },

    // Verify/Cek
    verify: function(itemName = 'permohonan') {
        return showConfirm({
            title: 'Verifikasi Permohonan?',
            text: `Anda akan memverifikasi ${itemName}. Pastikan semua data dan dokumen sudah lengkap.`,
            icon: 'info',
            confirmButtonText: 'Ya, Verifikasi',
            confirmButtonClass: 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm'
        });
    },

    // Receive/Terima
    receive: function(itemName = 'barang') {
        return showConfirm({
            title: 'Terima Barang?',
            text: `Anda akan menerima ${itemName} dari gudang. Pastikan barang yang diterima sesuai dengan yang dikirim.`,
            icon: 'success',
            confirmButtonText: 'Ya, Terima',
            confirmButtonClass: 'px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold text-sm'
        });
    },

    // Procurement/Beli Barang
    procurement: function(itemName = 'permohonan') {
        return showConfirm({
            title: 'Buat Permohonan Pembelian?',
            text: `Permohonan pembelian untuk ${itemName} akan diajukan ke admin untuk persetujuan.`,
            icon: 'info',
            details: 'Admin akan memverifikasi dan menyetujui permohonan ini sebelum proses pembelian dilakukan.',
            confirmButtonText: 'Ya, Ajukan',
            confirmButtonClass: 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm'
        });
    },

    // Installation/Pemasangan
    installation: function(itemName = 'barang') {
        return showConfirm({
            title: 'Proses Pemasangan?',
            text: `Anda akan memproses pemasangan ${itemName}. Pastikan lokasi dan detail sudah benar.`,
            icon: 'info',
            confirmButtonText: 'Ya, Proses',
            confirmButtonClass: 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm'
        });
    },

    // Custom konfirmasi
    custom: function(title, text, options = {}) {
        return showConfirm({
            title: title,
            text: text,
            ...options
        });
    }
};

// Auto-setup untuk tombol dengan class tertentu
document.addEventListener('DOMContentLoaded', function() {
    // Tombol logout
    const logoutBtns = document.querySelectorAll('a[href*="logout"], .logout-btn');
    logoutBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            confirmAction.logout().then(confirmed => {
                if (confirmed) {
                    window.location.href = this.getAttribute('href');
                }
            });
        });
    });

    // Tombol delete
    const deleteBtns = document.querySelectorAll('.btn-delete, .delete-btn, a[href*="/delete"], a[href*="/hapus"]');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const itemName = this.getAttribute('data-item-name') || 'item ini';
            confirmAction.delete(itemName).then(confirmed => {
                if (confirmed) {
                    // Submit form or navigate
                    const form = this.closest('form');
                    if (form) {
                        form.submit();
                    } else {
                        window.location.href = this.getAttribute('href');
                    }
                }
            });
        });
    });

    // Form submit dengan konfirmasi
    const formsWithConfirm = document.querySelectorAll('form[data-confirm], form.confirm-form');
    formsWithConfirm.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const confirmType = form.getAttribute('data-confirm') || 'submit';
            const formName = form.getAttribute('data-form-name') || 'form ini';
            const itemName = form.getAttribute('data-item-name') || '';

            if (confirmAction[confirmType]) {
                const promise = itemName ? confirmAction[confirmType](itemName) : confirmAction[confirmType](formName);
                promise.then(confirmed => {
                    if (confirmed) {
                        form.submit();
                    }
                });
            } else {
                form.submit();
            }
        });
    });
});

// Export untuk penggunaan global
window.confirmAction = confirmAction;
window.showToast = showToast;
