-- Agrega columnas SUNAT extendidas a la tabla invoice
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS sunat_hash TEXT;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS sunat_xml  TEXT;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS sunat_cdr  TEXT;
