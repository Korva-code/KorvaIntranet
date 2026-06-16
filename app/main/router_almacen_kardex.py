import json
from flask import render_template, request
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Item


# ── Helper: registrar movimientos de salida tras guardar una venta ──────────

def registrar_movimientos_venta(invoice_id, card_code, invoice_type,
                                id_tipo, doc_date, invoice_wh,
                                items_list, user_code):
    """Inserta una fila en movimientos_almacen por cada ítem de la venta.
    La cantidad se guarda en negativo (salida). No hace commit; el caller lo hace.
    """
    if not items_list:
        return

    item_codes = [i.get('item_code', '') or i.get('ItemCode', '')
                  for i in items_list]
    item_codes = [c for c in item_codes if c]
    items_map = {}
    if item_codes:
        for obj in Item.query.filter(Item.item_code.in_(item_codes)).all():
            items_map[obj.item_code] = obj

    for it in items_list:
        item_code = (it.get('item_code') or it.get('ItemCode') or '').strip()
        if not item_code:
            continue
        qty = float(it.get('quantity') or it.get('Quantity') or 0)
        if qty == 0:
            continue

        obj = items_map.get(item_code)
        if obj and (obj.invnt_item or 'N').strip().upper() != 'Y':
            continue

        avg_price = float(obj.avg_price) if obj and obj.avg_price is not None else 0.0
        item_name = (obj.item_name or item_code) if obj else item_code

        wh = (it.get('warehouse_code') or it.get('WarehouseCode') or invoice_wh or '').strip()
        qty_mov  = -abs(qty)
        subtotal = round(qty_mov * avg_price, 2)

        db.session.execute(text("""
            INSERT INTO movimientos_almacen
                (invoice_id, card_code, invoice_type, id_tipo, doc_date,
                 item_code, item_name, quantity, avg_price, subtotal,
                 almacen, tipo_movimiento, origen, user_code)
            VALUES
                (:inv_id, :card, :inv_type, :id_tipo, CAST(:doc_date AS DATE),
                 :item_code, :item_name, :qty, :avg_price, :subtotal,
                 :almacen, 'SAL', 'VENTA', :user_code)
        """), {
            'inv_id':    invoice_id,
            'card':      card_code,
            'inv_type':  invoice_type,
            'id_tipo':   id_tipo,
            'doc_date':  doc_date,
            'item_code': item_code,
            'item_name': item_name,
            'qty':       qty_mov,
            'avg_price': avg_price,
            'subtotal':  subtotal,
            'almacen':   wh,
            'user_code': str(user_code),
        })


# ── Helper: registrar movimientos de entrada tras guardar una compra ─────────

def registrar_movimientos_compra(invoice_id, card_code, invoice_type,
                                 id_tipo, doc_date, invoice_wh,
                                 items_list, user_code):
    """Inserta una fila en movimientos_almacen por cada ítem de la compra.
    La cantidad es positiva (entrada). Si es actualización borra primero los
    movimientos anteriores de ese invoice. No hace commit; el caller lo hace.
    """
    if not items_list:
        return

    # Construir mapa item_code → item_name consultando la tabla items
    item_codes = [it.get('item_code', '').strip() for it in items_list if it.get('item_code')]
    items_map  = {}
    if item_codes:
        for obj in Item.query.filter(Item.item_code.in_(item_codes)).all():
            items_map[obj.item_code] = obj

    # Si ya existían movimientos para esta factura (UPDATE), los elimina
    db.session.execute(text(
        "DELETE FROM movimientos_almacen WHERE invoice_id = :inv_id AND tipo_movimiento = 'ENT'"
    ), {'inv_id': invoice_id})

    for it in items_list:
        item_code = (it.get('item_code') or '').strip()
        if not item_code:
            continue
        qty = float(it.get('quantity') or 0)
        if qty == 0:
            continue

        # Precio sin IGV desde el precio con IGV de la factura de compra
        price_with_vat = float(it.get('price_after_vat') or 0)
        avg_price      = round(price_with_vat / 1.18, 4)

        obj       = items_map.get(item_code)
        item_name = (obj.item_name or item_code) if obj else item_code
        qty_mov   = abs(qty)
        subtotal  = round(qty_mov * avg_price, 2)

        db.session.execute(text("""
            INSERT INTO movimientos_almacen
                (invoice_id, card_code, invoice_type, id_tipo, doc_date,
                 item_code, item_name, quantity, avg_price, subtotal,
                 almacen, tipo_movimiento, origen, user_code)
            VALUES
                (:inv_id, :card, :inv_type, :id_tipo, CAST(:doc_date AS DATE),
                 :item_code, :item_name, :qty, :avg_price, :subtotal,
                 :almacen, 'ENT', 'COMPRA', :user_code)
        """), {
            'inv_id':    invoice_id,
            'card':      card_code,
            'inv_type':  invoice_type,
            'id_tipo':   id_tipo,
            'doc_date':  doc_date,
            'item_code': item_code,
            'item_name': item_name,
            'qty':       qty_mov,
            'avg_price': avg_price,
            'subtotal':  subtotal,
            'almacen':   (invoice_wh or '').strip(),
            'user_code': str(user_code),
        })


# ── Helper: sincronizar movimientos SAL al editar una venta ─────────────────

def sincronizar_movimientos_venta(invoice_id, card_code, invoice_type,
                                   id_tipo, doc_date, invoice_wh,
                                   items_list, user_code):
    """Elimina todos los movimientos SAL del invoice y los re-inserta
    desde items_list. Ítems eliminados del detalle quedan sin movimiento.
    No hace commit; el caller lo hace.
    """
    db.session.execute(text(
        "DELETE FROM movimientos_almacen "
        "WHERE invoice_id = :inv_id AND tipo_movimiento = 'SAL'"
    ), {'inv_id': invoice_id})

    registrar_movimientos_venta(
        invoice_id   = invoice_id,
        card_code    = card_code,
        invoice_type = invoice_type,
        id_tipo      = id_tipo,
        doc_date     = doc_date,
        invoice_wh   = invoice_wh,
        items_list   = items_list,
        user_code    = user_code,
    )


# ── Vista: Kardex valorizado ────────────────────────────────────────────────

def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id':              m.get('id'),
        'doc_date':        m['doc_date'].isoformat() if m.get('doc_date') else '',
        'invoice_id':      m.get('invoice_id'),
        'invoice_type':    m.get('invoice_type') or '',
        'card_code':       m.get('card_code') or '',
        'bp_name':         m.get('bp_name') or '',
        'item_code':       m.get('item_code') or '',
        'item_name':       m.get('item_name') or '',
        'almacen':         m.get('almacen') or '',
        'almacen_nombre':  m.get('almacen_nombre') or '',
        'origen':          m.get('origen') or '',
        'tipo_movimiento': m.get('tipo_movimiento') or 'SAL',
        'quantity':        float(m['quantity'])   if m.get('quantity')   is not None else 0.0,
        'avg_price':       float(m['avg_price'])  if m.get('avg_price')  is not None else 0.0,
        'subtotal':        float(m['subtotal'])   if m.get('subtotal')   is not None else 0.0,
        'stock_acum':      float(m['stock_acum']) if m.get('stock_acum') is not None else 0.0,
    }


@main.route('/almacen/kardex')
@login_required
def almacen_kardex():
    item_code = request.args.get('item_code', '').strip()
    almacen   = request.args.get('almacen',   '').strip()

    rows = db.session.execute(text(
        "SELECT * FROM sp_kardex_listar(:p_item, :p_alm)"
    ), {'p_item': item_code, 'p_alm': almacen}).fetchall()

    movimientos = [_row_to_dict(r) for r in rows]

    items_cat = Item.query.order_by(Item.item_name).all()
    items_list = [{'item_code': i.item_code or '', 'item_name': i.item_name or ''}
                  for i in items_cat]

    wh_rows = db.session.execute(text("SELECT * FROM warehouses_lista('')")).fetchall()
    warehouses = [{'whs_code': r[0] or '', 'whs_name': r[1] or ''} for r in wh_rows]

    return render_template('main/almacen_kardex.html',
                           title='Kardex Valorizado',
                           section='Almacén', page='Kardex Valorizado',
                           movimientos_json=json.dumps(movimientos, ensure_ascii=False),
                           items_json=json.dumps(items_list, ensure_ascii=False),
                           warehouses_json=json.dumps(warehouses, ensure_ascii=False),
                           selected_item=item_code,
                           selected_almacen=almacen,
                           total=len(movimientos))
