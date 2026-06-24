-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Stock por Almacén
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Agregar ítem al catálogo de menú ─────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (42, 4, 'Stock', 'main.almacen_stock', 'bi-layers', 2)
ON CONFLICT (id_menu) DO NOTHING;

-- ── 2. Función principal de consulta ────────────────────────────
CREATE OR REPLACE FUNCTION sp_stock_listar(p_almacen TEXT DEFAULT NULL)
RETURNS TABLE (
    item_code   TEXT,
    item_name   TEXT,
    almacen     TEXT,
    whs_name    TEXT,
    stock       NUMERIC,
    avg_price   NUMERIC,
    valor_total NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT
        m.item_code::TEXT,
        m.item_name::TEXT,
        TRIM(m.almacen)::TEXT                            AS almacen,
        COALESCE(TRIM(w.whs_name), TRIM(m.almacen))::TEXT AS whs_name,
        SUM(m.quantity)                                  AS stock,
        AVG(m.avg_price)                                 AS avg_price,
        SUM(m.quantity * COALESCE(m.price_cost, m.avg_price, 0)) AS valor_total
    FROM   movimientos_almacen m
    LEFT JOIN warehouses w ON TRIM(w.whs_code) = TRIM(m.almacen)
    WHERE  (p_almacen IS NULL OR p_almacen = ''
            OR TRIM(m.almacen) = TRIM(p_almacen))
    GROUP  BY m.item_code, m.item_name, TRIM(m.almacen), TRIM(w.whs_name)
    ORDER  BY m.item_code, TRIM(m.almacen);
$$;
