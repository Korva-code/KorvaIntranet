import json
from datetime import date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db

_MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
          'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

_PROCESOS = {
    'VENTAS':         'Ventas',
    'CANCELACIONES':  'Cancelaciones Ventas',
    'ESTADOS_CUENTA': 'Estados de Cuenta',
}


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_cierre':            m.get('id_cierre'),
        'tipo_proceso':         m.get('tipo_proceso') or 'VENTAS',
        'tipo_periodo':         m.get('tipo_periodo') or 'DIA',
        'periodo_anio':         m.get('periodo_anio'),
        'periodo_mes':          m.get('periodo_mes'),
        'periodo_dia':          m.get('periodo_dia'),
        'total_documentos':     m.get('total_documentos') or 0,
        'total_importe':        float(m['total_importe'])        if m.get('total_importe')        is not None else 0.0,
        'total_aplicados':      m.get('total_aplicados')      or 0,
        'total_sunat_aceptado': m.get('total_sunat_aceptado') or 0,
        'total_pendientes':     m.get('total_pendientes')     or 0,
        'total_anulados':       m.get('total_anulados')       or 0,
        'total_margen':          float(m['total_margen'])          if m.get('total_margen')          is not None else 0.0,
        'total_margen_bienes':   float(m['total_margen_bienes'])   if m.get('total_margen_bienes')   is not None else 0.0,
        'total_margen_servicios':float(m['total_margen_servicios'])if m.get('total_margen_servicios')is not None else 0.0,
        'observaciones':        m.get('observaciones') or '',
        'user_code':            m.get('user_code') or '',
        'fecha_registro':       m['fecha_registro'].isoformat() if m.get('fecha_registro') else '',
        'id_estado':            m.get('id_estado') if m.get('id_estado') is not None else 1,
    }


# ── Helpers de cálculo ────────────────────────────────────────────

def _calcular_ventas(anio, mes, dia):
    row = db.session.execute(text("""
        SELECT
            COUNT(DISTINCT i.invoice_id)                                               AS total_documentos,
            COALESCE(SUM(DISTINCT i.doc_total), 0)                                     AS total_importe,
            COUNT(DISTINCT i.invoice_id) FILTER (WHERE COALESCE(i.doc_status,1) = 2)  AS total_aplicados,
            COUNT(DISTINCT i.invoice_id) FILTER (WHERE i.sunat_estado = 'ACEPTADO')   AS total_sunat_aceptado,
            COUNT(DISTINCT i.invoice_id) FILTER (
                WHERE COALESCE(i.doc_status,1) = 1
                  AND (i.sunat_estado IS NULL
                   OR  i.sunat_estado NOT IN ('ACEPTADO','ANULADO'))
            )                                                                          AS total_pendientes,
            COUNT(DISTINCT i.invoice_id) FILTER (WHERE COALESCE(i.doc_status,1) = 3) AS total_anulados,
            COALESCE(SUM((ii.price - ii.price_cost) * ii.quantity), 0)                AS total_margen,
            COALESCE(SUM(CASE WHEN it."TipoBien" = 1
                         THEN (ii.price - ii.price_cost) * ii.quantity ELSE 0 END), 0) AS total_margen_bienes,
            COALESCE(SUM(CASE WHEN it."TipoBien" = 2
                         THEN (ii.price - ii.price_cost) * ii.quantity ELSE 0 END), 0) AS total_margen_servicios
        FROM invoice i
        LEFT JOIN invoice_item ii ON ii.invoice_id = i.invoice_id
        LEFT JOIN items         it ON it.item_code  = ii.item_code
        WHERE EXTRACT(YEAR  FROM i.doc_date) = :anio
          AND (:mes IS NULL OR EXTRACT(MONTH FROM i.doc_date) = :mes)
          AND (:dia IS NULL OR EXTRACT(DAY   FROM i.doc_date) = :dia)
    """), {'anio': anio, 'mes': mes, 'dia': dia}).fetchone()
    return row


def _calcular_cancelaciones(anio, mes, dia):
    row = db.session.execute(text("""
        SELECT
            COUNT(*)                                              AS total_documentos,
            COALESCE(SUM(monto_aplicado), 0)                     AS total_importe,
            COUNT(*) FILTER (WHERE id_estado = 1)                AS total_aplicados,
            0                                                    AS total_sunat_aceptado,
            COUNT(*) FILTER (WHERE id_estado <> 1)               AS total_pendientes
        FROM invoice_cancelaciones
        WHERE EXTRACT(YEAR  FROM fecha_pago) = :anio
          AND (:mes IS NULL OR EXTRACT(MONTH FROM fecha_pago) = :mes)
          AND (:dia IS NULL OR EXTRACT(DAY   FROM fecha_pago) = :dia)
    """), {'anio': anio, 'mes': mes, 'dia': dia}).fetchone()
    return row


def _calcular_estados_cuenta(anio, mes, dia):
    row = db.session.execute(text("""
        SELECT
            COUNT(*)                         AS total_documentos,
            COALESCE(SUM(monto_aplicado), 0) AS total_importe,
            COUNT(*)                         AS total_aplicados,
            0                                AS total_sunat_aceptado,
            0                                AS total_pendientes
        FROM bancos_estado_cuenta
        WHERE EXTRACT(YEAR  FROM fecha_pago) = :anio
          AND (:mes IS NULL OR EXTRACT(MONTH FROM fecha_pago) = :mes)
          AND (:dia IS NULL OR EXTRACT(DAY   FROM fecha_pago) = :dia)
    """), {'anio': anio, 'mes': mes, 'dia': dia}).fetchone()
    return row


# ── Rutas ─────────────────────────────────────────────────────────

@main.route('/maestras/cierres')
@login_required
def cierres():
    rows = db.session.execute(text("""
        SELECT * FROM cierres
        ORDER BY periodo_anio DESC, COALESCE(periodo_mes,0) DESC,
                 COALESCE(periodo_dia,0) DESC, id_cierre DESC
    """)).fetchall()
    datos = [_row_to_dict(r) for r in rows]
    hoy   = date.today()
    anios = list(range(hoy.year, hoy.year - 6, -1))
    return render_template(
        'main/cierres.html',
        title='Cierres por Proceso',
        section='Maestras', page='Cierres',
        datos_json=json.dumps(datos, ensure_ascii=False),
        total=len(datos),
        meses=_MESES,
        anios=anios,
        procesos=_PROCESOS,
        hoy_anio=hoy.year,
        hoy_mes=hoy.month,
        hoy_dia=hoy.day,
    )


@main.route('/api/cierres/calcular', methods=['POST'])
@login_required
def api_cierres_calcular():
    data         = request.get_json(force=True)
    tipo_proceso = (data.get('tipo_proceso') or 'VENTAS').strip().upper()
    tipo_periodo = (data.get('tipo_periodo') or 'DIA').strip().upper()
    try:
        anio = int(data.get('periodo_anio') or 0)
        mes  = int(data.get('periodo_mes')  or 0) or None
        dia  = int(data.get('periodo_dia')  or 0) or None
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Período inválido.'}), 400

    if not anio:
        return jsonify({'success': False, 'message': 'Ingrese el año.'}), 400
    if tipo_periodo in ('DIA', 'MES') and not mes:
        return jsonify({'success': False, 'message': 'Ingrese el mes.'}), 400
    if tipo_periodo == 'DIA' and not dia:
        return jsonify({'success': False, 'message': 'Ingrese el día.'}), 400

    if tipo_periodo == 'ANIO':
        mes = dia = None
    elif tipo_periodo == 'MES':
        dia = None

    try:
        if tipo_proceso == 'VENTAS':
            row = _calcular_ventas(anio, mes, dia)
        elif tipo_proceso == 'CANCELACIONES':
            row = _calcular_cancelaciones(anio, mes, dia)
        elif tipo_proceso == 'ESTADOS_CUENTA':
            row = _calcular_estados_cuenta(anio, mes, dia)
        else:
            return jsonify({'success': False, 'message': 'Proceso no reconocido.'}), 400

        es_ventas = tipo_proceso == 'VENTAS'
        anulados          = int(row[5]   or 0)   if es_ventas else 0
        margen            = float(row[6] or 0)   if es_ventas else 0.0
        margen_bienes     = float(row[7] or 0)   if es_ventas else 0.0
        margen_servicios  = float(row[8] or 0)   if es_ventas else 0.0
        return jsonify({
            'success':                True,
            'total_documentos':       int(row[0]   or 0),
            'total_importe':          float(row[1] or 0),
            'total_aplicados':        int(row[2]   or 0),
            'total_sunat_aceptado':   int(row[3]   or 0),
            'total_pendientes':       int(row[4]   or 0),
            'total_anulados':         anulados,
            'total_margen':           margen,
            'total_margen_bienes':    margen_bienes,
            'total_margen_servicios': margen_servicios,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/maestras/cierres/guardar', methods=['POST'])
@login_required
def cierres_guardar():
    data = request.get_json(force=True)
    try:
        id_cierre            = int(data.get('id_cierre')    or 0)
        tipo_proceso         = (data.get('tipo_proceso') or 'VENTAS').strip().upper()
        tipo_periodo         = (data.get('tipo_periodo') or 'DIA').strip().upper()
        periodo_anio         = int(data.get('periodo_anio') or 0)
        periodo_mes          = int(data.get('periodo_mes')  or 0) or None
        periodo_dia          = int(data.get('periodo_dia')  or 0) or None
        total_documentos     = int(data.get('total_documentos')     or 0)
        total_importe        = float(data.get('total_importe')      or 0)
        total_aplicados      = int(data.get('total_aplicados')      or 0)
        total_sunat_aceptado = int(data.get('total_sunat_aceptado') or 0)
        total_pendientes     = int(data.get('total_pendientes')     or 0)
        total_anulados        = int(data.get('total_anulados')        or 0)
        total_margen          = float(data.get('total_margen')        or 0)
        total_margen_bienes   = float(data.get('total_margen_bienes')   or 0)
        total_margen_servicios= float(data.get('total_margen_servicios')or 0)
        observaciones         = (data.get('observaciones') or '').strip() or None

        if not periodo_anio:
            return jsonify({'success': False, 'message': 'Año requerido.'}), 400

        if tipo_periodo == 'ANIO':
            periodo_mes = periodo_dia = None
        elif tipo_periodo == 'MES':
            periodo_dia = None

        params = {
            'proceso':      tipo_proceso,
            'periodo':      tipo_periodo,
            'anio':         periodo_anio,
            'mes':          periodo_mes,
            'dia':          periodo_dia,
            'total_doc':    total_documentos,
            'total_imp':    total_importe,
            'total_apl':    total_aplicados,
            'total_sunat':  total_sunat_aceptado,
            'total_pend':   total_pendientes,
            'total_anul':            total_anulados,
            'total_margen':          total_margen,
            'total_margen_bienes':   total_margen_bienes,
            'total_margen_servicios':total_margen_servicios,
            'obs':                   observaciones,
            'user':                  str(current_user.id_usuario),
        }

        if id_cierre > 0:
            params['id_cierre'] = id_cierre
            db.session.execute(text("""
                UPDATE cierres SET
                    tipo_proceso          = :proceso,
                    tipo_periodo          = :periodo,
                    periodo_anio          = :anio,
                    periodo_mes           = :mes,
                    periodo_dia           = :dia,
                    total_documentos      = :total_doc,
                    total_importe         = :total_imp,
                    total_aplicados       = :total_apl,
                    total_sunat_aceptado  = :total_sunat,
                    total_pendientes      = :total_pend,
                    total_anulados        = :total_anul,
                    total_margen          = :total_margen,
                    total_margen_bienes   = :total_margen_bienes,
                    total_margen_servicios= :total_margen_servicios,
                    observaciones         = :obs
                WHERE id_cierre = :id_cierre
            """), params)
            msg = 'Cierre actualizado correctamente.'
        else:
            db.session.execute(text("""
                INSERT INTO cierres (
                    tipo_proceso, tipo_periodo, periodo_anio, periodo_mes, periodo_dia,
                    total_documentos, total_importe, total_aplicados,
                    total_sunat_aceptado, total_pendientes, total_anulados, total_margen,
                    total_margen_bienes, total_margen_servicios,
                    observaciones, user_code, id_estado
                ) VALUES (
                    :proceso, :periodo, :anio, :mes, :dia,
                    :total_doc, :total_imp, :total_apl,
                    :total_sunat, :total_pend, :total_anul, :total_margen,
                    :total_margen_bienes, :total_margen_servicios,
                    :obs, :user, 1
                )
            """), params)
            msg = 'Cierre registrado correctamente.'

        db.session.commit()
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/maestras/cierres/<int:id_cierre>/anular', methods=['POST'])
@login_required
def cierres_anular(id_cierre):
    try:
        db.session.execute(
            text("UPDATE cierres SET id_estado = 0 WHERE id_cierre = :id"),
            {'id': id_cierre}
        )
        db.session.commit()
        return jsonify({'success': True, 'message': f'Cierre #{id_cierre} anulado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
