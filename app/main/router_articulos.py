import json
from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Item, ItemGroup


def _parse_date(val: str):
    if not val:
        return None
    try:
        return datetime.strptime(val, '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_num(val: str):
    if val is None or val == '':
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _apply_item_fields(item: Item, form) -> None:
    item.item_name    = form.get('item_name', '').strip() or None
    item.frgn_name    = form.get('frgn_name', '').strip() or None
    grp = form.get('itms_grp_cod', '')
    item.itms_grp_cod = int(grp) if grp else None
    if item.itms_grp_cod:
        g = db.session.get(ItemGroup, item.itms_grp_cod)
        item.itms_grp_nam = g.nombre if g else None
    else:
        item.itms_grp_nam = None

    item.invnt_item   = 'Y' if form.get('invnt_item') else 'N'
    item.sell_item    = 'Y' if form.get('sell_item')  else 'N'
    item.prchse_item  = 'Y' if form.get('prchse_item') else 'N'
    item.valid_for    = 'Y' if form.get('valid_for')  else 'N'
    item.frozen_for   = 'Y' if form.get('frozen_for') else 'N'

    tb = form.get('TipoBien', '').strip()
    item.TipoBien      = int(tb) if tb else None
    item.avg_price     = _parse_num(form.get('avg_price'))
    item.PriceAfterVAT = _parse_num(form.get('PriceAfterVAT'))
    item.on_hand       = 0
    item.is_commited   = 0
    item.on_order      = 0

    item.sal_unit_msr = form.get('sal_unit_msr', '').strip() or None
    item.buy_unit_msr = form.get('buy_unit_msr', '').strip() or None
    item.tax_code_ar  = form.get('tax_code_ar', '').strip() or None
    item.tax_code_ap  = form.get('tax_code_ap', '').strip() or None
    item.create_date  = _parse_date(form.get('create_date'))
    item.update_date  = _parse_date(form.get('update_date')) or date.today()


def _save_barcodes(item_code: str, barcodes_json: str) -> None:
    try:
        barcodes = json.loads(barcodes_json) if barcodes_json else []
    except (ValueError, TypeError):
        barcodes = []
    db.session.execute(text(
        "DELETE FROM items_barcode WHERE item_code = :code"
    ), {'code': item_code})
    for b in barcodes:
        val = (b.get('item_barcode') or '').strip()
        if not val:
            continue
        db.session.execute(text(
            "INSERT INTO items_barcode (item_code, item_barcode) VALUES (:code, :bc)"
        ), {'code': item_code, 'bc': val})


@main.route('/maestras/articulos')
@login_required
def articulos():
    items  = Item.query.order_by(Item.item_code).all()
    grupos = ItemGroup.query.order_by(ItemGroup.item_group_name).all()
    items_json = json.dumps([i.as_dict() for i in items], ensure_ascii=False)
    return render_template('main/articulos.html', title='Artículos',
                           section='Maestras', page='Artículos',
                           items=items, grupos=grupos, items_json=items_json)


@main.route('/maestras/articulos/nuevo', methods=['POST'])
@login_required
def articulo_nuevo():
    item_code = request.form.get('item_code', '').strip()
    if not item_code:
        flash('El código del artículo es obligatorio.', 'danger')
        return redirect(url_for('main.articulos'))

    if db.session.get(Item, item_code):
        flash(f'Ya existe un artículo con el código «{item_code}».', 'warning')
        return redirect(url_for('main.articulos'))

    item = Item(item_code=item_code, create_date=date.today(), update_date=date.today())
    _apply_item_fields(item, request.form)
    db.session.add(item)
    db.session.flush()
    _save_barcodes(item_code, request.form.get('barcodes_json', ''))
    db.session.commit()
    flash(f'Artículo «{item_code}» registrado correctamente.', 'success')
    return redirect(url_for('main.articulos'))


@main.route('/maestras/articulos/<path:item_code>/editar', methods=['POST'])
@login_required
def articulo_editar(item_code):
    item = db.session.get(Item, item_code)
    if not item:
        flash(f'Artículo «{item_code}» no encontrado.', 'danger')
        return redirect(url_for('main.articulos'))

    _apply_item_fields(item, request.form)
    _save_barcodes(item_code, request.form.get('barcodes_json', ''))
    db.session.commit()
    flash(f'Artículo «{item_code}» actualizado correctamente.', 'success')
    return redirect(url_for('main.articulos'))


@main.route('/api/articulos/<path:item_code>/barcodes')
@login_required
def api_articulo_barcodes(item_code):
    rows = db.session.execute(text(
        "SELECT item_barcode FROM items_barcode WHERE item_code = :code ORDER BY item_barcode"
    ), {'code': item_code}).fetchall()
    return jsonify([{'item_barcode': r[0] or ''} for r in rows])


@main.route('/api/unidad-medida')
@login_required
def api_unidad_medida():
    rows = db.session.execute(text(
        "SELECT codigo, descripcion FROM unidad_medida ORDER BY codigo"
    )).fetchall()
    return jsonify([{'codigo': r[0], 'descripcion': r[1]} for r in rows])


@main.route('/api/items-lista')
@login_required
def api_items_lista():
    rows = db.session.execute(text(
        "SELECT item_code, item_name FROM items ORDER BY item_name"
    )).fetchall()
    return jsonify([{'item_code': r[0] or '', 'item_name': r[1] or ''} for r in rows])


@main.route('/api/items-con-precio')
@login_required
def api_items_con_precio():
    card_code = (request.args.get('card_code') or '').strip()
    rows = db.session.execute(text(
        "SELECT * FROM sp_item_invoice_bp_lista(:card_code)"
    ), {'card_code': card_code}).fetchall()
    return jsonify([{
        'item_code':    r[0] or '',
        'item_name':    r[1] or '',
        'avg_price':    float(r[2]) if r[2] is not None else 0.0,
        'PriceAfterVAT': float(r[3]) if r[3] is not None else 0.0,
        'tax_code_ap':  r[4] or '',
        'sal_unit_msr': r[5] or '',
    } for r in rows])
