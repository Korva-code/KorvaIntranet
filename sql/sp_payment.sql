-- ═══════════════════════════════════════════════════════════════
-- Tabla: payment  (medios de pago)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS payment (
    id_payment   SERIAL PRIMARY KEY,
    payment_name TEXT   NOT NULL
);

INSERT INTO payment (payment_name) VALUES
    ('NINGUNO'),
    ('EFECTIVO'),
    ('VISA'),
    ('MASTERCARD'),
    ('YAPE')
ON CONFLICT DO NOTHING;

-- ── Listar medios de pago ─────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_payment_listar()
RETURNS TABLE (id_payment INTEGER, payment_name TEXT)
LANGUAGE sql STABLE AS $$
    SELECT id_payment, payment_name::TEXT FROM payment ORDER BY id_payment;
$$;

-- ── Agregar id_payment a invoice_cancelaciones ─────────────────
ALTER TABLE invoice_cancelaciones
    ADD COLUMN IF NOT EXISTS id_payment INTEGER REFERENCES payment(id_payment);

-- ── sp_cancelaciones_listar actualizado con payment_name ───────
CREATE OR REPLACE FUNCTION sp_cancelaciones_listar(
    p_id INTEGER
)
RETURNS TABLE (
    "id_cancelacion"  INTEGER,
    "invoice_id"      INTEGER,
    "invoice_numero"  TEXT,
    "card_code"       TEXT,
    "bp_name"         TEXT,
    "banco_nombre"    TEXT,
    "payment_name"    TEXT,
    "fecha_factura"   DATE,
    "fecha_pago"      DATE,
    "moneda_pago"     TEXT,
    "tipo_cambio"     NUMERIC,
    "importe"         NUMERIC,
    "moneda_factura"  TEXT,
    "monto_factura"   NUMERIC,
    "monto_aplicado"  NUMERIC,
    "doc_total"       NUMERIC,
    "doc_total_aply"  NUMERIC,
    "referencia"      TEXT,
    "concepto"        TEXT,
    "user_code"       TEXT,
    "fecha_registro"  TIMESTAMP,
    "id_estado"       INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_cancelacion,
        c.invoice_id,
        COALESCE(i.invoice_serie || '-' || i.invoice_number, '#' || c.invoice_id::TEXT) ::TEXT AS invoice_numero,
        c.card_code                                     ::TEXT,
        COALESCE(bp.card_name, c.card_code, '')         ::TEXT AS bp_name,
        COALESCE(b.nombre, '')                          ::TEXT AS banco_nombre,
        COALESCE(py.payment_name, '')                   ::TEXT AS payment_name,
        i.doc_date                                      AS fecha_factura,
        c.fecha_pago,
        c.moneda_pago                                   ::TEXT,
        c.tipo_cambio,
        c.importe,
        c.moneda_factura                                ::TEXT,
        c.monto_factura,
        c.monto_aplicado,
        COALESCE(i.doc_total, 0)                        AS doc_total,
        COALESCE(i.doc_total_aply, 0)                   AS doc_total_aply,
        c.referencia                                    ::TEXT,
        c.concepto                                      ::TEXT,
        c.user_code                                     ::TEXT,
        c.fecha_registro,
        c.id_estado
    FROM invoice_cancelaciones c
    LEFT JOIN invoice            i  ON i.invoice_id  = c.invoice_id
    LEFT JOIN business_partners  bp ON bp.card_code  = c.card_code
    LEFT JOIN bancos              b  ON b.id_banco    = c.id_banco
    LEFT JOIN payment            py  ON py.id_payment = c.id_payment
    WHERE (p_id = 0 OR c.id_cancelacion = p_id)
    ORDER BY c.fecha_registro DESC;
END;
$$ LANGUAGE plpgsql;
