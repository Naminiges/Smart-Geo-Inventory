-- Migration: Add verification fields to distributions table
-- Run this SQL directly in your PostgreSQL database

-- Add task_type column
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS task_type VARCHAR(50) DEFAULT 'installation';

-- Add verification_photo column
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS verification_photo VARCHAR(500);

-- Add verification_notes column
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS verification_notes TEXT;

-- Add verified_by column (foreign key to users)
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS verified_by INTEGER;

-- Add foreign key constraint for verified_by
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_distributions_verified_by'
    ) THEN
        ALTER TABLE distributions
        ADD CONSTRAINT fk_distributions_verified_by
        FOREIGN KEY (verified_by) REFERENCES users(id);
    END IF;
END $$;

-- Add verified_at column
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;

-- Add verification_status column
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'pending';

-- Add verification_rejection_reason column
ALTER TABLE distributions
ADD COLUMN IF NOT EXISTS verification_rejection_reason TEXT;

-- Create index on verification_status for better query performance
CREATE INDEX IF NOT EXISTS idx_distributions_verification_status ON distributions(verification_status);

-- Create index on field_staff_id and verification_status for field staff queries
CREATE INDEX IF NOT EXISTS idx_distributions_field_staff_verification ON distributions(field_staff_id, verification_status);

COMMENT ON COLUMN distributions.task_type IS 'Type of task: installation or delivery';
COMMENT ON COLUMN distributions.verification_photo IS 'Path to verification photo uploaded by field staff';
COMMENT ON COLUMN distributions.verification_notes IS 'Notes from field staff about task completion';
COMMENT ON COLUMN distributions.verified_by IS 'ID of warehouse staff who verified the task';
COMMENT ON COLUMN distributions.verified_at IS 'Timestamp when task was verified';
COMMENT ON COLUMN distributions.verification_status IS 'Verification status: pending, submitted, verified, rejected';
COMMENT ON COLUMN distributions.verification_rejection_reason IS 'Reason for rejection if verification was rejected';
