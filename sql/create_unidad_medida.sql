CREATE TABLE IF NOT EXISTS unidad_medida (
    codigo      VARCHAR(10)  PRIMARY KEY,
    descripcion VARCHAR(100) NOT NULL
);

INSERT INTO unidad_medida (codigo, descripcion) VALUES
    ('NIU', 'UNIDAD (BIENES)'),
    ('ZZ',  'UNIDAD (SERVICIOS)')
ON CONFLICT (codigo) DO NOTHING;
