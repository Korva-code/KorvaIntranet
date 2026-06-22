from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


@main.route('/punto-venta')
@login_required
def punto_venta():
    grupos = db.session.execute(text("""
        SELECT item_group_code, item_group_name
        FROM   items_group
        WHERE  item_group_name IS NOT NULL
        ORDER  BY item_group_name
    """)).fetchall()

    grupos_list = [
        {'codigo': r[0], 'nombre': (r[1] or '').strip()}
        for r in grupos
        if (r[1] or '').strip()
    ]

    return render_template(
        'main/punto_venta.html',
        title='Punto de Caja',
        section='Punto de Ventas', page='Punto de Caja',
        whs_name=current_user.whs_name,
        grupos=grupos_list,
    )


@main.route('/api/pv/buscar-cliente')
@login_required
def api_pv_buscar_cliente():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'success': False, 'message': 'Ingrese un RUC o DNI.'}), 400

    row = db.session.execute(text("""
        SELECT card_code, card_name, federal_tax_id,
               u_bpp_bptd, u_bpp_bpno, email, phone
        FROM   business_partners
        WHERE  federal_tax_id = :q OR u_bpp_bpno = :q
        LIMIT  1
    """), {'q': q}).fetchone()

    if not row:
        return jsonify({'success': False, 'message': 'Cliente no encontrado.'}), 404

    m = dict(row._mapping)
    return jsonify({
        'success': True,
        'cliente': {
            'card_code': m.get('card_code') or '',
            'card_name': m.get('card_name') or '',
            'ruc':       m.get('federal_tax_id') or '',
            'tipo_doc':  m.get('u_bpp_bptd') or '',
            'num_doc':   m.get('u_bpp_bpno') or '',
            'email':     m.get('email') or '',
            'phone':     m.get('phone') or '',
        }
    })


@main.route('/api/pv/buscar-articulo')
@login_required
def api_pv_buscar_articulo():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'success': False, 'message': 'Ingrese un código.'}), 400

    row = db.session.execute(text("""
        SELECT DISTINCT ON (i.item_code)
               i.item_code, i.item_name, i.itms_grp_nam,
               COALESCE(i."PriceAfterVAT", i.avg_price, 0) AS precio,
               i.sal_unit_msr, i.on_hand
        FROM   items i
        LEFT   JOIN items_barcode ib ON ib.item_code = i.item_code
        WHERE  (i.item_code ILIKE :q OR ib.item_barcode = :exact)
          AND  i.sell_item = 'Y'
          AND  i.valid_for = 'Y'
        LIMIT 1
    """), {'q': f'%{q}%', 'exact': q}).fetchone()

    if not row:
        return jsonify({'success': False, 'message': f'Artículo "{q}" no encontrado.'}), 404

    m = dict(row._mapping)
    return jsonify({
        'success': True,
        'articulo': {
            'item_code': m.get('item_code') or '',
            'item_name': m.get('item_name') or '',
            'grupo':     m.get('itms_grp_nam') or '',
            'precio':    float(m.get('precio') or 0),
            'unidad':    (m.get('sal_unit_msr') or 'UND').strip(),
            'stock':     float(m.get('on_hand') or 0),
        }
    })


@main.route('/api/pv/articulos-grupo/<int:grupo_cod>')
@login_required
def api_pv_articulos_grupo(grupo_cod):
    rows = db.session.execute(text("""
        SELECT i.item_code, i.item_name,
               COALESCE(i."PriceAfterVAT", i.avg_price, 0) AS precio,
               i.sal_unit_msr, i.on_hand
        FROM   items i
        WHERE  i.itms_grp_cod = :cod
          AND  i.sell_item = 'Y'
          AND  i.valid_for = 'Y'
        ORDER  BY i.item_name
        LIMIT  200
    """), {'cod': grupo_cod}).fetchall()

    articulos = [
        {
            'item_code': r[0] or '',
            'item_name': r[1] or '',
            'precio':    float(r[2] or 0),
            'unidad':    (r[3] or 'UND').strip(),
            'stock':     float(r[4] or 0),
        }
        for r in rows
    ]
    return jsonify({'success': True, 'articulos': articulos})
