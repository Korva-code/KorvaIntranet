-- Tabla bancos
CREATE TABLE IF NOT EXISTS bancos (
    id_banco   SERIAL PRIMARY KEY,
    cod_banco  TEXT,
    nombre     TEXT,
    nro_cuenta TEXT,
    cci        TEXT,
    moneda     TEXT DEFAULT 'SOL',
    id_estado  INTEGER DEFAULT 1
);

-- Función listado
CREATE OR REPLACE FUNCTION sp_bancos_listar(
    p_id_banco INTEGER
)
RETURNS TABLE (
    "id_banco"   INTEGER,
    "cod_banco"  TEXT,
    "nombre"     TEXT,
    "nro_cuenta" TEXT,
    "cci"        TEXT,
    "moneda"     TEXT,
    "id_estado"  INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        b.id_banco,
        b.cod_banco  ::TEXT,
        b.nombre     ::TEXT,
        b.nro_cuenta ::TEXT,
        b.cci        ::TEXT,
        b.moneda     ::TEXT,
        b.id_estado
    FROM bancos b
    WHERE
        (p_id_banco = 0 OR b.id_banco = p_id_banco)
    ORDER BY b.nombre;
END;
$$ LANGUAGE plpgsql;
