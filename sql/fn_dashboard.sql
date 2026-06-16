-- ============================================================
-- fn_dashboard.sql  –  Funciones PostgreSQL para Dashboard ERP
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. fn_dash_ventas_kpi()
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_ventas_kpi();
CREATE OR REPLACE FUNCTION fn_dash_ventas_kpi()
RETURNS TABLE (
    total_mes_actual    NUMERIC,
    total_mes_anterior  NUMERIC,
    variacion_pct       NUMERIC,
    docs_mes_actual     BIGINT,
    clientes_mes_actual BIGINT,
    ticket_promedio     NUMERIC,
    total_anio          NUMERIC,
    docs_anio           BIGINT
)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_actual    NUMERIC := 0;
    v_anterior  NUMERIC := 0;
    v_docs_act  BIGINT  := 0;
    v_clientes  BIGINT  := 0;
    v_anio      NUMERIC := 0;
    v_docs_anio BIGINT  := 0;
BEGIN
    SELECT
        COALESCE(SUM(CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                         THEN doc_total ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                         THEN doc_total ELSE 0 END), 0),
        COALESCE(COUNT(CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                           THEN invoice_id END), 0),
        COALESCE(COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                                     THEN card_code END), 0)
    INTO v_actual, v_anterior, v_docs_act, v_clientes
    FROM invoice
    WHERE doc_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month');

    SELECT
        COALESCE(SUM(doc_total), 0),
        COALESCE(COUNT(invoice_id), 0)
    INTO v_anio, v_docs_anio
    FROM invoice
    WHERE DATE_TRUNC('year', doc_date) = DATE_TRUNC('year', CURRENT_DATE);

    RETURN QUERY SELECT
        v_actual,
        v_anterior,
        CASE WHEN v_anterior = 0 THEN 0
             ELSE ROUND((v_actual - v_anterior) / NULLIF(v_anterior, 0) * 100, 1)
        END,
        v_docs_act,
        v_clientes,
        CASE WHEN v_docs_act = 0 THEN 0
             ELSE ROUND(v_actual / NULLIF(v_docs_act, 0), 2)
        END,
        v_anio,
        v_docs_anio;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 2. fn_dash_ventas_mensuales(p_meses INTEGER DEFAULT 12)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_ventas_mensuales(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_ventas_mensuales(p_meses INTEGER DEFAULT 12)
RETURNS TABLE (
    anio        INTEGER,
    mes         INTEGER,
    mes_nombre  TEXT,
    total_ventas NUMERIC,
    cant_docs   BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT
        EXTRACT(YEAR  FROM DATE_TRUNC('month', doc_date))::INTEGER  AS anio,
        EXTRACT(MONTH FROM DATE_TRUNC('month', doc_date))::INTEGER  AS mes,
        TO_CHAR(DATE_TRUNC('month', doc_date), 'Mon YYYY')          AS mes_nombre,
        COALESCE(SUM(doc_total), 0)                                  AS total_ventas,
        COUNT(invoice_id)                                            AS cant_docs
    FROM invoice
    WHERE doc_date >= DATE_TRUNC('month', CURRENT_DATE - ((p_meses - 1) * INTERVAL '1 month'))
    GROUP BY DATE_TRUNC('month', doc_date)
    ORDER BY anio, mes;
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. fn_dash_ventas_top_articulos(p_limit INTEGER DEFAULT 10)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_ventas_top_articulos(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_ventas_top_articulos(p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    item_code      TEXT,
    item_name      TEXT,
    total_cantidad NUMERIC,
    total_monto    NUMERIC,
    cant_facturas  BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT
        ii.item_code::TEXT,
        COALESCE(it.item_name, ii.item_code)::TEXT          AS item_name,
        COALESCE(SUM(ii.quantity), 0)                        AS total_cantidad,
        COALESCE(SUM(ii.quantity * ii.price_after_vat), 0)  AS total_monto,
        COUNT(DISTINCT i.invoice_id)                         AS cant_facturas
    FROM invoice_item ii
    JOIN invoice i ON i.invoice_id = ii.invoice_id
    LEFT JOIN items it ON it.item_code = ii.item_code
    WHERE i.doc_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY ii.item_code, COALESCE(it.item_name, ii.item_code)
    ORDER BY total_monto DESC
    LIMIT p_limit;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. fn_dash_ventas_top_clientes(p_limit INTEGER DEFAULT 8)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_ventas_top_clientes(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_ventas_top_clientes(p_limit INTEGER DEFAULT 8)
RETURNS TABLE (
    card_code   TEXT,
    card_name   TEXT,
    total_monto NUMERIC,
    cant_docs   BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT
        i.card_code::TEXT,
        COALESCE(bp.card_name, i.card_code)::TEXT  AS card_name,
        COALESCE(SUM(i.doc_total), 0)               AS total_monto,
        COUNT(i.invoice_id)                          AS cant_docs
    FROM invoice i
    LEFT JOIN business_partners bp ON bp.card_code = i.card_code
    WHERE i.doc_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY i.card_code, COALESCE(bp.card_name, i.card_code)
    ORDER BY total_monto DESC
    LIMIT p_limit;
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. fn_dash_compras_kpi()
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_compras_kpi();
CREATE OR REPLACE FUNCTION fn_dash_compras_kpi()
RETURNS TABLE (
    total_mes_actual    NUMERIC,
    total_mes_anterior  NUMERIC,
    variacion_pct       NUMERIC,
    docs_mes_actual     BIGINT,
    clientes_mes_actual BIGINT,
    ticket_promedio     NUMERIC,
    total_anio          NUMERIC,
    docs_anio           BIGINT
)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_actual    NUMERIC := 0;
    v_anterior  NUMERIC := 0;
    v_docs_act  BIGINT  := 0;
    v_proveed   BIGINT  := 0;
    v_anio      NUMERIC := 0;
    v_docs_anio BIGINT  := 0;
BEGIN
    SELECT
        COALESCE(SUM(CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                         THEN doc_total ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                         THEN doc_total ELSE 0 END), 0),
        COALESCE(COUNT(CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                           THEN invoice_id END), 0),
        COALESCE(COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                                     THEN card_code END), 0)
    INTO v_actual, v_anterior, v_docs_act, v_proveed
    FROM invoice_p
    WHERE doc_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month');

    SELECT
        COALESCE(SUM(doc_total), 0),
        COALESCE(COUNT(invoice_id), 0)
    INTO v_anio, v_docs_anio
    FROM invoice_p
    WHERE DATE_TRUNC('year', doc_date) = DATE_TRUNC('year', CURRENT_DATE);

    RETURN QUERY SELECT
        v_actual,
        v_anterior,
        CASE WHEN v_anterior = 0 THEN 0
             ELSE ROUND((v_actual - v_anterior) / NULLIF(v_anterior, 0) * 100, 1)
        END,
        v_docs_act,
        v_proveed,
        CASE WHEN v_docs_act = 0 THEN 0
             ELSE ROUND(v_actual / NULLIF(v_docs_act, 0), 2)
        END,
        v_anio,
        v_docs_anio;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. fn_dash_compras_mensuales(p_meses INTEGER DEFAULT 12)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_compras_mensuales(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_compras_mensuales(p_meses INTEGER DEFAULT 12)
RETURNS TABLE (
    anio          INTEGER,
    mes           INTEGER,
    mes_nombre    TEXT,
    total_ventas  NUMERIC,
    cant_docs     BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT
        EXTRACT(YEAR  FROM DATE_TRUNC('month', doc_date))::INTEGER  AS anio,
        EXTRACT(MONTH FROM DATE_TRUNC('month', doc_date))::INTEGER  AS mes,
        TO_CHAR(DATE_TRUNC('month', doc_date), 'Mon YYYY')          AS mes_nombre,
        COALESCE(SUM(doc_total), 0)                                  AS total_ventas,
        COUNT(invoice_id)                                            AS cant_docs
    FROM invoice_p
    WHERE doc_date >= DATE_TRUNC('month', CURRENT_DATE - ((p_meses - 1) * INTERVAL '1 month'))
    GROUP BY DATE_TRUNC('month', doc_date)
    ORDER BY anio, mes;
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. fn_dash_compras_top_articulos(p_limit INTEGER DEFAULT 10)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_compras_top_articulos(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_compras_top_articulos(p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    item_code      TEXT,
    item_name      TEXT,
    total_cantidad NUMERIC,
    total_monto    NUMERIC,
    cant_facturas  BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT
        ii.item_code::TEXT,
        COALESCE(it.item_name, ii.item_code)::TEXT          AS item_name,
        COALESCE(SUM(ii.quantity), 0)                        AS total_cantidad,
        COALESCE(SUM(ii.quantity * ii.price_after_vat), 0)  AS total_monto,
        COUNT(DISTINCT ip.invoice_id)                        AS cant_facturas
    FROM invoice_item_p ii
    JOIN invoice_p ip ON ip.invoice_id = ii.invoice_id
    LEFT JOIN items it ON it.item_code = ii.item_code
    WHERE ip.doc_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY ii.item_code, COALESCE(it.item_name, ii.item_code)
    ORDER BY total_monto DESC
    LIMIT p_limit;
$$;


-- ─────────────────────────────────────────────────────────────
-- 8. fn_dash_compras_top_proveedores(p_limit INTEGER DEFAULT 8)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_compras_top_proveedores(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_compras_top_proveedores(p_limit INTEGER DEFAULT 8)
RETURNS TABLE (
    card_code         TEXT,
    proveedor_nombre  TEXT,
    total_monto       NUMERIC,
    cant_docs         BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT
        ip.card_code::TEXT,
        COALESCE(bp.card_name, ip.card_code)::TEXT  AS proveedor_nombre,
        COALESCE(SUM(ip.doc_total), 0)               AS total_monto,
        COUNT(ip.invoice_id)                          AS cant_docs
    FROM invoice_p ip
    LEFT JOIN business_partners bp ON bp.card_code = ip.card_code
    WHERE ip.doc_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY ip.card_code, COALESCE(bp.card_name, ip.card_code)
    ORDER BY total_monto DESC
    LIMIT p_limit;
$$;


-- ─────────────────────────────────────────────────────────────
-- 9. fn_dash_ventas_mensuales_grupos(p_meses INTEGER DEFAULT 12)
--    Ventas mensuales desglosadas por grupo de artículo
--    items.itms_grp_cod → items_group.item_group_code
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_ventas_mensuales_grupos(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_ventas_mensuales_grupos(p_meses INTEGER DEFAULT 12)
RETURNS TABLE (
    anio         INTEGER,
    mes          INTEGER,
    mes_nombre   TEXT,
    group_code   INTEGER,
    group_name   TEXT,
    total_ventas NUMERIC
)
LANGUAGE sql STABLE AS $$
    SELECT
        EXTRACT(YEAR  FROM DATE_TRUNC('month', i.doc_date))::INTEGER   AS anio,
        EXTRACT(MONTH FROM DATE_TRUNC('month', i.doc_date))::INTEGER   AS mes,
        TO_CHAR(DATE_TRUNC('month', i.doc_date), 'Mon YYYY')           AS mes_nombre,
        COALESCE(it.itms_grp_cod, 0)::INTEGER                         AS group_code,
        COALESCE(ig.item_group_name, 'Sin Grupo')::TEXT               AS group_name,
        COALESCE(SUM(ii.quantity * ii.price_after_vat), 0)::NUMERIC   AS total_ventas
    FROM  invoice_item ii
    JOIN  invoice      i  ON i.invoice_id    = ii.invoice_id
    LEFT  JOIN items   it ON it.item_code    = ii.item_code
    LEFT  JOIN items_group ig ON ig.item_group_code = it.itms_grp_cod
    WHERE i.doc_date >= DATE_TRUNC('month', CURRENT_DATE - ((p_meses - 1) * INTERVAL '1 month'))
    GROUP BY
        DATE_TRUNC('month', i.doc_date),
        COALESCE(it.itms_grp_cod, 0),
        COALESCE(ig.item_group_name, 'Sin Grupo')
    ORDER BY anio, mes, group_name;
$$;


-- ─────────────────────────────────────────────────────────────
-- 10. fn_dash_compras_mensuales_grupos(p_meses INTEGER DEFAULT 12)
--     Compras mensuales desglosadas por grupo de artículo
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_compras_mensuales_grupos(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_compras_mensuales_grupos(p_meses INTEGER DEFAULT 12)
RETURNS TABLE (
    anio         INTEGER,
    mes          INTEGER,
    mes_nombre   TEXT,
    group_code   INTEGER,
    group_name   TEXT,
    total_compras NUMERIC
)
LANGUAGE sql STABLE AS $$
    SELECT
        EXTRACT(YEAR  FROM DATE_TRUNC('month', ip.doc_date))::INTEGER   AS anio,
        EXTRACT(MONTH FROM DATE_TRUNC('month', ip.doc_date))::INTEGER   AS mes,
        TO_CHAR(DATE_TRUNC('month', ip.doc_date), 'Mon YYYY')           AS mes_nombre,
        COALESCE(it.itms_grp_cod, 0)::INTEGER                          AS group_code,
        COALESCE(ig.item_group_name, 'Sin Grupo')::TEXT                AS group_name,
        COALESCE(SUM(ii.quantity * ii.price_after_vat), 0)::NUMERIC    AS total_compras
    FROM  invoice_item_p ii
    JOIN  invoice_p      ip ON ip.invoice_id     = ii.invoice_id
    LEFT  JOIN items     it ON it.item_code      = ii.item_code
    LEFT  JOIN items_group ig ON ig.item_group_code = it.itms_grp_cod
    WHERE ip.doc_date >= DATE_TRUNC('month', CURRENT_DATE - ((p_meses - 1) * INTERVAL '1 month'))
    GROUP BY
        DATE_TRUNC('month', ip.doc_date),
        COALESCE(it.itms_grp_cod, 0),
        COALESCE(ig.item_group_name, 'Sin Grupo')
    ORDER BY anio, mes, group_name;
$$;


-- ══════════════════════════════════════════════════════════════
-- ANÁLISIS DE INVENTARIO  (movimientos_almacen)
-- ══════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────
-- 11. fn_dash_inv_kpi()
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_inv_kpi();
CREATE OR REPLACE FUNCTION fn_dash_inv_kpi()
RETURNS TABLE (
    cant_entradas_mes   NUMERIC,
    cant_salidas_mes    NUMERIC,
    valor_entradas_mes  NUMERIC,
    valor_salidas_mes   NUMERIC,
    items_activos       BIGINT,
    almacenes_activos   BIGINT,
    stock_valor_total   NUMERIC,
    movimientos_hoy     BIGINT
)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_ent_qty   NUMERIC := 0;
    v_sal_qty   NUMERIC := 0;
    v_ent_val   NUMERIC := 0;
    v_sal_val   NUMERIC := 0;
    v_items     BIGINT  := 0;
    v_almacenes BIGINT  := 0;
    v_stock_val NUMERIC := 0;
    v_hoy       BIGINT  := 0;
BEGIN
    SELECT
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'ENT'
                           AND DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                          THEN quantity    ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'SAL'
                           AND DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                          THEN ABS(quantity) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'ENT'
                           AND DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                          THEN ABS(subtotal) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'SAL'
                           AND DATE_TRUNC('month', doc_date) = DATE_TRUNC('month', CURRENT_DATE)
                          THEN ABS(subtotal) ELSE 0 END), 0),
        COUNT(DISTINCT CASE WHEN doc_date >= CURRENT_DATE - 30 THEN item_code END),
        COUNT(DISTINCT CASE WHEN doc_date >= CURRENT_DATE - 30 THEN TRIM(almacen) END),
        COUNT(DISTINCT CASE WHEN doc_date = CURRENT_DATE THEN id END)
    INTO v_ent_qty, v_sal_qty, v_ent_val, v_sal_val, v_items, v_almacenes, v_hoy
    FROM movimientos_almacen;

    SELECT COALESCE(SUM(quantity * avg_price), 0)
    INTO   v_stock_val
    FROM   movimientos_almacen;

    RETURN QUERY SELECT
        v_ent_qty, v_sal_qty, v_ent_val, v_sal_val,
        v_items, v_almacenes, v_stock_val, v_hoy;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 12b. fn_dash_inv_mensuales_grupos(p_meses INTEGER DEFAULT 24)
--      Salidas mensuales desglosadas por grupo de artículo
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_inv_mensuales_grupos(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_inv_mensuales_grupos(p_meses INTEGER DEFAULT 24)
RETURNS TABLE (
    anio         INTEGER,
    mes          INTEGER,
    mes_nombre   TEXT,
    group_code   INTEGER,
    group_name   TEXT,
    cant_salidas NUMERIC
)
LANGUAGE sql STABLE AS $$
    SELECT
        EXTRACT(YEAR  FROM DATE_TRUNC('month', m.doc_date))::INTEGER   AS anio,
        EXTRACT(MONTH FROM DATE_TRUNC('month', m.doc_date))::INTEGER   AS mes,
        TO_CHAR(DATE_TRUNC('month', m.doc_date), 'Mon YYYY')           AS mes_nombre,
        COALESCE(it.itms_grp_cod, 0)::INTEGER                         AS group_code,
        COALESCE(ig.item_group_name, 'Sin Grupo')::TEXT               AS group_name,
        COALESCE(SUM(ABS(m.quantity)), 0)::NUMERIC                    AS cant_salidas
    FROM  movimientos_almacen m
    LEFT  JOIN items       it ON it.item_code       = m.item_code
    LEFT  JOIN items_group ig ON ig.item_group_code = it.itms_grp_cod
    WHERE m.tipo_movimiento = 'SAL'
      AND m.doc_date >= DATE_TRUNC('month', CURRENT_DATE - ((p_meses - 1) * INTERVAL '1 month'))
    GROUP BY
        DATE_TRUNC('month', m.doc_date),
        COALESCE(it.itms_grp_cod, 0),
        COALESCE(ig.item_group_name, 'Sin Grupo')
    ORDER BY anio, mes, group_name;
$$;


-- ─────────────────────────────────────────────────────────────
-- 12. fn_dash_inv_mensuales(p_meses INTEGER DEFAULT 12)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_inv_mensuales(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_inv_mensuales(p_meses INTEGER DEFAULT 12)
RETURNS TABLE (
    anio           INTEGER,
    mes            INTEGER,
    mes_nombre     TEXT,
    cant_entradas  NUMERIC,
    cant_salidas   NUMERIC,
    valor_entradas NUMERIC,
    valor_salidas  NUMERIC
)
LANGUAGE sql STABLE AS $$
    SELECT
        EXTRACT(YEAR  FROM DATE_TRUNC('month', doc_date))::INTEGER  AS anio,
        EXTRACT(MONTH FROM DATE_TRUNC('month', doc_date))::INTEGER  AS mes,
        TO_CHAR(DATE_TRUNC('month', doc_date), 'Mon YYYY')          AS mes_nombre,
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'ENT'
                          THEN quantity    ELSE 0 END), 0)           AS cant_entradas,
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'SAL'
                          THEN ABS(quantity) ELSE 0 END), 0)         AS cant_salidas,
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'ENT'
                          THEN ABS(subtotal) ELSE 0 END), 0)         AS valor_entradas,
        COALESCE(SUM(CASE WHEN tipo_movimiento = 'SAL'
                          THEN ABS(subtotal) ELSE 0 END), 0)         AS valor_salidas
    FROM  movimientos_almacen
    WHERE doc_date >= DATE_TRUNC('month', CURRENT_DATE - ((p_meses - 1) * INTERVAL '1 month'))
    GROUP BY DATE_TRUNC('month', doc_date)
    ORDER BY anio, mes;
$$;


-- ─────────────────────────────────────────────────────────────
-- 13. fn_dash_inv_top_rotacion(p_limit INTEGER DEFAULT 10)
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_inv_top_rotacion(INTEGER);
CREATE OR REPLACE FUNCTION fn_dash_inv_top_rotacion(p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    item_code      TEXT,
    item_name      TEXT,
    group_name     TEXT,
    total_salidas  NUMERIC,
    total_entradas NUMERIC,
    stock_actual   NUMERIC,
    valor_stock    NUMERIC
)
LANGUAGE sql STABLE AS $$
    SELECT
        m.item_code::TEXT,
        COALESCE(it.item_name, m.item_code)::TEXT                   AS item_name,
        COALESCE(ig.item_group_name, 'Sin Grupo')::TEXT             AS group_name,
        COALESCE(SUM(CASE WHEN m.tipo_movimiento = 'SAL'
                          THEN ABS(m.quantity) ELSE 0 END), 0)      AS total_salidas,
        COALESCE(SUM(CASE WHEN m.tipo_movimiento = 'ENT'
                          THEN m.quantity       ELSE 0 END), 0)      AS total_entradas,
        COALESCE(SUM(m.quantity), 0)                                 AS stock_actual,
        COALESCE(SUM(m.quantity * m.avg_price), 0)                  AS valor_stock
    FROM  movimientos_almacen m
    LEFT  JOIN items       it ON it.item_code       = m.item_code
    LEFT  JOIN items_group ig ON ig.item_group_code = it.itms_grp_cod
    GROUP BY m.item_code, COALESCE(it.item_name, m.item_code),
             COALESCE(ig.item_group_name, 'Sin Grupo')
    HAVING SUM(CASE WHEN m.tipo_movimiento = 'SAL' THEN ABS(m.quantity) ELSE 0 END) > 0
    ORDER BY total_salidas DESC
    LIMIT p_limit;
$$;


-- ─────────────────────────────────────────────────────────────
-- 14. fn_dash_inv_stock_almacen()
-- ─────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS fn_dash_inv_stock_almacen();
CREATE OR REPLACE FUNCTION fn_dash_inv_stock_almacen()
RETURNS TABLE (
    almacen        TEXT,
    whs_name       TEXT,
    cant_items     BIGINT,
    stock_positivo BIGINT,
    stock_negativo BIGINT,
    valor_total    NUMERIC
)
LANGUAGE sql STABLE AS $$
    WITH stock_por_item AS (
        SELECT
            TRIM(almacen)                   AS almacen,
            item_code,
            SUM(quantity)                   AS stock,
            SUM(quantity * avg_price)       AS valor
        FROM  movimientos_almacen
        GROUP BY TRIM(almacen), item_code
    )
    SELECT
        s.almacen::TEXT,
        COALESCE(TRIM(w.whs_name), s.almacen)::TEXT   AS whs_name,
        COUNT(s.item_code)::BIGINT                     AS cant_items,
        COUNT(CASE WHEN s.stock >  0 THEN 1 END)::BIGINT AS stock_positivo,
        COUNT(CASE WHEN s.stock <= 0 THEN 1 END)::BIGINT AS stock_negativo,
        COALESCE(SUM(s.valor), 0)::NUMERIC             AS valor_total
    FROM  stock_por_item s
    LEFT  JOIN warehouses w ON TRIM(w.whs_code) = s.almacen
    GROUP BY s.almacen, COALESCE(TRIM(w.whs_name), s.almacen)
    ORDER BY valor_total DESC;
$$;
