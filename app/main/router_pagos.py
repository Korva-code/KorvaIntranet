import json
from datetime import date, timedelta
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db

_MESES_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
             'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']


def _suscripcion_to_dict(r):
    m = dict(r._mapping)
    venc = m.get('fecha_vencimiento')
    hoy  = date.today()
    vencido = venc and venc < hoy and m.get('id_estado_pago', 0) != 1
    return {
        'id_suscripcion':    m.get('id_suscripcion'),
        'servicio':          m.get('servicio') or '',
        'fecha_inicio':      m['fecha_inicio'].isoformat()      if m.get('fecha_inicio')      else '',
        'fecha_vencimiento': m['fecha_vencimiento'].isoformat() if m.get('fecha_vencimiento') else '',
        'precio_acordado':   float(m['precio_acordado']) if m.get('precio_acordado') is not None else 0.0,
        'id_estado_pago':    m.get('id_estado_pago') if m.get('id_estado_pago') is not None else 0,
        'observaciones':     m.get('observaciones') or '',
        'incluye_igv':       bool(m.get('incluye_igv')),
        'vencido':           bool(vencido),
    }


def _medio_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_medio':      m.get('id_medio'),
        'tipo':          m.get('tipo') or '',
        'titular':       m.get('titular') or '',
        'numero_masked': m.get('numero_masked') or '',
        'marca':         m.get('marca') or '',
        'vencimiento':   m.get('vencimiento') or '',
        'telefono_yape': m.get('telefono_yape') or '',
    }


# ── Rutas ─────────────────────────────────────────────────────────

@main.route('/mi-perfil/pagos')
@login_required
def mi_perfil_pagos():
    id_empresa = current_user.id_empresa

    servicios = db.session.execute(text("""
        SELECT id_servicio, nombre, descripcion, precio, incluye_igv, periodicidad
        FROM suscripcion_servicios
        WHERE id_estado = 1
        ORDER BY id_servicio
    """)).fetchall()

    suscripciones = db.session.execute(text("""
        SELECT s.id_suscripcion,
               sv.nombre        AS servicio,
               s.fecha_inicio,
               s.fecha_vencimiento,
               s.precio_acordado,
               s.id_estado_pago,
               s.observaciones,
               sv.incluye_igv
        FROM suscripciones s
        JOIN suscripcion_servicios sv ON sv.id_servicio = s.id_servicio
        WHERE s.id_empresa IS NOT DISTINCT FROM :emp
        ORDER BY s.fecha_registro DESC
    """), {'emp': id_empresa}).fetchall()

    medios = db.session.execute(text("""
        SELECT id_medio, tipo, titular, numero_masked, marca, vencimiento, telefono_yape
        FROM medios_pago
        WHERE id_empresa IS NOT DISTINCT FROM :emp AND id_estado = 1
        ORDER BY tipo, id_medio
    """), {'emp': id_empresa}).fetchall()

    hoy  = date.today()
    anio = hoy.year

    pagos_men = db.session.execute(text("""
        SELECT id_pago, anio, mes, total_servicios, total_igv, total_pago,
               id_estado_pago, fecha_pago
        FROM pagos_mensuales
        WHERE id_empresa IS NOT DISTINCT FROM :emp AND anio = :anio
        ORDER BY mes
    """), {'emp': id_empresa, 'anio': anio}).fetchall()

    def _pago_to_dict(r):
        m = dict(r._mapping)
        return {
            'id_pago':         m.get('id_pago'),
            'anio':            m.get('anio'),
            'mes':             m.get('mes'),
            'mes_nombre':      _MESES_ES[(m.get('mes') or 1) - 1],
            'total_servicios': float(m['total_servicios']) if m.get('total_servicios') is not None else 0.0,
            'total_igv':       float(m['total_igv'])       if m.get('total_igv')       is not None else 0.0,
            'total_pago':      float(m['total_pago'])      if m.get('total_pago')       is not None else 0.0,
            'id_estado_pago':  m.get('id_estado_pago') if m.get('id_estado_pago') is not None else 0,
            'fecha_pago':      m['fecha_pago'].isoformat() if m.get('fecha_pago') else '',
        }

    svc_list = [dict(r._mapping) for r in servicios]
    for s in svc_list:
        s['precio']      = float(s['precio']) if s.get('precio') is not None else 0.0
        s['incluye_igv'] = bool(s.get('incluye_igv'))

    # Servicios contratados activos (para el ticket)
    contratados = db.session.execute(text("""
        SELECT DISTINCT sv.nombre, sv.precio, sv.incluye_igv
        FROM suscripciones s
        JOIN suscripcion_servicios sv ON sv.id_servicio = s.id_servicio
        WHERE s.id_empresa IS NOT DISTINCT FROM :emp AND sv.id_estado = 1
        ORDER BY sv.nombre
    """), {'emp': id_empresa}).fetchall()

    contratados_list = [
        {'nombre': r[0], 'precio': float(r[1]), 'incluye_igv': bool(r[2])}
        for r in contratados
    ]

    return render_template(
        'main/pagos.html',
        title='Información de Pagos',
        section='', page='Información de Pagos',
        whs_name=current_user.whs_name,
        servicios=svc_list,
        anio_actual=anio,
        mes_actual=hoy.month,
        suscripciones_json=json.dumps([_suscripcion_to_dict(r) for r in suscripciones], ensure_ascii=False),
        pagos_mensuales_json=json.dumps([_pago_to_dict(r) for r in pagos_men], ensure_ascii=False),
        medios_json=json.dumps([_medio_to_dict(r) for r in medios], ensure_ascii=False),
        contratados_json=json.dumps(contratados_list, ensure_ascii=False),
    )


@main.route('/api/pagos/suscripciones/nueva', methods=['POST'])
@login_required
def api_pagos_suscripcion_nueva():
    data = request.get_json(force=True)
    try:
        id_servicio   = int(data.get('id_servicio') or 0)
        observaciones = (data.get('observaciones') or '').strip() or None
        if not id_servicio:
            return jsonify({'success': False, 'message': 'Seleccione un servicio.'}), 400

        svc = db.session.execute(
            text("SELECT precio, incluye_igv FROM suscripcion_servicios WHERE id_servicio = :id AND id_estado = 1"),
            {'id': id_servicio}
        ).fetchone()
        if not svc:
            return jsonify({'success': False, 'message': 'Servicio no encontrado.'}), 404

        precio = float(svc[0])
        if svc[1]:
            precio = round(precio * 1.18, 2)

        hoy  = date.today()
        venc = hoy + timedelta(days=30)

        db.session.execute(text("""
            INSERT INTO suscripciones
                (id_empresa, id_servicio, fecha_inicio, fecha_vencimiento,
                 precio_acordado, id_estado_pago, observaciones, user_code)
            VALUES (:emp, :svc, :inicio, :venc, :precio, 0, :obs, :user)
        """), {
            'emp':    current_user.id_empresa,
            'svc':    id_servicio,
            'inicio': hoy,
            'venc':   venc,
            'precio': precio,
            'obs':    observaciones,
            'user':   str(current_user.id_usuario),
        })
        db.session.commit()
        return jsonify({'success': True, 'message': 'Servicio agregado correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/pagos/suscripciones/<int:id_suscripcion>/estado', methods=['POST'])
@login_required
def api_pagos_suscripcion_estado(id_suscripcion):
    data = request.get_json(force=True)
    try:
        nuevo_estado = int(data.get('id_estado_pago') or 0)
        db.session.execute(text("""
            UPDATE suscripciones
               SET id_estado_pago = :est
             WHERE id_suscripcion = :id AND id_empresa IS NOT DISTINCT FROM :emp
        """), {'est': nuevo_estado, 'id': id_suscripcion, 'emp': current_user.id_empresa})
        db.session.commit()
        return jsonify({'success': True, 'message': 'Estado actualizado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/pagos/medios/guardar', methods=['POST'])
@login_required
def api_pagos_medio_guardar():
    data = request.get_json(force=True)
    try:
        tipo = (data.get('tipo') or '').strip().upper()
        if tipo not in ('TARJETA', 'YAPE'):
            return jsonify({'success': False, 'message': 'Tipo de medio inválido.'}), 400

        titular       = (data.get('titular')      or '').strip() or None
        numero_raw    = (data.get('numero')        or '').strip().replace(' ', '')
        numero_masked = ('**** **** **** ' + numero_raw[-4:]) if len(numero_raw) >= 4 else None
        marca         = (data.get('marca')         or '').strip().upper() or None
        vencimiento   = (data.get('vencimiento')   or '').strip() or None
        telefono_yape = (data.get('telefono_yape') or '').strip() or None

        if tipo == 'YAPE' and not telefono_yape:
            return jsonify({'success': False, 'message': 'Ingrese el número de teléfono Yape.'}), 400
        if tipo == 'TARJETA' and not numero_masked:
            return jsonify({'success': False, 'message': 'Ingrese el número de tarjeta.'}), 400

        db.session.execute(text("""
            INSERT INTO medios_pago
                (id_empresa, tipo, titular, numero_masked, marca, vencimiento, telefono_yape)
            VALUES (:emp, :tipo, :titular, :num, :marca, :venc, :yape)
        """), {
            'emp':     current_user.id_empresa,
            'tipo':    tipo,
            'titular': titular,
            'num':     numero_masked,
            'marca':   marca,
            'venc':    vencimiento,
            'yape':    telefono_yape,
        })
        db.session.commit()
        return jsonify({'success': True, 'message': 'Método de pago registrado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/pagos/medios/<int:id_medio>/eliminar', methods=['POST'])
@login_required
def api_pagos_medio_eliminar(id_medio):
    try:
        db.session.execute(text("""
            UPDATE medios_pago SET id_estado = 0
             WHERE id_medio = :id AND id_empresa IS NOT DISTINCT FROM :emp
        """), {'id': id_medio, 'emp': current_user.id_empresa})
        db.session.commit()
        return jsonify({'success': True, 'message': 'Método de pago eliminado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/pagos/confirmar-pago', methods=['POST'])
@login_required
def api_pagos_confirmar_pago():
    """Genera 12 registros mensuales del año actual.
       Mes actual = Pagado; los 11 restantes = Pendiente.
       No sobreescribe meses que ya estén marcados como Pagado.
    """
    try:
        id_empresa = current_user.id_empresa
        hoy        = date.today()
        anio       = hoy.year
        mes_actual = hoy.month

        # Servicios contratados activos para esta empresa
        rows = db.session.execute(text("""
            SELECT DISTINCT sv.nombre, sv.precio, sv.incluye_igv
            FROM suscripciones s
            JOIN suscripcion_servicios sv ON sv.id_servicio = s.id_servicio
            WHERE s.id_empresa IS NOT DISTINCT FROM :emp AND sv.id_estado = 1
        """), {'emp': id_empresa}).fetchall()

        if not rows:
            return jsonify({'success': False, 'message': 'No tiene servicios contratados activos.'}), 400

        # Calcular totales
        subtotal = 0.0
        igv_total = 0.0
        detalle = []
        for r in rows:
            precio = float(r[1])
            igv    = round(precio * 0.18, 2) if r[2] else 0.0
            subtotal  += precio
            igv_total += igv
            detalle.append({'nombre': r[0], 'precio': precio,
                            'igv': igv, 'incluye_igv': bool(r[2])})

        total_pago = round(subtotal + igv_total, 2)
        detalle_json = json.dumps(detalle, ensure_ascii=False)

        # Insertar solo el mes indicado (o el mes actual por defecto)
        data_req = request.get_json(force=True) or {}
        mes_pagar = int(data_req.get('mes') or mes_actual)
        if not 1 <= mes_pagar <= 12:
            return jsonify({'success': False, 'message': 'Mes inválido.'}), 400

        db.session.execute(text("""
            INSERT INTO pagos_mensuales
                (id_empresa, anio, mes, total_servicios, total_igv, total_pago,
                 id_estado_pago, fecha_pago, detalle_json, user_code)
            VALUES
                (:emp, :anio, :mes, :subtotal, :igv, :total,
                 1, :fecha_pago, CAST(:detalle AS JSONB), :user)
            ON CONFLICT (id_empresa, anio, mes) DO UPDATE
                SET total_servicios = EXCLUDED.total_servicios,
                    total_igv       = EXCLUDED.total_igv,
                    total_pago      = EXCLUDED.total_pago,
                    detalle_json    = EXCLUDED.detalle_json,
                    id_estado_pago  = 1,
                    fecha_pago      = EXCLUDED.fecha_pago
        """), {
            'emp':        id_empresa,
            'anio':       anio,
            'mes':        mes_pagar,
            'subtotal':   subtotal,
            'igv':        igv_total,
            'total':      total_pago,
            'fecha_pago': hoy,
            'detalle':    detalle_json,
            'user':       str(current_user.id_usuario),
        })

        db.session.commit()
        return jsonify({
            'success':    True,
            'message':    f'Pago de {_MESES_ES[mes_pagar-1]} {anio} registrado correctamente.',
            'total_pago': total_pago,
            'mes_pagado': mes_pagar,
            'anio':       anio,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
