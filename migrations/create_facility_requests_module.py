"""Create the additive facility request POC schema.

Usage:
    python migrations/create_facility_requests_module.py
    python migrations/create_facility_requests_module.py --downgrade
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db


UPGRADE_SQL = """
CREATE SEQUENCE IF NOT EXISTS facility_form_number_seq START WITH 1 INCREMENT BY 1;

CREATE TABLE IF NOT EXISTS facility_requests (
    id SERIAL PRIMARY KEY,
    form_number VARCHAR(50) NOT NULL UNIQUE,
    unit_id INTEGER NOT NULL REFERENCES units(id),
    submitted_by INTEGER NOT NULL REFERENCES users(id),
    unit_name_snapshot VARCHAR(255) NOT NULL,
    submitter_name_snapshot VARCHAR(100) NOT NULL,
    submitter_email_snapshot VARCHAR(120),
    request_type VARCHAR(30) NOT NULL,
    other_request_type VARCHAR(255),
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    justification TEXT NOT NULL,
    impact_if_unavailable TEXT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'unit_signed',
    version INTEGER NOT NULL DEFAULT 1,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    linked_asset_request_id INTEGER REFERENCES asset_requests(id),
    warehouse_received_by INTEGER REFERENCES users(id),
    warehouse_received_at TIMESTAMP,
    released_by INTEGER REFERENCES users(id),
    released_at TIMESTAMP,
    received_by INTEGER REFERENCES users(id),
    received_at TIMESTAMP,
    receipt_notes TEXT,
    operational_notes TEXT,
    user_statement_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

ALTER TABLE facility_requests ADD COLUMN IF NOT EXISTS other_request_type VARCHAR(255);
ALTER TABLE facility_requests ADD COLUMN IF NOT EXISTS warehouse_received_by INTEGER REFERENCES users(id);
ALTER TABLE facility_requests ADD COLUMN IF NOT EXISTS warehouse_received_at TIMESTAMP;
ALTER TABLE facility_requests ADD COLUMN IF NOT EXISTS released_by INTEGER REFERENCES users(id);
ALTER TABLE facility_requests ADD COLUMN IF NOT EXISTS released_at TIMESTAMP;
ALTER TABLE facility_requests ADD COLUMN IF NOT EXISTS operational_notes TEXT;

CREATE TABLE IF NOT EXISTS facility_request_items (
    id SERIAL PRIMARY KEY,
    facility_request_id INTEGER NOT NULL REFERENCES facility_requests(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    facility_name VARCHAR(255) NOT NULL,
    specification TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    need_status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (need_status IN ('new', 'existing')),
    purpose TEXT,
    item_detail_id INTEGER REFERENCES item_details(id),
    brand_type VARCHAR(255),
    inventory_number VARCHAR(100),
    serial_number VARCHAR(100),
    handover_condition VARCHAR(30),
    handover_notes TEXT,
    linked_asset_request_item_id INTEGER REFERENCES asset_request_items(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS facility_verifications (
    id SERIAL PRIMARY KEY,
    facility_request_id INTEGER NOT NULL UNIQUE REFERENCES facility_requests(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    availability VARCHAR(30) NOT NULL,
    device_condition VARCHAR(30) NOT NULL,
    facility_source VARCHAR(30) NOT NULL,
    recommendation VARCHAR(30) NOT NULL,
    estimated_completion DATE,
    realization_priority VARCHAR(20) NOT NULL,
    notes TEXT,
    verified_by INTEGER NOT NULL REFERENCES users(id),
    verified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS facility_approvals (
    id SERIAL PRIMARY KEY,
    facility_request_id INTEGER NOT NULL REFERENCES facility_requests(id) ON DELETE CASCADE,
    stage VARCHAR(30) NOT NULL CHECK (stage IN ('unit_supervisor', 'administration', 'leadership')),
    expected_role VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    signed_by INTEGER NOT NULL REFERENCES users(id),
    signer_name_snapshot VARCHAR(100) NOT NULL,
    signer_role_snapshot VARCHAR(50) NOT NULL,
    decision VARCHAR(20) NOT NULL DEFAULT 'approved',
    notes TEXT,
    signature_data BYTEA NOT NULL,
    signature_mime VARCHAR(50) NOT NULL DEFAULT 'image/png',
    document_hash VARCHAR(64) NOT NULL,
    consent_text TEXT NOT NULL,
    consent_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    signed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT uq_facility_approval_stage_version UNIQUE (facility_request_id, stage, version)
);

CREATE TABLE IF NOT EXISTS facility_documents (
    id SERIAL PRIMARY KEY,
    facility_request_id INTEGER NOT NULL REFERENCES facility_requests(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    document_type VARCHAR(30) NOT NULL DEFAULT 'approved_form',
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
    file_size INTEGER NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    file_data BYTEA NOT NULL,
    is_final BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT uq_facility_document_version_type UNIQUE (facility_request_id, version, document_type)
);

CREATE TABLE IF NOT EXISTS facility_request_events (
    id SERIAL PRIMARY KEY,
    facility_request_id INTEGER NOT NULL REFERENCES facility_requests(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    actor_id INTEGER REFERENCES users(id),
    actor_name_snapshot VARCHAR(100) NOT NULL,
    actor_role_snapshot VARCHAR(50),
    old_status VARCHAR(40),
    new_status VARCHAR(40),
    event_data JSONB,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facility_requests_status ON facility_requests(status);
CREATE INDEX IF NOT EXISTS idx_facility_requests_unit ON facility_requests(unit_id);
CREATE INDEX IF NOT EXISTS idx_facility_requests_submitter ON facility_requests(submitted_by);
CREATE INDEX IF NOT EXISTS idx_facility_request_items_request ON facility_request_items(facility_request_id);
CREATE INDEX IF NOT EXISTS idx_facility_approvals_request ON facility_approvals(facility_request_id);
CREATE INDEX IF NOT EXISTS idx_facility_approvals_stage ON facility_approvals(stage);
CREATE INDEX IF NOT EXISTS idx_facility_documents_request ON facility_documents(facility_request_id);
CREATE INDEX IF NOT EXISTS idx_facility_documents_hash ON facility_documents(sha256);
CREATE INDEX IF NOT EXISTS idx_facility_events_request ON facility_request_events(facility_request_id);
CREATE INDEX IF NOT EXISTS idx_facility_events_type ON facility_request_events(event_type);
"""


DOWNGRADE_SQL = """
DROP TABLE IF EXISTS facility_request_events;
DROP TABLE IF EXISTS facility_documents;
DROP TABLE IF EXISTS facility_approvals;
DROP TABLE IF EXISTS facility_verifications;
DROP TABLE IF EXISTS facility_request_items;
DROP TABLE IF EXISTS facility_requests;
DROP SEQUENCE IF EXISTS facility_form_number_seq;
"""


def run(sql, label):
    app = create_app()
    with app.app_context():
        print(label)
        statements = [statement.strip() for statement in sql.split(';') if statement.strip()]
        try:
            for statement in statements:
                db.session.execute(db.text(statement))
            db.session.commit()
            print('Facility request schema operation completed successfully.')
        except Exception:
            db.session.rollback()
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Facility request POC migration')
    parser.add_argument('--downgrade', action='store_true', help='Drop all facility request POC objects')
    args = parser.parse_args()
    run(DOWNGRADE_SQL if args.downgrade else UPGRADE_SQL,
        'Downgrading facility request schema...' if args.downgrade else 'Upgrading facility request schema...')
