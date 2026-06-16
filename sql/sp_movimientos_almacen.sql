-- ═══════════════════════════════════════════════════════════════
--  Tabla: movimientos_almacen
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS movimientos_almacen (
    id              SERIAL          PRIMARY KEY,
    invoice_id      INTEGER,
    card_code       TEXT,
    invoice_type    TEXT,
    id_tipo         INTEGER,
    doc_date        DATE,
    item_code       TEXT,
    item_name       TEXT,
    quantity        NUMERIC(18, 4),
    avg_price       NUMERIC(18, 4),
    subtotal        NUMERIC(18, 2),
    almacen         TEXT,
    tipo_movimiento TEXT            DEFAULT 'SAL',
    user_code       TEXT,
    fecha_registro  TIMESTAMP       DEFAULT NOW()
);

ALTER TABLE movimientos_almacen
    ADD COLUMN IF NOT EXISTS origen TEXT;

CREATE INDEX IF NOT EXISTS idx_mov_item    ON movimientos_almacen (item_code);
CREATE INDEX IF NOT EXISTS idx_mov_almacen ON movimientos_almacen (almacen);
CREATE INDEX IF NOT EXISTS idx_mov_invoice ON movimientos_almacen (invoice_id);
CREATE INDEX IF NOT EXISTS idx_mov_fecha   ON movimientos_almacen (doc_date);


-- ═══════════════════════════════════════════════════════════════
--  sp_kardex_listar(p_item_code, p_almacen)
--  '' = todos
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_kardex_listar(
    p_item_code TEXT,
    p_almacen   TEXT
)
RETURNS TABLE (
    "id"              INTEGER,
    "doc_date"        DATE,
    "invoice_id"      INTEGER,
    "invoice_type"    TEXT,
    "card_code"       TEXT,
    "bp_name"         TEXT,
    "item_code"       TEXT,
    "item_name"       TEXT,
    "almacen"         TEXT,
    "almacen_nombre"  TEXT,
    "origen"          TEXT,
    "tipo_movimiento" TEXT,
    "quantity"        NUMERIC,
    "avg_price"       NUMERIC,
    "subtotal"        NUMERIC,
    "stock_acum"      NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.doc_date,
        m.invoice_id,
        COALESCE(m.invoice_type, '')                        ::TEXT,
        COALESCE(m.card_code, '')                           ::TEXT,
        COALESCE(bp.card_name, m.card_code, '')             ::TEXT AS bp_name,
        COALESCE(m.item_code, '')                           ::TEXT,
        COALESCE(it.item_name, m.item_name, m.item_code, '')::TEXT AS item_name,
        COALESCE(m.almacen, '')                             ::TEXT,
        TRIM(COALESCE(w.whs_name, m.almacen, ''))           ::TEXT AS almacen_nombre,
        COALESCE(m.origen, '')                              ::TEXT,
        COALESCE(m.tipo_movimiento, 'SAL')                  ::TEXT,
        COALESCE(m.quantity, 0),
        COALESCE(m.avg_price, 0),
        COALESCE(m.subtotal, 0),
        SUM(COALESCE(m.quantity, 0)) OVER (
            PARTITION BY m.item_code, m.almacen
            ORDER BY m.doc_date, m.id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS stock_acum
    FROM movimientos_almacen m
    LEFT JOIN business_partners bp ON bp.card_code        = m.card_code
    LEFT JOIN items             it ON it.item_code         = m.item_code
    LEFT JOIN warehouses         w ON TRIM(w.whs_code)    = TRIM(m.almacen)
    WHERE (p_item_code = '' OR m.item_code = p_item_code)
      AND (p_almacen   = '' OR m.almacen   = p_almacen)
    ORDER BY m.item_code, m.almacen, m.doc_date, m.id;
END;
$$ LANGUAGE plpgsql;
