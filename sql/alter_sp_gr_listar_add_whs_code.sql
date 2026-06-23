-- Actualiza sp_gr_listar para retornar el campo whs_code
-- Ejecutar DESPUÉS de alter_invoice_gr_add_whs_code.sql

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
