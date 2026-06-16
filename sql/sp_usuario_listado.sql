CREATE OR REPLACE FUNCTION sp_usuario_listado(
    p_perfil INTEGER
)
RETURNS TABLE (
    "id_usuario"  TEXT,
    "nombres"     TEXT,
    "id_perfil"   INTEGER,
    "id_estado"   INTEGER,
    "id_rol"      INTEGER,
    "whs_code"    TEXT,
    "correo"      TEXT,
    "ubicacion"   TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id_usuario  ::TEXT,
        u.nombres     ::TEXT,
        u.id_perfil,
        u.id_estado,
        u.id_rol,
        u.whs_code    ::TEXT,
        u.correo      ::TEXT,
        u.ubicacion   ::TEXT
    FROM w_usuarios u
    WHERE
        (p_perfil = 0 OR u.id_perfil = p_perfil)
    ORDER BY u.nombres;
END;
$$ LANGUAGE plpgsql;
