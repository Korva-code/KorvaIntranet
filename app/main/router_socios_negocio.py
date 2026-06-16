import json
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import BusinessPartner


def _parse_date(val: str):
    if not val:
        return None
    try:
        return datetime.strptime(val, '%Y-%m-%d').date()
    except ValueError:
        return None


def _apply_bp_fields(bp, form) -> None:
    bp.card_name      = form.get('card_name', '').strip() or None
    bp.card_type      = form.get('card_type', '').strip() or None
    bp.group_code     = form.get('group_code', '').strip() or None
    bp.federal_tax_id = form.get('federal_tax_id', '').strip() or None
    bp.currency       = form.get('currency', '').strip() or None
    bp.u_bpp_bptd     = form.get('u_bpp_bptd', '').strip() or None
    bp.u_bpp_bpno     = form.get('u_bpp_bpno', '').strip() or None
    bp.u_bpp_bpap     = form.get('u_bpp_bpap', '').strip() or None
    bp.u_bpp_bptp     = form.get('u_bpp_bptp', '').strip() or None
    bp.u_validc       = 'Y' if form.get('u_validc')    else 'N'
    bp.u_vs_afprcp    = 'Y' if form.get('u_vs_afprcp') else 'N'
    bp.u_cl_estmig    = form.get('u_cl_estmig', '').strip() or None
    bp.u_cl_resmig    = form.get('u_cl_resmig', '').strip() or None
    bp.u_cl_fecmig    = _parse_date(form.get('u_cl_fecmig'))
    bp.email          = form.get('email', '').strip() or None
    bp.phone          = form.get('phone', '').strip() or None
    bp.IsCredit       = int(form['IsCredit'])  if form.get('IsCredit')  else None
    bp.Creditday      = int(form['Creditday']) if form.get('Creditday') else None


def _save_addresses(card_code, addresses_json):
    try:
        addresses = json.loads(addresses_json) if addresses_json else []
    except (ValueError, TypeError):
        addresses = []
    db.session.execute(text(
        "DELETE FROM business_partners_addresses WHERE bp_code = :code"
    ), {'code': card_code})
    for a in addresses:
        if not any([a.get('address_name'), a.get('street'), a.get('city')]):
            continue
        db.session.execute(text("""
            INSERT INTO business_partners_addresses (bp_code, address_name, street, street_no, city, country)
            VALUES (:code, :name, :street, :street_no, :city, :country)
        """), {
            'code':      card_code,
            'name':      (a.get('address_name') or '').strip(),
            'street':    (a.get('street')        or '').strip(),
            'street_no': (a.get('street_no')     or '').strip(),
            'city':      (a.get('city')          or '').strip(),
            'country':   (a.get('country')       or '').strip(),
        })


def _save_descuentos(federal_tax_id, descuentos_json):
    try:
        descuentos = json.loads(descuentos_json) if descuentos_json else []
    except (ValueError, TypeError):
        descuentos = []
    ruc = (federal_tax_id or '').strip()
    if not ruc:
        return
    db.session.execute(text(
        "DELETE FROM business_partners_discount_item WHERE federal_tax_id = :ruc"
    ), {'ruc': ruc})
    for d in descuentos:
        if not d.get('item_code'):
            continue
        db.session.execute(text("""
            INSERT INTO business_partners_discount_item (federal_tax_id, item_code, descuento, status)
            VALUES (:ruc, :item_code, :descuento, 1)
        """), {
            'ruc':       ruc,
            'item_code': (d.get('item_code') or '').strip(),
            'descuento': d.get('descuento') or 0,
        })


@main.route('/maestras/socios')
@login_required
def socios_negocio():
    rows = db.session.execute(text("""
        SELECT
            bp.card_code,
            bp.card_name,
            bp.card_type,
            COALESCE(at2.nm_tipo_anexo, bp.card_type, '')  AS tipo_nombre,
            bp.group_code,
            COALESCE(bpg.group_name,   bp.group_code, '')  AS group_name,
            bp.federal_tax_id,
            bp.email,
            bp.phone,
            bp.u_validc,
            bp."IsCredit",
            bp."Creditday",
            bp.currency,
            bp.u_bpp_bptd,
            bp.u_bpp_bpno,
            bp.u_bpp_bpap,
            bp.u_bpp_bptp,
            bp.u_vs_afprcp,
            bp.u_cl_estmig,
            bp.u_cl_resmig,
            bp.u_cl_fecmig
        FROM business_partners bp
        LEFT JOIN anexo_tipo at2  ON at2.id_tipo_anexo        = bp.card_type
        LEFT JOIN business_partners_group bpg ON TRIM(bpg.group_code) = TRIM(bp.group_code)
        ORDER BY bp.card_code
    """)).fetchall()

    tipos  = db.session.execute(text(
        "SELECT TRIM(id_tipo_anexo) AS id_tipo_anexo, nm_tipo_anexo FROM anexo_tipo ORDER BY nm_tipo_anexo"
    )).fetchall()
    grupos = db.session.execute(text(
        "SELECT TRIM(group_code) AS group_code, group_name FROM business_partners_group ORDER BY group_name"
    )).fetchall()

    socios_list = [{
        'card_code':      r[0]  or '',
        'card_name':      r[1]  or '',
        'card_type':      (r[2]  or '').strip(),
        'tipo_nombre':    r[3]  or '',
        'group_code':     (r[4]  or '').strip(),
        'group_name':     r[5]  or '',
        'federal_tax_id': r[6]  or '',
        'email':          r[7]  or '',
        'phone':          r[8]  or '',
        'u_validc':       (r[9]  or '').strip(),
        'IsCredit':       r[10],
        'Creditday':      r[11],
        'currency':       r[12] or '',
        'u_bpp_bptd':     r[13] or '',
        'u_bpp_bpno':     r[14] or '',
        'u_bpp_bpap':     r[15] or '',
        'u_bpp_bptp':     r[16] or '',
        'u_vs_afprcp':    (r[17] or '').strip(),
        'u_cl_estmig':    (r[18] or '').strip(),
        'u_cl_resmig':    r[19] or '',
        'u_cl_fecmig':    r[20].isoformat() if r[20] else '',
    } for r in rows]

    socios_json = json.dumps(socios_list, ensure_ascii=False)
    return render_template('main/socios_negocio.html', title='Socios de Negocio',
                           section='Maestras', page='Socios de Negocio',
                           socios=rows, socios_json=socios_json,
                           tipos=tipos, grupos=grupos)


@main.route('/maestras/socios/nuevo', methods=['POST'])
@login_required
def socio_nuevo():
    card_code = request.form.get('card_code', '').strip()
    if not card_code:
        flash('El código del socio es obligatorio.', 'danger')
        return redirect(url_for('main.socios_negocio'))
    if db.session.get(BusinessPartner, card_code):
        flash(f'Ya existe un socio con el código «{card_code}».', 'warning')
        return redirect(url_for('main.socios_negocio'))
    bp = BusinessPartner(card_code=card_code)
    _apply_bp_fields(bp, request.form)
    db.session.add(bp)
    db.session.flush()
    _save_addresses(card_code, request.form.get('addresses_json', ''))
    _save_descuentos(bp.federal_tax_id or '', request.form.get('descuentos_json', ''))
    db.session.commit()
    flash(f'Socio «{card_code}» registrado correctamente.', 'success')
    return redirect(url_for('main.socios_negocio'))


@main.route('/maestras/socios/<path:card_code>/editar', methods=['POST'])
@login_required
def socio_editar(card_code):
    bp = db.session.get(BusinessPartner, card_code)
    if not bp:
        flash(f'Socio «{card_code}» no encontrado.', 'danger')
        return redirect(url_for('main.socios_negocio'))
    _apply_bp_fields(bp, request.form)
    _save_addresses(card_code, request.form.get('addresses_json', ''))
    _save_descuentos(bp.federal_tax_id or '', request.form.get('descuentos_json', ''))
    db.session.commit()
    flash(f'Socio «{card_code}» actualizado correctamente.', 'success')
    return redirect(url_for('main.socios_negocio'))


@main.route('/api/socios/<path:card_code>/direcciones')
@login_required
def api_socio_direcciones(card_code):
    rows = db.session.execute(text("""
        SELECT address_name, street, street_no, city, country
        FROM business_partners_addresses
        WHERE bp_code = :code
        ORDER BY address_name
    """), {'code': card_code}).fetchall()
    return jsonify([{
        'address_name': r[0] or '', 'street':    r[1] or '',
        'street_no':    r[2] or '', 'city':      r[3] or '',
        'country':      r[4] or '',
    } for r in rows])


@main.route('/api/descuentos')
@login_required
def api_descuentos():
    ruc = (request.args.get('ruc') or '').strip()
    if not ruc:
        return jsonify([])
    rows = db.session.execute(text("""
        SELECT d.item_code, COALESCE(i.item_name, d.item_code, '') AS item_name,
               d.descuento, d.status
        FROM business_partners_discount_item d
        LEFT JOIN items i ON i.item_code = d.item_code
        WHERE TRIM(d.federal_tax_id) = :ruc
        ORDER BY d.item_code
    """), {'ruc': ruc}).fetchall()
    return jsonify([{
        'item_code': r[0] or '', 'item_name': r[1] or '',
        'descuento': r[2], 'status': r[3],
    } for r in rows])
