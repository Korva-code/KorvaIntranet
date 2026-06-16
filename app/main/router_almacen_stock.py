import json
from flask import render_template, request
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'item_code':   m.get('item_code')  or '',
        'item_name':   m.get('item_name')  or '',
        'almacen':     m.get('almacen')    or '',
        'whs_name':    m.get('whs_name')   or '',
        'stock':       float(m['stock'])       if m.get('stock')       is not None else 0.0,
        'avg_price':   float(m['avg_price'])   if m.get('avg_price')   is not None else 0.0,
        'valor_total': float(m['valor_total']) if m.get('valor_total') is not None else 0.0,
    }


@main.route('/almacen/stock')
@login_required
def almacen_stock():
    almacen = request.args.get('almacen', '').strip()

    rows  = db.session.execute(
        text("SELECT * FROM sp_stock_listar(:p)"),
        {'p': almacen or None}
    ).fetchall()
    stock_list = [_row_to_dict(r) for r in rows]

    whs_rows = db.session.execute(
        text("SELECT DISTINCT TRIM(whs_code) AS whs_code, whs_name FROM warehouses ORDER BY whs_name")
    ).fetchall()
    almacenes = [{'whs_code': dict(r._mapping).get('whs_code') or '',
                  'whs_name': dict(r._mapping).get('whs_name') or ''}
                 for r in whs_rows]

    return render_template('main/almacen_stock.html',
                           title='Stock por Almacén',
                           section='Almacén', page='Stock',
                           stock_json=json.dumps(stock_list, ensure_ascii=False),
                           almacenes_json=json.dumps(almacenes, ensure_ascii=False),
                           almacenes=almacenes,
                           selected_almacen=almacen,
                           total=len(stock_list))
