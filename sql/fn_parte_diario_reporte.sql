-- ══════════════════════════════════════════════════════════════
-- REPORTE PARTE DIARIO — Funciones de consulta
-- Requiere: invoice.fecha_hora_transaccion (alter_invoice_fecha_hora_transaccion.sql)
-- ══════════════════════════════════════════════════════════════

-- ── 1. Resumen por medio de pago ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_parte_resumen_dia(
    p_user_code    TEXT,
    p_fecha_inicio TIMESTAMP,
    p_fecha_fin    TIMESTAMP
) RETURNS TABLE(
    payment_name  TEXT,
    total_cobrado NUMERIC,
    cant_docs     INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(pm.payment_name, 'Sin Medio')::TEXT    AS payment_name,
        COALESCE(SUM(ic.monto_aplicado), 0)::NUMERIC    AS total_cobrado,
        COUNT(DISTINCT i.invoice_id)::INTEGER            AS cant_docs
    FROM  invoice i
    LEFT  JOIN invoice_cancelaciones ic
           ON  ic.invoice_id = i.invoice_id
           AND ic.id_estado  = 1
    LEFT  JOIN payment pm
           ON  pm.id_payment = ic.id_payment
    WHERE i.user_code::TEXT = p_user_code
      AND i.fecha_hora_transaccion BETWEEN p_fecha_inicio AND p_fecha_fin
    GROUP BY pm.payment_name
    ORDER BY pm.payment_name NULLS LAST;
END;
$$ LANGUAGE plpgsql;


-- ── 2. Detalle de facturas/boletas del turno ──────────────────────────────────
CREATE OR REPLACE FUNCTION fn_parte_facturas_lista(
    p_user_code    TEXT,
    p_fecha_inicio TIMESTAMP,
    p_fecha_fin    TIMESTAMP
) RETURNS TABLE(
    invoice_id    INTEGER,
    tipo_doc      TEXT,
    folio         TEXT,
    nro_doc       TEXT,
    bp_name       TEXT,
    payment_name  TEXT,
    nro_operacion TEXT,
    fecha         DATE,
    doc_total     NUMERIC,
    monto_cobrado NUMERIC,
    doc_currency  TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.invoice_id,
        COALESCE(i.invoice_type::TEXT, '')                                                       AS tipo_doc,
        (COALESCE(i.invoice_serie::TEXT,'') || '-' || COALESCE(i.invoice_number::TEXT,''))::TEXT AS folio,
        COALESCE(bp.federal_tax_id::TEXT, i.card_code::TEXT, '')                                 AS nro_doc,
        COALESCE(bp.card_name, i.card_code, '')::TEXT                                            AS bp_name,
        COALESCE(STRING_AGG(DISTINCT pm.payment_name, ' / '), '—')::TEXT                        AS payment_name,
        COALESCE(STRING_AGG(DISTINCT ic.referencia, ' / ')
                 FILTER (WHERE ic.referencia IS NOT NULL AND ic.referencia <> ''),
                 '')::TEXT                                                                        AS nro_operacion,
        i.doc_date::DATE                                                                          AS fecha,
        COALESCE(i.doc_total, 0)::NUMERIC                                                        AS doc_total,
        COALESCE(SUM(ic.monto_aplicado), 0)::NUMERIC                                            AS monto_cobrado,
        COALESCE(i.doc_currency, '')::TEXT                                                       AS doc_currency
    FROM  invoice i
    LEFT  JOIN business_partners bp ON bp.card_code = i.card_code
    LEFT  JOIN invoice_cancelaciones ic
           ON  ic.invoice_id = i.invoice_id
           AND ic.id_estado  = 1
    LEFT  JOIN payment pm
           ON  pm.id_payment = ic.id_payment
    WHERE i.user_code::TEXT = p_user_code
      AND i.fecha_hora_transaccion BETWEEN p_fecha_inicio AND p_fecha_fin
    GROUP BY i.invoice_id, i.invoice_type, i.invoice_serie, i.invoice_number,
             bp.federal_tax_id, bp.card_name, i.card_code,
             i.doc_date, i.doc_total, i.doc_currency, i.fecha_hora_transaccion
    ORDER BY i.fecha_hora_transaccion, i.invoice_id;
END;
$$ LANGUAGE plpgsql;
