-- ═══════════════════════════════════════════════════════════════════
-- CRUD: Grupos de Socios de Negocio
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Listar todos ──────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_grupos_socios_listar()
RETURNS TABLE (
    group_code TEXT,
    group_name TEXT,
    id_estado  INTEGER
) LANGUAGE sql STABLE AS $$
    SELECT TRIM(group_code)::TEXT,
           TRIM(group_name)::TEXT,
           COALESCE(id_estado, 1)
    FROM   business_partners_group
    ORDER  BY group_name;
$$;

-- ── 2. Guardar (INSERT si es nuevo, UPDATE si existe) ─────────────
CREATE OR REPLACE FUNCTION sp_grupos_socios_guardar(
    p_group_code TEXT,
    p_group_name TEXT,
    p_es_nuevo   BOOLEAN DEFAULT TRUE
) RETURNS TABLE (success BOOLEAN, message TEXT, group_code TEXT)
LANGUAGE plpgsql AS $$
DECLARE
    v_code TEXT := UPPER(TRIM(p_group_code));
    v_name TEXT := TRIM(p_group_name);
BEGIN
    IF v_code = '' OR v_code IS NULL THEN
        RETURN QUERY SELECT FALSE, 'El código no puede estar vacío.'::TEXT, ''::TEXT;
        RETURN;
    END IF;
    IF v_name = '' OR v_name IS NULL THEN
        RETURN QUERY SELECT FALSE, 'El nombre no puede estar vacío.'::TEXT, ''::TEXT;
        RETURN;
    END IF;

    IF p_es_nuevo THEN
        IF EXISTS (SELECT 1 FROM business_partners_group WHERE TRIM(business_partners_group.group_code) = v_code) THEN
            RETURN QUERY SELECT FALSE, 'El código ya existe.'::TEXT, v_code;
            RETURN;
        END IF;
        INSERT INTO business_partners_group (group_code, group_name, id_estado)
        VALUES (v_code, v_name, 1);
        RETURN QUERY SELECT TRUE, 'Grupo creado correctamente.'::TEXT, v_code;
    ELSE
        UPDATE business_partners_group
           SET group_name = v_name
         WHERE TRIM(business_partners_group.group_code) = v_code;
        IF FOUND THEN
            RETURN QUERY SELECT TRUE, 'Grupo actualizado correctamente.'::TEXT, v_code;
        ELSE
            RETURN QUERY SELECT FALSE, 'Grupo no encontrado.'::TEXT, v_code;
        END IF;
    END IF;
END;
$$;

-- ── 3. Cambiar estado ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_grupos_socios_estado(
    p_group_code TEXT,
    p_id_estado  INTEGER
) RETURNS TABLE (success BOOLEAN, message TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE business_partners_group
       SET id_estado = p_id_estado
     WHERE TRIM(group_code) = UPPER(TRIM(p_group_code));
    IF FOUND THEN
        RETURN QUERY SELECT TRUE,
            CASE WHEN p_id_estado = 1 THEN 'Grupo activado correctamente.'
                                      ELSE 'Grupo desactivado correctamente.'
            END::TEXT;
    ELSE
        RETURN QUERY SELECT FALSE, 'Grupo no encontrado.'::TEXT;
    END IF;
END;
$$;

-- ── 4. Agregar columna id_estado si no existe ─────────────────────
ALTER TABLE business_partners_group ADD COLUMN IF NOT EXISTS id_estado INTEGER DEFAULT 1;

-- ── 5. Ítem de menú (sub de Maestras id_parent=1) ─────────────────
INSERT INTO menu_items (id_menu, id_parent, label, endpoint, icon, orden)
VALUES (17, 1, 'Grupos Socios', 'main.maestras_grupos_socios', 'bi-diagram-3', 7)
ON CONFLICT (id_menu) DO NOTHING;
