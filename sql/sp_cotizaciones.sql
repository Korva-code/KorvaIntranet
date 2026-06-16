-- ═══════════════════════════════════════════════════════════════
--  Menú: Ventas > Cotizaciones
--  Ejecutar UNA sola vez.  id_parent=2 = sección "Ventas"
-- ═══════════════════════════════════════════════════════════════
INSERT INTO menu_items (id_parent, label, endpoint, icon, orden)
VALUES (2, 'Cotizaciones', 'main.ventas_cotizaciones', 'bi-file-earmark-text', 4)
ON CONFLICT DO NOTHING;


-- ═══════════════════════════════════════════════════════════════
--  Tablas: invoice_cotizaciones (cabecera) e invoice_item_cotizaciones (detalle)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS invoice_cotizaciones (
    cot_id         SERIAL        PRIMARY KEY,
    card_code      TEXT          NOT NULL,
    doc_date       DATE,
    doc_due_date   DATE,
    doc_currency   TEXT          DEFAULT 'SOL',
    tipo_cambio    NUMERIC(12,6) DEFAULT 1,
    doc_total      NUMERIC(18,4) DEFAULT 0,
    doc_subtotal   NUMERIC(18,4) DEFAULT 0,
    doc_igv        NUMERIC(18,4) DEFAULT 0,
    invoice_wh     TEXT,
    num_at_card    TEXT,
    comments       TEXT,
    journal_memo   TEXT,
    user_code      TEXT,
    id_estado      INTEGER       DEFAULT 1,   -- 1=activa, 0=anulada
    fecha_registro TIMESTAMP     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoice_item_cotizaciones (
    item_cot_id     SERIAL        PRIMARY KEY,
    cot_id          INTEGER       NOT NULL REFERENCES invoice_cotizaciones(cot_id),
    item_code       TEXT,
    item_name       TEXT,
    quantity        NUMERIC(18,4) DEFAULT 0,
    price_after_vat NUMERIC(18,4) DEFAULT 0,
    tax_code        TEXT          DEFAULT 'I18',
    warehouse_code  TEXT
);


-- ═══════════════════════════════════════════════════════════════
--  sp_cot_listar(p_cot_id)   0 = todas, >0 = una
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_cot_listar(p_cot_id INTEGER)
RETURNS TABLE (
    "cot_id"         INTEGER,
    "card_code"      TEXT,
    "bp_name"        TEXT,
    "doc_date"       DATE,
    "doc_due_date"   DATE,
    "doc_currency"   TEXT,
    "tipo_cambio"    NUMERIC,
    "doc_total"      NUMERIC,
    "doc_subtotal"   NUMERIC,
    "doc_igv"        NUMERIC,
    "invoice_wh"     TEXT,
    "num_at_card"    TEXT,
    "comments"       TEXT,
    "journal_memo"   TEXT,
    "user_code"      TEXT,
    "user_name"      TEXT,
    "id_estado"      INTEGER,
    "fecha_registro" TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.cot_id,
        c.card_code                                             ::TEXT,
        COALESCE(bp.card_name, c.card_code, '')                ::TEXT  AS bp_name,
        c.doc_date,
        c.doc_due_date,
        COALESCE(c.doc_currency, 'SOL')                        ::TEXT,
        COALESCE(c.tipo_cambio, 1),
        COALESCE(c.doc_total, 0),
        COALESCE(c.doc_subtotal, 0),
        COALESCE(c.doc_igv, 0),
        COALESCE(c.invoice_wh, '')                             ::TEXT,
        COALESCE(c.num_at_card, '')                            ::TEXT,
        COALESCE(c.comments, '')                               ::TEXT,
        COALESCE(c.journal_memo, '')                           ::TEXT,
        COALESCE(c.user_code, '')                              ::TEXT,
        COALESCE(u.nombres, c.user_code, '')                   ::TEXT  AS user_name,
        COALESCE(c.id_estado, 1),
        c.fecha_registro
    FROM invoice_cotizaciones c
    LEFT JOIN business_partners bp ON bp.card_code = c.card_code
    LEFT JOIN w_usuarios          u ON u.id_usuario  = c.user_code
    WHERE (p_cot_id = 0 OR c.cot_id = p_cot_id)
    ORDER BY c.cot_id DESC;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_cot_items_listar(p_cot_id)   0 = todos
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_cot_items_listar(p_cot_id INTEGER)
RETURNS TABLE (
    "item_cot_id"    INTEGER,
    "cot_id"         INTEGER,
    "item_code"      TEXT,
    "item_name"      TEXT,
    "quantity"       NUMERIC,
    "price_after_vat" NUMERIC,
    "tax_code"       TEXT,
    "warehouse_code" TEXT,
    "subtotal"       NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.item_cot_id,
        d.cot_id,
        COALESCE(d.item_code, '')                               ::TEXT,
        COALESCE(d.item_name, it.item_name, d.item_code, '')    ::TEXT,
        COALESCE(d.quantity, 0),
        COALESCE(d.price_after_vat, 0),
        COALESCE(d.tax_code, 'I18')                             ::TEXT,
        COALESCE(d.warehouse_code, '')                          ::TEXT,
        ROUND(COALESCE(d.quantity, 0) * COALESCE(d.price_after_vat, 0), 4) AS subtotal
    FROM invoice_item_cotizaciones d
    LEFT JOIN items it ON it.item_code = d.item_code
    WHERE (p_cot_id = 0 OR d.cot_id = p_cot_id)
    ORDER BY d.cot_id, d.item_cot_id;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  fn_cot_guardar — INSERT cabecera + ítems en JSONB
--  Retorna: success, message, cot_id
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION fn_cot_guardar(
    p_card_code    TEXT,
    p_doc_date     DATE,
    p_doc_due_date DATE,
    p_doc_currency TEXT,
    p_tipo_cambio  NUMERIC,
    p_doc_total    NUMERIC,
    p_doc_subtotal NUMERIC,
    p_doc_igv      NUMERIC,
    p_invoice_wh   TEXT,
    p_num_at_card  TEXT,
    p_comments     TEXT,
    p_journal_memo TEXT,
    p_user_code    TEXT,
    p_items        JSONB
)
RETURNS TABLE ("success" BOOLEAN, "message" TEXT, "cot_id" INTEGER) AS $$
DECLARE
    v_id   INTEGER;
    v_item JSONB;
BEGIN
    INSERT INTO invoice_cotizaciones (
        card_code, doc_date, doc_due_date,
        doc_currency, tipo_cambio,
        doc_total, doc_subtotal, doc_igv,
        invoice_wh, num_at_card, comments, journal_memo,
        user_code, id_estado
    ) VALUES (
        p_card_code, p_doc_date, p_doc_due_date,
        p_doc_currency, p_tipo_cambio,
        p_doc_total, p_doc_subtotal, p_doc_igv,
        p_invoice_wh, p_num_at_card, p_comments, p_journal_memo,
        p_user_code, 1
    ) RETURNING invoice_cotizaciones.cot_id INTO v_id;

    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items) LOOP
        INSERT INTO invoice_item_cotizaciones (
            cot_id, item_code, item_name,
            quantity, price_after_vat, tax_code, warehouse_code
        ) VALUES (
            v_id,
            v_item->>'item_code',
            COALESCE(v_item->>'item_name', ''),
            COALESCE((v_item->>'quantity')::NUMERIC, 0),
            COALESCE((v_item->>'price_after_vat')::NUMERIC, 0),
            COALESCE(v_item->>'tax_code', 'I18'),
            COALESCE(v_item->>'warehouse_code', '')
        );
    END LOOP;

    RETURN QUERY SELECT TRUE, 'OK'::TEXT, v_id;
EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT, 0;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  fn_cot_anular(p_cot_id)
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION fn_cot_anular(p_cot_id INTEGER)
RETURNS TABLE ("success" BOOLEAN, "message" TEXT) AS $$
BEGIN
    UPDATE invoice_cotizaciones SET id_estado = 0 WHERE cot_id = p_cot_id;
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Cotización no encontrada.'::TEXT;
    ELSE
        RETURN QUERY SELECT TRUE, 'Cotización anulada correctamente.'::TEXT;
    END IF;
EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT;
END;
$$ LANGUAGE plpgsql;
