-- ═══════════════════════════════════════════════════════════════
--  Agregar campo doc_total_aply a la tabla invoice
--  Almacena la suma acumulada de montos aplicados (cancelaciones)
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE invoice
    ADD COLUMN IF NOT EXISTS doc_total_aply NUMERIC(18, 2) DEFAULT 0;

-- Inicializar con los montos ya registrados en invoice_cancelaciones
-- (solo si la tabla ya tiene datos previos)
UPDATE invoice i
SET doc_total_aply = COALESCE((
    SELECT SUM(ic.monto_aplicado)
    FROM invoice_cancelaciones ic
    WHERE ic.invoice_id = i.invoice_id
      AND ic.id_estado  = 1
), 0);
