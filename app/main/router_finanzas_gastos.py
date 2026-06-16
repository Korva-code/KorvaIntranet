import json
from datetime import date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Banco

_SQL_LISTAR = """
    SELECT
        g.gasto_id,
        g.id_tipo_gasto,
        COALESCE(tg.nombre, '')                     AS tipo_nombre,
        COALESCE(g.card_code, '')                   AS card_code,
        COALESCE(bp.card_name, g.card_code, '')     AS bp_name,
        COALESCE(g.nro_documento, '')               AS nro_documento,
        g.doc_date,
        g.doc_due_date,
        COALESCE(g.doc_currency, 'SOL')             AS doc_currency,
        COALESCE(g.tipo_cambio, 1)                  AS tipo_cambio,
        COALESCE(g.monto, 0)                        AS monto,
        g.id_banco,
        COALESCE(b.nombre, '')                      AS banco_nombre,
        COALESCE(g.referencia, '')                  AS referencia,
        COALESCE(g.concepto, '')                    AS concepto,
        COALESCE(g.journal_memo, '')                AS journal_memo,
        COALESCE(g.user_code, '')                   AS user_code,
        COALESCE(u.nombres, g.user_code, '')        AS user_nombre,
        g.id_estado,
        g.fecha_registro,
        COALESCE(g.imagen, '')                      AS imagen
    FROM  gastos g
    LEFT  JOIN tipos_gasto       tg ON tg.id_tipo_gasto = g.id_tipo_gasto
    LEFT  JOIN business_partners bp ON bp.card_code     = g.card_code
    LEFT  JOIN bancos             b  ON b.id_banco       = g.id_banco
    LEFT  JOIN w_usuarios         u  ON u.id_usuario::text = g.user_code::text
    WHERE g.id_estado IN (1, 2)
    ORDER BY g.gasto_id DESC
"""


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'gasto_id':       m.get('gasto_id'),
        'id_tipo_gasto':  m.get('id_tipo_gasto'),
        'tipo_nombre':    m.get('tipo_nombre')   or '',
        'card_code':      m.get('card_code')     or '',
        'bp_name':        m.get('bp_name')       or '',
        'nro_documento':  m.get('nro_documento') or '',
        'doc_date':       m['doc_date'].isoformat()     if m.get('doc_date')     else '',
        'doc_due_date':   m['doc_due_date'].isoformat() if m.get('doc_due_date') else '',
        'doc_currency':   m.get('doc_currency')  or 'SOL',
        'tipo_cambio':    float(m['tipo_cambio']) if m.get('tipo_cambio')  is not None else 1.0,
        'monto':          float(m['monto'])       if m.get('monto')        is not None else 0.0,
        'id_banco':       m.get('id_banco'),
        'banco_nombre':   m.get('banco_nombre')  or '',
        'referencia':     m.get('referencia')    or '',
        'concepto':       m.get('concepto')      or '',
        'journal_memo':   m.get('journal_memo')  or '',
        'user_code':      m.get('user_code')      or '',
        'user_nombre':    m.get('user_nombre')   or '',
        'id_estado':      m.get('id_estado') if m.get('id_estado') is not None else 1,
        'fecha_registro': m['fecha_registro'].isoformat() if m.get('fecha_registro') else '',
        'imagen':         m.get('imagen') or '',
    }


@main.route('/finanzas/gastos')
@login_required
def finanzas_gastos():
    gastos_list = [_row_to_dict(r) for r in
                   db.session.execute(text(_SQL_LISTAR)).fetchall()]

    tipos_list = [{'id_tipo_gasto': dict(r._mapping)['id_tipo_gasto'],
                   'nombre':        dict(r._mapping)['nombre']}
                  for r in db.session.execute(
                      text("SELECT id_tipo_gasto, nombre FROM tipos_gasto "
                           "WHERE id_estado = 1 ORDER BY nombre")
                  ).fetchall()]

    bancos_list = [b.as_dict() for b in
                   Banco.query.filter_by(id_estado=1).order_by(Banco.nombre).all()]

    socios_list = [{'card_code': dict(r._mapping)['card_code'],
                    'card_name': dict(r._mapping)['card_name'] or ''}
                   for r in db.session.execute(
                       text("SELECT card_code, card_name FROM business_partners ORDER BY card_name")
                   ).fetchall()]

    return render_template(
        'main/finanzas_gastos.html',
        title='Gastos',
        section='Finanzas', page='Gastos',
        gastos_json=json.dumps(gastos_list,  ensure_ascii=False),
        tipos_json =json.dumps(tipos_list,   ensure_ascii=False),
        bancos_json=json.dumps(bancos_list,  ensure_ascii=False),
        socios_json=json.dumps(socios_list,  ensure_ascii=False),
        total=len(gastos_list),
        today=date.today().isoformat(),
    )


def _registrar_banco_gasto(gasto_id, card_code, nro_documento, doc_date,
                           doc_currency, referencia, concepto, monto,
                           id_banco, user_code):
    """Inserta una fila en bancos_estado_cuenta vinculada al gasto (egreso = monto negativo).
    No hace commit; el caller lo hace.
    """
    nombre_banco = ''
    if id_banco:
        banco_obj = db.session.get(Banco, id_banco)
        nombre_banco = banco_obj.nombre if banco_obj else ''

    db.session.execute(text("""
        INSERT INTO bancos_estado_cuenta (
            id_gasto, card_code, nro_documento,
            fecha_pago, moneda_pago, referencia, concepto,
            monto_aplicado, id_banco, nombre_banco, user_code
        ) VALUES (
            :id_gasto, :card_code, :nro_documento,
            CAST(NULLIF(:fecha_pago, '') AS DATE),
            :moneda_pago, :referencia, :concepto,
            :monto_aplicado, :id_banco, :nombre_banco, :user_code
        )
    """), {
        'id_gasto':       gasto_id,
        'card_code':      card_code,
        'nro_documento':  nro_documento,
        'fecha_pago':     doc_date or '',
        'moneda_pago':    doc_currency,
        'referencia':     referencia,
        'concepto':       concepto,
        'monto_aplicado': -abs(monto),
        'id_banco':       id_banco,
        'nombre_banco':   nombre_banco,
        'user_code':      user_code,
    })


@main.route('/finanzas/gastos/guardar', methods=['POST'])
@login_required
def finanzas_gastos_guardar():
    data = request.get_json(silent=True) or {}
    try:
        gasto_id      = int(data.get('gasto_id') or 0)
        id_tipo_gasto = int(data.get('id_tipo_gasto') or 0) or None
        card_code     = (data.get('card_code')    or '').strip() or None
        nro_documento = (data.get('nro_documento') or '').strip() or None
        doc_date      = data.get('doc_date')     or None
        doc_due_date  = data.get('doc_due_date') or None
        doc_currency  = data.get('doc_currency') or 'SOL'
        tipo_cambio   = float(data.get('tipo_cambio') or 1)
        monto         = float(data.get('monto') or 0)
        id_banco      = int(data.get('id_banco') or 0) or None
        referencia    = (data.get('referencia')   or '').strip() or None
        concepto      = (data.get('concepto')     or '').strip() or None
        journal_memo  = (data.get('journal_memo') or '').strip() or None
        user_code     = str(current_user.id_usuario)
        imagen        = (data.get('imagen') or '').strip() or None

        params = dict(
            id_tipo_gasto=id_tipo_gasto, card_code=card_code,
            nro_documento=nro_documento, doc_date=doc_date, doc_due_date=doc_due_date,
            doc_currency=doc_currency, tipo_cambio=tipo_cambio, monto=monto,
            id_banco=id_banco, referencia=referencia, concepto=concepto,
            journal_memo=journal_memo, user_code=user_code, imagen=imagen,
        )

        if gasto_id == 0:
            new_id = db.session.execute(text("""
                INSERT INTO gastos (
                    id_tipo_gasto, card_code, nro_documento,
                    doc_date, doc_due_date, doc_currency, tipo_cambio, monto,
                    id_banco, referencia, concepto, journal_memo, user_code,
                    imagen, id_estado
                ) VALUES (
                    :id_tipo_gasto, :card_code, :nro_documento,
                    CAST(:doc_date AS DATE), CAST(:doc_due_date AS DATE),
                    :doc_currency, :tipo_cambio, :monto,
                    :id_banco, :referencia, :concepto, :journal_memo, :user_code,
                    :imagen, 1
                )
                RETURNING gasto_id
            """), params).scalar()

            db.session.commit()
            return jsonify({'success': True, 'gasto_id': new_id,
                            'message': 'Gasto registrado correctamente.'})
        else:
            # No se puede editar un gasto ya aplicado
            estado_actual = db.session.execute(
                text("SELECT id_estado FROM gastos WHERE gasto_id = :id"),
                {'id': gasto_id}
            ).scalar()
            if estado_actual == 2:
                return jsonify({'success': False,
                                'message': 'No se puede editar un gasto ya aplicado en banco.'}), 400

            params['gasto_id'] = gasto_id
            db.session.execute(text("""
                UPDATE gastos SET
                    id_tipo_gasto = :id_tipo_gasto,
                    card_code     = :card_code,
                    nro_documento = :nro_documento,
                    doc_date      = CAST(:doc_date AS DATE),
                    doc_due_date  = CAST(:doc_due_date AS DATE),
                    doc_currency  = :doc_currency,
                    tipo_cambio   = :tipo_cambio,
                    monto         = :monto,
                    id_banco      = :id_banco,
                    referencia    = :referencia,
                    concepto      = :concepto,
                    journal_memo  = :journal_memo,
                    user_code     = :user_code,
                    imagen        = :imagen
                WHERE gasto_id = :gasto_id
            """), params)
            db.session.commit()
            return jsonify({'success': True, 'gasto_id': gasto_id,
                            'message': 'Gasto actualizado correctamente.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@main.route('/finanzas/gastos/<int:gasto_id>/anular', methods=['POST'])
@login_required
def finanzas_gasto_anular(gasto_id):
    try:
        db.session.execute(
            text("UPDATE gastos SET id_estado = 0 WHERE gasto_id = :id"),
            {'id': gasto_id}
        )
        db.session.execute(
            text("DELETE FROM bancos_estado_cuenta WHERE id_gasto = :id"),
            {'id': gasto_id}
        )
        db.session.commit()
        return jsonify({'success': True, 'message': f'Gasto #{gasto_id} anulado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@main.route('/finanzas/gastos/<int:gasto_id>/aplicar', methods=['POST'])
@login_required
def finanzas_gasto_aplicar(gasto_id):
    gasto = db.session.execute(
        text("SELECT * FROM gastos WHERE gasto_id = :id"),
        {'id': gasto_id}
    ).fetchone()
    if not gasto:
        return jsonify({'success': False, 'message': f'Gasto #{gasto_id} no encontrado.'}), 404

    g = dict(gasto._mapping)
    if g.get('id_estado') == 2:
        return jsonify({'success': False, 'message': 'El gasto ya fue aplicado anteriormente.'}), 400
    if g.get('id_estado') != 1:
        return jsonify({'success': False, 'message': 'El gasto debe estar activo para aplicarlo.'}), 400

    try:
        _registrar_banco_gasto(
            gasto_id,
            g.get('card_code'),
            g.get('nro_documento'),
            g['doc_date'].isoformat() if g.get('doc_date') else '',
            g.get('doc_currency') or 'SOL',
            g.get('referencia'),
            g.get('concepto'),
            float(g['monto']) if g.get('monto') is not None else 0.0,
            g.get('id_banco'),
            str(current_user.id_usuario),
        )
        db.session.execute(
            text("UPDATE gastos SET id_estado = 2 WHERE gasto_id = :id"),
            {'id': gasto_id}
        )
        db.session.commit()
        return jsonify({'success': True, 'message': f'Gasto #{gasto_id} aplicado correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
