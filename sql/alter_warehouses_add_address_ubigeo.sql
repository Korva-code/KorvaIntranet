-- Agrega dirección completa y ubigeo a warehouses (para usar en Guías de Remisión)
ALTER TABLE warehouses
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS ubigeo  TEXT;
