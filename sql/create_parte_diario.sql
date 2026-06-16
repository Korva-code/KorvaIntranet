-- ══════════════════════════════════════════════════════════════
-- PARTE DIARIO — Tablas, funciones y menú
-- ══════════════════════════════════════════════════════════════

-- 1. Tabla punto de venta
CREATE TABLE IF NOT EXISTS punto_venta (
    id_punto_venta SERIAL PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    descripcion    TEXT,
    id_estado      SMALLINT DEFAULT 1,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- Datos iniciales de ejemplo
INSERT INTO punto_venta (nombre, descripcion) VALUES
    ('Caja 1', 'Punto de venta principal'),
    ('Caja 2', 'Punto de venta secundario')
ON CONFLICT DO NOTHING;

-- 2. Tabla parte diario
CREATE TABLE IF NOT EXISTS parte_diario (
    id_parte             SERIAL PRIMARY KEY,
    id_punto_venta       INTEGER REFERENCES punto_venta(id_punto_venta),
    user_code            VARCHAR(50),
    fecha_apertura       TIMESTAMP DEFAULT NOW(),
    fecha_cierre         TIMESTAMP,
    monto_inicial        NUMERIC(14,2) DEFAULT 0,
    monto_final          NUMERIC(14,2),
    observacion_apertura TEXT,
    observacion_cierre   TEXT,
    id_estado            SMALLINT DEFAULT 1,   -- 1=Abierto  2=Cerrado
    fecha_registro       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parte_estado       ON parte_diario (id_estado);
CREATE INDEX IF NOT EXISTS idx_parte_user         ON parte_diario (user_code);
CREATE INDEX IF NOT EXISTS idx_parte_apertura     ON parte_diario (fecha_apertura);
CREATE INDEX IF NOT EXISTS idx_parte_punto_venta  ON parte_diario (id_punto_venta);

-- 3. sp_parte_diario_listar
CREATE OR REPLACE FUNCTION sp_parte_diario_listar(p_dias INTEGER DEFAULT 30)
RETURNS TABLE(
    id_parte             INTEGER,
    id_punto_venta       INTEGER,
    punto_venta_nombre   TEXT,
    user_code            TEXT,
    user_nombre          TEXT,
    fecha_apertura       TIMESTAMP,
    fecha_cierre         TIMESTAMP,
    monto_inicial        NUMERIC,
    monto_final          NUMERIC,
    observacion_apertura TEXT,
    observacion_cierre   TEXT,
    id_estado            SMALLINT,
    fecha_registro       TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pd.id_parte,
        pd.id_punto_venta,
        COALESCE(pv.nombre,    '')::TEXT           AS punto_venta_nombre,
        COALESCE(pd.user_code, '')::TEXT           AS user_code,
        COALESCE(u.nombres, pd.user_code, '')::TEXT AS user_nombre,
        pd.fecha_apertura,
        pd.fecha_cierre,
        COALESCE(pd.monto_inicial, 0)::NUMERIC     AS monto_inicial,
        pd.monto_final,
        COALESCE(pd.observacion_apertura, '')::TEXT AS observacion_apertura,
        COALESCE(pd.observacion_cierre,   '')::TEXT AS observacion_cierre,
        pd.id_estado,
        pd.fecha_registro
    FROM  parte_diario pd
    LEFT  JOIN punto_venta pv ON pv.id_punto_venta = pd.id_punto_venta
    LEFT  JOIN w_usuarios  u  ON u.id_usuario::TEXT = pd.user_code
    WHERE pd.fecha_apertura >= (CURRENT_DATE - p_dias)
    ORDER BY pd.id_parte DESC;
END;
$$ LANGUAGE plpgsql;

-- 4. fn_parte_diario_aperturar
CREATE OR REPLACE FUNCTION fn_parte_diario_aperturar(
    p_user_code      TEXT,
    p_id_punto_venta INTEGER,
    p_monto_inicial  NUMERIC DEFAULT 0,
    p_observacion    TEXT    DEFAULT ''
) RETURNS TABLE(success BOOLEAN, message TEXT, id_parte INTEGER) AS $$
DECLARE
    v_id_parte   INTEGER;
    v_ya_abierto INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_ya_abierto
    FROM   parte_diario
    WHERE  user_code       = p_user_code
      AND  id_punto_venta  = p_id_punto_venta
      AND  id_estado       = 1;

    IF v_ya_abierto > 0 THEN
        RETURN QUERY SELECT FALSE::BOOLEAN,
            'Ya existe un parte abierto para este usuario en este punto de venta.'::TEXT, 0;
        RETURN;
    END IF;

    INSERT INTO parte_diario (
        id_punto_venta, user_code, monto_inicial,
        observacion_apertura, id_estado, fecha_apertura, fecha_registro
    ) VALUES (
        p_id_punto_venta, p_user_code, p_monto_inicial,
        NULLIF(TRIM(p_observacion), ''), 1, NOW(), NOW()
    ) RETURNING parte_diario.id_parte INTO v_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario aperturado correctamente.'::TEXT, v_id_parte;
END;
$$ LANGUAGE plpgsql;

-- 5. fn_parte_diario_cerrar
CREATE OR REPLACE FUNCTION fn_parte_diario_cerrar(
    p_id_parte    INTEGER,
    p_monto_final NUMERIC DEFAULT 0,
    p_observacion TEXT    DEFAULT ''
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_estado SMALLINT;
BEGIN
    SELECT id_estado INTO v_estado FROM parte_diario WHERE id_parte = p_id_parte;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'Parte diario no encontrado.'::TEXT;
        RETURN;
    END IF;
    IF v_estado != 1 THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'El parte diario ya fue cerrado.'::TEXT;
        RETURN;
    END IF;

    UPDATE parte_diario
       SET id_estado          = 2,
           fecha_cierre       = NOW(),
           monto_final        = p_monto_final,
           observacion_cierre = NULLIF(TRIM(p_observacion), '')
     WHERE id_parte = p_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario cerrado correctamente.'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 6. sp_punto_venta_listar
CREATE OR REPLACE FUNCTION sp_punto_venta_listar()
RETURNS TABLE(id_punto_venta INTEGER, nombre TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT pv.id_punto_venta, pv.nombre::TEXT
    FROM   punto_venta pv
    WHERE  pv.id_estado = 1
    ORDER  BY pv.nombre;
END;
$$ LANGUAGE plpgsql;

-- 7. Insertar ítem en menú Ventas (id_parent=2, orden=4)
INSERT INTO menu_items (id_parent, label, endpoint, icon, orden, id_estado)
VALUES (2, 'Parte Diario', 'main.ventas_parte_diario', 'bi-clock-history', 4, 1)
ON CONFLICT DO NOTHING;
