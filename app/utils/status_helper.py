"""
Helper functions untuk translate status teknis ke bahasa Indonesia
yang mudah dipahami oleh pengguna awam.
"""

def translate_status(status, context='general'):
    """
    Translate status teknis ke bahasa Indonesia yang mudah dipahami.

    Args:
        status (str): Status dalam bahasa Inggris
        context (str): Konteks status (general, asset, procurement, dll)

    Returns:
        str: Status dalam bahasa Indonesia
    """
    if not status:
        return '-'

    status_lower = status.lower().replace('_', ' ').replace('-', ' ')

    # Mapping status umum
    status_map = {
        # General status
        'pending': 'Menunggu',
        'approved': 'Disetujui',
        'rejected': 'Ditolak',
        'cancelled': 'Batal',
        'completed': 'Selesai',
        'in progress': 'Sedang Diproses',
        'in_progress': 'Sedang Diproses',
        'processing': 'Sedang Diproses',
        'draft': 'Draft',
        'active': 'Aktif',
        'inactive': 'Tidak Aktif',
        'closed': 'Ditutup',
        'open': 'Terbuka',

        # Asset status
        'available': 'Tersedia',
        'used': 'Sedang Dipakai',
        'maintenance': 'Perbaikan',
        'broken': 'Rusak',
        'lost': 'Hilang',
        'distributed': 'Sudah Dikirim',
        'returned': 'Sudah Kembali',
        'loaned': 'Dipinjam',

        # Procurement status
        'verified': 'Sudah Dicek',
        'ordered': 'Sudah Dipesan',
        'received': 'Sudah Diterima',
        'partial': 'Sebagian',

        # Request status
        'verified by warehouse': 'Sudah Dicek Gudang',
        'ready to distribute': 'Siap Dikirim',
        'distributed': 'Sudah Dikirim',
        'received by unit': 'Sudah Diterima Unit',
        'returned to warehouse': 'Sudah Kembali ke Gudang',

        # Task status
        'assigned': 'Sudah Ditugaskan',
        'in progress': 'Sedang Dikerjakan',
        'completed': 'Sudah Selesai',
        'cancelled': 'Dibatalkan',

        # Loan status
        'approved': 'Disetujui',
        'rejected': 'Ditolak',
        'active': 'Sedang Berjalan',
        'completed': 'Sudah Selesai',
        'overdue': 'Terlambat',

        # Installation/Distribution status
        'draft': 'Draft',
        'ready': 'Siap',
        'distributed': 'Sudah Dikirim',
    }

    # Cek mapping umum
    if status_lower in status_map:
        return status_map[status_lower]

    # Jika tidak ada di mapping, return original dengan formatting
    return status.replace('_', ' ').title()


def get_status_color(status):
    """
    Dapatkan warna badge untuk status tertentu.

    Args:
        status (str): Status dalam bahasa Inggris

    Returns:
        str: Kelas CSS untuk warna badge
    """
    if not status:
        return 'bg-gray-100 text-gray-800'

    status_lower = status.lower().replace('_', ' ').replace('-', ' ')

    color_map = {
        # Hijau - positif/selesai
        'approved': 'bg-green-100 text-green-800',
        'completed': 'bg-green-100 text-green-800',
        'received': 'bg-green-100 text-green-800',
        'available': 'bg-green-100 text-green-800',
        'active': 'bg-green-100 text-green-800',
        'verified': 'bg-green-100 text-green-800',
        'distributed': 'bg-green-100 text-green-800',
        'returned': 'bg-green-100 text-green-800',
        'received by unit': 'bg-green-100 text-green-800',

        # Kuning - proses/menunggu
        'pending': 'bg-yellow-100 text-yellow-800',
        'in progress': 'bg-yellow-100 text-yellow-800',
        'in_progress': 'bg-yellow-100 text-yellow-800',
        'processing': 'bg-yellow-100 text-yellow-800',
        'draft': 'bg-yellow-100 text-yellow-800',
        'verified by warehouse': 'bg-yellow-100 text-yellow-800',
        'ready to distribute': 'bg-yellow-100 text-yellow-800',
        'assigned': 'bg-yellow-100 text-yellow-800',
        'partial': 'bg-yellow-100 text-yellow-800',

        # Biru - informasi
        'open': 'bg-blue-100 text-blue-800',
        'used': 'bg-blue-100 text-blue-800',
        'loaned': 'bg-blue-100 text-blue-800',
        'ordered': 'bg-blue-100 text-blue-800',
        'ready': 'bg-blue-100 text-blue-800',

        # Merah - negatif/rusak/ditolak
        'rejected': 'bg-red-100 text-red-800',
        'cancelled': 'bg-red-100 text-red-800',
        'broken': 'bg-red-100 text-red-800',
        'lost': 'bg-red-100 text-red-800',
        'inactive': 'bg-red-100 text-red-800',
        'closed': 'bg-red-100 text-red-800',
        'overdue': 'bg-red-100 text-red-800',

        # Abu-abu - netral
        'maintenance': 'bg-gray-100 text-gray-800',
    }

    return color_map.get(status_lower, 'bg-gray-100 text-gray-800')


def get_status_icon(status):
    """
    Dapatkan icon untuk status tertentu.

    Args:
        status (str): Status dalam bahasa Inggris

    Returns:
        str: Kelas Font Awesome untuk icon
    """
    if not status:
        return 'fas fa-question-circle'

    status_lower = status.lower().replace('_', ' ').replace('-', ' ')

    icon_map = {
        # Completed/Success
        'approved': 'fas fa-check-circle',
        'completed': 'fas fa-check-circle',
        'received': 'fas fa-check-circle',
        'verified': 'fas fa-check-circle',

        # Pending/Processing
        'pending': 'fas fa-clock',
        'in progress': 'fas fa-spinner',
        'in_progress': 'fas fa-spinner',
        'processing': 'fas fa-spinner',
        'draft': 'fas fa-file',

        # Available/Active
        'available': 'fas fa-check',
        'active': 'fas fa-bolt',

        # Rejected/Cancelled
        'rejected': 'fas fa-times-circle',
        'cancelled': 'fas fa-ban',
        'broken': 'fas fa-tools',
        'lost': 'fas fa-search',

        # Distributed/Moved
        'distributed': 'fas fa-truck',
        'returned': 'fas fa-undo',

        # Other
        'ordered': 'fas fa-shopping-cart',
        'maintenance': 'fas fa-wrench',
    }

    return icon_map.get(status_lower, 'fas fa-circle')
