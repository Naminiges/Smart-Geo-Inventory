// Main JavaScript file for Smart Geo Inventory

// Auto-dismiss alerts after 5 seconds
setTimeout(function() {
    $('.alert').fadeOut('slow');
}, 5000);

// Confirm delete action
function confirmDelete(message) {
    return confirm(message || 'Apakah Anda yakin ingin menghapus data ini?');
}

// Format numbers with thousand separator
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Format date to Indonesian locale
function formatDate(date) {
    return new Date(date).toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Format datetime to Indonesian locale
function formatDateTime(date) {
    return new Date(date).toLocaleString('id-ID', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Show loading spinner
function showLoading() {
    $('#loading-spinner').show();
}

// Hide loading spinner
function hideLoading() {
    $('#loading-spinner').hide();
}

// AJAX error handler
function handleError(xhr, status, error) {
    hideLoading();
    let errorMessage = 'Terjadi kesalahan. Silakan coba lagi.';

    if (xhr.responseJSON && xhr.responseJSON.message) {
        errorMessage = xhr.responseJSON.message;
    } else if (xhr.responseText) {
        try {
            const response = JSON.parse(xhr.responseText);
            if (response.message) {
                errorMessage = response.message;
            }
        } catch (e) {
            console.error('Error parsing response:', e);
        }
    }

    showAlert(errorMessage, 'danger');
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertClasses = {
        'success': 'bg-emerald-50 border-emerald-400 text-emerald-800',
        'danger': 'bg-red-50 border-red-400 text-red-800',
        'warning': 'bg-amber-50 border-amber-400 text-amber-800',
        'info': 'bg-blue-50 border-blue-400 text-blue-800'
    };

    const iconClasses = {
        'success': 'fa-check-circle',
        'danger': 'fa-exclamation-triangle',
        'warning': 'fa-exclamation-circle',
        'info': 'fa-info-circle'
    };

    const alertHtml = `
        <div class="${alertClasses[type] || alertClasses['info']} border-l-4 rounded-lg p-4 shadow-md flex items-center justify-between mb-3">
            <div class="flex items-center">
                <div class="${type === 'success' ? 'bg-emerald-100 text-emerald-700' : type === 'danger' ? 'bg-red-100 text-red-700' : type === 'warning' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'} rounded-full p-2 mr-3">
                    <i class="fas ${iconClasses[type] || iconClasses['info']}"></i>
                </div>
                <div class="flex-1">
                    <p class="font-medium">${message}</p>
                </div>
            </div>
            <button type="button" class="ml-4 text-gray-400 hover:text-gray-600 transition-colors" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    // Add alert to container
    const alertContainer = document.getElementById('alert-container') || document.body;
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = alertHtml;
    alertContainer.insertBefore(tempDiv.firstElementChild, alertContainer.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('[class*="border-l-4"]');
        if (alerts.length > 0) {
            alerts[0].style.opacity = '0';
            setTimeout(() => alerts[0].remove(), 300);
        }
    }, 5000);
}

// Print page
function printPage() {
    window.print();
}

// Export to CSV (placeholder)
function exportToCSV(data, filename) {
    const csv = [];
    const headers = Object.keys(data[0]);

    csv.push(headers.join(','));

    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header];
            return typeof value === 'string' ? `"${value}"` : value;
        });
        csv.push(values.join(','));
    });

    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'export.csv';
    a.click();
    window.URL.revokeObjectURL(url);
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showAlert('Teks berhasil disalin!', 'success');
    }, function(err) {
        showAlert('Gagal menyalin teks', 'danger');
    });
}

// Validate form
function validateForm(formId) {
    const form = document.getElementById(formId);
    return form.checkValidity();
}

// Smooth scroll
$(document).on('click', 'a[href^="#"]', function(event) {
    if (this.hash !== '') {
        event.preventDefault();
        const hash = this.hash;

        $('html, body').animate({
            scrollTop: $(hash).offset().top
        }, 800);
    }
});

// Prevent form resubmission on page refresh
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
}

console.log('Smart Geo Inventory System loaded successfully.');
