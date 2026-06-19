import json
from datetime import datetime
import requests as http_requests
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import BusinessPartner

_DNIRUC_TOKEN = '4f9b09b3-e397-46bf-ae2d-5d896b5045a8'


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
        avg  = float(d.get('avg_price_d')    or 0)
        cigv = float(d.get('priceaftervat_d') or avg * 1.18)
        db.session.execute(text("""
            INSERT INTO business_partners_discount_item
                   (federal_tax_id, item_code, avg_price_d, priceaftervat_d, status)
            VALUES (:ruc, :item_code, :avg, :cigv, 1)
        """), {
            'ruc':       ruc,
            'item_code': (d.get('item_code') or '').strip(),
            'avg':       avg,
            'cigv':      cigv,
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


@main.route('/api/socios-todos')
@login_required
def api_socios_todos():
    rows = db.session.execute(text("""
        SELECT card_code, card_name
        FROM   business_partners
        ORDER  BY card_code
    """)).fetchall()
    return jsonify([{'card_code': r[0] or '', 'card_name': r[1] or ''} for r in rows])


@main.route('/api/descuentos')
@login_required
def api_descuentos():
    ruc = (request.args.get('ruc') or '').strip()
    if not ruc:
        return jsonify([])
    rows = db.session.execute(text("""
        SELECT d.item_code, COALESCE(i.item_name, d.item_code, '') AS item_name,
               COALESCE(d.avg_price_d, 0) AS avg_price_d,
               COALESCE(d.status, 1)      AS status
        FROM business_partners_discount_item d
        LEFT JOIN items i ON i.item_code = d.item_code
        WHERE TRIM(d.federal_tax_id) = :ruc
        ORDER BY d.item_code
    """), {'ruc': ruc}).fetchall()
    return jsonify([{
        'item_code':      r[0] or '',
        'item_name':      r[1] or '',
        'avg_price_d':    float(r[2]),
        'priceaftervat_d': round(float(r[2]) * 1.18, 4),
        'status':         r[3],
    } for r in rows])


@main.route('/api/sunat/buscar/<numero>')
@login_required
def api_sunat_buscar_numero(numero):
    numero = numero.strip()
    if len(numero) == 11:
        url = f'https://api.dniruc.com/api/search/ruc/{numero}/{_DNIRUC_TOKEN}'
    else:
        url = f'https://api.dniruc.com/api/search/dni/{numero}/{_DNIRUC_TOKEN}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    try:
        resp = http_requests.get(url, headers=headers, timeout=10)
        data = resp.json()
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error de conexión: {e}'}), 502

    if not data.get('success') or not data.get('data'):
        return jsonify({'success': False, 'message': data.get('message', 'No encontrado.')}), 404

    d = data['data']
    return jsonify({
        'success':   True,
        'numero':    numero,
        'nombre':    d.get('nombre_razon_social') or d.get('nombre_completo') or d.get('nombre', ''),
        'direccion': d.get('calle') or d.get('ubigeotext', ''),
        'ciudad':    d.get('distrito', ''),
        'estado':    d.get('estado', ''),
        'condicion': d.get('condicion', ''),
    })
