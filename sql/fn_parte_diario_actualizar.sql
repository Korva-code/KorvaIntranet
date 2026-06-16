-- Permite modificar un parte diario mientras esté abierto (id_estado = 1)
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
           fecha_apertura       = p_fecha_apertura,
           monto_inicial        = p_monto_inicial,
           observacion_apertura = NULLIF(TRIM(p_observacion), '')
     WHERE id_parte = p_id_parte;

    RETURN QUERY SELECT TRUE::BOOLEAN, 'Parte diario actualizado correctamente.'::TEXT;
END;
$$ LANGUAGE plpgsql;
