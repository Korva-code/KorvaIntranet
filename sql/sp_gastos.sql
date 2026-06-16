-- ═══════════════════════════════════════════════════════════════
--  Módulo: Finanzas > Gastos
--  Ejecutar una sola vez.
-- ═══════════════════════════════════════════════════════════════

-- ── Menú: asignar a la sección Finanzas (actualiza si ya existe como placeholder) ──
UPDATE menu_items
   SET endpoint = 'main.finanzas_gastos'
 WHERE endpoint = 'main.gastos';

INSERT INTO menu_items (id_parent, label, endpoint, icon, orden)
SELECT id_menu, 'Gastos', 'main.finanzas_gastos', 'bi-receipt', 10
FROM   menu_items
WHERE  label = 'Finanzas' AND id_parent IS NULL
ON CONFLICT DO NOTHING;

-- ── Tabla: categorías de gasto ──────────────────────────────────
CREATE TABLE IF NOT EXISTS tipos_gasto (
    id_tipo_gasto  SERIAL  PRIMARY KEY,
    nombre         TEXT    NOT NULL UNIQUE,
    id_estado      INTEGER DEFAULT 1
);

INSERT INTO tipos_gasto (nombre) VALUES
    ('Servicios'),
    ('Alquiler'),
    ('Sueldos y Salarios'),
    ('Materiales de Oficina'),
    ('Transporte'),
    ('Mantenimiento'),
    ('Publicidad'),
    ('Otros')
ON CONFLICT DO NOTHING;

-- ── Tabla principal: gastos ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS gastos (
    gasto_id        SERIAL        PRIMARY KEY,
    id_tipo_gasto   INTEGER       REFERENCES tipos_gasto(id_tipo_gasto),
    card_code       TEXT,
    nro_documento   TEXT,
    doc_date        DATE,
    doc_due_date    DATE,
    doc_currency    TEXT          DEFAULT 'SOL',
    tipo_cambio     NUMERIC(12,6) DEFAULT 1,
    monto           NUMERIC(18,4) DEFAULT 0,
    id_banco        INTEGER       REFERENCES bancos(id_banco),
    referencia      TEXT,
    concepto        TEXT,
    journal_memo    TEXT,
    user_code       TEXT,
    id_estado       INTEGER       DEFAULT 1,
    fecha_registro  TIMESTAMP     DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
--  sp_gastos_listar(p_gasto_id)   0 = todos, >0 = uno específico
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_gastos_listar(p_gasto_id INTEGER)
RETURNS TABLE (
    gasto_id        INTEGER,
    id_tipo_gasto   INTEGER,
    tipo_nombre     TEXT,
    card_code       TEXT,
    bp_name         TEXT,
    nro_documento   TEXT,
    doc_date        DATE,
    doc_due_date    DATE,
    doc_currency    TEXT,
    tipo_cambio     NUMERIC,
    monto           NUMERIC,
    id_banco        INTEGER,
    banco_nombre    TEXT,
    referencia      TEXT,
    concepto        TEXT,
    journal_memo    TEXT,
    user_code       TEXT,
    id_estado       INTEGER,
    fecha_registro  TIMESTAMP
) LANGUAGE sql STABLE AS $$
    SELECT
        g.gasto_id,
        g.id_tipo_gasto,
        tg.nombre                                          AS tipo_nombre,
        g.card_code,
        COALESCE(bp.card_name, g.card_code, '')           AS bp_name,
        g.nro_documento,
        g.doc_date,
        g.doc_due_date,
        g.doc_currency,
        g.tipo_cambio,
        g.monto,
        g.id_banco,
        COALESCE(b.nombre, '')                            AS banco_nombre,
        g.referencia,
        g.concepto,
        g.journal_memo,
        g.user_code,
        g.id_estado,
        g.fecha_registro
    FROM  gastos g
    LEFT  JOIN tipos_gasto       tg ON tg.id_tipo_gasto = g.id_tipo_gasto
    LEFT  JOIN business_partners bp ON bp.card_code     = g.card_code
    LEFT  JOIN bancos             b  ON b.id_banco       = g.id_banco
    WHERE g.id_estado = 1
      AND (p_gasto_id = 0 OR g.gasto_id = p_gasto_id)
    ORDER BY g.gasto_id DESC;
$$;

-- ═══════════════════════════════════════════════════════════════
--  sp_gastos_guardar(...)  — INSERT si p_gasto_id=0, UPDATE si >0
--  Retorna el gasto_id resultante.
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_gastos_guardar(
    p_gasto_id      INTEGER,
    p_id_tipo_gasto INTEGER,
    p_card_code     TEXT,
    p_nro_documento TEXT,
    p_doc_date      DATE,
    p_doc_due_date  DATE,
    p_doc_currency  TEXT,
    p_tipo_cambio   NUMERIC,
    p_monto         NUMERIC,
    p_id_banco      INTEGER,
    p_referencia    TEXT,
    p_concepto      TEXT,
    p_journal_memo  TEXT,
    p_user_code     TEXT
)
RETURNS INTEGER LANGUAGE plpgsql AS $$
DECLARE
    v_id INTEGER;
BEGIN
    IF p_gasto_id = 0 THEN
        INSERT INTO gastos (
            id_tipo_gasto, card_code, nro_documento,
            doc_date, doc_due_date, doc_currency, tipo_cambio, monto,
            id_banco, referencia, concepto, journal_memo, user_code
        ) VALUES (
            NULLIF(p_id_tipo_gasto, 0),
            NULLIF(TRIM(p_card_code), ''),
            NULLIF(TRIM(p_nro_documento), ''),
            p_doc_date,
            p_doc_due_date,
            p_doc_currency,
            p_tipo_cambio,
            p_monto,
            NULLIF(p_id_banco, 0),
            NULLIF(TRIM(p_referencia), ''),
            NULLIF(TRIM(p_concepto), ''),
            NULLIF(TRIM(p_journal_memo), ''),
            p_user_code
        )
        RETURNING gasto_id INTO v_id;
    ELSE
        UPDATE gastos SET
            id_tipo_gasto  = NULLIF(p_id_tipo_gasto, 0),
            card_code      = NULLIF(TRIM(p_card_code), ''),
            nro_documento  = NULLIF(TRIM(p_nro_documento), ''),
            doc_date       = p_doc_date,
            doc_due_date   = p_doc_due_date,
            doc_currency   = p_doc_currency,
            tipo_cambio    = p_tipo_cambio,
            monto          = p_monto,
            id_banco       = NULLIF(p_id_banco, 0),
            referencia     = NULLIF(TRIM(p_referencia), ''),
            concepto       = NULLIF(TRIM(p_concepto), ''),
            journal_memo   = NULLIF(TRIM(p_journal_memo), ''),
            user_code      = p_user_code
        WHERE gasto_id = p_gasto_id
        RETURNING gasto_id INTO v_id;
    END IF;
    RETURN v_id;
END;
$$;

-- ── Columna id_gasto en bancos_estado_cuenta para trazabilidad ──
ALTER TABLE bancos_estado_cuenta
    ADD COLUMN IF NOT EXISTS id_gasto INTEGER;

CREATE INDEX IF NOT EXISTS idx_bec_gasto ON bancos_estado_cuenta (id_gasto);

-- ═══════════════════════════════════════════════════════════════
--  sp_tipos_gasto_listar()
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_tipos_gasto_listar()
RETURNS TABLE (id_tipo_gasto INTEGER, nombre TEXT)
LANGUAGE sql STABLE AS $$
    SELECT id_tipo_gasto, nombre
    FROM   tipos_gasto
    WHERE  id_estado = 1
    ORDER  BY nombre;
$$;
