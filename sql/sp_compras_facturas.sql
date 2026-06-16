-- ═══════════════════════════════════════════════════════════════
--  Tabla: tipos_compra
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS tipos_compra (
    id_tipo   SERIAL  PRIMARY KEY,
    nombre    TEXT    NOT NULL,
    id_estado INTEGER DEFAULT 1
);

INSERT INTO tipos_compra (nombre) VALUES
    ('Servicios de Luz'),
    ('Internet'),
    ('Productos de Venta')
ON CONFLICT DO NOTHING;

-- Campo en invoice_p para el tipo de compra
ALTER TABLE invoice_p
    ADD COLUMN IF NOT EXISTS id_tipo_compra INTEGER REFERENCES tipos_compra(id_tipo);


-- ═══════════════════════════════════════════════════════════════
--  sp_tipos_compra_listar
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_tipos_compra_listar()
RETURNS TABLE (
    "id_tipo"  INTEGER,
    "nombre"   TEXT,
    "id_estado" INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.id_tipo, t.nombre::TEXT, t.id_estado
    FROM   tipos_compra t
    WHERE  t.id_estado = 1
    ORDER  BY t.nombre;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_compras_listar(p_invoice_id)
--  0 = todas, >0 = una sola
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_compras_listar(p_invoice_id INTEGER)
RETURNS TABLE (
    "invoice_id"     INTEGER,
    "card_code"      TEXT,
    "bp_name"        TEXT,
    "id_tipo_compra" INTEGER,
    "tipo_nombre"    TEXT,
    "invoice_type"   TEXT,
    "invoice_serie"  TEXT,
    "invoice_number" TEXT,
    "doc_date"       DATE,
    "tax_date"       DATE,
    "doc_due_date"   DATE,
    "doc_currency"   TEXT,
    "doc_total"      NUMERIC,
    "invoice_wh"     TEXT,
    "num_at_card"    TEXT,
    "journal_memo"   TEXT,
    "comments"       TEXT,
    "user_code"      TEXT,
    "sunat_estado"   TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.invoice_id,
        i.card_code                                         ::TEXT,
        COALESCE(bp.card_name, i.card_code, '')            ::TEXT AS bp_name,
        i.id_tipo_compra,
        COALESCE(tc.nombre, '')                            ::TEXT AS tipo_nombre,
        COALESCE(i.invoice_type, '')                       ::TEXT,
        COALESCE(i.invoice_serie, '')                      ::TEXT,
        COALESCE(i.invoice_number, '')                     ::TEXT,
        i.doc_date,
        i.tax_date,
        i.doc_due_date,
        COALESCE(i.doc_currency, 'SOL')                   ::TEXT,
        COALESCE(i.doc_total, 0),
        COALESCE(i.invoice_wh, '')                        ::TEXT,
        COALESCE(i.num_at_card, '')                       ::TEXT,
        COALESCE(i.journal_memo, '')                      ::TEXT,
        COALESCE(i.comments, '')                          ::TEXT,
        COALESCE(i.user_code, '')                         ::TEXT,
        COALESCE(i.sunat_estado, '')                      ::TEXT
    FROM invoice_p i
    LEFT JOIN business_partners bp ON bp.card_code   = i.card_code
    LEFT JOIN tipos_compra      tc ON tc.id_tipo     = i.id_tipo_compra
    WHERE (p_invoice_id = 0 OR i.invoice_id = p_invoice_id)
    ORDER BY i.invoice_id DESC;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_compras_items_listar(p_invoice_id)
--  0 = todos los ítems, >0 = de una factura
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_compras_items_listar(p_invoice_id INTEGER)
RETURNS TABLE (
    "invoice_id"      INTEGER,
    "item_code"       TEXT,
    "item_name"       TEXT,
    "quantity"        NUMERIC,
    "price_after_vat" NUMERIC,
    "tax_code"        TEXT,
    "subtotal"        NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.invoice_id,
        d.item_code                                         ::TEXT,
        COALESCE(it.item_name, d.item_code, '')            ::TEXT AS item_name,
        COALESCE(d.quantity, 0),
        COALESCE(d.price_after_vat, 0),
        COALESCE(d.tax_code, '')                           ::TEXT,
        COALESCE(d.quantity, 0) * COALESCE(d.price_after_vat, 0) AS subtotal
    FROM invoice_item_p d
    LEFT JOIN items it ON it.item_code = d.item_code
    WHERE (p_invoice_id = 0 OR d.invoice_id = p_invoice_id)
    ORDER BY d.invoice_id;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_compras_guardar
--  p_invoice_id = 0 → INSERT, >0 → UPDATE
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_compras_guardar(
    p_invoice_id    INTEGER,
    p_card_code     TEXT,
    p_id_tipo       INTEGER,
    p_invoice_type  TEXT,
    p_invoice_serie TEXT,
    p_invoice_number TEXT,
    p_doc_date      DATE,
    p_tax_date      DATE,
    p_doc_due_date  DATE,
    p_doc_currency  TEXT,
    p_doc_total     NUMERIC,
    p_invoice_wh    TEXT,
    p_num_at_card   TEXT,
    p_journal_memo  TEXT,
    p_comments      TEXT,
    p_user_code     TEXT,
    p_items         JSONB
)
RETURNS TABLE ("success" BOOLEAN, "message" TEXT, "invoice_id" INTEGER) AS $$
DECLARE
    v_id   INTEGER;
    v_item JSONB;
BEGIN
    IF p_invoice_id = 0 THEN
        -- ── INSERT ────────────────────────────────────────────
        INSERT INTO invoice_p (
            card_code, id_tipo_compra,
            invoice_type, invoice_serie, invoice_number,
            doc_date, tax_date, doc_due_date,
            doc_currency, doc_total,
            invoice_wh, num_at_card, journal_memo, comments,
            user_code
        ) VALUES (
            p_card_code, p_id_tipo,
            p_invoice_type, p_invoice_serie, p_invoice_number,
            p_doc_date, p_tax_date, p_doc_due_date,
            p_doc_currency, p_doc_total,
            p_invoice_wh, p_num_at_card, p_journal_memo, p_comments,
            p_user_code
        ) RETURNING invoice_p.invoice_id INTO v_id;
    ELSE
        -- ── UPDATE ────────────────────────────────────────────
        v_id := p_invoice_id;
        UPDATE invoice_p SET
            card_code      = p_card_code,
            id_tipo_compra = p_id_tipo,
            invoice_type   = p_invoice_type,
            invoice_serie  = p_invoice_serie,
            invoice_number = p_invoice_number,
            doc_date       = p_doc_date,
            tax_date       = p_tax_date,
            doc_due_date   = p_doc_due_date,
            doc_currency   = p_doc_currency,
            doc_total      = p_doc_total,
            invoice_wh     = p_invoice_wh,
            num_at_card    = p_num_at_card,
            journal_memo   = p_journal_memo,
            comments       = p_comments,
            user_code      = p_user_code
        WHERE invoice_p.invoice_id = v_id;
        -- Eliminar ítems anteriores
        DELETE FROM invoice_itemp WHERE invoice_itemp.invoice_id = v_id;
    END IF;

    -- ── Insertar ítems ─────────────────────────────────────
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items) LOOP
        INSERT INTO invoice_item_p (
            invoice_id, item_code, quantity, price_after_vat, tax_code
        ) VALUES (
            v_id,
            v_item->>'item_code',
            COALESCE((v_item->>'quantity')::NUMERIC, 0),
            COALESCE((v_item->>'price_after_vat')::NUMERIC, 0),
            COALESCE(v_item->>'tax_code', '')
        );
    END LOOP;

    RETURN QUERY SELECT TRUE, 'OK'::TEXT, v_id;
EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT, 0;
END;
$$ LANGUAGE plpgsql;
