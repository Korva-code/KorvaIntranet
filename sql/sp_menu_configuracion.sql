-- ═══════════════════════════════════════════════════════════════════
-- Agregar sección Configuración al catálogo de menú
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Sección padre ────────────────────────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (7, NULL, 'Configuración', NULL, 'bi-gear-fill', 70)
ON CONFLICT (id_menu) DO NOTHING;

-- ── 2. Ítems hoja ────────────────────────────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden) VALUES
(71, 7, 'Usuarios',       'main.usuarios',       'bi-person-gear',   1),
(72, 7, 'Accesos al Menú','main.config_accesos', 'bi-shield-check',  2),
(73, 7, 'Sistema',        'main.sistema',        'bi-sliders',       3)
ON CONFLICT (id_menu) DO NOTHING;

-- ── 3. Asignar Configuración completa al perfil administrador ────
-- Ajusta id_perfil = 1 si el admin tiene un id diferente en w_perfil.
-- Puedes verificarlo con: SELECT id_perfil, descripcion FROM w_perfil;

INSERT INTO perfil_menu (id_perfil, id_menu)
SELECT 1, id_menu
FROM   menu_items
WHERE  id_menu IN (71, 72, 73)
ON CONFLICT (id_perfil, id_menu) DO NOTHING;
