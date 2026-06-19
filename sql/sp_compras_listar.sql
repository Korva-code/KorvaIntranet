-- SP: sp_compras_listar
-- Listado de facturas de compra con doc_total_aply incluido

DROP FUNCTION IF EXISTS public.sp_compras_listar(integer);

CREATE FUNCTION public.sp_compras_listar(p_invoice_id integer)
  RETURNS TABLE(
    invoice_id      integer,
    card_code       text,
    bp_name         text,
    id_tipo_compra  integer,
    tipo_nombre     text,
    invoice_type    text,
    invoice_serie   text,
    invoice_number  text,
    doc_date        date,
    tax_date        date,
    doc_due_date    date,
    doc_currency    text,
    doc_total       numeric,
    doc_total_aply  numeric,
    invoice_wh      text,
    num_at_card     text,
    journal_memo    text,
    comments        text,
    user_code       text,
    sunat_estado    text
  )
  LANGUAGE plpgsql
AS $function$
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
        COALESCE(i.doc_total_aply, 0),
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
$function$;
