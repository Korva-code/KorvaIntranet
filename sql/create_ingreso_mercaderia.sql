-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Ingreso de Mercadería
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ingreso_c (
    id               SERIAL         PRIMARY KEY,
    tipo_ingreso     TEXT           NOT NULL,
    fecha_ingreso    DATE           NOT NULL,
    almacen          TEXT,
    nro_orden_compra TEXT,
    observaciones    TEXT,
    id_estado        INTEGER        DEFAULT 1,
    user_code        TEXT,
    fecha_registro   TIMESTAMP      DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingreso_d (
    id          SERIAL         PRIMARY KEY,
    ingreso_id  INTEGER        NOT NULL REFERENCES ingreso_c(id) ON DELETE CASCADE,
    item_code   TEXT           NOT NULL,
    item_name   TEXT,
    quantity    NUMERIC(18, 4) DEFAULT 0,
    uom         TEXT,
    price_cost  NUMERIC(18, 4) DEFAULT 0,
    subtotal    NUMERIC(18, 2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ingreso_d_cab ON ingreso_d (ingreso_id);

-- ── SP listar ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_ingreso_listar(p_limit INTEGER DEFAULT 200)
RETURNS TABLE (
    id               INTEGER,
    tipo_ingreso     TEXT,
    fecha_ingreso    DATE,
    almacen          TEXT,
    whs_name         TEXT,
    nro_orden_compra TEXT,
    observaciones    TEXT,
    id_estado           INTEGER,
    user_code           TEXT,
    user_nombre         TEXT,
    fecha_registro      TIMESTAMP,
    fecha_modificacion  TIMESTAMP,
    total_items         BIGINT,
    total_costo         NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT
        c.id,
        COALESCE(c.tipo_ingreso, '')::TEXT,
        c.fecha_ingreso,
        COALESCE(c.almacen, '')::TEXT,
        COALESCE(TRIM(w.whs_name), c.almacen, '')::TEXT,
        COALESCE(c.nro_orden_compra, '')::TEXT,
        COALESCE(c.observaciones, '')::TEXT,
        COALESCE(c.id_estado, 1),
        COALESCE(c.user_code, '')::TEXT,
        COALESCE(u.nombres, c.user_code, '')::TEXT AS user_nombre,
        c.fecha_registro,
        c.fecha_modificacion,
        COUNT(d.id),
        COALESCE(SUM(d.subtotal), 0)
    FROM ingreso_c c
    LEFT JOIN ingreso_d d ON d.ingreso_id = c.id
    LEFT JOIN warehouses w ON TRIM(w.whs_code) = TRIM(c.almacen)
    LEFT JOIN w_usuarios u ON u.id_usuario = c.user_code
    GROUP BY c.id, c.tipo_ingreso, c.fecha_ingreso, c.almacen, w.whs_name,
             c.nro_orden_compra, c.observaciones, c.id_estado, c.user_code, u.nombres,
             c.fecha_registro, c.fecha_modificacion
    ORDER BY c.id DESC
    LIMIT p_limit;
$$;

-- ── SP items ─────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_ingreso_items_listar(p_ingreso_id INTEGER)
RETURNS TABLE (
    id          INTEGER,
    ingreso_id  INTEGER,
    item_code   TEXT,
    item_name   TEXT,
    quantity    NUMERIC,
    uom         TEXT,
    price_cost  NUMERIC,
    subtotal    NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT d.id, d.ingreso_id,
           COALESCE(d.item_code, '')::TEXT,
           COALESCE(d.item_name, d.item_code, '')::TEXT,
           COALESCE(d.quantity, 0),
           COALESCE(d.uom, '')::TEXT,
           COALESCE(d.price_cost, 0),
           COALESCE(d.subtotal, 0)
    FROM ingreso_d d
    WHERE d.ingreso_id = p_ingreso_id
    ORDER BY d.id;
$$;

-- ── Menú (submenu Almacén id_parent=4) ───────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (46, 4, 'Ingresos', 'main.almacen_ingresos', 'bi-box-arrow-in-down', 3)
ON CONFLICT (id_menu) DO NOTHING;
