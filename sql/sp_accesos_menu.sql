-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Accesos de Menú por Perfil
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. TABLAS ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS menu_items (
    id_menu    SERIAL  PRIMARY KEY,
    id_parent  INTEGER REFERENCES menu_items(id_menu) ON DELETE CASCADE,
    label      TEXT    NOT NULL,
    endpoint   TEXT,                        -- Flask endpoint, NULL en secciones
    icon       TEXT    DEFAULT 'bi-circle',
    orden      INTEGER DEFAULT 0,
    id_estado  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS perfil_menu (
    id        SERIAL  PRIMARY KEY,
    id_perfil INTEGER NOT NULL,
    id_menu   INTEGER NOT NULL REFERENCES menu_items(id_menu) ON DELETE CASCADE,
    UNIQUE (id_perfil, id_menu)
);

-- ── 2. SEED: catálogo completo del menú actual ───────────────────
-- Secciones (id_parent NULL) + ítems hoja

INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden) VALUES
-- Secciones principales
(1,  NULL, 'Maestras',  NULL, 'bi-box-seam-fill', 10),
(2,  NULL, 'Ventas',    NULL, 'bi-bag-check',      20),
(3,  NULL, 'Compras',   NULL, 'bi-cart',           30),
(4,  NULL, 'Almacén',   NULL, 'bi-boxes',          40),
(5,  NULL, 'Bancos',    NULL, 'bi-bank',           50),
(6,  NULL, 'Finanzas',  NULL, 'bi-cash-coin',      60),

-- Maestras
(11, 1, 'Artículos',           'main.articulos',            'bi-tags',              1),
(12, 1, 'Grupos de Artículos', 'main.grupos_articulos',     'bi-collection',        2),
(13, 1, 'Socios de Negocio',   'main.socios_negocio',       'bi-people',            3),
(14, 1, 'Bancos',              'main.bancos',               'bi-bank',              4),

-- Ventas
(21, 2, 'Facturas',            'main.ventas_facturas',      'bi-receipt',           1),
(22, 2, 'Boletas',             'main.ventas_boletas',       'bi-file-earmark-text', 2),
(23, 2, 'Cancelaciones',       'main.ventas_cancelaciones', 'bi-check2-circle',     3),

-- Compras
(31, 3, 'Facturas',            'main.compras_facturas',     'bi-receipt',           1),
(32, 3, 'Pago a Proveedores',  'main.compras_cancelaciones','bi-cash-coin',          2),

-- Almacén
(41, 4, 'Kardex Valorizado',   'main.almacen_kardex',       'bi-clipboard2-data',   1),

-- Bancos
(51, 5, 'Estado de Cuenta',    'main.bancos_estado_cuenta', 'bi-journal-text',      1),

-- Finanzas
(61, 6, 'Abonos',              'main.abonos',               'bi-cash-coin',         1),
(62, 6, 'Presupuesto',         'main.presupuesto',          'bi-cash-stack',        2),
(63, 6, 'Gastos',              'main.gastos',               'bi-receipt',           3),
(64, 6, 'Reportes',            'main.reportes_finanzas',    'bi-bar-chart-line',    4)

ON CONFLICT (id_menu) DO NOTHING;

SELECT setval('menu_items_id_menu_seq', 100, true);

-- ── 3. FUNCIÓN: menú visible para un perfil ──────────────────────
-- Devuelve ítems hoja permitidos + secciones padre automáticamente.
-- Solo se guardan ítems hoja en perfil_menu.

CREATE OR REPLACE FUNCTION sp_menu_perfil(p_id_perfil INTEGER)
RETURNS TABLE (
    id_menu   INTEGER,
    id_parent INTEGER,
    label     TEXT,
    endpoint  TEXT,
    icon      TEXT,
    orden     INTEGER
) LANGUAGE sql STABLE AS $$
    SELECT m.id_menu, m.id_parent, m.label, m.endpoint, m.icon, m.orden
    FROM   menu_items m
    WHERE  m.id_estado = 1
      AND (
            -- ítem hoja con permiso
            (m.id_parent IS NOT NULL AND EXISTS (
                SELECT 1 FROM perfil_menu pm
                WHERE pm.id_perfil = p_id_perfil AND pm.id_menu = m.id_menu
            ))
            OR
            -- sección padre con al menos un hijo permitido
            (m.id_parent IS NULL AND EXISTS (
                SELECT 1 FROM menu_items child
                JOIN   perfil_menu pm ON pm.id_menu = child.id_menu
                WHERE  child.id_parent = m.id_menu
                  AND  pm.id_perfil   = p_id_perfil
            ))
          )
    ORDER BY m.orden, m.id_menu;
$$;

-- ── 4. FUNCIÓN: todos los ítems (para el formulario de config) ───

CREATE OR REPLACE FUNCTION sp_menu_items_listar()
RETURNS TABLE (
    id_menu   INTEGER,
    id_parent INTEGER,
    label     TEXT,
    endpoint  TEXT,
    icon      TEXT,
    orden     INTEGER,
    id_estado INTEGER
) LANGUAGE sql STABLE AS $$
    SELECT id_menu, id_parent, label, endpoint, icon, orden, id_estado
    FROM   menu_items
    ORDER  BY orden, id_menu;
$$;

-- ── 5. FUNCIÓN: IDs de ítems hoja del perfil (para checkboxes) ───

CREATE OR REPLACE FUNCTION sp_perfil_menu_ids(p_id_perfil INTEGER)
RETURNS TABLE (id_menu INTEGER) LANGUAGE sql STABLE AS $$
    SELECT id_menu FROM perfil_menu WHERE id_perfil = p_id_perfil;
$$;

-- ── 6. FUNCIÓN: guardar permisos de un perfil (replace) ──────────

CREATE OR REPLACE FUNCTION sp_perfil_menu_guardar(
    p_id_perfil INTEGER,
    p_menu_ids  JSONB        -- array de id_menu hoja: [11, 21, 22, ...]
) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM perfil_menu WHERE id_perfil = p_id_perfil;
    INSERT INTO perfil_menu (id_perfil, id_menu)
    SELECT p_id_perfil, (val::TEXT)::INTEGER
    FROM   jsonb_array_elements(p_menu_ids) AS t(val)
    ON CONFLICT DO NOTHING;
END;
$$;

-- ── 7. FUNCIÓN: asignar perfil a usuario + guardar permisos ──────

CREATE OR REPLACE FUNCTION sp_usuario_acceso_guardar(
    p_id_usuario TEXT,
    p_id_perfil  INTEGER,
    p_menu_ids   JSONB
) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE w_usuarios
       SET id_perfil = p_id_perfil
     WHERE id_usuario = p_id_usuario;

    PERFORM sp_perfil_menu_guardar(p_id_perfil, p_menu_ids);
END;
$$;

-- ── 8. FUNCIÓN: listar usuarios con su perfil ────────────────────

CREATE OR REPLACE FUNCTION sp_usuarios_con_perfil()
RETURNS TABLE (
    id_usuario    TEXT,
    nombres       TEXT,
    id_perfil     INTEGER,
    perfil_nombre TEXT,
    id_estado     INTEGER
) LANGUAGE sql STABLE AS $$
    SELECT u.id_usuario::TEXT,
           u.nombres::TEXT,
           u.id_perfil,
           COALESCE(p.descripcion, '—')::TEXT,
           u.id_estado
    FROM   w_usuarios u
    LEFT JOIN w_perfil p ON p.id_perfil = u.id_perfil
    ORDER  BY u.nombres;
$$;

-- ── 9. FUNCIÓN: listar perfiles activos ──────────────────────────

CREATE OR REPLACE FUNCTION sp_perfiles_listar()
RETURNS TABLE (
    id_perfil INTEGER,
    nombre    TEXT
) LANGUAGE sql STABLE AS $$
    SELECT id_perfil, COALESCE(descripcion, '')::TEXT
    FROM   w_perfil
    WHERE  COALESCE(id_estado, 1) = 1
    ORDER  BY descripcion;
$$;
