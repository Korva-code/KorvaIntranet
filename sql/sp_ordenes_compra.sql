-- ═══════════════════════════════════════════════════════════════
--  Menú: Compras > Órdenes de Compra
--  Ejecutar UNA sola vez.  id_parent=3 = sección "Compras"
-- ═══════════════════════════════════════════════════════════════
INSERT INTO menu_items (id_parent, label, endpoint, icon, orden)
VALUES (3, 'Órdenes de Compra', 'main.compras_ordenes_compra', 'bi-cart3', 3)
ON CONFLICT DO NOTHING;


-- ═══════════════════════════════════════════════════════════════
--  Tablas: invoice_oc (cabecera) e invoice_item_oc (detalle)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS invoice_oc (
    oc_id          SERIAL        PRIMARY KEY,
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

-- Columnas adicionales por si la tabla ya existía sin ellas
ALTER TABLE invoice_oc ADD COLUMN IF NOT EXISTS tipo_cambio   NUMERIC(12,6) DEFAULT 1;
ALTER TABLE invoice_oc ADD COLUMN IF NOT EXISTS doc_subtotal  NUMERIC(18,4) DEFAULT 0;
ALTER TABLE invoice_oc ADD COLUMN IF NOT EXISTS doc_igv       NUMERIC(18,4) DEFAULT 0;

CREATE TABLE IF NOT EXISTS invoice_item_oc (
    item_oc_id      SERIAL        PRIMARY KEY,
    oc_id           INTEGER       NOT NULL REFERENCES invoice_oc(oc_id),
    item_code       TEXT,
    item_name       TEXT,
    quantity        NUMERIC(18,4) DEFAULT 0,
    price_after_vat NUMERIC(18,4) DEFAULT 0,
    tax_code        TEXT          DEFAULT 'I18',
    warehouse_code  TEXT
);

ALTER TABLE invoice_item_oc ADD COLUMN IF NOT EXISTS item_name TEXT;


-- ═══════════════════════════════════════════════════════════════
--  sp_oc_listar(p_oc_id)   0 = todas, >0 = una
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_oc_listar(p_oc_id INTEGER)
RETURNS TABLE (
    "oc_id"          INTEGER,
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
        oc.oc_id,
        oc.card_code                                            ::TEXT,
        COALESCE(bp.card_name, oc.card_code, '')               ::TEXT  AS bp_name,
        oc.doc_date,
        oc.doc_due_date,
        COALESCE(oc.doc_currency, 'SOL')                       ::TEXT,
        COALESCE(oc.tipo_cambio, 1),
        COALESCE(oc.doc_total, 0),
        COALESCE(oc.doc_subtotal, 0),
        COALESCE(oc.doc_igv, 0),
        COALESCE(oc.invoice_wh, '')                            ::TEXT,
        COALESCE(oc.num_at_card, '')                           ::TEXT,
        COALESCE(oc.comments, '')                              ::TEXT,
        COALESCE(oc.journal_memo, '')                          ::TEXT,
        COALESCE(oc.user_code, '')                             ::TEXT,
        COALESCE(u.nombres, oc.user_code, '')                  ::TEXT  AS user_name,
        COALESCE(oc.id_estado, 1),
        oc.fecha_registro
    FROM invoice_oc oc
    LEFT JOIN business_partners bp ON bp.card_code = oc.card_code
    LEFT JOIN w_usuarios          u  ON u.id_usuario  = oc.user_code
    WHERE (p_oc_id = 0 OR oc.oc_id = p_oc_id)
    ORDER BY oc.oc_id DESC;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  sp_oc_items_listar(p_oc_id)   0 = todos
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION sp_oc_items_listar(p_oc_id INTEGER)
RETURNS TABLE (
    "item_oc_id"     INTEGER,
    "oc_id"          INTEGER,
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
        d.item_oc_id,
        d.oc_id,
        COALESCE(d.item_code, '')                               ::TEXT,
        COALESCE(d.item_name, it.item_name, d.item_code, '')    ::TEXT,
        COALESCE(d.quantity, 0),
        COALESCE(d.price_after_vat, 0),
        COALESCE(d.tax_code, 'I18')                             ::TEXT,
        COALESCE(d.warehouse_code, '')                          ::TEXT,
        ROUND(COALESCE(d.quantity, 0) * COALESCE(d.price_after_vat, 0), 4) AS subtotal
    FROM invoice_item_oc d
    LEFT JOIN items it ON it.item_code = d.item_code
    WHERE (p_oc_id = 0 OR d.oc_id = p_oc_id)
    ORDER BY d.oc_id, d.item_oc_id;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════
--  fn_oc_guardar — INSERT cabecera + ítems en JSONB
--  Retorna: success, message, oc_id
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION fn_oc_guardar(
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
RETURNS TABLE ("success" BOOLEAN, "message" TEXT, "oc_id" INTEGER) AS $$
DECLARE
    v_id   INTEGER;
    v_item JSONB;
BEGIN
    INSERT INTO invoice_oc (
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
    ) RETURNING invoice_oc.oc_id INTO v_id;

    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items) LOOP
        INSERT INTO invoice_item_oc (
            oc_id, item_code, item_name,
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
--  fn_oc_anular(p_oc_id)
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION fn_oc_anular(p_oc_id INTEGER)
RETURNS TABLE ("success" BOOLEAN, "message" TEXT) AS $$
BEGIN
    UPDATE invoice_oc SET id_estado = 0 WHERE oc_id = p_oc_id;
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Orden de Compra no encontrada.'::TEXT;
    ELSE
        RETURN QUERY SELECT TRUE, 'Orden de Compra anulada correctamente.'::TEXT;
    END IF;
EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT;
END;
$$ LANGUAGE plpgsql;
