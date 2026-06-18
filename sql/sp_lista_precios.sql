-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Lista de Precios por Socio de Negocio
-- Columnas de business_partners_discount_item:
--   item_code, federal_tax_id, status, avg_price_d, priceaftervat_d
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Agregar entrada de menú bajo Ventas (id_parent = 2) ──────────
INSERT INTO menu_items (id_parent, label, endpoint, icon, orden)
VALUES (2, 'Lista de Precios', 'main.ventas_lista_precios', 'bi-tags', 4)
ON CONFLICT DO NOTHING;

-- Dar acceso al perfil 1 (administrador)
INSERT INTO perfil_menu (id_perfil, id_menu)
SELECT 1, id_menu FROM menu_items WHERE endpoint = 'main.ventas_lista_precios'
ON CONFLICT DO NOTHING;

-- ── 2. Función: socios con contador de ítems en lista ────────────────
CREATE OR REPLACE FUNCTION fn_lista_precios_socios()
RETURNS TABLE (
    card_code      TEXT,
    card_name      TEXT,
    federal_tax_id TEXT,
    card_type      TEXT,
    total_items    BIGINT
) LANGUAGE sql STABLE AS $$
    SELECT
        bp.card_code::TEXT,
        COALESCE(bp.card_name, bp.card_code)::TEXT,
        COALESCE(bp.federal_tax_id, '')::TEXT,
        COALESCE(bp.card_type, '')::TEXT,
        COUNT(d.item_code)
    FROM business_partners bp
    LEFT JOIN business_partners_discount_item d
           ON TRIM(d.federal_tax_id) = TRIM(bp.federal_tax_id)
    GROUP BY bp.card_code, bp.card_name, bp.federal_tax_id, bp.card_type
    ORDER BY bp.card_name;
$$;

-- ── 3. Función: ítems de la lista de precios de un socio ─────────────
CREATE OR REPLACE FUNCTION fn_lista_precios_items(p_federal_tax_id TEXT)
RETURNS TABLE (
    item_code       TEXT,
    item_name       TEXT,
    catalog_price   NUMERIC,
    avg_price_d     NUMERIC,
    priceaftervat_d NUMERIC,
    status          INTEGER
) LANGUAGE sql STABLE AS $$
    SELECT
        d.item_code::TEXT,
        COALESCE(i.item_name, d.item_code)::TEXT,
        COALESCE(i."PriceAfterVAT", 0)::NUMERIC          AS catalog_price,
        COALESCE(d.avg_price_d, 0)::NUMERIC               AS avg_price_d,
        COALESCE(d.priceaftervat_d, 0)::NUMERIC           AS priceaftervat_d,
        COALESCE(d.status, 1)::INTEGER
    FROM business_partners_discount_item d
    LEFT JOIN items i ON i.item_code = d.item_code
    WHERE TRIM(d.federal_tax_id) = TRIM(p_federal_tax_id)
    ORDER BY i.item_name, d.item_code;
$$;
