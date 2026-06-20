-- Direct SQL fix for the documents table
-- Run this in your MySQL client with: mysql -u username -p database_name < fix_documents_table.sql

-- Fix the created_at column to have a proper default value
ALTER TABLE documents 
MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Make sure all other required columns exist and have proper defaults
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255) NULL,
ADD COLUMN IF NOT EXISTS storage_path VARCHAR(512) NOT NULL DEFAULT '' AFTER file_type,
ADD COLUMN IF NOT EXISTS is_excel TINYINT(1) NOT NULL DEFAULT 0 AFTER created_at;

-- Ensure session_id has the proper index
ALTER TABLE documents 
ADD INDEX IF NOT EXISTS ix_documents_session_id (session_id);

SHOW COLUMNS FROM documents;
