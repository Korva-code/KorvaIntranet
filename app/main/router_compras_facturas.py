import json
from datetime import date
from flask import render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Item


def _row_to_dict_compra(r):
    m = dict(r._mapping)
    return {
        'invoice_id':     m.get('invoice_id'),
        'card_code':      m.get('card_code') or '',
        'bp_name':        m.get('bp_name') or '',
        'id_tipo_compra': m.get('id_tipo_compra'),
        'tipo_nombre':    m.get('tipo_nombre') or '',
        'invoice_type':   m.get('invoice_type') or '',
        'invoice_serie':  m.get('invoice_serie') or '',
        'invoice_number': m.get('invoice_number') or '',
        'doc_date':       m['doc_date'].isoformat() if m.get('doc_date') else '',
        'tax_date':       m['tax_date'].isoformat() if m.get('tax_date') else '',
        'doc_due_date':   m['doc_due_date'].isoformat() if m.get('doc_due_date') else '',
        'doc_currency':   m.get('doc_currency') or 'SOL',
        'doc_total':      float(m['doc_total'])      if m.get('doc_total')      is not None else 0.0,
        'doc_total_aply': float(m['doc_total_aply']) if m.get('doc_total_aply') is not None else 0.0,
        'invoice_wh':     m.get('invoice_wh') or '',
        'num_at_card':    m.get('num_at_card') or '',
        'journal_memo':   m.get('journal_memo') or '',
        'comments':       m.get('comments') or '',
        'user_code':      m.get('user_code') or '',
        'sunat_estado':   m.get('sunat_estado') or '',
        'items':          [],
    }


def _row_to_dict_item(r):
    m = dict(r._mapping)
    return {
        'invoice_id':      m.get('invoice_id'),
        'item_code':       m.get('item_code') or '',
        'item_name':       m.get('item_name') or '',
        'quantity':        float(m['quantity']) if m.get('quantity') is not None else 0.0,
        'price_after_vat': float(m['price_after_vat']) if m.get('price_after_vat') is not None else 0.0,
        'tax_code':        m.get('tax_code') or '',
        'subtotal':        float(m['subtotal']) if m.get('subtotal') is not None else 0.0,
    }


@main.route('/compras/facturas')
@login_required
def compras_facturas():
    rows      = db.session.execute(text("SELECT * FROM sp_compras_listar(0)")).fetchall()
    item_rows = db.session.execute(text("SELECT * FROM sp_compras_items_listar(0)")).fetchall()

    items_by_inv = {}
    for r in item_rows:
        d = _row_to_dict_item(r)
        items_by_inv.setdefault(d['invoice_id'], []).append(d)

    facturas = [_row_to_dict_compra(r) for r in rows]
    for f in facturas:
        f['items'] = items_by_inv.get(f['invoice_id'], [])

    tipos_rows = db.session.execute(text("SELECT * FROM sp_tipos_compra_listar()")).fetchall()
    tipos = [{'id_tipo': dict(r._mapping)['id_tipo'], 'nombre': dict(r._mapping)['nombre']}
             for r in tipos_rows]

    socios_rows = db.session.execute(text("SELECT * FROM business_partners_lista_tipo('1')")).fetchall()
    socios_list = [{'card_code': dict(r._mapping).get('card_code') or '',
                    'card_name': dict(r._mapping).get('card_name') or ''}
                   for r in socios_rows]

    items_cat = Item.query.order_by(Item.item_name).all()
    items_list = [{
        'item_code':    i.item_code or '',
        'item_name':    i.item_name or '',
        'avg_price':    float(i.avg_price)     if i.avg_price     is not None else None,
        'PriceAfterVAT':float(i.PriceAfterVAT) if i.PriceAfterVAT is not None else None,
        'buy_unit_msr': (i.buy_unit_msr or '').strip(),
        'tax_code_ap':  (i.tax_code_ap  or '').strip(),
    } for i in items_cat]

    today = date.today().isoformat()

    inv_type_rows = db.session.execute(text("SELECT * FROM invoice_type_lista(2)")).fetchall()
    inv_types_list = [{'idtype': dict(r._mapping).get('idtype') or '',
                       'invoice_type': dict(r._mapping).get('invoice_type') or ''}
                      for r in inv_type_rows]

    return render_template('main/compras_facturas.html',
                           title='Facturas de Compra',
                           section='Compras', page='Facturas',
                           facturas_json=json.dumps(facturas, ensure_ascii=False),
                           tipos_json=json.dumps(tipos, ensure_ascii=False),
                           socios_json=json.dumps(socios_list, ensure_ascii=False),
                           items_json=json.dumps(items_list, ensure_ascii=False),
                           invoice_types_json=json.dumps(inv_types_list, ensure_ascii=False),
                           total=len(facturas),
                           today=today)


@main.route('/compras/facturas/guardar', methods=['POST'])
@login_required
def compras_facturas_guardar():
    data = request.get_json(force=True)

    invoice_id     = int(data.get('invoice_id') or 0)
    card_code      = data.get('card_code') or None
    try:
        id_tipo = int(data.get('id_tipo_compra') or 0) or None
    except (ValueError, TypeError):
        id_tipo = None
    invoice_type   = data.get('invoice_type') or ''
    invoice_serie  = data.get('invoice_serie') or ''
    invoice_number = data.get('invoice_number') or ''
    doc_date       = data.get('doc_date') or None
    tax_date       = data.get('tax_date') or None
    doc_due_date   = data.get('doc_due_date') or None
    doc_currency   = data.get('doc_currency') or 'SOL'
    doc_total      = float(data.get('doc_total') or 0)
    invoice_wh     = data.get('invoice_wh') or ''
    num_at_card    = data.get('num_at_card') or ''
    journal_memo   = data.get('journal_memo') or ''
    comments       = data.get('comments') or ''
    user_code      = str(current_user.id_usuario)
    items          = data.get('items') or []

    try:
        row = db.session.execute(text("""
            SELECT success, message, invoice_id
            FROM sp_compras_guardar(
                :p_invoice_id, :p_card_code, :p_id_tipo,
                :p_invoice_type, :p_invoice_serie, :p_invoice_number,
                CAST(:p_doc_date AS DATE), CAST(:p_tax_date AS DATE), CAST(:p_doc_due_date AS DATE),
                :p_doc_currency, :p_doc_total,
                :p_invoice_wh, :p_num_at_card, :p_journal_memo, :p_comments,
                :p_user_code, CAST(:p_items AS JSONB)
            )
        """), {
            'p_invoice_id':     invoice_id,
            'p_card_code':      card_code,
            'p_id_tipo':        id_tipo,
            'p_invoice_type':   invoice_type,
            'p_invoice_serie':  invoice_serie,
            'p_invoice_number': invoice_number,
            'p_doc_date':       doc_date,
            'p_tax_date':       tax_date,
            'p_doc_due_date':   doc_due_date,
            'p_doc_currency':   doc_currency,
            'p_doc_total':      doc_total,
            'p_invoice_wh':     invoice_wh,
            'p_num_at_card':    num_at_card,
            'p_journal_memo':   journal_memo,
            'p_comments':       comments,
            'p_user_code':      user_code,
            'p_items':          json.dumps(items),
        }).fetchone()

        if row and row[0]:
            db.session.commit()
            # Registrar movimientos de entrada en el kardex
            try:
                from app.main.router_almacen_kardex import registrar_movimientos_compra
                registrar_movimientos_compra(
                    invoice_id   = row[2],
                    card_code    = card_code,
                    invoice_type = invoice_type,
                    id_tipo      = id_tipo,
                    doc_date     = doc_date,
                    invoice_wh   = invoice_wh,
                    items_list   = items,
                    user_code    = user_code,
                )
                db.session.commit()
            except Exception as e_mov:
                db.session.rollback()
            return jsonify({'success': True, 'message': row[1], 'invoice_id': row[2]})
        else:
            db.session.rollback()
            return jsonify({'success': False, 'message': row[1] if row else 'Error desconocido'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@main.route('/compras/facturas/nueva', methods=['GET', 'POST'])
@login_required
def compras_facturas_nueva():
    return redirect(url_for('main.compras_facturas'))
