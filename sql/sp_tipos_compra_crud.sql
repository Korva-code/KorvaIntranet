-- ═══════════════════════════════════════════════════════════════════
-- CRUD: Tipos de Compra
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Listar todos (admin — incluye inactivos) ──────────────────
CREATE OR REPLACE FUNCTION sp_tipos_compra_listar_todos()
RETURNS TABLE (
    id_tipo   INTEGER,
    nombre    TEXT,
    id_estado INTEGER
) LANGUAGE sql STABLE AS $$
    SELECT id_tipo, nombre::TEXT, id_estado
    FROM   tipos_compra
    ORDER  BY nombre;
$$;

-- ── 2. Guardar (INSERT si p_id_tipo=0, UPDATE si >0) ─────────────
CREATE OR REPLACE FUNCTION sp_tipos_compra_guardar(
    p_id_tipo INTEGER,
    p_nombre  TEXT
) RETURNS TABLE (success BOOLEAN, message TEXT, id_tipo INTEGER)
LANGUAGE plpgsql AS $$
DECLARE
    v_id INTEGER;
    v_nombre TEXT := TRIM(p_nombre);
BEGIN
    IF v_nombre = '' OR v_nombre IS NULL THEN
        RETURN QUERY SELECT FALSE, 'El nombre no puede estar vacío.'::TEXT, 0;
        RETURN;
    END IF;

    IF p_id_tipo = 0 THEN
        INSERT INTO tipos_compra (nombre, id_estado)
        VALUES (v_nombre, 1)
        RETURNING tipos_compra.id_tipo INTO v_id;
        RETURN QUERY SELECT TRUE, 'Tipo de compra creado correctamente.'::TEXT, v_id;
    ELSE
        UPDATE tipos_compra
           SET nombre = v_nombre
         WHERE tipos_compra.id_tipo = p_id_tipo
        RETURNING tipos_compra.id_tipo INTO v_id;

        IF v_id IS NULL THEN
            RETURN QUERY SELECT FALSE, 'Tipo de compra no encontrado.'::TEXT, 0;
        ELSE
            RETURN QUERY SELECT TRUE, 'Tipo de compra actualizado correctamente.'::TEXT, v_id;
        END IF;
    END IF;
END;
$$;

-- ── 3. Cambiar estado (activar / desactivar) ─────────────────────
CREATE OR REPLACE FUNCTION sp_tipos_compra_estado(
    p_id_tipo  INTEGER,
    p_id_estado INTEGER   -- 1=activo, 0=inactivo
) RETURNS TABLE (success BOOLEAN, message TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE tipos_compra SET id_estado = p_id_estado WHERE tipos_compra.id_tipo = p_id_tipo;
    IF FOUND THEN
        RETURN QUERY SELECT TRUE,
            CASE WHEN p_id_estado = 1 THEN 'Tipo activado correctamente.'
                                      ELSE 'Tipo desactivado correctamente.'
            END::TEXT;
    ELSE
        RETURN QUERY SELECT FALSE, 'Tipo de compra no encontrado.'::TEXT;
    END IF;
END;
$$;

-- ── 4. Ítem de menú ──────────────────────────────────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (15, 1, 'Tipos de Compra', 'main.maestras_tipos_compra', 'bi-tags', 5)
ON CONFLICT (id_menu) DO NOTHING;
