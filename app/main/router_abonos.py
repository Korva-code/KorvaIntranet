import json
from datetime import date
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Abono, Banco


def _row_to_dict(r):
    return {
        'id_abono':     r[0],
        'id_banco':     r[1],
        'banco_nombre': r[2] or '',
        'fecha':        r[3].isoformat() if r[3] else '',
        'monto':        float(r[4]) if r[4] is not None else 0.0,
        'moneda':       r[5] or 'SOL',
        'referencia':   r[6] or '',
        'concepto':     r[7] or '',
        'card_code':    r[8] or '',
        'bp_name':      r[9] or '',
        'id_estado':    r[10] if r[10] is not None else 1,
        'tipo':         r[11] if r[11] is not None else 1,
    }


@main.route('/finanzas/abonos')
@login_required
def abonos():
    rows = db.session.execute(text("SELECT * FROM sp_abonos_listar(0)")).fetchall()
    abonos_list = [_row_to_dict(r) for r in rows]
    abonos_json = json.dumps(abonos_list, ensure_ascii=False)
    today = date.today().isoformat()
    return render_template('main/abonos.html', title='Abonos',
                           section='Finanzas', page='Abonos',
                           abonos_json=abonos_json,
                           total=len(abonos_list),
                           today=today)


@main.route('/api/abonos/<int:id_abono>/imagen')
@login_required
def api_abono_imagen(id_abono):
    row = db.session.execute(
        text("SELECT imagen FROM abonos WHERE id_abono = :id"),
        {'id': id_abono}
    ).fetchone()
    return jsonify({'imagen': row[0] if row and row[0] else None})


@main.route('/api/abonos-ingreso')
@login_required
def api_abonos_ingreso():
    rows = db.session.execute(text("""
        SELECT
            a.id_abono,
            a.id_banco,
            COALESCE(b.nombre, '')                          AS banco_nombre,
            a.fecha,
            a.monto,
            a.moneda,
            a.referencia,
            a.concepto,
            a.card_code,
            COALESCE(bp.card_name, a.card_code, '')         AS bp_name,
            a.id_estado,
            COALESCE(a.tipo, 1)                             AS tipo
        FROM   abonos a
        LEFT   JOIN bancos              b  ON b.id_banco  = a.id_banco
        LEFT   JOIN business_partners   bp ON bp.card_code = a.card_code
        WHERE  a.id_estado = 1
          AND  COALESCE(a.tipo, 1) = 1
        ORDER  BY a.fecha DESC, a.id_abono DESC
    """)).fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@main.route('/api/abonos-salida')
@login_required
def api_abonos_salida():
    rows = db.session.execute(text("""
        SELECT
            a.id_abono,
            a.id_banco,
            COALESCE(b.nombre, '')                          AS banco_nombre,
            a.fecha,
            a.monto,
            a.moneda,
            a.referencia,
            a.concepto,
            a.card_code,
            COALESCE(bp.card_name, a.card_code, '')         AS bp_name,
            a.id_estado,
            COALESCE(a.tipo, 1)                             AS tipo
        FROM   abonos a
        LEFT   JOIN bancos              b  ON b.id_banco  = a.id_banco
        LEFT   JOIN business_partners   bp ON bp.card_code = a.card_code
        WHERE  a.id_estado = 1
          AND  COALESCE(a.tipo, 1) = 2
        ORDER  BY a.fecha DESC, a.id_abono DESC
    """)).fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@main.route('/finanzas/abonos/nuevo', methods=['POST'])
@login_required
def abono_nuevo():
    fecha_str = request.form.get('fecha', '').strip()
    try:
        from datetime import datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None
    except ValueError:
        fecha = None

    imagen_b64 = request.form.get('imagen_b64', '').strip() or None
    abono = Abono(
        id_banco   = int(request.form.get('id_banco', 0) or 0) or None,
        fecha      = fecha,
        monto      = float(request.form.get('monto', 0) or 0),
        moneda     = request.form.get('moneda', 'SOL').strip(),
        referencia = request.form.get('referencia', '').strip() or None,
        concepto   = request.form.get('concepto', '').strip() or None,
        card_code  = request.form.get('card_code', '').strip() or None,
        id_estado  = int(request.form.get('id_estado', 1) or 1),
        tipo       = int(request.form.get('tipo', 1) or 1),
        imagen     = imagen_b64,
    )
    db.session.add(abono)
    db.session.commit()
    flash(f'Abono #{abono.id_abono} registrado correctamente.', 'success')
    return redirect(url_for('main.abonos'))


@main.route('/finanzas/abonos/<int:id_abono>/editar', methods=['POST'])
@login_required
def abono_editar(id_abono):
    abono = db.session.get(Abono, id_abono)
    if not abono:
        flash(f'Abono #{id_abono} no encontrado.', 'danger')
        return redirect(url_for('main.abonos'))

    fecha_str = request.form.get('fecha', '').strip()
    try:
        from datetime import datetime
        abono.fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None
    except ValueError:
        abono.fecha = None

    abono.id_banco   = int(request.form.get('id_banco', 0) or 0) or None
    abono.monto      = float(request.form.get('monto', 0) or 0)
    abono.moneda     = request.form.get('moneda', 'SOL').strip()
    abono.referencia = request.form.get('referencia', '').strip() or None
    abono.concepto   = request.form.get('concepto', '').strip() or None
    abono.card_code  = request.form.get('card_code', '').strip() or None
    abono.id_estado  = int(request.form.get('id_estado', 1) or 1)
    abono.tipo       = int(request.form.get('tipo', 1) or 1)
    imagen_b64 = request.form.get('imagen_b64', '').strip()
    if imagen_b64:
        abono.imagen = imagen_b64
    db.session.commit()
    flash(f'Abono #{id_abono} actualizado correctamente.', 'success')
    return redirect(url_for('main.abonos'))


@main.route('/finanzas/abonos/<int:id_abono>/aplicar', methods=['POST'])
@login_required
def abono_aplicar(id_abono):
    abono = db.session.get(Abono, id_abono)
    if not abono:
        return jsonify({'success': False, 'message': f'Abono #{id_abono} no encontrado.'}), 404
    if abono.id_estado == 2:
        return jsonify({'success': False, 'message': 'El abono ya fue aplicado anteriormente.'}), 400
    if abono.id_estado != 1:
        return jsonify({'success': False, 'message': 'El abono debe estar activo para poder aplicarlo.'}), 400

    try:
        nombre_banco = ''
        if abono.id_banco:
            banco_obj = db.session.get(Banco, abono.id_banco)
            nombre_banco = banco_obj.nombre if banco_obj else ''

        db.session.execute(text("""
            INSERT INTO bancos_estado_cuenta (
                id_abono, card_code, nro_documento,
                fecha_pago, moneda_pago, referencia, concepto,
                monto_aplicado, id_banco, nombre_banco, user_code
            ) VALUES (
                :id_abono, :card_code, :nro_documento,
                CAST(NULLIF(:fecha_pago, '') AS DATE),
                :moneda_pago, :referencia, :concepto,
                :monto_aplicado, :id_banco, :nombre_banco, :user_code
            )
        """), {
            'id_abono':       id_abono,
            'card_code':      abono.card_code,
            'nro_documento':  abono.referencia,
            'fecha_pago':     abono.fecha.isoformat() if abono.fecha else '',
            'moneda_pago':    abono.moneda or 'SOL',
            'referencia':     abono.referencia,
            'concepto':       abono.concepto,
            'monto_aplicado': (-1 if (abono.tipo or 1) == 2 else 1) * (float(abono.monto) if abono.monto is not None else 0.0),
            'id_banco':       abono.id_banco,
            'nombre_banco':   nombre_banco,
            'user_code':      str(current_user.id_usuario),
        })

        abono.id_estado = 2
        db.session.commit()
        return jsonify({'success': True, 'message': f'Abono #{id_abono} aplicado correctamente.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
