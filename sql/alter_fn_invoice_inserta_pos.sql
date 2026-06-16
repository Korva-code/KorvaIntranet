-- ═══════════════════════════════════════════════════════════════
-- Modificación de fn_invoice_inserta_pos
-- Agrega inserción en movimientos_almacen DESPUÉS del UPDATE
-- de invoce_doc_number usando INSERT INTO ... SELECT desde
-- invoice_item filtrando por el nuevo invoice_id (new_id).
-- ═══════════════════════════════════════════════════════════════

-- ── Pegar dentro del cuerpo de fn_invoice_inserta_pos ────────
-- Ubicación exacta: inmediatamente después del bloque:
--
--   UPDATE invoce_doc_number
--      SET invoice_number = siguiente_numero
--    WHERE invoice_type = p_invoice_type
--      AND invoice_wh   = p_invoice_wh
--      AND invoice_pos  = p_invoice_pos;
-- ─────────────────────────────────────────────────────────────

	-- Código existente (referencia de ubicación) ───────────────
	UPDATE invoce_doc_number
	   SET invoice_number = siguiente_numero
	 WHERE invoice_type = p_invoice_type
	   AND invoice_wh   = p_invoice_wh
	   AND invoice_pos  = p_invoice_pos;

	-- ══════════════════════════════════════════════════════════
	--  NUEVO: Movimientos de almacén — salida POS
	-- ══════════════════════════════════════════════════════════
	INSERT INTO movimientos_almacen
	    (invoice_id,
	     card_code,
	     invoice_type,
	     id_tipo,
	     doc_date,
	     item_code,
	     item_name,
	     quantity,
	     avg_price,
	     subtotal,
	     almacen,
	     tipo_movimiento,
	     origen,
	     user_code)
	SELECT
	    ii.invoice_id,
	    p_card_code,
	    p_invoice_type,
	    p_idtype,
	    p_doc_date,
	    ii.item_code,
	    COALESCE(it.item_name, ii.item_code),
	    -ABS(ii.quantity),                                          -- negativo = salida
	    COALESCE(it.avg_price, 0),
	    ROUND(-ABS(ii.quantity) * COALESCE(it.avg_price, 0), 2),
	    COALESCE(NULLIF(TRIM(ii.warehouse_code), ''), p_invoice_wh),
	    'SAL',
	    'POS',
	    p_user
	FROM  invoice_item ii
	LEFT  JOIN items it ON it.item_code = ii.item_code
	WHERE ii.invoice_id = new_id
	  AND COALESCE(ii.quantity, 0) <> 0;
	-- ══════════════════════════════════════════════════════════
