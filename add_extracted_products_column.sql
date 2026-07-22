-- Add extracted_products column to email_ingestions table
-- Run this on the production database after deploying the code change
ALTER TABLE email_ingestions ADD COLUMN IF NOT EXISTS extracted_products JSON;
