-- ══════════════════════════════════════════════════════════════
-- NOTA DE CRÉDITO — Tablas, funciones y menú
-- ══════════════════════════════════════════════════════════════

-- 0a. Tipos de documento para NC (invoice_type donde operation_type=1, idtype=6)
CREATE OR REPLACE FUNCTION sp_nc_tipos_listar()
RETURNS TABLE(idtype INTEGER, invoice_type TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT t.idtype, t.invoice_type::TEXT
    FROM   invoice_type t
    WHERE  t.operation_type = 1
      AND  t.idtype         = 6
    ORDER  BY t.invoice_type;
END;
$$ LANGUAGE plpgsql;

-- 0b. Serie y próximo número para NC dado un idtype
--     Lee invoce_doc_number uniendo con invoice_type por el texto del tipo
CREATE OR REPLACE FUNCTION fn_nc_get_doc_number(p_idtype INTEGER)
RETURNS TABLE(invoice_serie TEXT, next_number INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(d.invoice_serie, '')::TEXT,
        COALESCE(d.invoice_number + 1, 1)::INTEGER
    FROM  invoce_doc_number d
    JOIN  invoice_type      t ON t.idtype = d.idtype
    WHERE t.idtype = p_idtype
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 0c. Buscar factura de venta por serie + número (cabecera)
CREATE OR REPLACE FUNCTION fn_nc_buscar_factura(p_serie TEXT, p_number INTEGER)
RETURNS TABLE(
    invoice_id     INTEGER,
    card_code      TEXT,
    bp_name        TEXT,
    invoice_type   TEXT,
    invoice_serie  TEXT,
    invoice_number TEXT,
    doc_date       DATE,
    doc_currency   TEXT,
    doc_total      NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.invoice_id,
        COALESCE(i.card_code, '')::TEXT,
        COALESCE(bp.card_name, i.card_code, '')::TEXT,
        COALESCE(i.invoice_type, '')::TEXT,
        COALESCE(i.invoice_serie::TEXT, '')::TEXT,
        COALESCE(i.invoice_number::TEXT, '')::TEXT,
        i.doc_date,
        COALESCE(i.doc_currency, 'PEN')::TEXT,
        COALESCE(i.doc_total, 0)::NUMERIC
    FROM  invoice i
    LEFT  JOIN business_partners bp ON bp.card_code = i.card_code
    WHERE TRIM(UPPER(i.invoice_serie::TEXT)) = TRIM(UPPER(p_serie))
      AND i.invoice_number::TEXT             = p_number::TEXT
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 0d. Ítems de una factura de referencia (con nombre del artículo)
CREATE OR REPLACE FUNCTION fn_nc_buscar_factura_items(p_invoice_id INTEGER)
RETURNS TABLE(
    item_code       TEXT,
    item_name       TEXT,
    quantity        NUMERIC,
    price_after_vat NUMERIC,
    tax_code        TEXT,
    warehouse_code  TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(ii.item_code, '')::TEXT,
        COALESCE(it.item_name, ii.item_code, '')::TEXT,
        COALESCE(ii.quantity, 0)::NUMERIC,
        COALESCE(ii.price_after_vat, 0)::NUMERIC,
        COALESCE(ii.tax_code, '')::TEXT,
        COALESCE(ii.warehouse_code, '')::TEXT
    FROM  invoice_item ii
    LEFT  JOIN items it ON it.item_code = ii.item_code
    WHERE ii.invoice_id = p_invoice_id
    ORDER BY ii.item_code;
END;
$$ LANGUAGE plpgsql;

-- 1. Tabla de motivos (maestra SUNAT)
CREATE TABLE IF NOT EXISTS motivos_nc (
    id_motivo   SERIAL PRIMARY KEY,
    code        VARCHAR(5)   NOT NULL UNIQUE,
    description VARCHAR(200) NOT NULL,
    id_estado   SMALLINT DEFAULT 1
);

INSERT INTO motivos_nc (code, description) VALUES
    ('01', 'Anulación de la operación'),
    ('02', 'Anulación por error en el RUC'),
    ('03', 'Corrección por error en la descripción'),
    ('04', 'Descuento global'),
    ('05', 'Descuento por ítem'),
    ('06', 'Devolución total'),
    ('07', 'Devolución por ítem'),
    ('08', 'Bonificación'),
    ('09', 'Disminución en el valor'),
    ('10', 'Otros conceptos')
ON CONFLICT (code) DO NOTHING;

-- sp_motivos_nc_listar
CREATE OR REPLACE FUNCTION sp_motivos_nc_listar()
RETURNS TABLE(code TEXT, description TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT m.code::TEXT, m.description::TEXT
    FROM   motivos_nc m
    WHERE  m.id_estado = 1
    ORDER  BY m.code;
END;
$$ LANGUAGE plpgsql;

-- 2. Tabla encabezado NC
CREATE TABLE IF NOT EXISTS invoice_nc (
    id_nc                  SERIAL PRIMARY KEY,
    invoice_id             INTEGER REFERENCES invoice(invoice_id),
    nc_serie               VARCHAR(10),
    nc_number              INTEGER,
    nc_type                VARCHAR(20),
    card_code              VARCHAR(50),
    doc_date               DATE DEFAULT CURRENT_DATE,
    doc_currency           VARCHAR(5)  DEFAULT 'PEN',
    doc_total              NUMERIC(14,2) DEFAULT 0,
    motivo_code            VARCHAR(5) REFERENCES motivos_nc(code),
    comments               TEXT,
    sunat_estado           VARCHAR(30),
    sunat_hash             TEXT,
    sunat_xml              TEXT,
    sunat_cdr              TEXT,
    sunat_ticket           TEXT,
    sunat_a4               TEXT,
    id_estado              SMALLINT DEFAULT 1,
    user_code              VARCHAR(50),
    fecha_hora_transaccion TIMESTAMP(0),
    fecha_registro         TIMESTAMP(0) DEFAULT date_trunc('second', NOW() AT TIME ZONE 'America/Lima')
);

-- 3. Tabla ítems
CREATE TABLE IF NOT EXISTS invoice_item_nc (
    id_nc_item      SERIAL PRIMARY KEY,
    id_nc           INTEGER REFERENCES invoice_nc(id_nc) ON DELETE CASCADE,
    item_code       VARCHAR(50),
    description     TEXT,
    quantity        NUMERIC(14,4) DEFAULT 1,
    price_after_vat NUMERIC(14,4) DEFAULT 0,
    tax_code        VARCHAR(10),
    warehouse_code  VARCHAR(20)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_nc_invoice_id  ON invoice_nc (invoice_id);
CREATE INDEX IF NOT EXISTS idx_nc_card_code   ON invoice_nc (card_code);
CREATE INDEX IF NOT EXISTS idx_nc_doc_date    ON invoice_nc (doc_date);
CREATE INDEX IF NOT EXISTS idx_nc_id_estado   ON invoice_nc (id_estado);
CREATE INDEX IF NOT EXISTS idx_nc_item_id_nc  ON invoice_item_nc (id_nc);

-- 4. Trigger: fecha_hora_transaccion en hora Lima
CREATE OR REPLACE FUNCTION trg_invoice_nc_set_fecha_hora()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_hora_transaccion :=
        date_trunc('second', NOW() AT TIME ZONE 'America/Lima');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_invoice_nc_fecha_hora ON invoice_nc;
CREATE TRIGGER trg_invoice_nc_fecha_hora
    BEFORE INSERT ON invoice_nc
    FOR EACH ROW EXECUTE FUNCTION trg_invoice_nc_set_fecha_hora();

-- 5. sp_nc_listar: incluye descripción del motivo desde la tabla
CREATE OR REPLACE FUNCTION sp_nc_listar(p_dias INTEGER DEFAULT 60)
RETURNS TABLE(
    id_nc          INTEGER,
    nc_serie       TEXT,
    nc_number      INTEGER,
    nc_type        TEXT,
    card_code      TEXT,
    bp_name        TEXT,
    doc_date       DATE,
    doc_currency   TEXT,
    doc_total      NUMERIC,
    motivo_code    TEXT,
    motivo_desc    TEXT,
    comments       TEXT,
    sunat_estado   TEXT,
    sunat_a4       TEXT,
    sunat_ticket   TEXT,
    sunat_hash     TEXT,
    sunat_xml      TEXT,
    sunat_cdr      TEXT,
    id_estado      SMALLINT,
    user_code      TEXT,
    user_nombre    TEXT,
    invoice_id     INTEGER,
    ref_serie      TEXT,
    ref_number     TEXT,
    fecha_registro TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        nc.id_nc,
        COALESCE(nc.nc_serie, '')::TEXT,
        nc.nc_number,
        COALESCE(nc.nc_type, '')::TEXT,
        COALESCE(nc.card_code, '')::TEXT,
        COALESCE(bp.card_name, nc.card_code, '')::TEXT         AS bp_name,
        nc.doc_date,
        COALESCE(nc.doc_currency, 'PEN')::TEXT,
        COALESCE(nc.doc_total, 0)::NUMERIC,
        COALESCE(nc.motivo_code, '')::TEXT,
        COALESCE(mn.description, nc.motivo_code, '')::TEXT     AS motivo_desc,
        COALESCE(nc.comments, '')::TEXT,
        COALESCE(nc.sunat_estado, '')::TEXT,
        COALESCE(nc.sunat_a4, '')::TEXT,
        COALESCE(nc.sunat_ticket, '')::TEXT,
        COALESCE(nc.sunat_hash, '')::TEXT,
        COALESCE(nc.sunat_xml, '')::TEXT,
        COALESCE(nc.sunat_cdr, '')::TEXT,
        nc.id_estado,
        COALESCE(nc.user_code, '')::TEXT,
        COALESCE(u.nombres, nc.user_code, '')::TEXT            AS user_nombre,
        nc.invoice_id,
        COALESCE(i.invoice_serie::TEXT, '')                    AS ref_serie,
        COALESCE(i.invoice_number::TEXT, '')                   AS ref_number,
        nc.fecha_registro
    FROM  invoice_nc nc
    LEFT  JOIN motivos_nc      mn ON mn.code      = nc.motivo_code
    LEFT  JOIN business_partners bp ON bp.card_code = nc.card_code
    LEFT  JOIN w_usuarios       u  ON u.id_usuario::TEXT = nc.user_code
    LEFT  JOIN invoice          i  ON i.invoice_id = nc.invoice_id
    WHERE nc.doc_date >= (CURRENT_DATE - p_dias)
    ORDER BY nc.id_nc DESC;
END;
$$ LANGUAGE plpgsql;

-- 6. sp_nc_items_listar
CREATE OR REPLACE FUNCTION sp_nc_items_listar(p_id_nc INTEGER)
RETURNS TABLE(
    id_nc_item      INTEGER,
    item_code       TEXT,
    description     TEXT,
    quantity        NUMERIC,
    price_after_vat NUMERIC,
    tax_code        TEXT,
    warehouse_code  TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        it.id_nc_item,
        COALESCE(it.item_code, '')::TEXT,
        COALESCE(it.description, '')::TEXT,
        COALESCE(it.quantity, 0)::NUMERIC,
        COALESCE(it.price_after_vat, 0)::NUMERIC,
        COALESCE(it.tax_code, '')::TEXT,
        COALESCE(it.warehouse_code, '')::TEXT
    FROM invoice_item_nc it
    WHERE it.id_nc = p_id_nc
    ORDER BY it.id_nc_item;
END;
$$ LANGUAGE plpgsql;

-- 7. fn_nc_insertar: inserta NC, actualiza contador en invoce_doc_number
CREATE OR REPLACE FUNCTION fn_nc_insertar(
    p_invoice_id   INTEGER,
    p_nc_serie     TEXT,
    p_nc_number    INTEGER,
    p_nc_type      TEXT,
    p_idtype       INTEGER,
    p_card_code    TEXT,
    p_doc_date     DATE,
    p_doc_currency TEXT,
    p_doc_total    NUMERIC,
    p_motivo_code  TEXT,
    p_comments     TEXT,
    p_user_code    TEXT,
    p_items        JSONB DEFAULT '[]'::JSONB
) RETURNS TABLE(success BOOLEAN, message TEXT, id_nc INTEGER) AS $$
DECLARE
    v_id_nc    INTEGER;
    v_item     JSONB;
    v_mot_desc TEXT;
BEGIN
    IF p_nc_serie IS NULL OR TRIM(p_nc_serie) = '' THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'Ingrese la serie de la nota de crédito.'::TEXT, 0; RETURN;
    END IF;
    IF p_nc_number IS NULL OR p_nc_number <= 0 THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'Ingrese un número válido.'::TEXT, 0; RETURN;
    END IF;
    IF p_motivo_code IS NULL OR TRIM(p_motivo_code) = '' THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'Seleccione el motivo.'::TEXT, 0; RETURN;
    END IF;

    -- Verificar motivo
    SELECT description INTO v_mot_desc FROM motivos_nc WHERE code = TRIM(p_motivo_code);
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, format('Motivo "%s" no válido.', p_motivo_code)::TEXT, 0; RETURN;
    END IF;

    -- Validar duplicado
    IF EXISTS (SELECT 1 FROM invoice_nc WHERE nc_serie = TRIM(p_nc_serie) AND nc_number = p_nc_number) THEN
        RETURN QUERY SELECT FALSE::BOOLEAN,
            format('La NC %s-%s ya existe.', TRIM(p_nc_serie), p_nc_number)::TEXT, 0; RETURN;
    END IF;

    INSERT INTO invoice_nc (
        invoice_id, nc_serie, nc_number, nc_type, card_code,
        doc_date, doc_currency, doc_total,
        motivo_code, comments,
        user_code, id_estado, fecha_registro
    ) VALUES (
        NULLIF(p_invoice_id, 0),
        TRIM(p_nc_serie), p_nc_number, TRIM(p_nc_type), TRIM(p_card_code),
        p_doc_date, TRIM(p_doc_currency), p_doc_total,
        TRIM(p_motivo_code),
        NULLIF(TRIM(COALESCE(p_comments,'')), ''),
        p_user_code, 1,
        date_trunc('second', NOW() AT TIME ZONE 'America/Lima')
    ) RETURNING invoice_nc.id_nc INTO v_id_nc;

    -- Insertar ítems
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        INSERT INTO invoice_item_nc (
            id_nc, item_code, description, quantity, price_after_vat, tax_code, warehouse_code
        ) VALUES (
            v_id_nc,
            NULLIF(TRIM(COALESCE(v_item->>'item_code','')), ''),
            NULLIF(TRIM(COALESCE(v_item->>'description','')), ''),
            COALESCE((v_item->>'quantity')::NUMERIC, 1),
            COALESCE((v_item->>'price_after_vat')::NUMERIC, 0),
            NULLIF(TRIM(COALESCE(v_item->>'tax_code','')), ''),
            NULLIF(TRIM(COALESCE(v_item->>'warehouse_code','')), '')
        );
    END LOOP;

    -- Actualizar contador en invoce_doc_number
    UPDATE invoce_doc_number d
       SET invoice_number = p_nc_number
      FROM invoice_type t
     WHERE t.invoice_type = d.invoice_type
       AND t.idtype       = p_idtype;

    RETURN QUERY SELECT TRUE::BOOLEAN,
        format('Nota de Crédito %s-%s registrada correctamente.', TRIM(p_nc_serie), p_nc_number)::TEXT,
        v_id_nc;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE::BOOLEAN, SQLERRM::TEXT, 0;
END;
$$ LANGUAGE plpgsql;

-- 8. fn_nc_anular
CREATE OR REPLACE FUNCTION fn_nc_anular(p_id_nc INTEGER)
RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_estado SMALLINT;
BEGIN
    SELECT id_estado INTO v_estado FROM invoice_nc WHERE id_nc = p_id_nc;
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'Nota de crédito no encontrada.'::TEXT; RETURN;
    END IF;
    IF v_estado = 0 THEN
        RETURN QUERY SELECT FALSE::BOOLEAN, 'La nota de crédito ya fue anulada.'::TEXT; RETURN;
    END IF;
    UPDATE invoice_nc SET id_estado = 0 WHERE id_nc = p_id_nc;
    RETURN QUERY SELECT TRUE::BOOLEAN, format('NC #%s anulada correctamente.', p_id_nc)::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 9. Menú: Nota de Crédito bajo Ventas (id_parent=2)
INSERT INTO menu_items (id_parent, label, endpoint, icon, orden, id_estado)
VALUES (2, 'Notas de Crédito', 'main.ventas_notas_credito', 'bi-file-earmark-minus', 5, 1)
ON CONFLICT DO NOTHING;
