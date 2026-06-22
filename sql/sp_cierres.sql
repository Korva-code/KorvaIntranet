-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Cierres por Proceso
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. TABLA ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cierres (
    id_cierre            SERIAL  PRIMARY KEY,
    tipo_proceso         TEXT    NOT NULL DEFAULT 'VENTAS',
    tipo_periodo         TEXT    NOT NULL DEFAULT 'DIA',   -- DIA | MES | ANIO
    periodo_anio         INTEGER NOT NULL,
    periodo_mes          INTEGER,                          -- NULL cuando tipo_periodo = ANIO
    periodo_dia          INTEGER,                          -- NULL cuando tipo_periodo != DIA
    total_documentos     INTEGER DEFAULT 0,
    total_importe        NUMERIC(18,2) DEFAULT 0,
    total_aplicados      INTEGER DEFAULT 0,
    total_sunat_aceptado INTEGER DEFAULT 0,
    total_pendientes     INTEGER DEFAULT 0,
    observaciones        TEXT,
    user_code            TEXT,
    fecha_registro       TIMESTAMP DEFAULT NOW(),
    id_estado            INTEGER DEFAULT 1
);

-- ── 1b. COLUMNAS ADICIONALES (ejecutar si la tabla ya existe) ────
ALTER TABLE cierres ADD COLUMN IF NOT EXISTS total_anulados        INTEGER       DEFAULT 0;
ALTER TABLE cierres ADD COLUMN IF NOT EXISTS total_margen          NUMERIC(18,2) DEFAULT 0;
ALTER TABLE cierres ADD COLUMN IF NOT EXISTS total_margen_bienes   NUMERIC(18,2) DEFAULT 0;
ALTER TABLE cierres ADD COLUMN IF NOT EXISTS total_margen_servicios NUMERIC(18,2) DEFAULT 0;

-- ── 2. MENÚ ──────────────────────────────────────────────────────

INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (15, 1, 'Cierres', 'main.cierres', 'bi-calendar-check-fill', 5)
ON CONFLICT (id_menu) DO NOTHING;

-- Asignar al perfil 1 (administrador)
INSERT INTO perfil_menu (id_perfil, id_menu)
SELECT 1, id_menu FROM menu_items WHERE endpoint = 'main.cierres'
ON CONFLICT DO NOTHING;
