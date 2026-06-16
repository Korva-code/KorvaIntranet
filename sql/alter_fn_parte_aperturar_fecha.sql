-- Agrega parámetro p_fecha_apertura a fn_parte_diario_aperturar
-- Permite que el cajero elija fecha/hora de apertura en lugar de forzar NOW()

CREATE OR REPLACE FUNCTION fn_parte_diario_aperturar(
    p_user_code      TEXT,
    p_id_punto_venta INTEGER,
    p_monto_inicial  NUMERIC   DEFAULT 0,
    p_observacion    TEXT      DEFAULT '',
    p_fecha_apertura TIMESTAMP DEFAULT NOW()
) RETURNS TABLE(success BOOLEAN, message TEXT, id_parte INTEGER) AS $$
DECLARE
    v_id_parte   INTEGER;
    v_ya_abierto INTEGER;
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

    INSERT INTO parte_diario (
        id_punto_venta, user_code, monto_inicial,
        observacion_apertura, id_estado, fecha_apertura, fecha_registro
    ) VALUES (
        p_id_punto_venta, p_user_code, p_monto_inicial,
        NULLIF(TRIM(p_observacion), ''), 1, p_fecha_apertura, NOW()
    ) RETURNING parte_diario.id_parte INTO v_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario aperturado correctamente.'::TEXT, v_id_parte;
END;
$$ LANGUAGE plpgsql;
