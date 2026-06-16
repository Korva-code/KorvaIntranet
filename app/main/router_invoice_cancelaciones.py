import json
from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import InvoiceCancelacion, Invoice


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_cancelacion': m.get('id_cancelacion'),
        'invoice_id':     m.get('invoice_id'),
        'invoice_numero': m.get('invoice_numero') or '',
        'card_code':      m.get('card_code') or '',
        'bp_name':        m.get('bp_name') or '',
        'banco_nombre':   m.get('banco_nombre') or '',
        'fecha_factura':  m['fecha_factura'].isoformat() if m.get('fecha_factura') else '',
        'fecha_pago':     m['fecha_pago'].isoformat() if m.get('fecha_pago') else '',
        'moneda_pago':    m.get('moneda_pago') or 'SOL',
        'tipo_cambio':    float(m['tipo_cambio'])  if m.get('tipo_cambio')  is not None else 1.0,
        'importe':        float(m['importe'])       if m.get('importe')      is not None else 0.0,
        'moneda_factura': m.get('moneda_factura') or '',
        'monto_factura':  float(m['monto_factura'])  if m.get('monto_factura')  is not None else 0.0,
        'monto_aplicado': float(m['monto_aplicado']) if m.get('monto_aplicado') is not None else 0.0,
        'doc_total':      float(m['doc_total'])      if m.get('doc_total')      is not None else 0.0,
        'doc_total_aply': float(m['doc_total_aply']) if m.get('doc_total_aply') is not None else 0.0,
        'referencia':     m.get('referencia') or '',
        'concepto':       m.get('concepto') or '',
        'user_code':      m.get('user_code') or '',
        'user_name':      m.get('user_name') or m.get('user_code') or '',
        'fecha_registro': m['fecha_registro'].isoformat() if m.get('fecha_registro') else '',
        'id_estado':      m.get('id_estado') if m.get('id_estado') is not None else 1,
        'payment_name':   m.get('payment_name') or '',
    }


@main.route('/ventas/cancelaciones')
@login_required
def ventas_cancelaciones():
    rows = db.session.execute(text("SELECT * FROM sp_cancelaciones_listar(0)")).fetchall()
    cancelaciones_list = [_row_to_dict(r) for r in rows]

    # Enriquecer user_name desde w_usuarios
    user_codes = {c['user_code'] for c in cancelaciones_list if c['user_code']}
    if user_codes:
        u_rows = db.session.execute(
            text("SELECT id_usuario::text, nombres FROM w_usuarios WHERE id_usuario::text = ANY(:codes)"),
            {'codes': list(user_codes)}
        ).fetchall()
        nombres_map = {r[0]: r[1] for r in u_rows}
        for c in cancelaciones_list:
            if c['user_code'] and c['user_code'] in nombres_map:
                c['user_name'] = nombres_map[c['user_code']] or c['user_code']

    cancelaciones_json = json.dumps(cancelaciones_list, ensure_ascii=False)
    today = date.today().isoformat()
    return render_template('main/invoice_cancelaciones.html',
                           title='Cancelaciones',
                           section='Ventas', page='Cancelaciones',
                           cancelaciones_json=cancelaciones_json,
                           total=len(cancelaciones_list),
                           today=today)


@main.route('/ventas/cancelaciones/nueva', methods=['GET', 'POST'])
@login_required
def ventas_cancelaciones_nueva():
    if request.method == 'GET':
        today = date.today().isoformat()
        pay_rows = db.session.execute(text("SELECT * FROM sp_payment_listar()")).fetchall()
        payments = [{'id_payment': r[0], 'payment_name': r[1]} for r in pay_rows]
        return render_template('main/invoice_cancelaciones_nueva.html',
                               title='Nueva Cancelación',
                               section='Ventas', page='Nueva Cancelación',
                               today=today,
                               payments_json=json.dumps(payments, ensure_ascii=False))

    # ── POST: save one row per invoice line ─────────────────────────────────
    card_code     = request.form.get('card_code', '').strip() or None
    id_payment_str = request.form.get('id_payment', '').strip()
    id_payment    = int(id_payment_str) if id_payment_str.isdigit() else None
    id_banco_str  = request.form.get('id_banco', '').strip()
    id_banco     = int(id_banco_str) if id_banco_str.isdigit() else None
    fecha_str    = request.form.get('fecha_pago', '').strip()
    try:
        fecha_pago = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None
    except ValueError:
        fecha_pago = None
    moneda_pago = request.form.get('moneda_pago', 'SOL').strip()
    tc_str      = request.form.get('tipo_cambio', '1').strip().replace(',', '.')
    try:
        tipo_cambio = float(tc_str) if tc_str else 1.0
    except ValueError:
        tipo_cambio = 1.0
    imp_str     = request.form.get('importe', '').strip().replace(',', '.')
    try:
        importe = float(imp_str) if imp_str else None
    except ValueError:
        importe = None
    referencia  = request.form.get('referencia', '').strip() or None
    concepto    = request.form.get('concepto', '').strip() or None
    lineas_raw  = request.form.get('lineas_json', '[]')
    try:
        lineas = json.loads(lineas_raw)
    except Exception:
        lineas = []

    if not lineas:
        flash('Debe seleccionar al menos una factura para aplicar.', 'warning')
        return redirect(url_for('main.ventas_cancelaciones_nueva'))

    saved_cancs = []
    for lin in lineas:
        invoice_id     = lin.get('invoice_id')
        monto_aplicado = float(lin.get('monto_aplicado', 0) or 0)
        monto_factura  = float(lin.get('monto_factura', 0) or 0)
        moneda_factura = lin.get('moneda_factura', '') or ''
        if not invoice_id or monto_aplicado <= 0:
            continue
        canc = InvoiceCancelacion(
            invoice_id     = invoice_id,
            card_code      = card_code,
            id_banco       = id_banco,
            id_payment     = id_payment,
            fecha_pago     = fecha_pago,
            moneda_pago    = moneda_pago,
            tipo_cambio    = tipo_cambio,
            importe        = importe,
            referencia     = referencia,
            concepto       = concepto,
            monto_factura  = monto_factura,
            moneda_factura = moneda_factura,
            monto_aplicado = monto_aplicado,
            user_code      = current_user.id_usuario,
            id_estado      = 1,
        )
        db.session.add(canc)
        inv = db.session.get(Invoice, invoice_id)
        if inv is not None:
            inv.doc_total_aply = float(inv.doc_total_aply or 0) + monto_aplicado
        inv_fields = db.session.execute(text(
            "SELECT invoice_serie, invoice_number FROM invoice WHERE invoice_id = :id"
        ), {'id': invoice_id}).fetchone()
        nro_doc = f"{inv_fields[0] or ''}-{inv_fields[1] or ''}" if inv_fields else ''
        saved_cancs.append((canc, invoice_id, monto_aplicado, nro_doc))

    if not saved_cancs:
        flash('Sin montos válidos para guardar.', 'warning')
        return redirect(url_for('main.ventas_cancelaciones_nueva'))

    db.session.commit()

    # Registrar en estado de cuenta bancario
    try:
        from app.main.router_bancos_estado_cuenta import registrar_estado_cuenta
        from app.models import Banco
        banco_obj    = db.session.get(Banco, id_banco)
        nombre_banco = banco_obj.nombre if banco_obj else ''
        for canc, inv_id, monto_aply, nro_doc in saved_cancs:
            registrar_estado_cuenta(
                id_cancelacion = canc.id_cancelacion,
                id_invoice     = inv_id,
                card_code      = card_code,
                nro_documento  = nro_doc,
                fecha_pago     = fecha_pago,
                moneda_pago    = moneda_pago,
                referencia     = referencia,
                concepto       = concepto,
                monto_aplicado = monto_aply,
                id_banco       = id_banco,
                nombre_banco   = nombre_banco,
                user_code      = current_user.id_usuario,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()

    flash(f'{len(saved_cancs)} cancelación(es) registrada(s) correctamente.', 'success')
    return redirect(url_for('main.ventas_cancelaciones'))


@main.route('/ventas/cancelaciones/<int:id_cancelacion>/anular', methods=['POST'])
@login_required
def ventas_cancelacion_anular(id_cancelacion):
    canc = db.session.get(InvoiceCancelacion, id_cancelacion)
    if not canc:
        return jsonify({'success': False, 'message': f'Cancelación #{id_cancelacion} no encontrada.'}), 404
    try:
        canc.id_estado = 0
        if canc.invoice_id and canc.monto_aplicado:
            inv = db.session.get(Invoice, canc.invoice_id)
            if inv is not None:
                inv.doc_total_aply = max(0.0, float(inv.doc_total_aply or 0) - float(canc.monto_aplicado))
        db.session.commit()
        return jsonify({'success': True, 'message': f'Cancelación #{id_cancelacion} anulada correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@main.route('/api/facturas-pendientes')
@login_required
def api_facturas_pendientes():
    card_code = request.args.get('card_code', '').strip()
    rows = db.session.execute(
        text("SELECT * FROM sp_facturas_pendientes(:p)"),
        {'p': card_code}
    ).fetchall()
    result = []
    for r in rows:
        result.append({
            'invoice_id':      r[0],
            'card_code':       r[1] or '',
            'bp_name':         r[2] or '',
            'invoice_type':    r[3] or '',
            'invoice_serie':   r[4] or '',
            'invoice_number':  r[5] or '',
            'doc_date':        r[6].isoformat() if r[6] else '',
            'doc_due_date':    r[7].isoformat() if r[7] else '',
            'doc_currency':    r[8] or '',
            'monto_factura':   float(r[9])  if r[9]  is not None else 0.0,
            'total_aplicado':  float(r[10]) if r[10] is not None else 0.0,
            'saldo_pendiente': float(r[11]) if r[11] is not None else 0.0,
        })
    return jsonify(result)
