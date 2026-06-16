-- ══════════════════════════════════════════════════════════════
-- Corrección fecha_hora_transaccion en invoice
-- Problemas: (1) hora en UTC en vez de Lima  (2) microsegundos
-- Solución : TIMESTAMP(0) + AT TIME ZONE 'America/Lima'
-- ══════════════════════════════════════════════════════════════

-- 1. Agregar columna si no existe (primera ejecución)
ALTER TABLE invoice
    ADD COLUMN IF NOT EXISTS fecha_hora_transaccion TIMESTAMP(0);

-- 2. Cambiar precisión a TIMESTAMP(0) — elimina microsegundos
--    (si ya existía como TIMESTAMP normal)
ALTER TABLE invoice
    ALTER COLUMN fecha_hora_transaccion TYPE TIMESTAMP(0)
    USING fecha_hora_transaccion::TIMESTAMP(0);

-- 3. Trigger: hora local Lima, sin microsegundos
CREATE OR REPLACE FUNCTION trg_invoice_set_fecha_hora()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_hora_transaccion :=
        date_trunc('second', NOW() AT TIME ZONE 'America/Lima');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_invoice_fecha_hora ON invoice;

CREATE TRIGGER trg_invoice_fecha_hora
    BEFORE INSERT ON invoice
    FOR EACH ROW
    EXECUTE FUNCTION trg_invoice_set_fecha_hora();

-- 4. Corregir registros existentes con hora UTC incorrecta
UPDATE invoice
   SET fecha_hora_transaccion =
       date_trunc('second',
           fecha_hora_transaccion AT TIME ZONE 'UTC'
                                 AT TIME ZONE 'America/Lima')
 WHERE fecha_hora_transaccion IS NOT NULL;
