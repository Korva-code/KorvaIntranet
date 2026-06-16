-- ══════════════════════════════════════════════════════════════
-- Tabla: impuestos
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS impuestos (
    id          SERIAL          PRIMARY KEY,
    codigo      VARCHAR(10)     NOT NULL UNIQUE,
    descripcion VARCHAR(100),
    valor       NUMERIC(6, 2)   NOT NULL DEFAULT 0,
    id_estado   SMALLINT        DEFAULT 1
);

INSERT INTO impuestos (codigo, descripcion, valor) VALUES
    ('IGV', 'Impuesto General a las Ventas', 16.00),
    ('EXO', 'Exonerado',                      0.01)
ON CONFLICT (codigo) DO NOTHING;
