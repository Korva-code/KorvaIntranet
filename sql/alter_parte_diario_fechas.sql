-- ══════════════════════════════════════════════════════════════
-- Corrección fechas en parte_diario
-- Problemas: hora en UTC en vez de Lima + microsegundos
-- ══════════════════════════════════════════════════════════════

-- 1. Cambiar columnas a TIMESTAMP(0) — elimina microsegundos
ALTER TABLE parte_diario
    ALTER COLUMN fecha_apertura  TYPE TIMESTAMP(0) USING fecha_apertura::TIMESTAMP(0),
    ALTER COLUMN fecha_cierre    TYPE TIMESTAMP(0) USING fecha_cierre::TIMESTAMP(0),
    ALTER COLUMN fecha_registro  TYPE TIMESTAMP(0) USING fecha_registro::TIMESTAMP(0);

-- DEFAULT de fecha_registro: hora Lima sin microsegundos (aplica a inserts directos)
ALTER TABLE parte_diario
    ALTER COLUMN fecha_registro SET DEFAULT date_trunc('second', NOW() AT TIME ZONE 'America/Lima');

-- 2. Corregir registros existentes con hora UTC incorrecta
UPDATE parte_diario
   SET fecha_cierre = date_trunc('second',
           fecha_cierre AT TIME ZONE 'UTC' AT TIME ZONE 'America/Lima')
 WHERE fecha_cierre IS NOT NULL;

UPDATE parte_diario
   SET fecha_apertura = date_trunc('second',
           fecha_apertura AT TIME ZONE 'UTC' AT TIME ZONE 'America/Lima')
 WHERE fecha_apertura IS NOT NULL;

UPDATE parte_diario
   SET fecha_registro = date_trunc('second',
           fecha_registro AT TIME ZONE 'UTC' AT TIME ZONE 'America/Lima')
 WHERE fecha_registro IS NOT NULL;

-- 3. fn_parte_diario_cerrar — usa hora Lima sin microsegundos
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
           fecha_cierre       = date_trunc('second', NOW() AT TIME ZONE 'America/Lima'),
           monto_final        = p_monto_final,
           observacion_cierre = NULLIF(TRIM(p_observacion), '')
     WHERE id_parte = p_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario cerrado correctamente.'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 4. fn_parte_diario_aperturar — fecha_registro también con hora Lima
CREATE OR REPLACE FUNCTION fn_parte_diario_aperturar(
    p_user_code      TEXT,
    p_id_punto_venta INTEGER,
    p_monto_inicial  NUMERIC   DEFAULT 0,
    p_observacion    TEXT      DEFAULT '',
    p_fecha_apertura TIMESTAMP DEFAULT NULL
) RETURNS TABLE(success BOOLEAN, message TEXT, id_parte INTEGER) AS $$
DECLARE
    v_id_parte   INTEGER;
    v_ya_abierto INTEGER;
    v_fecha      TIMESTAMP(0);
BEGIN
    SELECT COUNT(*) INTO v_ya_abierto
    FROM   parte_diario
    WHERE  user_code      = p_user_code
      AND  id_punto_venta = p_id_punto_venta
      AND  id_estado      = 1;

    IF v_ya_abierto > 0 THEN
        RETURN QUERY SELECT FALSE::BOOLEAN,
            'Ya existe un parte abierto para este usuario en este punto de venta.'::TEXT, 0;
        RETURN;
    END IF;

    v_fecha := COALESCE(
        date_trunc('second', p_fecha_apertura),
        date_trunc('second', NOW() AT TIME ZONE 'America/Lima')
    );

    INSERT INTO parte_diario (
        id_punto_venta, user_code, monto_inicial,
        observacion_apertura, id_estado, fecha_apertura, fecha_registro
    ) VALUES (
        p_id_punto_venta, p_user_code, p_monto_inicial,
        NULLIF(TRIM(p_observacion), ''), 1,
        v_fecha,
        date_trunc('second', NOW() AT TIME ZONE 'America/Lima')
    ) RETURNING parte_diario.id_parte INTO v_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario aperturado correctamente.'::TEXT, v_id_parte;
END;
$$ LANGUAGE plpgsql;

-- 5. fn_parte_diario_actualizar — sin cambio en fechas pero por completitud
CREATE OR REPLACE FUNCTION fn_parte_diario_actualizar(
    p_id_parte       INTEGER,
    p_id_punto_venta INTEGER,
    p_fecha_apertura TIMESTAMP,
    p_monto_inicial  NUMERIC,
    p_observacion    TEXT DEFAULT ''
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
        RETURN QUERY SELECT FALSE::BOOLEAN, 'Solo se puede modificar un parte abierto.'::TEXT;
        RETURN;
    END IF;

    UPDATE parte_diario
       SET id_punto_venta       = p_id_punto_venta,
           fecha_apertura       = date_trunc('second', p_fecha_apertura),
           monto_inicial        = p_monto_inicial,
           observacion_apertura = NULLIF(TRIM(p_observacion), '')
     WHERE id_parte = p_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario actualizado correctamente.'::TEXT;
END;
$$ LANGUAGE plpgsql;
