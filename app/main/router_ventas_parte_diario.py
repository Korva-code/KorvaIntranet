import json
from datetime import datetime
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


def _row_to_dict(r):
    m = dict(r._mapping)
    def fmt(v): return v.isoformat() if v else ''
    return {
        'id_parte':             m.get('id_parte'),
        'id_punto_venta':       m.get('id_punto_venta'),
        'punto_venta_nombre':   m.get('punto_venta_nombre') or '',
        'user_code':            m.get('user_code') or '',
        'user_nombre':          m.get('user_nombre') or '',
        'fecha_apertura':       fmt(m.get('fecha_apertura')),
        'fecha_cierre':         fmt(m.get('fecha_cierre')),
        'monto_inicial':        float(m['monto_inicial']) if m.get('monto_inicial') is not None else 0.0,
        'monto_final':          float(m['monto_final'])   if m.get('monto_final')   is not None else None,
        'observacion_apertura': m.get('observacion_apertura') or '',
        'observacion_cierre':   m.get('observacion_cierre')   or '',
        'id_estado':            m.get('id_estado') if m.get('id_estado') is not None else 1,
    }


@main.route('/ventas/parte-diario')
@login_required
def ventas_parte_diario():
    partes = [_row_to_dict(r) for r in
              db.session.execute(text("SELECT * FROM sp_parte_diario_listar(60)")).fetchall()]

    puntos = [{'id': r[0], 'nombre': r[1]} for r in
              db.session.execute(text("SELECT * FROM sp_punto_venta_listar()")).fetchall()]

    return render_template(
        'main/ventas_parte_diario.html',
        title='Parte Diario',
        section='Ventas', page='Parte Diario',
        partes_json=json.dumps(partes,  ensure_ascii=False),
        puntos_json=json.dumps(puntos,  ensure_ascii=False),
        total=len(partes),
        user_code=str(current_user.id_usuario),
    )


@main.route('/ventas/parte-diario/aperturar', methods=['POST'])
@login_required
def ventas_parte_diario_aperturar():
    data = request.get_json(silent=True) or {}
    try:
        id_punto_venta  = int(data.get('id_punto_venta') or 0)
        monto_inicial   = float(data.get('monto_inicial') or 0)
        observacion     = (data.get('observacion') or '').strip()
        user_code       = str(current_user.id_usuario)
        fecha_apertura_str = (data.get('fecha_apertura') or '').strip()

        if not id_punto_venta:
            return jsonify({'success': False, 'message': 'Seleccione un punto de venta.'}), 400

        try:
            from datetime import datetime as _dt
            fecha_apertura = _dt.fromisoformat(fecha_apertura_str) if fecha_apertura_str else datetime.now()
        except ValueError:
            fecha_apertura = datetime.now()

        row = db.session.execute(text("""
            SELECT success, message, id_parte
            FROM fn_parte_diario_aperturar(:user, :pv, :monto, :obs, :fa)
        """), {'user': user_code, 'pv': id_punto_venta,
               'monto': monto_inicial, 'obs': observacion,
               'fa': fecha_apertura}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1], 'id_parte': row[2]})
        db.session.rollback()
        return jsonify({'success': False, 'message': row[1] if row else 'Error al aperturar.'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@main.route('/ventas/parte-diario/<int:id_parte>/reporte')
@login_required
def ventas_parte_diario_reporte(id_parte):
    try:
        parte_row = db.session.execute(text("""
            SELECT pd.user_code, pd.fecha_apertura, pd.fecha_cierre, pd.monto_inicial,
                   COALESCE(pv.nombre, '')                         AS punto_venta_nombre,
                   COALESCE(u.nombres, pd.user_code, '')::TEXT     AS user_nombre
            FROM parte_diario pd
            LEFT JOIN punto_venta pv ON pv.id_punto_venta = pd.id_punto_venta
            LEFT JOIN w_usuarios  u  ON u.id_usuario::TEXT = pd.user_code
            WHERE pd.id_parte = :id
        """), {'id': id_parte}).fetchone()

        if not parte_row:
            return jsonify({'success': False, 'message': f'Parte #{id_parte} no encontrado.'}), 404

        user_code     = str(parte_row[0] or '')
        fecha_inicio  = parte_row[1]
        fecha_cierre  = parte_row[2]
        monto_inicial = float(parte_row[3] or 0)
        pv_nombre     = parte_row[4] or ''
        user_nombre   = parte_row[5] or user_code
        fecha_fin     = fecha_cierre if fecha_cierre else datetime.now()

        resumen_rows  = db.session.execute(text(
            "SELECT * FROM fn_parte_resumen_dia(:uc, :fi, :ff)"
        ), {'uc': user_code, 'fi': fecha_inicio, 'ff': fecha_fin}).fetchall()

        facturas_rows = db.session.execute(text(
            "SELECT * FROM fn_parte_facturas_lista(:uc, :fi, :ff)"
        ), {'uc': user_code, 'fi': fecha_inicio, 'ff': fecha_fin}).fetchall()

        return jsonify({
            'success': True,
            'parte': {
                'id_parte':           id_parte,
                'user_code':          user_code,
                'user_nombre':        user_nombre,
                'punto_venta_nombre': pv_nombre,
                'fecha_apertura':     fecha_inicio.isoformat() if fecha_inicio else '',
                'fecha_cierre':       fecha_cierre.isoformat() if fecha_cierre else '',
                'monto_inicial':      monto_inicial,
            },
            'resumen': [
                {'payment_name': r[0], 'total_cobrado': float(r[1] or 0), 'cant_docs': int(r[2] or 0)}
                for r in resumen_rows
            ],
            'facturas': [{
                'invoice_id':    r[0],
                'tipo_doc':      r[1],
                'folio':         r[2],
                'nro_doc':       r[3],
                'bp_name':       r[4],
                'payment_name':  r[5],
                'nro_operacion': r[6],
                'fecha':         r[7].isoformat() if r[7] else '',
                'doc_total':     float(r[8] or 0),
                'monto_cobrado': float(r[9] or 0),
                'doc_currency':  r[10],
            } for r in facturas_rows],
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/ventas/parte-diario/<int:id_parte>/actualizar', methods=['POST'])
@login_required
def ventas_parte_diario_actualizar(id_parte):
    data = request.get_json(silent=True) or {}
    try:
        id_punto_venta     = int(data.get('id_punto_venta') or 0)
        monto_inicial      = float(data.get('monto_inicial') or 0)
        observacion        = (data.get('observacion') or '').strip()
        fecha_apertura_str = (data.get('fecha_apertura') or '').strip()

        if not id_punto_venta:
            return jsonify({'success': False, 'message': 'Seleccione un punto de venta.'}), 400
        if not fecha_apertura_str:
            return jsonify({'success': False, 'message': 'Ingrese la fecha de apertura.'}), 400

        try:
            fecha_apertura = datetime.fromisoformat(fecha_apertura_str)
        except ValueError:
            return jsonify({'success': False, 'message': 'Fecha de apertura inválida.'}), 400

        row = db.session.execute(text("""
            SELECT success, message
            FROM fn_parte_diario_actualizar(:id, :pv, :fa, :monto, :obs)
        """), {'id': id_parte, 'pv': id_punto_venta, 'fa': fecha_apertura,
               'monto': monto_inicial, 'obs': observacion}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1]})
        db.session.rollback()
        return jsonify({'success': False, 'message': row[1] if row else 'Error al actualizar.'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/ventas/parte-diario/<int:id_parte>/cerrar', methods=['POST'])
@login_required
def ventas_parte_diario_cerrar(id_parte):
    data = request.get_json(silent=True) or {}
    try:
        monto_final = float(data.get('monto_final') or 0)
        observacion = (data.get('observacion') or '').strip()

        row = db.session.execute(text("""
            SELECT success, message
            FROM fn_parte_diario_cerrar(:id, :monto, :obs)
        """), {'id': id_parte, 'monto': monto_final, 'obs': observacion}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1]})
        db.session.rollback()
        return jsonify({'success': False, 'message': row[1] if row else 'Error al cerrar.'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
