-- ═══════════════════════════════════════════════════════════════════
-- MÓDULO: Pagos / Suscripciones
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Catálogo de servicios disponibles ─────────────────────────
CREATE TABLE IF NOT EXISTS suscripcion_servicios (
    id_servicio   SERIAL PRIMARY KEY,
    nombre        TEXT          NOT NULL,
    descripcion   TEXT,
    precio        NUMERIC(10,2) NOT NULL,
    incluye_igv   BOOLEAN       DEFAULT FALSE,
    periodicidad  TEXT          DEFAULT 'MENSUAL',  -- MENSUAL | ANUAL
    id_estado     INTEGER       DEFAULT 1
);

-- ── 2. Suscripciones adquiridas por empresa ───────────────────────
CREATE TABLE IF NOT EXISTS suscripciones (
    id_suscripcion    SERIAL PRIMARY KEY,
    id_empresa        INTEGER,
    id_servicio       INTEGER REFERENCES suscripcion_servicios(id_servicio),
    fecha_inicio      DATE          NOT NULL DEFAULT CURRENT_DATE,
    fecha_vencimiento DATE,
    precio_acordado   NUMERIC(10,2),
    id_estado_pago    INTEGER       DEFAULT 0,  -- 0=Pendiente, 1=Pagado, 2=Vencido
    observaciones     TEXT,
    user_code         TEXT,
    fecha_registro    TIMESTAMP     DEFAULT NOW()
);

-- ── 3. Métodos de pago registrados ───────────────────────────────
CREATE TABLE IF NOT EXISTS medios_pago (
    id_medio       SERIAL PRIMARY KEY,
    id_empresa     INTEGER,
    tipo           TEXT      NOT NULL,   -- TARJETA | YAPE
    titular        TEXT,
    numero_masked  TEXT,                 -- Solo últimos 4 dígitos
    marca          TEXT,                 -- VISA | MASTERCARD | AMEX | DINERS
    vencimiento    TEXT,                 -- MM/AA
    telefono_yape  TEXT,
    id_estado      INTEGER   DEFAULT 1,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- ── 4. Pagos mensuales consolidados (1 registro por mes/año) ─────
CREATE TABLE IF NOT EXISTS pagos_mensuales (
    id_pago         SERIAL PRIMARY KEY,
    id_empresa      INTEGER       NOT NULL,
    anio            INTEGER       NOT NULL,
    mes             INTEGER       NOT NULL,  -- 1-12
    total_servicios NUMERIC(10,2) DEFAULT 0, -- subtotal sin IGV
    total_igv       NUMERIC(10,2) DEFAULT 0,
    total_pago      NUMERIC(10,2) DEFAULT 0, -- total final
    id_estado_pago  INTEGER       DEFAULT 0, -- 0=Pendiente, 1=Pagado
    fecha_pago      DATE,
    detalle_json    JSONB,                   -- snapshot de servicios del mes
    user_code       TEXT,
    fecha_registro  TIMESTAMP     DEFAULT NOW(),
    UNIQUE (id_empresa, anio, mes)
);

-- ── 5. Catálogo inicial de servicios ─────────────────────────────
INSERT INTO suscripcion_servicios (id_servicio, nombre, descripcion, precio, incluye_igv, periodicidad)
VALUES
  (1, 'Base de Datos 5MB',        'Almacenamiento en base de datos PostgreSQL hasta 5MB', 35.00, FALSE, 'MENSUAL'),
  (2, 'Alojamiento de Intranet',  'Hosting del servidor web para la intranet',            35.00, FALSE, 'MENSUAL'),
  (3, 'Alquiler de la Intranet',  'Licencia mensual de uso de la plataforma Intranet',   100.00, TRUE,  'MENSUAL')
ON CONFLICT (id_servicio) DO NOTHING;

-- Reiniciar secuencia si se insertaron con IDs fijos
SELECT setval('suscripcion_servicios_id_servicio_seq', (SELECT MAX(id_servicio) FROM suscripcion_servicios));
