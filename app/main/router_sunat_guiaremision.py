import json
import requests
from flask import current_app, Response, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


def _json_resp(data):
    """Response JSON que preserva el orden de las claves (sin sort_keys)."""
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json'
    )


def _num(v, default=0):
    """Convierte a número: int si es entero, float si tiene decimales."""
    try:
        f = float(v or default)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return default


def _str(v):
    return (v or '').strip() or None


# ── Construir payload SUNAT desde gr_id ──────────────────────────────────────

def _build_gr_payload(gr_id: int) -> dict:
    gr = db.session.execute(text("""
        SELECT gr_id, serie, numero, fecha_emision, hora_emision,
               modalidad_transporte, motivo_traslado, fecha_inicio_traslado,
               dest_tipo_doc, dest_num_doc, dest_denominacion, dest_direccion,
               partida_ubigeo, partida_direccion,
               llegada_ubigeo, llegada_direccion,
               peso_bruto_total, peso_bruto_uom, numero_bultos, observaciones,
               doc_rel_tipo, doc_rel_serie, doc_rel_numero, doc_rel_ruc_emisor,
               transp_ruc, transp_denominacion, transp_num_mtc,
               transp_num_autorizacion, transp_cod_entidad,
               conductores, vehiculos
        FROM   invoice_gr
        WHERE  gr_id = :id AND id_estado = 1
    """), {'id': gr_id}).fetchone()

    if not gr:
        raise ValueError(f'Guía #{gr_id} no encontrada o anulada.')

    g = dict(gr._mapping)

    items_rows = db.session.execute(text("""
        SELECT codigo_interno, descripcion, unidad_medida, cantidad
        FROM   invoice_gr_item
        WHERE  gr_id = :id
        ORDER  BY gr_item_id
    """), {'id': gr_id}).fetchall()

    # Documento relacionado — mismo orden que el JSON esperado
    doc_rel = []
    if g.get('doc_rel_serie'):
        tipo_map = {'01': 'factura', '03': 'boleta', '09': 'guia_remision_remitente'}
        doc_rel.append({
            'documento':  tipo_map.get((g.get('doc_rel_tipo') or ''), 'factura'),
            'serie':      (g.get('doc_rel_serie')      or '').strip(),
            'numero':     str(g.get('doc_rel_numero')  or ''),
            'ruc_emisor': (g.get('doc_rel_ruc_emisor') or '').strip(),
        })

    # Conductores — orden exacto del JSON esperado
    conductores_raw = g.get('conductores') or []
    if isinstance(conductores_raw, str):
        conductores_raw = json.loads(conductores_raw)
    conductores = [{
        'conductor':                c.get('conductor')               or 'principal',
        'tipo_de_documento':        c.get('tipo_de_documento')       or '1',
        'numero_de_documento':      c.get('numero_de_documento')     or '',
        'nombres':                  c.get('nombres')                 or '',
        'apellidos':                c.get('apellidos')               or '',
        'numero_licencia_conducir': c.get('numero_licencia_conducir') or '',
    } for c in conductores_raw]

    # Vehículos — orden exacto del JSON esperado
    vehiculos_raw = g.get('vehiculos') or []
    if isinstance(vehiculos_raw, str):
        vehiculos_raw = json.loads(vehiculos_raw)
    vehiculos = [{
        'vehiculo':        v.get('vehiculo')        or 'principal',
        'numero_de_placa': v.get('numero_de_placa') or '',
    } for v in vehiculos_raw]

    # Items — orden exacto: codigo_interno, descripcion, unidad_de_medida, cantidad
    items = [{
        'codigo_interno':   (r._mapping.get('codigo_interno') or ''),
        'descripcion':      (r._mapping.get('descripcion')    or ''),
        'unidad_de_medida': (r._mapping.get('unidad_medida')  or 'NIU'),
        'cantidad':         _num(r._mapping.get('cantidad'), 1),
    } for r in items_rows]

    # Fechas / hora
    def _d(v): return v.isoformat() if v and hasattr(v, 'isoformat') else (str(v) if v else '')
    hora = g.get('hora_emision')
    hora_str = hora.strftime('%H:%M:%S') if hora and hasattr(hora, 'strftime') else (str(hora)[:8] if hora else '00:00:00')

    # Payload en el orden EXACTO del JSON requerido por apisunat.pe
    return {
        'documento':                         'guia_remision_remitente',
        'serie':                             (g.get('serie')   or '').strip(),
        'numero':                            str(g.get('numero') or ''),
        'fecha_de_emision':                  _d(g.get('fecha_emision')),
        'hora_de_emision':                   hora_str,
        'modalidad_de_transporte':           g.get('modalidad_transporte') or '02',
        'motivo_de_traslado':                g.get('motivo_traslado')      or '01',
        'fecha_inicio_de_traslado':          _d(g.get('fecha_inicio_traslado')),
        'destinatario_tipo_de_documento':    g.get('dest_tipo_doc')       or '6',
        'destinatario_numero_de_documento':  (g.get('dest_num_doc')       or '').strip(),
        'destinatario_denominacion':         (g.get('dest_denominacion')  or '').strip(),
        'destinatario_direccion':            (g.get('dest_direccion')     or '').strip(),
        'punto_de_partida_ubigeo':           (g.get('partida_ubigeo')     or '').strip(),
        'punto_de_partida_direccion':        (g.get('partida_direccion')  or '').strip(),
        'punto_de_llegada_ubigeo':           (g.get('llegada_ubigeo')     or '').strip(),
        'punto_de_llegada_direccion':        (g.get('llegada_direccion')  or '').strip(),
        'peso_bruto_total':                  str(float(g.get('peso_bruto_total') or 0)),
        'peso_bruto_unidad_de_medida':       g.get('peso_bruto_uom') or 'KGM',
        'numero_de_bultos':                  int(g.get('numero_bultos') or 1),
        'observaciones':                     _str(g.get('observaciones')),
        'documentos_relacionados':           doc_rel,
        'transportista': {
            'ruc':                         (g.get('transp_ruc')              or '').strip(),
            'denominacion':                (g.get('transp_denominacion')     or '').strip(),
            'numero_registro_MTC':         (g.get('transp_num_mtc')          or '').strip(),
            'numero_autorizacion':         (g.get('transp_num_autorizacion') or '').strip(),
            'codigo_entidad_autorizadora': (g.get('transp_cod_entidad')      or '').strip(),
        },
        'conductores': conductores,
        'vehiculos':   vehiculos,
        'items':       items,
    }


# ── Rutas ─────────────────────────────────────────────────────────────────────

@main.route('/api/sunat/gr/preview/<int:gr_id>')
@login_required
def sunat_gr_preview(gr_id):
    """Devuelve el JSON que se enviaría a SUNAT preservando el orden de campos."""
    try:
        payload = _build_gr_payload(gr_id)
        config  = {
            'modo': current_app.config.get('APISUNAT_MODO'),
            'url':  current_app.config.get('APISUNAT_GR_URL'),
        }
        return _json_resp({'success': True, 'payload': payload, 'config': config})
    except ValueError as e:
        return _json_resp({'success': False, 'message': str(e)})
    except Exception as e:
        return _json_resp({'success': False, 'message': str(e)})


@main.route('/api/sunat/gr/enviar/<int:gr_id>', methods=['POST'])
@login_required
def sunat_gr_enviar(gr_id):
    """Envía la guía de remisión a la API de SUNAT y guarda el resultado."""
    try:
        payload = _build_gr_payload(gr_id)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al preparar datos: {e}'}), 500

    token = current_app.config['APISUNAT_TOKEN']
    url   = current_app.config['APISUNAT_GR_URL']

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            },
            timeout=30,
        )
        resp_data = resp.json() if resp.content else {}
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': 'Timeout al conectar con SUNAT.'}), 504
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error de conexión: {e}'}), 502

    ok      = resp.status_code in (200, 201)
    inner   = resp_data.get('payload') or {}
    estado  = inner.get('estado') or ('ACEPTADO' if ok else f'ERROR_{resp.status_code}')
    hash_   = inner.get('hash', '')
    xml_url = inner.get('xml', '')
    cdr_url = inner.get('cdr', '')
    pdf     = inner.get('pdf') or {}
    ticket  = pdf.get('ticket', '')
    a4_url  = pdf.get('a4', '')
    msg_api = resp_data.get('message', '')

    try:
        db.session.execute(text("""
            UPDATE invoice_gr
               SET sunat_estado = :estado,
                   sunat_hash   = :hash,
                   sunat_xml    = :xml,
                   sunat_cdr    = :cdr,
                   sunat_ticket = :ticket,
                   sunat_a4     = :a4
             WHERE gr_id = :id
        """), {
            'estado': estado, 'hash': hash_, 'xml': xml_url,
            'cdr': cdr_url,  'ticket': ticket, 'a4': a4_url, 'id': gr_id,
        })
        db.session.commit()
    except Exception:
        db.session.rollback()

    if ok:
        return jsonify({
            'success':      True,
            'message':      msg_api or f'Guía #{gr_id} enviada correctamente a SUNAT.',
            'sunat_estado': estado,
            'sunat_hash':   hash_,
            'sunat_xml':    xml_url,
            'sunat_cdr':    cdr_url,
            'sunat_ticket': ticket,
            'sunat_a4':     a4_url,
        })

    return jsonify({
        'success':      False,
        'message':      msg_api or f'SUNAT respondió con error {resp.status_code}.',
        'sunat_estado': estado,
        'url_usada':    url,
        'response':     resp_data,
    }), resp.status_code
