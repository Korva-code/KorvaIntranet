-- ═══════════════════════════════════════════════════════════════
--  Tabla: invoice_cancelaciones
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS invoice_cancelaciones (
    id_cancelacion  SERIAL          PRIMARY KEY,
    invoice_id      INTEGER         NOT NULL,        -- factura de venta
    card_code       TEXT,                            -- socio de negocio
    id_banco        INTEGER,                         -- banco donde se recibió el pago
    fecha_pago      DATE,
    moneda_pago     TEXT  DEFAULT 'SOL',             -- moneda del pago recibido
    tipo_cambio     NUMERIC(18, 6) DEFAULT 1,        -- TC cuando monedas difieren
    importe         NUMERIC(18, 2),                  -- monto total recibido (en moneda_pago)
    referencia      TEXT,                            -- N° operación / voucher
    concepto        TEXT,
    monto_factura   NUMERIC(18, 2),                  -- total de la factura
    moneda_factura  TEXT,                            -- moneda de la factura
    monto_aplicado  NUMERIC(18, 2),                  -- monto cancelado (en moneda factura)
    user_code       TEXT,
    fecha_registro  TIMESTAMP DEFAULT NOW(),
    id_estado       INTEGER DEFAULT 1
);

-- ═══════════════════════════════════════════════════════════════
--  sp_facturas_pendientes(p_card_code)
--  Devuelve facturas con saldo pendiente de cobro
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_facturas_pendientes(
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
    FROM invoice i
    LEFT JOIN business_partners       bp ON bp.card_code  = i.card_code
    LEFT JOIN invoice_cancelaciones   ic ON ic.invoice_id = i.invoice_id
                                        AND ic.id_estado  = 1
    WHERE (p_card_code = '' OR i.card_code = p_card_code)
    GROUP BY i.invoice_id, i.card_code, bp.card_name,
             i.invoice_type, i.invoice_serie, i.invoice_number,
             i.doc_date, i.doc_due_date, i.doc_currency, i.doc_total
    HAVING COALESCE(i.doc_total, 0) - COALESCE(SUM(ic.monto_aplicado), 0) > 0
    ORDER BY i.doc_due_date ASC NULLS LAST, i.invoice_id ASC;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_cancelaciones_listar(p_id)
--  Lista cancelaciones (0 = todas)
-- ═══════════════════════════════════════════════════════════════
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
    "user_name"       TEXT,
    "fecha_registro"  TIMESTAMP,
    "id_estado"       INTEGER,
    "id_payment"      INTEGER,
    "payment_name"    TEXT
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
        COALESCE(u.nombres, c.user_code, '')            ::TEXT AS user_name,
        c.fecha_registro,
        c.id_estado,
        c.id_payment,
        COALESCE(py.payment_name, '')                   ::TEXT AS payment_name
    FROM invoice_cancelaciones c
    LEFT JOIN invoice            i  ON i.invoice_id  = c.invoice_id
    LEFT JOIN business_partners  bp ON bp.card_code  = c.card_code
    LEFT JOIN bancos              b  ON b.id_banco    = c.id_banco
    LEFT JOIN usuarios           u  ON u.id_usuario  = c.user_code
    LEFT JOIN payment            py ON py.id_payment = c.id_payment
    WHERE (p_id = 0 OR c.id_cancelacion = p_id)
    ORDER BY c.fecha_registro DESC;
END;
$$ LANGUAGE plpgsql;
