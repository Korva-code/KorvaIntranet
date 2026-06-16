import json
from flask import render_template, request
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Banco


# ── Helper: registrar entrada en estado de cuenta tras guardar cancelacion ──

def registrar_estado_cuenta(id_cancelacion, id_invoice, card_code,
                            nro_documento, fecha_pago, moneda_pago,
                            referencia, concepto, monto_aplicado,
                            id_banco, nombre_banco, user_code):
    """Inserta una fila en bancos_estado_cuenta.
    No hace commit; el caller lo hace.
    """
    db.session.execute(text("""
        INSERT INTO bancos_estado_cuenta
            (id_cancelacion, id_invoice, card_code, nro_documento,
             fecha_pago, moneda_pago, referencia, concepto, monto_aplicado,
             id_banco, nombre_banco, user_code)
        VALUES
            (:id_canc, :id_inv, :card_code, :nro_doc,
             CAST(:fecha AS DATE), :moneda, :ref, :concepto, :monto,
             :id_banco, :nombre_banco, :user_code)
    """), {
        'id_canc':      id_cancelacion,
        'id_inv':       id_invoice,
        'card_code':    card_code,
        'nro_doc':      nro_documento,
        'fecha':        fecha_pago.isoformat() if fecha_pago else None,
        'moneda':       moneda_pago,
        'ref':          referencia,
        'concepto':     concepto,
        'monto':        monto_aplicado,
        'id_banco':     id_banco,
        'nombre_banco': nombre_banco,
        'user_code':    str(user_code),
    })


# ── Vista ───────────────────────────────────────────────────────────────────

def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id':             m.get('id'),
        'id_cancelacion': m.get('id_cancelacion'),
        'id_invoice':     m.get('id_invoice'),
        'nro_documento':  m.get('nro_documento') or '',
        'card_code':      m.get('card_code') or '',
        'card_name':      m.get('card_name') or '',
        'id_banco':       m.get('id_banco'),
        'nombre_banco':   m.get('nombre_banco') or '',
        'fecha_pago':     m['fecha_pago'].isoformat() if m.get('fecha_pago') else '',
        'moneda_pago':    m.get('moneda_pago') or 'SOL',
        'referencia':     m.get('referencia') or '',
        'concepto':       m.get('concepto') or '',
        'monto_aplicado': float(m['monto_aplicado']) if m.get('monto_aplicado') is not None else 0.0,
        'user_code':      m.get('user_code') or '',
        'fecha_registro': m['fecha_registro'].isoformat() if m.get('fecha_registro') else '',
        'id_estado':      m.get('id_estado') if m.get('id_estado') is not None else 1,
    }


@main.route('/bancos/estado-cuenta')
@login_required
def bancos_estado_cuenta():
    try:
        id_banco = int(request.args.get('id_banco', 0))
    except (ValueError, TypeError):
        id_banco = 0

    rows = db.session.execute(text(
        "SELECT * FROM sp_bancos_estado_cuenta_listar(:p)"
    ), {'p': id_banco}).fetchall()

    movimientos = [_row_to_dict(r) for r in rows]

    bancos_list = [b.as_dict() for b in
                   Banco.query.filter_by(id_estado=1).order_by(Banco.nombre).all()]

    return render_template('main/bancos_estado_cuenta.html',
                           title='Estado de Cuenta',
                           section='Bancos', page='Estado de Cuenta',
                           movimientos_json=json.dumps(movimientos, ensure_ascii=False),
                           bancos_json=json.dumps(bancos_list, ensure_ascii=False),
                           selected_banco=id_banco,
                           total=len(movimientos))
