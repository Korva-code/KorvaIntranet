-- ═══════════════════════════════════════════════════════════════
--  Módulo: Ventas > Guías de Remisión (Remitente)
--  Ejecutar UNA sola vez en PostgreSQL.
-- ═══════════════════════════════════════════════════════════════

-- ── Menú ──────────────────────────────────────────────────────
INSERT INTO menu_items (id_parent, label, endpoint, icon, orden)
VALUES (2, 'Guías de Remisión', 'main.invoice_gr_list', 'bi-truck', 10)
ON CONFLICT DO NOTHING;


-- ── Tablas ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS invoice_gr (
    gr_id                    SERIAL        PRIMARY KEY,
    -- Cabecera
    serie                    TEXT,
    numero                   TEXT,
    fecha_emision            DATE,
    hora_emision             TIME,
    modalidad_transporte     TEXT          DEFAULT '02',  -- 01=público 02=privado
    motivo_traslado          TEXT          DEFAULT '01',  -- 01=venta 02=compra ...
    fecha_inicio_traslado    DATE,
    -- Destinatario
    dest_tipo_doc            TEXT          DEFAULT '6',   -- 1=DNI 6=RUC
    dest_num_doc             TEXT,
    dest_denominacion        TEXT,
    dest_direccion           TEXT,
    -- Punto de partida
    partida_ubigeo           TEXT,
    partida_direccion        TEXT,
    -- Punto de llegada
    llegada_ubigeo           TEXT,
    llegada_direccion        TEXT,
    -- Carga
    peso_bruto_total         NUMERIC(18,4),
    peso_bruto_uom           TEXT          DEFAULT 'KGM',
    numero_bultos            INTEGER       DEFAULT 1,
    observaciones            TEXT,
    -- Documento relacionado (factura/boleta de referencia)
    doc_rel_tipo             TEXT,
    doc_rel_serie            TEXT,
    doc_rel_numero           TEXT,
    doc_rel_ruc_emisor       TEXT,
    -- Transportista
    transp_ruc               TEXT,
    transp_denominacion      TEXT,
    transp_num_mtc           TEXT,
    transp_num_autorizacion  TEXT,
    transp_cod_entidad       TEXT,
    -- Conductores y vehículos como JSONB (admiten múltiples)
    conductores              JSONB         DEFAULT '[]',
    vehiculos                JSONB         DEFAULT '[]',
    -- Control
    id_estado                INTEGER       DEFAULT 1,     -- 1=activa 0=anulada
    user_code                TEXT,
    fecha_registro           TIMESTAMP     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoice_gr_item (
    gr_item_id       SERIAL        PRIMARY KEY,
    gr_id            INTEGER       NOT NULL REFERENCES invoice_gr(gr_id) ON DELETE CASCADE,
    codigo_interno   TEXT,
    descripcion      TEXT,
    unidad_medida    TEXT          DEFAULT 'NIU',
    cantidad         NUMERIC(18,4) DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_invoice_gr_item_gr_id ON invoice_gr_item(gr_id);


-- ── sp_gr_listar(p_gr_id)   0 = todas, >0 = una ──────────────

CREATE OR REPLACE FUNCTION sp_gr_listar(p_gr_id INTEGER)
RETURNS TABLE (
    "gr_id"                   INTEGER,
    "serie"                   TEXT,
    "numero"                  TEXT,
    "fecha_emision"           DATE,
    "hora_emision"            TEXT,
    "modalidad_transporte"    TEXT,
    "motivo_traslado"         TEXT,
    "fecha_inicio_traslado"   DATE,
    "dest_tipo_doc"           TEXT,
    "dest_num_doc"            TEXT,
    "dest_denominacion"       TEXT,
    "dest_direccion"          TEXT,
    "whs_code"                TEXT,
    "partida_ubigeo"          TEXT,
    "partida_direccion"       TEXT,
    "llegada_ubigeo"          TEXT,
    "llegada_direccion"       TEXT,
    "peso_bruto_total"        NUMERIC,
    "peso_bruto_uom"          TEXT,
    "numero_bultos"           INTEGER,
    "observaciones"           TEXT,
    "doc_rel_tipo"            TEXT,
    "doc_rel_serie"           TEXT,
    "doc_rel_numero"          TEXT,
    "doc_rel_ruc_emisor"      TEXT,
    "transp_ruc"              TEXT,
    "transp_denominacion"     TEXT,
    "transp_num_mtc"          TEXT,
    "transp_num_autorizacion" TEXT,
    "transp_cod_entidad"      TEXT,
    "conductores"             JSONB,
    "vehiculos"               JSONB,
    "id_estado"               INTEGER,
    "user_code"               TEXT,
    "user_name"               TEXT,
    "fecha_registro"          TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        g.gr_id,
        COALESCE(g.serie, '')                                  ::TEXT,
        COALESCE(g.numero, '')                                 ::TEXT,
        g.fecha_emision,
        TO_CHAR(g.hora_emision, 'HH24:MI:SS')                 ::TEXT,
        COALESCE(g.modalidad_transporte, '02')                 ::TEXT,
        COALESCE(g.motivo_traslado, '01')                      ::TEXT,
        g.fecha_inicio_traslado,
        COALESCE(g.dest_tipo_doc, '6')                         ::TEXT,
        COALESCE(g.dest_num_doc, '')                           ::TEXT,
        COALESCE(g.dest_denominacion, '')                      ::TEXT,
        COALESCE(g.dest_direccion, '')                         ::TEXT,
        COALESCE(g.whs_code, '')                               ::TEXT,
        COALESCE(g.partida_ubigeo, '')                         ::TEXT,
        COALESCE(g.partida_direccion, '')                      ::TEXT,
        COALESCE(g.llegada_ubigeo, '')                         ::TEXT,
        COALESCE(g.llegada_direccion, '')                      ::TEXT,
        COALESCE(g.peso_bruto_total, 0),
        COALESCE(g.peso_bruto_uom, 'KGM')                     ::TEXT,
        COALESCE(g.numero_bultos, 1),
        COALESCE(g.observaciones, '')                          ::TEXT,
        COALESCE(g.doc_rel_tipo, '')                           ::TEXT,
        COALESCE(g.doc_rel_serie, '')                          ::TEXT,
        COALESCE(g.doc_rel_numero, '')                         ::TEXT,
        COALESCE(g.doc_rel_ruc_emisor, '')                     ::TEXT,
        COALESCE(g.transp_ruc, '')                             ::TEXT,
        COALESCE(g.transp_denominacion, '')                    ::TEXT,
        COALESCE(g.transp_num_mtc, '')                         ::TEXT,
        COALESCE(g.transp_num_autorizacion, '')                ::TEXT,
        COALESCE(g.transp_cod_entidad, '')                     ::TEXT,
        COALESCE(g.conductores, '[]'::JSONB),
        COALESCE(g.vehiculos,   '[]'::JSONB),
        COALESCE(g.id_estado, 1),
        COALESCE(g.user_code, '')                              ::TEXT,
        COALESCE(u.nombres, g.user_code, '')                   ::TEXT  AS user_name,
        g.fecha_registro
    FROM   invoice_gr g
    LEFT   JOIN w_usuarios u ON u.id_usuario = g.user_code
    WHERE  (p_gr_id = 0 OR g.gr_id = p_gr_id)
    ORDER  BY g.gr_id DESC;
END;
$$ LANGUAGE plpgsql;


-- ── sp_gr_items_listar(p_gr_id)  0 = todos ───────────────────

CREATE OR REPLACE FUNCTION sp_gr_items_listar(p_gr_id INTEGER)
RETURNS TABLE (
    "gr_item_id"     INTEGER,
    "gr_id"          INTEGER,
    "codigo_interno" TEXT,
    "descripcion"    TEXT,
    "unidad_medida"  TEXT,
    "cantidad"       NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.gr_item_id,
        i.gr_id,
        COALESCE(i.codigo_interno, '')  ::TEXT,
        COALESCE(i.descripcion, '')     ::TEXT,
        COALESCE(i.unidad_medida, 'NIU')::TEXT,
        COALESCE(i.cantidad, 1)
    FROM   invoice_gr_item i
    WHERE  (p_gr_id = 0 OR i.gr_id = p_gr_id)
    ORDER  BY i.gr_item_id;
END;
$$ LANGUAGE plpgsql;


-- ── sp_gr_guardar(...)  INSERT o UPDATE + items ───────────────

CREATE OR REPLACE FUNCTION sp_gr_guardar(
    p_gr_id                   INTEGER,
    p_serie                   TEXT,
    p_numero                  TEXT,
    p_fecha_emision           DATE,
    p_hora_emision            TEXT,
    p_modalidad_transporte    TEXT,
    p_motivo_traslado         TEXT,
    p_fecha_inicio_traslado   DATE,
    p_dest_tipo_doc           TEXT,
    p_dest_num_doc            TEXT,
    p_dest_denominacion       TEXT,
    p_dest_direccion          TEXT,
    p_partida_ubigeo          TEXT,
    p_partida_direccion       TEXT,
    p_llegada_ubigeo          TEXT,
    p_llegada_direccion       TEXT,
    p_peso_bruto_total        NUMERIC,
    p_peso_bruto_uom          TEXT,
    p_numero_bultos           INTEGER,
    p_observaciones           TEXT,
    p_doc_rel_tipo            TEXT,
    p_doc_rel_serie           TEXT,
    p_doc_rel_numero          TEXT,
    p_doc_rel_ruc_emisor      TEXT,
    p_transp_ruc              TEXT,
    p_transp_denominacion     TEXT,
    p_transp_num_mtc          TEXT,
    p_transp_num_autorizacion TEXT,
    p_transp_cod_entidad      TEXT,
    p_conductores             JSONB,
    p_vehiculos               JSONB,
    p_user_code               TEXT,
    p_items_json              JSONB
) RETURNS INTEGER AS $$
DECLARE
    v_gr_id INTEGER;
    v_item  JSONB;
    v_hora  TIME;
BEGIN
    v_hora := CASE WHEN p_hora_emision IS NOT NULL AND p_hora_emision <> ''
                   THEN p_hora_emision::TIME ELSE NULL END;

    IF p_gr_id IS NULL OR p_gr_id = 0 THEN
        INSERT INTO invoice_gr (
            serie, numero, fecha_emision, hora_emision,
            modalidad_transporte, motivo_traslado, fecha_inicio_traslado,
            dest_tipo_doc, dest_num_doc, dest_denominacion, dest_direccion,
            partida_ubigeo, partida_direccion,
            llegada_ubigeo, llegada_direccion,
            peso_bruto_total, peso_bruto_uom, numero_bultos, observaciones,
            doc_rel_tipo, doc_rel_serie, doc_rel_numero, doc_rel_ruc_emisor,
            transp_ruc, transp_denominacion, transp_num_mtc,
            transp_num_autorizacion, transp_cod_entidad,
            conductores, vehiculos, user_code
        ) VALUES (
            p_serie, p_numero, p_fecha_emision, v_hora,
            p_modalidad_transporte, p_motivo_traslado, p_fecha_inicio_traslado,
            p_dest_tipo_doc, p_dest_num_doc, p_dest_denominacion, p_dest_direccion,
            p_partida_ubigeo, p_partida_direccion,
            p_llegada_ubigeo, p_llegada_direccion,
            p_peso_bruto_total, COALESCE(p_peso_bruto_uom, 'KGM'),
            COALESCE(p_numero_bultos, 1), p_observaciones,
            p_doc_rel_tipo, p_doc_rel_serie, p_doc_rel_numero, p_doc_rel_ruc_emisor,
            p_transp_ruc, p_transp_denominacion, p_transp_num_mtc,
            p_transp_num_autorizacion, p_transp_cod_entidad,
            COALESCE(p_conductores, '[]'), COALESCE(p_vehiculos, '[]'),
            p_user_code
        ) RETURNING gr_id INTO v_gr_id;
    ELSE
        UPDATE invoice_gr SET
            serie                   = p_serie,
            numero                  = p_numero,
            fecha_emision           = p_fecha_emision,
            hora_emision            = v_hora,
            modalidad_transporte    = p_modalidad_transporte,
            motivo_traslado         = p_motivo_traslado,
            fecha_inicio_traslado   = p_fecha_inicio_traslado,
            dest_tipo_doc           = p_dest_tipo_doc,
            dest_num_doc            = p_dest_num_doc,
            dest_denominacion       = p_dest_denominacion,
            dest_direccion          = p_dest_direccion,
            partida_ubigeo          = p_partida_ubigeo,
            partida_direccion       = p_partida_direccion,
            llegada_ubigeo          = p_llegada_ubigeo,
            llegada_direccion       = p_llegada_direccion,
            peso_bruto_total        = p_peso_bruto_total,
            peso_bruto_uom          = COALESCE(p_peso_bruto_uom, 'KGM'),
            numero_bultos           = COALESCE(p_numero_bultos, 1),
            observaciones           = p_observaciones,
            doc_rel_tipo            = p_doc_rel_tipo,
            doc_rel_serie           = p_doc_rel_serie,
            doc_rel_numero          = p_doc_rel_numero,
            doc_rel_ruc_emisor      = p_doc_rel_ruc_emisor,
            transp_ruc              = p_transp_ruc,
            transp_denominacion     = p_transp_denominacion,
            transp_num_mtc          = p_transp_num_mtc,
            transp_num_autorizacion = p_transp_num_autorizacion,
            transp_cod_entidad      = p_transp_cod_entidad,
            conductores             = COALESCE(p_conductores, '[]'),
            vehiculos               = COALESCE(p_vehiculos,   '[]'),
            user_code               = p_user_code
        WHERE gr_id = p_gr_id;
        v_gr_id := p_gr_id;
        DELETE FROM invoice_gr_item WHERE gr_id = v_gr_id;
    END IF;

    FOR v_item IN SELECT * FROM jsonb_array_elements(COALESCE(p_items_json, '[]'))
    LOOP
        INSERT INTO invoice_gr_item (gr_id, codigo_interno, descripcion, unidad_medida, cantidad)
        VALUES (
            v_gr_id,
            NULLIF(TRIM(v_item->>'codigo_interno'), ''),
            NULLIF(TRIM(v_item->>'descripcion'), ''),
            COALESCE(NULLIF(TRIM(v_item->>'unidad_medida'), ''), 'NIU'),
            COALESCE((v_item->>'cantidad')::NUMERIC, 1)
        );
    END LOOP;

    RETURN v_gr_id;
END;
$$ LANGUAGE plpgsql;


-- ── sp_gr_anular(p_gr_id) ────────────────────────────────────

CREATE OR REPLACE FUNCTION sp_gr_anular(p_gr_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE invoice_gr SET id_estado = 0 WHERE gr_id = p_gr_id;
END;
$$ LANGUAGE plpgsql;
