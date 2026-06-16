-- ═══════════════════════════════════════════════════════════════
--  Tabla: bancos_estado_cuenta
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS bancos_estado_cuenta (
    id             SERIAL         PRIMARY KEY,
    id_cancelacion INTEGER,
    id_invoice     INTEGER,
    fecha_pago     DATE,
    moneda_pago    TEXT           DEFAULT 'SOL',
    referencia     TEXT,
    concepto       TEXT,
    monto_aplicado NUMERIC(18, 2),
    id_banco       INTEGER,
    nombre_banco   TEXT,
    user_code      TEXT,
    fecha_registro TIMESTAMP      DEFAULT NOW()
);

ALTER TABLE bancos_estado_cuenta
    ADD COLUMN IF NOT EXISTS card_code     TEXT;
ALTER TABLE bancos_estado_cuenta
    ADD COLUMN IF NOT EXISTS nro_documento TEXT;

CREATE INDEX IF NOT EXISTS idx_bec_banco   ON bancos_estado_cuenta (id_banco);
CREATE INDEX IF NOT EXISTS idx_bec_canc    ON bancos_estado_cuenta (id_cancelacion);
CREATE INDEX IF NOT EXISTS idx_bec_invoice ON bancos_estado_cuenta (id_invoice);
CREATE INDEX IF NOT EXISTS idx_bec_fecha   ON bancos_estado_cuenta (fecha_pago);


-- ═══════════════════════════════════════════════════════════════
--  sp_bancos_estado_cuenta_listar(p_id_banco)
--  0 = todos los bancos
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_bancos_estado_cuenta_listar(
    p_id_banco INTEGER
)
RETURNS TABLE (
    "id"             INTEGER,
    "id_cancelacion" INTEGER,
    "id_invoice"     INTEGER,
    "nro_documento"  TEXT,
    "card_code"      TEXT,
    "card_name"      TEXT,
    "id_banco"       INTEGER,
    "nombre_banco"   TEXT,
    "fecha_pago"     DATE,
    "moneda_pago"    TEXT,
    "referencia"     TEXT,
    "concepto"       TEXT,
    "monto_aplicado" NUMERIC,
    "user_code"      TEXT,
    "fecha_registro" TIMESTAMP,
    "id_estado"      INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bec.id,
        bec.id_cancelacion,
        bec.id_invoice,
        COALESCE(
            bec.nro_documento,
            inv.invoice_serie || '-' || inv.invoice_number,
            '#' || bec.id_invoice::TEXT
        )                                              ::TEXT AS nro_documento,
        COALESCE(bec.card_code, '')                    ::TEXT,
        COALESCE(bp.card_name, bec.card_code, '')      ::TEXT AS card_name,
        bec.id_banco,
        COALESCE(bk.nombre, bec.nombre_banco, '')      ::TEXT AS nombre_banco,
        bec.fecha_pago,
        COALESCE(bec.moneda_pago, 'SOL')               ::TEXT,
        COALESCE(bec.referencia, '')                   ::TEXT,
        COALESCE(bec.concepto, '')                     ::TEXT,
        COALESCE(bec.monto_aplicado, 0),
        COALESCE(bec.user_code, '')                    ::TEXT,
        bec.fecha_registro,
        COALESCE(ic.id_estado, 1)                      AS id_estado
    FROM bancos_estado_cuenta      bec
    LEFT JOIN bancos               bk  ON bk.id_banco         = bec.id_banco
    LEFT JOIN invoice              inv ON inv.invoice_id       = bec.id_invoice
    LEFT JOIN invoice_cancelaciones ic ON ic.id_cancelacion   = bec.id_cancelacion
    LEFT JOIN business_partners    bp  ON bp.card_code         = bec.card_code
    WHERE (p_id_banco = 0 OR bec.id_banco = p_id_banco)
    ORDER BY bec.fecha_registro DESC;
END;
$$ LANGUAGE plpgsql;
