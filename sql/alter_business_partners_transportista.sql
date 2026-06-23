-- Agrega campos de transportista a business_partners
ALTER TABLE business_partners
    ADD COLUMN IF NOT EXISTS transp_num_mtc           TEXT,
    ADD COLUMN IF NOT EXISTS transp_num_autorizacion  TEXT,
    ADD COLUMN IF NOT EXISTS transp_cod_entidad        TEXT;
