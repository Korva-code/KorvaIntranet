-- ═══════════════════════════════════════════════════════════════
--  Tabla: invoice_p_cancelaciones
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS invoice_p_cancelaciones (
    id_p_cancelacion SERIAL          PRIMARY KEY,
    invoice_p_id     INTEGER         NOT NULL,
    card_code        TEXT,
    id_banco         INTEGER,
    fecha_pago       DATE,
    moneda_pago      TEXT  DEFAULT 'SOL',
    tipo_cambio      NUMERIC(18, 6) DEFAULT 1,
    importe          NUMERIC(18, 2),
    referencia       TEXT,
    concepto         TEXT,
    monto_factura    NUMERIC(18, 2),
    moneda_factura   TEXT,
    monto_aplicado   NUMERIC(18, 2),
    user_code        TEXT,
    fecha_registro   TIMESTAMP DEFAULT NOW(),
    id_estado        INTEGER DEFAULT 1
);

-- Campo en invoice_p para acumulado aplicado
ALTER TABLE invoice_p
    ADD COLUMN IF NOT EXISTS doc_total_aply NUMERIC(18, 2) DEFAULT 0;

-- Recalcular doc_total_aply desde datos existentes
UPDATE invoice_p ip SET doc_total_aply = COALESCE((
    SELECT SUM(ic.monto_aplicado) FROM invoice_p_cancelaciones ic
    WHERE ic.invoice_p_id = ip.invoice_id AND ic.id_estado = 1
), 0);


-- ═══════════════════════════════════════════════════════════════
--  sp_facturas_p_pendientes(p_card_code)
--  Facturas de compra con saldo pendiente de pago
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_facturas_p_pendientes(
    p_card_code TEXT
)
RETURNS TABLE (
    "invoice_id"       INTEGER,
    "card_code"        TEXT,
    "bp_name"          TEXT,
    "invoice_type"     TEXT,
    "invoice_serie"    TEXT,
    "invoice_number"   TEXT,
    "doc_date"         DATE,
    "doc_due_date"     DATE,
    "doc_currency"     TEXT,
    "monto_factura"    NUMERIC,
    "total_aplicado"   NUMERIC,
    "saldo_pendiente"  NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.invoice_id,
        i.card_code                                        ::TEXT,
        COALESCE(bp.card_name, i.card_code)               ::TEXT AS bp_name,
        i.invoice_type                                     ::TEXT,
        i.invoice_serie                                    ::TEXT,
        i.invoice_number                                   ::TEXT,
        i.doc_date,
        i.doc_due_date,
        i.doc_currency                                     ::TEXT,
        COALESCE(i.doc_total, 0)                           AS monto_factura,
        COALESCE(SUM(ic.monto_aplicado), 0)                AS total_aplicado,
        COALESCE(i.doc_total, 0) - COALESCE(SUM(ic.monto_aplicado), 0) AS saldo_pendiente
    FROM invoice_p i
    LEFT JOIN business_partners         bp ON bp.card_code   = i.card_code
    LEFT JOIN invoice_p_cancelaciones   ic ON ic.invoice_p_id = i.invoice_id
                                          AND ic.id_estado    = 1
    WHERE (p_card_code = '' OR i.card_code = p_card_code)
    GROUP BY i.invoice_id, i.card_code, bp.card_name,
             i.invoice_type, i.invoice_serie, i.invoice_number,
             i.doc_date, i.doc_due_date, i.doc_currency, i.doc_total
    HAVING COALESCE(i.doc_total, 0) - COALESCE(SUM(ic.monto_aplicado), 0) > 0
    ORDER BY i.doc_due_date ASC NULLS LAST, i.invoice_id ASC;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_p_cancelaciones_listar(p_id)
--  Lista pagos a proveedores (0 = todos)
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_p_cancelaciones_listar(
    p_id INTEGER
)
RETURNS TABLE (
    "id_p_cancelacion" INTEGER,
    "invoice_p_id"     INTEGER,
    "invoice_numero"   TEXT,
    "card_code"        TEXT,
    "bp_name"          TEXT,
    "banco_nombre"     TEXT,
    "fecha_factura"    DATE,
    "fecha_pago"       DATE,
    "moneda_pago"      TEXT,
    "tipo_cambio"      NUMERIC,
    "importe"          NUMERIC,
    "moneda_factura"   TEXT,
    "monto_factura"    NUMERIC,
    "monto_aplicado"   NUMERIC,
    "doc_total"        NUMERIC,
    "doc_total_aply"   NUMERIC,
    "referencia"       TEXT,
    "concepto"         TEXT,
    "user_code"        TEXT,
    "fecha_registro"   TIMESTAMP,
    "id_estado"        INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_p_cancelacion,
        c.invoice_p_id,
        COALESCE(i.invoice_serie || '-' || i.invoice_number, '#' || c.invoice_p_id::TEXT) ::TEXT AS invoice_numero,
        c.card_code                                     ::TEXT,
        COALESCE(bp.card_name, c.card_code, '')         ::TEXT AS bp_name,
        COALESCE(b.nombre, '')                          ::TEXT AS banco_nombre,
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
    FROM invoice_p_cancelaciones c
    LEFT JOIN invoice_p           i  ON i.invoice_id  = c.invoice_p_id
    LEFT JOIN business_partners   bp ON bp.card_code  = c.card_code
    LEFT JOIN bancos               b  ON b.id_banco    = c.id_banco
    WHERE (p_id = 0 OR c.id_p_cancelacion = p_id)
    ORDER BY c.fecha_registro DESC;
END;
$$ LANGUAGE plpgsql;
