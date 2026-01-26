/**
 * Table Pagination Helper
 * Automatically adds pagination to tables with class "paginated-table"
 * Shows pagination controls when data exceeds 8 rows
 */

(function() {
    'use strict';

    const ITEMS_PER_PAGE = 8;

    class TablePagination {
        constructor(tableElement) {
            this.table = tableElement;
            this.tbody = this.table.querySelector('tbody');
            this.rows = Array.from(this.tbody.querySelectorAll('tr'));
            this.totalRows = this.rows.length;
            this.currentPage = 1;
            this.totalPages = Math.ceil(this.totalRows / ITEMS_PER_PAGE);

            // Skip if no data rows or if row is "no data" message
            if (this.totalRows === 0 || this.hasNoDataRow()) {
                return;
            }

            // Only add pagination if more than 8 rows
            if (this.totalRows > ITEMS_PER_PAGE) {
                this.init();
            }
        }

        hasNoDataRow() {
            return this.rows.some(row => {
                const text = row.textContent.toLowerCase();
                return text.includes('tidak ada') || text.includes('belum ada') || text.includes('no data');
            });
        }

        init() {
            // Wrap table in container
            const wrapper = this.table.closest('.bg-white') || this.table.parentElement;
            this.container = wrapper;

            // Add pagination container
            this.paginationContainer = document.createElement('div');
            this.paginationContainer.className = 'table-pagination-wrapper mt-4 px-6 pb-6';
            this.paginationContainer.innerHTML = this.createPaginationHTML();
            wrapper.appendChild(this.paginationContainer);

            // Add event listeners
            this.attachEventListeners();

            // Show first page
            this.showPage(1);
        }

        createPaginationHTML() {
            return `
                <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div class="text-sm text-gray-600">
                        Menampilkan <span id="pagination-info-start">1</span> - <span id="pagination-info-end">${ITEMS_PER_PAGE}</span> dari <span id="pagination-info-total">${this.totalRows}</span> data
                    </div>
                    <ul class="flex items-center gap-1" id="pagination-controls">
                        ${this.createPageButtons()}
                    </ul>
                </div>
            `;
        }

        createPageButtons() {
            let html = '';

            // Previous button
            html += `
                <li>
                    <button class="pagination-btn px-3 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            data-page="prev" ${this.currentPage === 1 ? 'disabled' : ''}>
                        <i class="fas fa-chevron-left"></i>
                    </button>
                </li>
            `;

            // Page numbers
            for (let i = 1; i <= this.totalPages; i++) {
                const isActive = i === this.currentPage;
                html += `
                    <li>
                        <button class="pagination-btn px-3 py-2 rounded-lg transition-colors ${isActive ? 'bg-emerald-600 text-white font-medium' : 'border border-gray-300 text-gray-700 hover:bg-gray-50'}"
                                data-page="${i}" ${isActive ? 'disabled' : ''}>
                            ${i}
                        </button>
                    </li>
                `;
            }

            // Next button
            html += `
                <li>
                    <button class="pagination-btn px-3 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            data-page="next" ${this.currentPage === this.totalPages ? 'disabled' : ''}>
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </li>
            `;

            return html;
        }

        attachEventListeners() {
            this.paginationContainer.addEventListener('click', (e) => {
                const btn = e.target.closest('.pagination-btn');
                if (!btn || btn.disabled) return;

                const page = btn.dataset.page;

                if (page === 'prev') {
                    this.showPage(this.currentPage - 1);
                } else if (page === 'next') {
                    this.showPage(this.currentPage + 1);
                } else {
                    this.showPage(parseInt(page));
                }
            });
        }

        showPage(pageNum) {
            this.currentPage = pageNum;

            // Calculate range
            const start = (pageNum - 1) * ITEMS_PER_PAGE;
            const end = start + ITEMS_PER_PAGE;

            // Show/hide rows
            this.rows.forEach((row, index) => {
                if (index >= start && index < end) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });

            // Update info
            const actualEnd = Math.min(end, this.totalRows);
            document.getElementById('pagination-info-start').textContent = start + 1;
            document.getElementById('pagination-info-end').textContent = actualEnd;

            // Update buttons
            this.updatePaginationButtons();
        }

        updatePaginationButtons() {
            const controls = document.getElementById('pagination-controls');
            controls.innerHTML = this.createPageButtons();
        }
    }

    // Auto-initialize on DOM ready
    function initPagination() {
        const tables = document.querySelectorAll('.paginated-table');
        tables.forEach(table => new TablePagination(table));
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPagination);
    } else {
        initPagination();
    }

    // Also expose to global scope for manual initialization
    window.TablePagination = TablePagination;
    window.initTablePagination = initPagination;

})();
