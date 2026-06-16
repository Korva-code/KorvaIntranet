-- Ejecutar una sola vez.
-- Agrega columna id_abono a bancos_estado_cuenta para trazabilidad de abonos aplicados.

ALTER TABLE bancos_estado_cuenta
    ADD COLUMN IF NOT EXISTS id_abono INTEGER;

CREATE INDEX IF NOT EXISTS idx_bec_abono ON bancos_estado_cuenta (id_abono);
