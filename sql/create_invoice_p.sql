-- Tablas invoice_p e invoice_item_p: misma estructura que invoice e invoice_item
CREATE TABLE IF NOT EXISTS invoice_p (
    invoice_id     SERIAL          PRIMARY KEY,
    card_code      TEXT,
    invoice_type   TEXT,
    invoice_serie  TEXT,
    invoice_number TEXT,
    doc_date       DATE,
    tax_date       DATE,
    doc_due_date   DATE,
    doc_currency   TEXT,
    doc_total      NUMERIC(18, 4),
    invoice_wh     TEXT,
    invoice_pos    INTEGER,
    user_code      TEXT,
    comments       TEXT,
    num_at_card    TEXT,
    journal_memo   TEXT,
    sunat_estado   TEXT,
    sunat_a4       TEXT,
    sunat_ticket   TEXT
);

-- Tabla invoice_item_p: misma estructura que invoice_item
CREATE TABLE IF NOT EXISTS invoice_item_p (
    id              SERIAL          PRIMARY KEY,
    invoice_id      INTEGER         NOT NULL REFERENCES invoice_p(invoice_id) ON DELETE CASCADE,
    item_code       TEXT,
    quantity        NUMERIC(18, 4),
    price_after_vat NUMERIC(18, 4),
    tax_code        TEXT,
    warehouse_code  TEXT,
    costing_code    TEXT,
    costing_code2   TEXT,
    costing_code3   TEXT
);

CREATE INDEX IF NOT EXISTS idx_invoice_item_p_invoice_id ON invoice_item_p(invoice_id);
