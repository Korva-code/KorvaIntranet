-- Agrega campo ubigeo a business_partners_addresses
ALTER TABLE business_partners_addresses
    ADD COLUMN IF NOT EXISTS ubigeo TEXT;
