import json
from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


def _row_to_dict(r):
    m = dict(r._mapping)
    def _dt(v): return v.isoformat() if v else ''
    def _ts(v): return v.isoformat(sep=' ', timespec='seconds') if v else ''
    return {
        'cot_id':         m.get('cot_id'),
        'card_code':      m.get('card_code') or '',
        'bp_name':        m.get('bp_name') or '',
        'doc_date':       _dt(m.get('doc_date')),
        'doc_due_date':   _dt(m.get('doc_due_date')),
        'doc_currency':   m.get('doc_currency') or 'SOL',
        'tipo_cambio':    float(m['tipo_cambio'])   if m.get('tipo_cambio')   is not None else 1.0,
        'doc_total':      float(m['doc_total'])     if m.get('doc_total')     is not None else 0.0,
        'doc_subtotal':   float(m['doc_subtotal'])  if m.get('doc_subtotal')  is not None else 0.0,
        'doc_igv':        float(m['doc_igv'])       if m.get('doc_igv')       is not None else 0.0,
        'invoice_wh':     m.get('invoice_wh') or '',
        'num_at_card':    m.get('num_at_card') or '',
        'comments':       m.get('comments') or '',
        'journal_memo':   m.get('journal_memo') or '',
        'user_code':      m.get('user_code') or '',
        'user_name':      m.get('user_name') or m.get('user_code') or '',
        'id_estado':      m.get('id_estado') if m.get('id_estado') is not None else 1,
        'fecha_registro': _ts(m.get('fecha_registro')),
        'items':          [],
    }


def _item_to_dict(r):
    m = dict(r._mapping)
    return {
        'item_cot_id':    m.get('item_cot_id'),
        'cot_id':         m.get('cot_id'),
        'item_code':      m.get('item_code') or '',
        'item_name':      m.get('item_name') or '',
        'quantity':       float(m['quantity'])       if m.get('quantity')       is not None else 0.0,
        'price_after_vat': float(m['price_after_vat']) if m.get('price_after_vat') is not None else 0.0,
        'tax_code':       m.get('tax_code') or 'I18',
        'warehouse_code': m.get('warehouse_code') or '',
        'subtotal':       float(m['subtotal'])       if m.get('subtotal')       is not None else 0.0,
    }


# ── Listado ────────────────────────────────────────────────────

@main.route('/ventas/cotizaciones')
@login_required
def ventas_cotizaciones():
    cot_rows  = db.session.execute(text("SELECT * FROM sp_cot_listar(0)")).fetchall()
    item_rows = db.session.execute(text("SELECT * FROM sp_cot_items_listar(0)")).fetchall()

    items_by_cot = {}
    for r in item_rows:
        d = _item_to_dict(r)
        items_by_cot.setdefault(d['cot_id'], []).append(d)

    cot_list = []
    for r in cot_rows:
        d = _row_to_dict(r)
        d['items'] = items_by_cot.get(d['cot_id'], [])
        cot_list.append(d)

    usuarios = db.session.execute(text(
        "SELECT id_usuario, nombres FROM w_usuarios ORDER BY nombres"
    )).fetchall()

    return render_template('main/cotizaciones.html',
                           title='Cotizaciones',
                           section='Ventas', page='Cotizaciones',
                           cot_json=json.dumps(cot_list, ensure_ascii=False),
                           total=len(cot_list),
                           usuarios=usuarios,
                           today=date.today().isoformat())


# ── Nueva Cotización (POST desde el drawer) ────────────────────

@main.route('/ventas/cotizaciones/nueva', methods=['POST'])
@login_required
def ventas_cotizaciones_nueva():
    def _parse_date(s):
        try:
            return datetime.strptime(s.strip(), '%Y-%m-%d').date() if s and s.strip() else None
        except ValueError:
            return None

    card_code    = request.form.get('card_code',    '').strip() or None
    doc_date     = _parse_date(request.form.get('doc_date',    ''))
    doc_due_date = _parse_date(request.form.get('doc_due_date', ''))
    doc_currency = request.form.get('doc_currency', 'SOL').strip()
    tc_str       = request.form.get('tipo_cambio',  '1').strip().replace(',', '.')
    try:
        tipo_cambio = float(tc_str) if tc_str else 1.0
    except ValueError:
        tipo_cambio = 1.0
    invoice_wh   = request.form.get('invoice_wh',   '').strip() or None
    num_at_card  = request.form.get('num_at_card',  '').strip() or None
    comments     = request.form.get('comments',     '').strip() or None
    journal_memo = request.form.get('journal_memo', '').strip() or None
    p_user       = request.form.get('invoice_user', '').strip() or current_user.id_usuario
    items_raw    = request.form.get('items_json',   '[]')

    try:
        items_list = json.loads(items_raw)
    except Exception:
        items_list = []

    if not card_code:
        flash('El Cliente es obligatorio.', 'danger')
        return redirect(url_for('main.ventas_cotizaciones'))
    if not items_list:
        flash('Debe agregar al menos un ítem en el detalle.', 'warning')
        return redirect(url_for('main.ventas_cotizaciones'))

    IGV_RATE = 0.18
    doc_total    = sum(float(i.get('price_after_vat', 0)) * float(i.get('quantity', 0)) for i in items_list)
    subtotal_sin = sum(
        float(i.get('price_after_vat', 0)) / (1 + IGV_RATE) * float(i.get('quantity', 0))
        if i.get('tax_code', 'I18') == 'I18'
        else float(i.get('price_after_vat', 0)) * float(i.get('quantity', 0))
        for i in items_list
    )
    doc_igv      = doc_total - subtotal_sin
    doc_subtotal = subtotal_sin

    items_for_db = [{
        'item_code':       i.get('item_code', ''),
        'item_name':       i.get('item_name', ''),
        'quantity':        float(i.get('quantity', 0)),
        'price_after_vat': float(i.get('price_after_vat', 0)),
        'tax_code':        i.get('tax_code', 'I18'),
        'warehouse_code':  i.get('warehouse_code', '') or (invoice_wh or ''),
    } for i in items_list]

    try:
        row = db.session.execute(text("""
            SELECT success, message, cot_id
            FROM fn_cot_guardar(
                :p_card_code,
                CAST(:p_doc_date     AS DATE),
                CAST(:p_doc_due_date AS DATE),
                :p_doc_currency,
                :p_tipo_cambio,
                :p_doc_total,
                :p_doc_subtotal,
                :p_doc_igv,
                :p_invoice_wh,
                :p_num_at_card,
                :p_comments,
                :p_journal_memo,
                :p_user_code,
                CAST(:p_items AS jsonb)
            )
        """), {
            'p_card_code':    card_code,
            'p_doc_date':     doc_date.isoformat() if doc_date else None,
            'p_doc_due_date': doc_due_date.isoformat() if doc_due_date else None,
            'p_doc_currency': doc_currency,
            'p_tipo_cambio':  tipo_cambio,
            'p_doc_total':    round(doc_total, 4),
            'p_doc_subtotal': round(doc_subtotal, 4),
            'p_doc_igv':      round(doc_igv, 4),
            'p_invoice_wh':   invoice_wh or '',
            'p_num_at_card':  num_at_card or '',
            'p_comments':     comments or '',
            'p_journal_memo': journal_memo or '',
            'p_user_code':    str(p_user),
            'p_items':        json.dumps(items_for_db),
        }).fetchone()

        if row and row[0]:
            db.session.commit()
            flash(f'Cotización COT-{row[2]:05d} registrada correctamente.', 'success')
        else:
            db.session.rollback()
            flash(row[1] if row else 'Error al registrar la Cotización.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar: {e}', 'danger')

    return redirect(url_for('main.ventas_cotizaciones'))


# ── Anular Cotización ──────────────────────────────────────────

@main.route('/ventas/cotizaciones/<int:cot_id>/anular', methods=['POST'])
@login_required
def ventas_cotizacion_anular(cot_id):
    try:
        row = db.session.execute(
            text("SELECT success, message FROM fn_cot_anular(:id)"),
            {'id': cot_id}
        ).fetchone()
        if row and row[0]:
            db.session.commit()
            flash(f'COT-{cot_id:05d} anulada correctamente.', 'success')
        else:
            db.session.rollback()
            flash(row[1] if row else 'Error al anular.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('main.ventas_cotizaciones'))


# ── API: ítems para Cotizaciones ───────────────────────────────

@main.route('/api/items-ventas')
@login_required
def api_items_ventas():
    rows = db.session.execute(text("""
        SELECT
            item_code,
            item_name,
            COALESCE("PriceAfterVAT", avg_price, 0)    AS price_after_vat,
            COALESCE(sal_unit_msr, '')                  AS unit_msr,
            COALESCE(tax_code_ar, 'I18')                AS tax_code
        FROM items
        WHERE COALESCE(valid_for, 'Y') = 'Y'
        ORDER BY item_name
    """)).fetchall()
    return jsonify([{
        'item_code':       r[0] or '',
        'item_name':       r[1] or '',
        'price_after_vat': float(r[2]) if r[2] is not None else 0.0,
        'unit_msr':        r[3] or '',
        'tax_code':        r[4] or 'I18',
    } for r in rows])
