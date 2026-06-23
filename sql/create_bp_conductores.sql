-- Conductores por socio de negocio (transportistas)
CREATE TABLE IF NOT EXISTS bp_conductores (
    id                       SERIAL PRIMARY KEY,
    card_code                TEXT NOT NULL REFERENCES business_partners(card_code) ON DELETE CASCADE,
    conductor                TEXT DEFAULT 'principal',
    tipo_de_documento        TEXT DEFAULT '1',
    numero_de_documento      TEXT,
    nombres                  TEXT,
    apellidos                TEXT,
    numero_licencia_conducir TEXT
);

CREATE INDEX IF NOT EXISTS idx_bp_conductores_card_code ON bp_conductores(card_code);
