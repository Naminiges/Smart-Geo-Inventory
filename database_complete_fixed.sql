-- ============================================================
-- SMART GEO INVENTORY - COMPLETE DATABASE SCHEMA
-- Dengan fitur Pengadaan Barang & Serial Numbers
-- PostgreSQL 15 + PostGIS 3.4
-- ============================================================

-- Drop semua tabel jika ada (HATI-HATI: Ini akan menghapus data!)
-- Uncomment baris di bawah ini jika ingin drop semua tabel
-- DROP SCHEMA public CASCADE;
-- CREATE SCHEMA public;

-- ============================================================
-- 1. MASTER DATA (URUTAN BENAR)
-- ============================================================

-- Categories Table (tidak ada foreign key)
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Suppliers Table (tidak ada foreign key)
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(120),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Warehouses Table (tidak ada foreign key)
CREATE TABLE IF NOT EXISTS warehouses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Items Table (foreign key ke categories - SUDAH ADA)
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL,
    item_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_items_category FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Item Details Table (foreign key ke items, suppliers, warehouses - SEMUA SUDAH ADA)
CREATE TABLE IF NOT EXISTS item_details (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) DEFAULT 'available',
    specification_notes TEXT,
    supplier_id INTEGER,
    warehouse_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_item_details_item FOREIGN KEY (item_id) REFERENCES items(id),
    CONSTRAINT fk_item_details_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    CONSTRAINT fk_item_details_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
);

-- ============================================================
-- 2. USER MANAGEMENT (TANPA FOREIGN KEY KE PROCUREMENTS)
-- ============================================================

-- Users Table (foreign key ke warehouses - SUDAH ADA)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    warehouse_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
);

-- User Warehouses Table (foreign keys ke users dan warehouses - SUDAH ADA)
CREATE TABLE IF NOT EXISTS user_warehouses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_warehouse_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_warehouse_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
    CONSTRAINT unique_user_warehouse UNIQUE (user_id, warehouse_id)
);

-- ============================================================
-- 3. PROCUREMENT SYSTEM (FOREIGN KEYS KE TABEL YANG SUDAH ADA)
-- ============================================================

CREATE TABLE IF NOT EXISTS procurements (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER,
    item_id INTEGER,
    quantity INTEGER NOT NULL,
    unit_price FLOAT,

    -- Request tracking
    requested_by INTEGER NOT NULL,
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    request_notes TEXT,

    -- Approval tracking
    approved_by INTEGER,
    approval_date TIMESTAMP,

    -- Rejection tracking
    rejected_by INTEGER,
    rejection_date TIMESTAMP,
    rejection_reason TEXT,

    -- Goods receipt tracking
    received_by INTEGER,
    receipt_date TIMESTAMP,
    receipt_number VARCHAR(100),
    actual_quantity INTEGER,
    serial_numbers TEXT,

    -- For new items (if item doesn't exist yet)
    new_item_name VARCHAR(200),
    new_item_category VARCHAR(100),
    new_item_unit VARCHAR(50),

    -- Completion tracking
    completed_by INTEGER,
    completion_date TIMESTAMP,

    -- Notes
    notes TEXT,

    -- Status: pending, approved, rejected, received, completed
    status VARCHAR(20) DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Keys (SEMUA ke tabel yang SUDAH dibuat)
    CONSTRAINT fk_procurements_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    CONSTRAINT fk_procurements_item FOREIGN KEY (item_id) REFERENCES items(id),
    CONSTRAINT fk_procurements_requested_by FOREIGN KEY (requested_by) REFERENCES users(id),
    CONSTRAINT fk_procurements_approved_by FOREIGN KEY (approved_by) REFERENCES users(id),
    CONSTRAINT fk_procurements_rejected_by FOREIGN KEY (rejected_by) REFERENCES users(id),
    CONSTRAINT fk_procurements_received_by FOREIGN KEY (received_by) REFERENCES users(id),
    CONSTRAINT fk_procurements_completed_by FOREIGN KEY (completed_by) REFERENCES users(id)
);

-- ============================================================
-- 4. FACILITIES (LOCATIONS)
-- ============================================================

-- Units Table (tidak ada foreign key)
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unit Details Table (foreign key ke units)
CREATE TABLE IF NOT EXISTS unit_details (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER NOT NULL,
    room_name VARCHAR(255),
    floor VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_unit_details_unit FOREIGN KEY (unit_id) REFERENCES units(id)
);

-- ============================================================
-- 5. INVENTORY & STOCK
-- ============================================================

-- Stocks Table (foreign keys ke items dan warehouses - SUDAH ADA)
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stocks_item FOREIGN KEY (item_id) REFERENCES items(id),
    CONSTRAINT fk_stocks_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    CONSTRAINT unique_item_warehouse UNIQUE (item_id, warehouse_id)
);

-- Stock Transactions Table (foreign keys ke items, warehouses - SUDAH ADA)
CREATE TABLE IF NOT EXISTS stock_transactions (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    transaction_type VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    reference_id INTEGER,
    reference_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_trans_item FOREIGN KEY (item_id) REFERENCES items(id),
    CONSTRAINT fk_stock_trans_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
);

-- ============================================================
-- 6. FIELD OPERATIONS (DISTRIBUTION)
-- ============================================================

-- Distributions Table (foreign keys ke tabel yang SUDAH ADA)
CREATE TABLE IF NOT EXISTS distributions (
    id SERIAL PRIMARY KEY,
    item_detail_id INTEGER NOT NULL UNIQUE,
    warehouse_id INTEGER NOT NULL,
    field_staff_id INTEGER NOT NULL,
    unit_id INTEGER NOT NULL,
    unit_detail_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    geom GEOMETRY(POINT, 4326),
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'installing',
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_distributions_item_detail FOREIGN KEY (item_detail_id) REFERENCES item_details(id),
    CONSTRAINT fk_distributions_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    CONSTRAINT fk_distributions_field_staff FOREIGN KEY (field_staff_id) REFERENCES users(id),
    CONSTRAINT fk_distributions_unit FOREIGN KEY (unit_id) REFERENCES units(id),
    CONSTRAINT fk_distributions_unit_detail FOREIGN KEY (unit_detail_id) REFERENCES unit_details(id)
);

-- ============================================================
-- 7. LOGGING (INDEPENDENT)
-- ============================================================

-- Activity Logs Table (foreign key ke users - SUDAH ADA)
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    username VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER,
    old_data JSONB,
    new_data JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_activity_logs_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Asset Movement Logs Table (foreign keys ke item_details dan users - SUDAH ADA)
CREATE TABLE IF NOT EXISTS asset_movement_logs (
    id SERIAL PRIMARY KEY,
    item_detail_id INTEGER,
    serial_number VARCHAR(100),
    operator_id INTEGER,
    operator_name VARCHAR(100),
    origin_type VARCHAR(50),
    origin_id INTEGER,
    destination_type VARCHAR(50),
    destination_id INTEGER,
    status_before VARCHAR(50),
    status_after VARCHAR(50),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_movement_item_detail FOREIGN KEY (item_detail_id) REFERENCES item_details(id),
    CONSTRAINT fk_asset_movement_operator FOREIGN KEY (operator_id) REFERENCES users(id)
);

-- ============================================================
-- 8. CREATE INDEXES FOR PERFORMANCE
-- ============================================================

-- Indexes for Master Data
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
CREATE INDEX IF NOT EXISTS idx_item_details_item ON item_details(item_id);
CREATE INDEX IF NOT EXISTS idx_item_details_status ON item_details(status);
CREATE INDEX IF NOT EXISTS idx_item_details_warehouse ON item_details(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_item_details_serial ON item_details(serial_number);

-- Indexes for Procurements
CREATE INDEX IF NOT EXISTS idx_procurements_status ON procurements(status);
CREATE INDEX IF NOT EXISTS idx_procurements_requested_by ON procurements(requested_by);
CREATE INDEX IF NOT EXISTS idx_procurements_supplier_id ON procurements(supplier_id);
CREATE INDEX IF NOT EXISTS idx_procurements_item_id ON procurements(item_id);
CREATE INDEX IF NOT EXISTS idx_procurements_created_at ON procurements(created_at);

-- Indexes for GIS Columns (PostGIS)
CREATE INDEX IF NOT EXISTS idx_warehouses_geom ON warehouses USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_units_geom ON units USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_distributions_geom ON distributions USING GIST(geom);

-- Indexes for Inventory
CREATE INDEX IF NOT EXISTS idx_stocks_item ON stocks(item_id);
CREATE INDEX IF NOT EXISTS idx_stocks_warehouse ON stocks(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_item ON stock_transactions(item_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_date ON stock_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_reference ON stock_transactions(reference_id, reference_type);

-- Indexes for Users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_warehouse ON users(warehouse_id);

-- Indexes for Distributions
CREATE INDEX IF NOT EXISTS idx_distributions_item_detail ON distributions(item_detail_id);
CREATE INDEX IF NOT EXISTS idx_distributions_status ON distributions(status);
CREATE INDEX IF NOT EXISTS idx_distributions_field_staff ON distributions(field_staff_id);
CREATE INDEX IF NOT EXISTS idx_distributions_unit ON distributions(unit_id);

-- Indexes for Logging
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_table ON activity_logs(table_name);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_asset_movement_item_detail ON asset_movement_logs(item_detail_id);
CREATE INDEX IF NOT EXISTS idx_asset_movement_created ON asset_movement_logs(created_at);

-- ============================================================
-- 9. INSERT SAMPLE DATA FOR TESTING
-- ============================================================

-- Insert Sample Categories
INSERT INTO categories (name, description) VALUES
('Networking', 'Perangkat jaringan seperti router, switch, access point'),
('Computer', 'Perangkat komputer desktop dan laptop'),
('Peripheral', 'Peripheral seperti monitor, keyboard, mouse'),
('Cabling', 'Kabel dan konektor jaringan')
ON CONFLICT (name) DO NOTHING;

-- Insert Sample Items
INSERT INTO items (category_id, item_code, name, unit) VALUES
(1, 'NET-001', 'Router Cisco ISR 4321', 'unit'),
(1, 'NET-002', 'Switch Cisco Catalyst 2960', 'unit'),
(1, 'NET-003', 'Access Point Ubiquiti UniFi', 'unit'),
(2, 'COMP-001', 'Desktop Dell OptiPlex', 'unit'),
(2, 'COMP-002', 'Laptop ThinkPad X1', 'unit'),
(3, 'PER-001', 'Monitor LG 24"', 'unit')
ON CONFLICT (item_code) DO NOTHING;

-- Insert Sample Supplier
INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES
('PT Teknologi Indonesia', 'Budi Santoso', '08123456789', 'sales@teknologi.co.id', 'Jl. Teknologi No. 123, Jakarta'),
('CV Komputer Maju', 'Ahmad Dani', '08198765432', 'ahmad@komputermaju.com', 'Jl. Komputer No. 45, Surabaya')
ON CONFLICT DO NOTHING;

-- Insert Sample Warehouse dengan koordinat (USU area)
INSERT INTO warehouses (name, address, geom) VALUES
('Gudang Pusat USU', 'Universitas Sumatera Utara, Padang Bulan, Medan',
 ST_SetSRID(ST_MakePoint(98.6563423, 3.561676), 4326)),
('Gudang Teknik', 'Fakultas Teknik USU, Medan',
 ST_SetSRID(ST_MakePoint(98.6570000, 3.5620000), 4326))
ON CONFLICT DO NOTHING;

-- Insert Sample Units
INSERT INTO units (name, address, geom) VALUES
('Gedung Rektorat USU', 'Universitas Sumatera Utara, Padang Bulan, Medan',
 ST_SetSRID(ST_MakePoint(98.6565000, 3.5618000), 4326)),
('Fakultas Ilmu Komputer', 'USU, Medan',
 ST_SetSRID(ST_MakePoint(98.6572000, 3.5621000), 4326)),
('Perpustakaan USU', 'Universitas Sumatera Utara, Medan',
 ST_SetSRID(ST_MakePoint(98.6568000, 3.5615000), 4326))
ON CONFLICT DO NOTHING;

-- Insert Sample Unit Details
INSERT INTO unit_details (unit_id, room_name, floor, description) VALUES
(1, 'Ruang Rektor', 'Lantai 2', 'Ruang kerja Rektor'),
(1, 'Ruang Rapat', 'Lantai 3', 'Ruang rapat pimpinan'),
(2, 'Lab Komputer 1', 'Lantai 1', 'Laboratorium komputer untuk praktikum'),
(2, 'Ruang Kuliah A', 'Lantai 2', 'Ruang kuliah bersama'),
(3, 'Ruang Baca', 'Lantai 1', 'Ruang baca perpustakaan')
ON CONFLICT DO NOTHING;

-- Insert Sample Users (password: admin123, warehouse123, field123)
-- Password hash di-generate menggunakan Werkzeug scrypt
-- Format: scrypt:32768:8:1$salt$hash
INSERT INTO users (name, email, password_hash, role, warehouse_id) VALUES
('Administrator', 'admin@smartgeo.com',
 'scrypt:32768:8:1$jHxE8e3CPfz7piep$16ff2ac66fe2960577f1888572422e970a3519ca4585aa784b78a9e07ef1bcf232f204e959e93719536019ff3be6fe0ac914c60debf32efa21ec1714ff6e1e3d', 'admin', NULL),
('Warehouse Staff', 'warehouse@smartgeo.com',
 'scrypt:32768:8:1$D50y4eQhnO8rxwui$ae5699df52be06aa4c1782eb52d8c36109887772a02220badf7da473a1b122666c277f8948e5cf81cb3fc4693cca69ed2b9727dd2953fde0ab2f263e748417f5', 'warehouse_staff', 1),
('Field Staff', 'field@smartgeo.com',
 'scrypt:32768:8:1$QlpnqUOwVVR4T3Os$b72499665044aa210453bc602b40ca884605b00d2b891174d4b4b4a99213e10978be6c26d0468e539f303b33e60aeb9bc798959b6a06f525c92054c9830cb4de', 'field_staff', NULL)
ON CONFLICT (email) DO NOTHING;

-- Insert Sample Item Details dengan serial numbers
INSERT INTO item_details (item_id, serial_number, status, specification_notes, supplier_id, warehouse_id) VALUES
(1, 'CISCO-ROUTER-4321-SN001', 'available', 'Router Cisco ISR 4321 - Procurement #1', 1, 1),
(1, 'CISCO-ROUTER-4321-SN002', 'available', 'Router Cisco ISR 4321 - Procurement #1', 1, 1),
(2, 'CISCO-SWITCH-2960-SN001', 'used', 'Switch Cisco 2960 - Installed at Rektorat', 1, 1),
(4, 'DELL-OPTIPLEX-SN001', 'available', 'Desktop Dell OptiPlex - Lab Komputer', 1, 2)
ON CONFLICT (serial_number) DO NOTHING;

-- Insert Sample Procurements
INSERT INTO procurements (
    item_id, quantity, unit_price, request_notes, status,
    requested_by, approved_by, approval_date, supplier_id,
    received_by, receipt_date, receipt_number, actual_quantity, serial_numbers,
    completed_by, completion_date
) VALUES
(
    1, 2, 8500000, 'Pengadaan 2 unit Router Cisco untuk gedung baru', 'completed',
    2, 1, CURRENT_TIMESTAMP - INTERVAL '3 days', 1,
    2, CURRENT_TIMESTAMP - INTERVAL '2 days', 'INV-2024-001', 2,
    '["CISCO-ROUTER-4321-SN001", "CISCO-ROUTER-4321-SN002"]',
    2, CURRENT_TIMESTAMP - INTERVAL '2 days'
),
(
    2, 5, 3500000, 'Pengadaan Switch Cisco untuk penggantian', 'received',
    2, 1, CURRENT_TIMESTAMP - INTERVAL '1 day', 1,
    2, CURRENT_TIMESTAMP, 'INV-2024-002', 5,
    '["CISCO-SWITCH-2960-SN002", "CISCO-SWITCH-2960-SN003", "CISCO-SWITCH-2960-SN004", "CISCO-SWITCH-2960-SN005", "CISCO-SWITCH-2960-SN006"]',
    NULL, NULL
),
(
    4, 10, 12000000, 'Pengadaan Laptop baru untuk staff', 'pending',
    2, NULL, NULL, NULL,
    NULL, NULL, NULL, NULL, NULL,
    NULL, NULL
)
ON CONFLICT DO NOTHING;

-- Insert Sample Stocks
INSERT INTO stocks (item_id, warehouse_id, quantity) VALUES
(1, 1, 2),
(2, 1, 1),
(4, 1, 1),
(4, 2, 3)
ON CONFLICT (item_id, warehouse_id) DO NOTHING;

-- Insert Sample Stock Transactions
INSERT INTO stock_transactions (item_id, warehouse_id, transaction_type, quantity, note, reference_id, reference_type) VALUES
(1, 1, 'IN', 2, 'Procurement #1 - INV-2024-001', 1, 'procurement'),
(2, 1, 'OUT', 1, 'Distribution to Rektorat', 1, 'distribution')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 10. ADD COMMENTS FOR DOCUMENTATION
-- ============================================================

COMMENT ON TABLE procurements IS 'Tabel untuk tracking pengadaan barang dari permohonan sampai selesai dengan serial numbers';
COMMENT ON COLUMN procurements.serial_numbers IS 'JSON array of serial numbers: ["SN001", "SN002", ...]';
COMMENT ON COLUMN procurements.new_item_name IS 'Nama barang baru (jika barang belum ada di items)';
COMMENT ON COLUMN item_details.serial_number IS 'Serial number unik untuk setiap unit barang';
COMMENT ON COLUMN item_details.status IS 'available, processing, maintenance, used';
COMMENT ON TABLE stocks IS 'Stok aggregate per item per warehouse (jumlah total)';
COMMENT ON TABLE item_details IS 'Unit individual barang dengan serial number unik';

-- ============================================================
-- 11. VERIFY INSTALLATION
-- ============================================================

-- Cek semua tabel
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = information_schema.tables.table_name) as column_count
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Hitung jumlah tabel
SELECT
    COUNT(*) as total_tables,
    'Database setup completed successfully!' as message
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';

-- Cek PostGIS version
SELECT PostGIS_Version();

-- ============================================================
-- END OF DATABASE SETUP
-- ============================================================
