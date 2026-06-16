-- Tabla abonos
CREATE TABLE IF NOT EXISTS abonos (
    id_abono   SERIAL PRIMARY KEY,
    id_banco   INTEGER,
    fecha      DATE,
    monto      NUMERIC(18, 2),
    moneda     TEXT DEFAULT 'SOL',
    referencia TEXT,
    concepto   TEXT,
    card_code  TEXT,
    id_estado  INTEGER DEFAULT 1
);

-- Función listado
CREATE OR REPLACE FUNCTION sp_abonos_listar(
    p_id_abono INTEGER
)
RETURNS TABLE (
    "id_abono"   INTEGER,
    "id_banco"   INTEGER,
    "banco_nombre" TEXT,
    "fecha"      DATE,
    "monto"      NUMERIC,
    "moneda"     TEXT,
    "referencia" TEXT,
    "concepto"   TEXT,
    "card_code"  TEXT,
    "bp_name"    TEXT,
    "id_estado"  INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id_abono,
        a.id_banco,
        COALESCE(b.nombre, '')            ::TEXT  AS banco_nombre,
        a.fecha,
        a.monto,
        a.moneda                          ::TEXT,
        a.referencia                      ::TEXT,
        a.concepto                        ::TEXT,
        a.card_code                       ::TEXT,
        COALESCE(bp.card_name, a.card_code, '') ::TEXT AS bp_name,
        a.id_estado
    FROM abonos a
    LEFT JOIN bancos           b  ON b.id_banco  = a.id_banco
    LEFT JOIN business_partners bp ON bp.card_code = a.card_code
    WHERE
        (p_id_abono = 0 OR a.id_abono = p_id_abono)
    ORDER BY a.fecha DESC, a.id_abono DESC;
END;
$$ LANGUAGE plpgsql;
