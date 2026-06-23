-- Vehículos por socio de negocio (transportistas)
CREATE TABLE IF NOT EXISTS bp_vehiculos (
    id               SERIAL PRIMARY KEY,
    card_code        TEXT NOT NULL REFERENCES business_partners(card_code) ON DELETE CASCADE,
    vehiculo         TEXT DEFAULT 'principal',
    numero_de_placa  TEXT
);

CREATE INDEX IF NOT EXISTS idx_bp_vehiculos_card_code ON bp_vehiculos(card_code);
