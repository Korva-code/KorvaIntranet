-- Agrega campos SUNAT a invoice_gr para guardar la respuesta de apisunat.pe
ALTER TABLE invoice_gr
    ADD COLUMN IF NOT EXISTS sunat_estado  TEXT,
    ADD COLUMN IF NOT EXISTS sunat_hash    TEXT,
    ADD COLUMN IF NOT EXISTS sunat_xml     TEXT,
    ADD COLUMN IF NOT EXISTS sunat_cdr     TEXT,
    ADD COLUMN IF NOT EXISTS sunat_ticket  TEXT,
    ADD COLUMN IF NOT EXISTS sunat_a4      TEXT;
