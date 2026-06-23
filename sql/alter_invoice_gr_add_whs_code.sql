-- Agrega campo whs_code a invoice_gr para registrar el almacén de partida
ALTER TABLE invoice_gr ADD COLUMN IF NOT EXISTS whs_code TEXT;
