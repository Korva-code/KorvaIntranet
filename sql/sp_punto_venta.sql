-- ═══════════════════════════════════════════════════════════════════
-- Módulo: Punto de Ventas
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Sección padre ────────────────────────────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (200, NULL, 'Punto de Ventas', NULL, 'bi-shop-window', 200)
ON CONFLICT (id_menu) DO NOTHING;

-- ── 2. Ítems hoja ───────────────────────────────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (201, 200, 'Punto de Caja', 'main.punto_venta', 'bi-cash-register', 1)
ON CONFLICT (id_menu) DO NOTHING;

-- ── 3. Asignar al perfil administrador (id_perfil = 1) ──────────────
INSERT INTO perfil_menu (id_perfil, id_menu)
SELECT 1, id_menu
FROM   menu_items
WHERE  id_menu IN (200, 201)
ON CONFLICT (id_perfil, id_menu) DO NOTHING;
