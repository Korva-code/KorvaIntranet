-- ═══════════════════════════════════════════════════════════════
-- CRUD: Tipos de Cambio (USD/SOL – fuente SUNAT)
-- ═══════════════════════════════════════════════════════════════

-- ── Tabla ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tipos_cambio (
    id_tipo_cambio  SERIAL        PRIMARY KEY,
    anio            INTEGER       NOT NULL,
    mes             INTEGER       NOT NULL,
    dia             INTEGER       NOT NULL,
    tc_compra       NUMERIC(10,4),
    tc_venta        NUMERIC(10,4),
    UNIQUE (anio, mes, dia)
);

-- ── Listar por año y mes ─────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_tipos_cambio_listar(p_anio INTEGER, p_mes INTEGER)
RETURNS TABLE (
    id_tipo_cambio  INTEGER,
    anio            INTEGER,
    mes             INTEGER,
    dia             INTEGER,
    tc_compra       NUMERIC,
    tc_venta        NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT id_tipo_cambio, anio, mes, dia, tc_compra, tc_venta
    FROM   tipos_cambio
    WHERE  anio = p_anio AND mes = p_mes
    ORDER  BY dia;
$$;

-- ── Ítem de menú (sub de Maestras id_parent=1) ──────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (16, 1, 'Tipo Cambio', 'main.maestras_tipos_cambio', 'bi-currency-exchange', 6)
ON CONFLICT (id_menu) DO NOTHING;
