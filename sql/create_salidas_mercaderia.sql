-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Salidas de Mercadería
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS salidas_c (
    id               SERIAL         PRIMARY KEY,
    tipo_salida      TEXT           NOT NULL,
    fecha_salida     DATE           NOT NULL,
    almacen          TEXT,
    nro_referencia   TEXT,
    observaciones    TEXT,
    id_estado        INTEGER        DEFAULT 1,
    user_code        TEXT,
    imagen           TEXT,
    fecha_registro   TIMESTAMP      DEFAULT NOW(),
    fecha_modificacion TIMESTAMP
);

CREATE TABLE IF NOT EXISTS salidas_d (
    id          SERIAL         PRIMARY KEY,
    salida_id   INTEGER        NOT NULL REFERENCES salidas_c(id) ON DELETE CASCADE,
    item_code   TEXT           NOT NULL,
    item_name   TEXT,
    quantity    NUMERIC(18, 4) DEFAULT 0,
    uom         TEXT,
    price_cost  NUMERIC(18, 4) DEFAULT 0,
    subtotal    NUMERIC(18, 2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_salidas_d_cab ON salidas_d (salida_id);

-- ── SP listar ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_salida_listar(p_limit INTEGER DEFAULT 200)
RETURNS TABLE (
    id                 INTEGER,
    tipo_salida        TEXT,
    fecha_salida       DATE,
    almacen            TEXT,
    whs_name           TEXT,
    nro_referencia     TEXT,
    observaciones      TEXT,
    id_estado          INTEGER,
    user_code          TEXT,
    user_nombre        TEXT,
    fecha_registro     TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    total_items        BIGINT,
    total_costo        NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT
        c.id,
        COALESCE(c.tipo_salida, '')::TEXT,
        c.fecha_salida,
        COALESCE(c.almacen, '')::TEXT,
        COALESCE(TRIM(w.whs_name), c.almacen, '')::TEXT,
        COALESCE(c.nro_referencia, '')::TEXT,
        COALESCE(c.observaciones, '')::TEXT,
        COALESCE(c.id_estado, 1),
        COALESCE(c.user_code, '')::TEXT,
        COALESCE(u.nombres, c.user_code, '')::TEXT AS user_nombre,
        c.fecha_registro,
        c.fecha_modificacion,
        COUNT(d.id),
        COALESCE(SUM(d.subtotal), 0)
    FROM salidas_c c
    LEFT JOIN salidas_d d ON d.salida_id = c.id
    LEFT JOIN warehouses w ON TRIM(w.whs_code) = TRIM(c.almacen)
    LEFT JOIN w_usuarios u ON u.id_usuario = c.user_code
    GROUP BY c.id, c.tipo_salida, c.fecha_salida, c.almacen, w.whs_name,
             c.nro_referencia, c.observaciones, c.id_estado, c.user_code, u.nombres,
             c.fecha_registro, c.fecha_modificacion
    ORDER BY c.id DESC
    LIMIT p_limit;
$$;

-- ── SP items ─────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_salida_items_listar(p_salida_id INTEGER)
RETURNS TABLE (
    id         INTEGER,
    salida_id  INTEGER,
    item_code  TEXT,
    item_name  TEXT,
    quantity   NUMERIC,
    uom        TEXT,
    price_cost NUMERIC,
    subtotal   NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT d.id, d.salida_id,
           COALESCE(d.item_code, '')::TEXT,
           COALESCE(d.item_name, d.item_code, '')::TEXT,
           COALESCE(d.quantity, 0),
           COALESCE(d.uom, '')::TEXT,
           COALESCE(d.price_cost, 0),
           COALESCE(d.subtotal, 0)
    FROM salidas_d d
    WHERE d.salida_id = p_salida_id
    ORDER BY d.id;
$$;

-- ── Menú (submenu Almacén id_parent=4) ───────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (47, 4, 'Salidas', 'main.almacen_salidas', 'bi-box-arrow-up', 4)
ON CONFLICT (id_menu) DO NOTHING;
