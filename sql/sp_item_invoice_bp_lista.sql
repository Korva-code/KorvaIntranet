DROP FUNCTION IF EXISTS public.sp_item_invoice_bp_lista(text);
CREATE OR REPLACE FUNCTION public.sp_item_invoice_bp_lista(p_cardcode text)
  RETURNS TABLE(
    item_code      text,
    item_name      text,
    avg_price      numeric,
    "PriceAfterVAT" numeric,
    tax_code_ap    character,
    sal_unit_msr   character,
    ultimo_costo   numeric
  )
  LANGUAGE plpgsql
AS $func$
BEGIN
  RETURN QUERY
    SELECT
        i.item_code,
        i.item_name,
        CASE
           WHEN COALESCE(desct.avg_price_d, 0) > 0
           THEN desct.avg_price_d
           ELSE i.avg_price
       END AS avg_price,
       CASE
           WHEN COALESCE(desct.priceaftervat_d, 0) > 0
           THEN desct.priceaftervat_d
           ELSE i."PriceAfterVAT"
       END AS "PriceAfterVAT",
        i.tax_code_ap,
        i.sal_unit_msr,
        i.ultimo_costo
    FROM items i
    INNER JOIN items_group ig ON ig.item_group_code = i.itms_grp_cod
    LEFT JOIN business_partners_discount_item desct
    ON desct.item_code = i.item_code
    AND TRIM(desct.federal_tax_id) = p_cardcode
    ORDER BY i.item_name;
END;
$func$;
