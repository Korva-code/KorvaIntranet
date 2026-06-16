import json
from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import InvoicePCancelacion


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_p_cancelacion': m.get('id_p_cancelacion'),
        'invoice_p_id':     m.get('invoice_p_id'),
        'invoice_numero':   m.get('invoice_numero') or '',
        'card_code':        m.get('card_code') or '',
        'bp_name':          m.get('bp_name') or '',
        'banco_nombre':     m.get('banco_nombre') or '',
        'fecha_factura':    m['fecha_factura'].isoformat() if m.get('fecha_factura') else '',
        'fecha_pago':       m['fecha_pago'].isoformat()    if m.get('fecha_pago')    else '',
        'moneda_pago':      m.get('moneda_pago') or 'SOL',
        'tipo_cambio':      float(m['tipo_cambio'])  if m.get('tipo_cambio')  is not None else 1.0,
        'importe':          float(m['importe'])       if m.get('importe')      is not None else 0.0,
        'moneda_factura':   m.get('moneda_factura') or '',
        'monto_factura':    float(m['monto_factura'])    if m.get('monto_factura')    is not None else 0.0,
        'monto_aplicado':   float(m['monto_aplicado'])   if m.get('monto_aplicado')   is not None else 0.0,
        'doc_total':        float(m['doc_total'])         if m.get('doc_total')        is not None else 0.0,
        'doc_total_aply':   float(m['doc_total_aply'])    if m.get('doc_total_aply')   is not None else 0.0,
        'referencia':       m.get('referencia') or '',
        'concepto':         m.get('concepto') or '',
        'user_code':        m.get('user_code') or '',
        'fecha_registro':   m['fecha_registro'].isoformat() if m.get('fecha_registro') else '',
        'id_estado':        m.get('id_estado') if m.get('id_estado') is not None else 1,
    }


@main.route('/compras/cancelaciones')
@login_required
def compras_cancelaciones():
    rows = db.session.execute(text("SELECT * FROM sp_p_cancelaciones_listar(0)")).fetchall()
    cancelaciones_list = [_row_to_dict(r) for r in rows]
    cancelaciones_json = json.dumps(cancelaciones_list, ensure_ascii=False)
    today = date.today().isoformat()
    return render_template('main/compras_cancelaciones.html',
                           title='Pago a Proveedores',
                           section='Compras', page='Pago a Proveedores',
                           cancelaciones_json=cancelaciones_json,
                           total=len(cancelaciones_list),
                           today=today)


@main.route('/compras/cancelaciones/nueva', methods=['GET', 'POST'])
@login_required
def compras_cancelaciones_nueva():
    if request.method == 'GET':
        today = date.today().isoformat()
        return render_template('main/compras_cancelaciones_nueva.html',
                               title='Nuevo Pago a Proveedor',
                               section='Compras', page='Nuevo Pago',
                               today=today)

    card_code    = request.form.get('card_code', '').strip() or None
    id_banco_str = request.form.get('id_banco', '').strip()
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
    imp_str = request.form.get('importe', '').strip().replace(',', '.')
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
        return redirect(url_for('main.compras_cancelaciones_nueva'))

    saved_cancs = []
    for lin in lineas:
        invoice_p_id   = lin.get('invoice_id')
        monto_aplicado = float(lin.get('monto_aplicado', 0) or 0)
        monto_factura  = float(lin.get('monto_factura',  0) or 0)
        moneda_factura = lin.get('moneda_factura', '') or ''
        if not invoice_p_id or monto_aplicado <= 0:
            continue
        canc = InvoicePCancelacion(
            invoice_p_id   = invoice_p_id,
            card_code      = card_code,
            id_banco       = id_banco,
            fecha_pago     = fecha_pago,
            moneda_pago    = moneda_pago,
            tipo_cambio    = tipo_cambio,
            importe        = importe,
            referencia     = referencia,
            concepto       = concepto,
            monto_factura  = monto_factura,
            moneda_factura = moneda_factura,
            monto_aplicado = monto_aplicado,
            user_code      = str(current_user.id_usuario),
            id_estado      = 1,
        )
        db.session.add(canc)
        db.session.execute(text("""
            UPDATE invoice_p
               SET doc_total_aply = COALESCE(doc_total_aply, 0) + :monto
             WHERE invoice_id = :id
        """), {'monto': monto_aplicado, 'id': invoice_p_id})
        inv_p = db.session.execute(text(
            "SELECT invoice_serie, invoice_number FROM invoice_p WHERE invoice_id = :id"
        ), {'id': invoice_p_id}).fetchone()
        nro_doc = f"{inv_p[0] or ''}-{inv_p[1] or ''}" if inv_p else ''
        saved_cancs.append((canc, invoice_p_id, monto_aplicado, nro_doc))

    if not saved_cancs:
        flash('Sin montos válidos para guardar.', 'warning')
        return redirect(url_for('main.compras_cancelaciones_nueva'))

    db.session.commit()

    # Registrar en estado de cuenta bancario (monto negativo = egreso)
    try:
        from app.main.router_bancos_estado_cuenta import registrar_estado_cuenta
        from app.models import Banco
        banco_obj    = db.session.get(Banco, id_banco)
        nombre_banco = banco_obj.nombre if banco_obj else ''
        for canc, inv_p_id, monto_aply, nro_doc in saved_cancs:
            registrar_estado_cuenta(
                id_cancelacion = canc.id_p_cancelacion,
                id_invoice     = inv_p_id,
                card_code      = card_code,
                nro_documento  = nro_doc,
                fecha_pago     = fecha_pago,
                moneda_pago    = moneda_pago,
                referencia     = referencia,
                concepto       = concepto,
                monto_aplicado = -abs(monto_aply),
                id_banco       = id_banco,
                nombre_banco   = nombre_banco,
                user_code      = current_user.id_usuario,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()

    flash(f'{len(saved_cancs)} pago(s) registrado(s) correctamente.', 'success')
    return redirect(url_for('main.compras_cancelaciones'))


@main.route('/compras/cancelaciones/<int:id_p_cancelacion>/anular', methods=['POST'])
@login_required
def compras_cancelacion_anular(id_p_cancelacion):
    canc = db.session.get(InvoicePCancelacion, id_p_cancelacion)
    if not canc:
        flash(f'Pago #{id_p_cancelacion} no encontrado.', 'danger')
        return redirect(url_for('main.compras_cancelaciones'))
    canc.id_estado = 0
    if canc.invoice_p_id and canc.monto_aplicado:
        db.session.execute(text("""
            UPDATE invoice_p
               SET doc_total_aply = GREATEST(0, COALESCE(doc_total_aply, 0) - :monto)
             WHERE invoice_id = :id
        """), {'monto': float(canc.monto_aplicado), 'id': canc.invoice_p_id})
    db.session.commit()
    flash(f'Pago #{id_p_cancelacion} anulado correctamente.', 'success')
    return redirect(url_for('main.compras_cancelaciones'))


@main.route('/api/facturas-p-pendientes')
@login_required
def api_facturas_p_pendientes():
    card_code = request.args.get('card_code', '').strip()
    rows = db.session.execute(
        text("SELECT * FROM sp_facturas_p_pendientes(:p)"),
        {'p': card_code}
    ).fetchall()
    result = []
    for r in rows:
        m = dict(r._mapping)
        result.append({
            'invoice_id':      m.get('invoice_id'),
            'card_code':       m.get('card_code') or '',
            'bp_name':         m.get('bp_name') or '',
            'invoice_type':    m.get('invoice_type') or '',
            'invoice_serie':   m.get('invoice_serie') or '',
            'invoice_number':  m.get('invoice_number') or '',
            'doc_date':        m['doc_date'].isoformat()     if m.get('doc_date')     else '',
            'doc_due_date':    m['doc_due_date'].isoformat() if m.get('doc_due_date') else '',
            'doc_currency':    m.get('doc_currency') or '',
            'monto_factura':   float(m['monto_factura'])   if m.get('monto_factura')   is not None else 0.0,
            'total_aplicado':  float(m['total_aplicado'])  if m.get('total_aplicado')  is not None else 0.0,
            'saldo_pendiente': float(m['saldo_pendiente']) if m.get('saldo_pendiente') is not None else 0.0,
        })
    return jsonify(result)


@main.route('/api/socios-compras')
@login_required
def api_socios_compras():
    rows = db.session.execute(text("SELECT * FROM business_partners_lista_tipo('1')")).fetchall()
    result = [{'card_code': dict(r._mapping).get('card_code') or '',
               'card_name': dict(r._mapping).get('card_name') or ''}
              for r in rows]
    return jsonify(result)
