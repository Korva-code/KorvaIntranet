import json
from datetime import date, datetime
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


# ── helpers ───────────────────────────────────────────────────

def _row_to_dict(r):
    m = dict(r._mapping)
    def _d(v): return v.isoformat() if v else ''
    def _ts(v): return v.isoformat(sep=' ', timespec='seconds') if v else ''
    return {
        'gr_id':                   m.get('gr_id'),
        'serie':                   m.get('serie') or '',
        'numero':                  m.get('numero') or '',
        'fecha_emision':           _d(m.get('fecha_emision')),
        'hora_emision':            m.get('hora_emision') or '',
        'modalidad_transporte':    m.get('modalidad_transporte') or '02',
        'motivo_traslado':         m.get('motivo_traslado') or '01',
        'fecha_inicio_traslado':   _d(m.get('fecha_inicio_traslado')),
        'dest_tipo_doc':           m.get('dest_tipo_doc') or '6',
        'dest_num_doc':            m.get('dest_num_doc') or '',
        'dest_denominacion':       m.get('dest_denominacion') or '',
        'dest_direccion':          m.get('dest_direccion') or '',
        'whs_code':                m.get('whs_code') or '',
        'partida_ubigeo':          m.get('partida_ubigeo') or '',
        'partida_direccion':       m.get('partida_direccion') or '',
        'llegada_ubigeo':          m.get('llegada_ubigeo') or '',
        'llegada_direccion':       m.get('llegada_direccion') or '',
        'peso_bruto_total':        float(m['peso_bruto_total']) if m.get('peso_bruto_total') is not None else 0.0,
        'peso_bruto_uom':          m.get('peso_bruto_uom') or 'KGM',
        'numero_bultos':           m.get('numero_bultos') or 1,
        'observaciones':           m.get('observaciones') or '',
        'doc_rel_tipo':            m.get('doc_rel_tipo') or '',
        'doc_rel_serie':           m.get('doc_rel_serie') or '',
        'doc_rel_numero':          m.get('doc_rel_numero') or '',
        'doc_rel_ruc_emisor':      m.get('doc_rel_ruc_emisor') or '',
        'transp_ruc':              m.get('transp_ruc') or '',
        'transp_denominacion':     m.get('transp_denominacion') or '',
        'transp_num_mtc':          m.get('transp_num_mtc') or '',
        'transp_num_autorizacion': m.get('transp_num_autorizacion') or '',
        'transp_cod_entidad':      m.get('transp_cod_entidad') or '',
        'conductores':             m.get('conductores') or [],
        'vehiculos':               m.get('vehiculos') or [],
        'id_estado':               m.get('id_estado') if m.get('id_estado') is not None else 1,
        'user_code':               m.get('user_code') or '',
        'user_name':               m.get('user_name') or '',
        'fecha_registro':          _ts(m.get('fecha_registro')),
        'items':                   [],
    }


def _item_to_dict(r):
    m = dict(r._mapping)
    return {
        'gr_item_id':    m.get('gr_item_id'),
        'gr_id':         m.get('gr_id'),
        'codigo_interno': m.get('codigo_interno') or '',
        'descripcion':   m.get('descripcion') or '',
        'unidad_medida': m.get('unidad_medida') or 'NIU',
        'cantidad':      float(m['cantidad']) if m.get('cantidad') is not None else 1.0,
    }


def _parse_date(s):
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d').date() if s and s.strip() else None
    except ValueError:
        return None


# ── Listado ───────────────────────────────────────────────────

@main.route('/ventas/guias-remision')
@login_required
def invoice_gr_list():
    gr_rows   = db.session.execute(text("SELECT * FROM sp_gr_listar(0)")).fetchall()
    item_rows = db.session.execute(text("SELECT * FROM sp_gr_items_listar(0)")).fetchall()

    items_by_gr = {}
    for r in item_rows:
        d = _item_to_dict(r)
        items_by_gr.setdefault(d['gr_id'], []).append(d)

    gr_list = []
    for r in gr_rows:
        d = _row_to_dict(r)
        d['items'] = items_by_gr.get(d['gr_id'], [])
        gr_list.append(d)

    tipo_rows  = db.session.execute(text("SELECT * FROM invoice_type_lista(1)")).fetchall()
    inv_types  = [{'idtype': dict(r._mapping).get('idtype'),
                   'invoice_type': dict(r._mapping).get('invoice_type') or ''}
                  for r in tipo_rows]

    try:
        whs_rows = db.session.execute(text("""
            SELECT whs_code, TRIM(whs_name) AS whs_name,
                   COALESCE(address, street, '') AS address,
                   COALESCE(ubigeo, '')          AS ubigeo
            FROM   warehouses
            ORDER  BY whs_name
        """)).fetchall()
        warehouses = [{
            'whs_code': r[0] or '',
            'whs_name': r[1] or '',
            'address':  r[2] or '',
            'ubigeo':   r[3] or '',
        } for r in whs_rows]
    except Exception:
        db.session.rollback()
        warehouses = []

    transp_rows = db.session.execute(text("""
        SELECT card_code, card_name,
               COALESCE(federal_tax_id,          '') AS ruc,
               COALESCE(transp_num_mtc,          '') AS transp_num_mtc,
               COALESCE(transp_num_autorizacion, '') AS transp_num_autorizacion,
               COALESCE(transp_cod_entidad,      '') AS transp_cod_entidad
        FROM   business_partners
        WHERE  card_type = '5'
        ORDER  BY card_name
    """)).fetchall()
    transportistas = [{
        'card_code':              r[0] or '',
        'card_name':              r[1] or '',
        'ruc':                    r[2],
        'transp_num_mtc':         r[3],
        'transp_num_autorizacion':r[4],
        'transp_cod_entidad':     r[5],
    } for r in transp_rows]

    return render_template(
        'main/invoice_gr.html',
        title='Guías de Remisión',
        section='Ventas', page='Guías de Remisión',
        gr_json=json.dumps(gr_list, ensure_ascii=False, default=str),
        inv_types_json=json.dumps(inv_types, ensure_ascii=False),
        transportistas_json=json.dumps(transportistas, ensure_ascii=False),
        warehouses_json=json.dumps(warehouses, ensure_ascii=False),
        total=len(gr_list),
        today=date.today().isoformat(),
    )


# ── Guardar (insert / update) ─────────────────────────────────

@main.route('/api/gr/guardar', methods=['POST'])
@login_required
def api_gr_guardar():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'success': False, 'message': 'Payload vacío.'}), 400

    try:
        gr_id     = int(data.get('gr_id') or 0)
        items     = data.get('items')       or []
        cond_json = json.dumps(data.get('conductores') or [], ensure_ascii=False)
        veh_json  = json.dumps(data.get('vehiculos')   or [], ensure_ascii=False)

        p = {
            'serie':                   (data.get('serie')                   or '').strip() or None,
            'numero':                  (data.get('numero')                  or '').strip() or None,
            'fecha_emision':           data.get('fecha_emision')            or None,
            'hora_emision':            (data.get('hora_emision')            or '').strip() or None,
            'modalidad_transporte':    (data.get('modalidad_transporte')    or '02'),
            'motivo_traslado':         (data.get('motivo_traslado')         or '01'),
            'fecha_inicio_traslado':   data.get('fecha_inicio_traslado')    or None,
            'dest_tipo_doc':           (data.get('dest_tipo_doc')           or '6'),
            'dest_num_doc':            (data.get('dest_num_doc')            or '').strip() or None,
            'dest_denominacion':       (data.get('dest_denominacion')       or '').strip() or None,
            'dest_direccion':          (data.get('dest_direccion')          or '').strip() or None,
            'whs_code':                (data.get('whs_code')                or '').strip() or None,
            'partida_ubigeo':          (data.get('partida_ubigeo')          or '').strip() or None,
            'partida_direccion':       (data.get('partida_direccion')       or '').strip() or None,
            'llegada_ubigeo':          (data.get('llegada_ubigeo')          or '').strip() or None,
            'llegada_direccion':       (data.get('llegada_direccion')       or '').strip() or None,
            'peso_bruto_total':        float(data.get('peso_bruto_total')   or 0),
            'peso_bruto_uom':          (data.get('peso_bruto_uom')          or 'KGM'),
            'numero_bultos':           int(data.get('numero_bultos')        or 1),
            'observaciones':           (data.get('observaciones')           or '').strip() or None,
            'doc_rel_tipo':            (data.get('doc_rel_tipo')            or '').strip() or None,
            'doc_rel_serie':           (data.get('doc_rel_serie')           or '').strip() or None,
            'doc_rel_numero':          (data.get('doc_rel_numero')          or '').strip() or None,
            'doc_rel_ruc_emisor':      (data.get('doc_rel_ruc_emisor')      or '').strip() or None,
            'transp_ruc':              (data.get('transp_ruc')              or '').strip() or None,
            'transp_denominacion':     (data.get('transp_denominacion')     or '').strip() or None,
            'transp_num_mtc':          (data.get('transp_num_mtc')          or '').strip() or None,
            'transp_num_autorizacion': (data.get('transp_num_autorizacion') or '').strip() or None,
            'transp_cod_entidad':      (data.get('transp_cod_entidad')      or '').strip() or None,
            'conductores':             cond_json,
            'vehiculos':               veh_json,
            'user_code':               current_user.id_usuario,
        }

        if gr_id == 0:
            row = db.session.execute(text("""
                INSERT INTO invoice_gr (
                    serie, numero, fecha_emision, hora_emision,
                    modalidad_transporte, motivo_traslado, fecha_inicio_traslado,
                    dest_tipo_doc, dest_num_doc, dest_denominacion, dest_direccion,
                    whs_code, partida_ubigeo, partida_direccion,
                    llegada_ubigeo, llegada_direccion,
                    peso_bruto_total, peso_bruto_uom, numero_bultos, observaciones,
                    doc_rel_tipo, doc_rel_serie, doc_rel_numero, doc_rel_ruc_emisor,
                    transp_ruc, transp_denominacion, transp_num_mtc,
                    transp_num_autorizacion, transp_cod_entidad,
                    conductores, vehiculos, user_code
                ) VALUES (
                    :serie, :numero, :fecha_emision, :hora_emision,
                    :modalidad_transporte, :motivo_traslado, :fecha_inicio_traslado,
                    :dest_tipo_doc, :dest_num_doc, :dest_denominacion, :dest_direccion,
                    :whs_code, :partida_ubigeo, :partida_direccion,
                    :llegada_ubigeo, :llegada_direccion,
                    :peso_bruto_total, :peso_bruto_uom, :numero_bultos, :observaciones,
                    :doc_rel_tipo, :doc_rel_serie, :doc_rel_numero, :doc_rel_ruc_emisor,
                    :transp_ruc, :transp_denominacion, :transp_num_mtc,
                    :transp_num_autorizacion, :transp_cod_entidad,
                    :conductores, :vehiculos, :user_code
                ) RETURNING gr_id
            """), p)
            new_id = row.scalar()
            # Actualizar el correlativo en invoce_doc_number para la siguiente GR
            db.session.execute(text("""
                UPDATE invoce_doc_number
                   SET invoice_number = :num
                 WHERE idtype = 7
                   AND TRIM(invoice_serie) = :serie
            """), {'num': int(p['numero'] or 0), 'serie': (p['serie'] or '').strip()})
        else:
            p['gr_id'] = gr_id
            db.session.execute(text("""
                UPDATE invoice_gr SET
                    serie                   = :serie,
                    numero                  = :numero,
                    fecha_emision           = :fecha_emision,
                    hora_emision            = :hora_emision,
                    modalidad_transporte    = :modalidad_transporte,
                    motivo_traslado         = :motivo_traslado,
                    fecha_inicio_traslado   = :fecha_inicio_traslado,
                    dest_tipo_doc           = :dest_tipo_doc,
                    dest_num_doc            = :dest_num_doc,
                    dest_denominacion       = :dest_denominacion,
                    dest_direccion          = :dest_direccion,
                    whs_code                = :whs_code,
                    partida_ubigeo          = :partida_ubigeo,
                    partida_direccion       = :partida_direccion,
                    llegada_ubigeo          = :llegada_ubigeo,
                    llegada_direccion       = :llegada_direccion,
                    peso_bruto_total        = :peso_bruto_total,
                    peso_bruto_uom          = :peso_bruto_uom,
                    numero_bultos           = :numero_bultos,
                    observaciones           = :observaciones,
                    doc_rel_tipo            = :doc_rel_tipo,
                    doc_rel_serie           = :doc_rel_serie,
                    doc_rel_numero          = :doc_rel_numero,
                    doc_rel_ruc_emisor      = :doc_rel_ruc_emisor,
                    transp_ruc              = :transp_ruc,
                    transp_denominacion     = :transp_denominacion,
                    transp_num_mtc          = :transp_num_mtc,
                    transp_num_autorizacion = :transp_num_autorizacion,
                    transp_cod_entidad      = :transp_cod_entidad,
                    conductores             = :conductores,
                    vehiculos               = :vehiculos,
                    user_code               = :user_code
                WHERE gr_id = :gr_id
            """), p)
            db.session.execute(text(
                "DELETE FROM invoice_gr_item WHERE gr_id = :gr_id"
            ), {'gr_id': gr_id})
            new_id = gr_id

        for it in items:
            db.session.execute(text("""
                INSERT INTO invoice_gr_item (gr_id, codigo_interno, descripcion, unidad_medida, cantidad)
                VALUES (:gr_id, :codigo, :desc, :uom, :qty)
            """), {
                'gr_id':  new_id,
                'codigo': (it.get('codigo_interno') or '').strip() or None,
                'desc':   (it.get('descripcion')    or '').strip() or None,
                'uom':    (it.get('unidad_medida')  or 'NIU').strip(),
                'qty':    float(it.get('cantidad')  or 1),
            })

        db.session.commit()
        return jsonify({'success': True, 'gr_id': new_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Anular ────────────────────────────────────────────────────

@main.route('/api/gr/<int:gr_id>/anular', methods=['POST'])
@login_required
def api_gr_anular(gr_id):
    try:
        db.session.execute(text("SELECT sp_gr_anular(:id)"), {'id': gr_id})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Buscar factura → prefill GR ───────────────────────────────

@main.route('/api/gr/buscar-factura')
@login_required
def api_gr_buscar_factura():
    idtype_str = (request.args.get('idtype') or '').strip()
    serie      = (request.args.get('serie')  or '').strip()
    numero_str = (request.args.get('numero') or '').strip()
    if not serie or not numero_str:
        return jsonify({'success': False, 'message': 'Ingrese serie y número.'}), 400

    # Normalizar: serie siempre en mayúsculas sin espacios
    serie = serie.upper().strip()

    # Comparamos todo como TEXT para evitar conflictos de tipo con SQLAlchemy
    params = {'serie': serie, 'numero': numero_str}
    if idtype_str:
        where_idtype = 'AND i.idtype::TEXT = :idtype'
        params['idtype'] = idtype_str
    else:
        where_idtype = ''

    row = db.session.execute(text(f"""
        SELECT
            i.invoice_id,
            i.card_code,
            COALESCE(bp.federal_tax_id, '')          AS bp_ruc,
            COALESCE(bp.card_name, i.card_code, '')  AS bp_name,
            COALESCE(bp.u_bpp_bptd, '6')             AS bp_tipo_doc
        FROM   invoice i
        LEFT   JOIN business_partners bp ON bp.card_code = i.card_code
        WHERE  UPPER(TRIM(i.invoice_serie)) = :serie
          AND  i.invoice_number::TEXT       = :numero
          {where_idtype}
        LIMIT  1
    """), params).fetchone()

    if not row:
        label = f'{serie}-{numero_str}'
        return jsonify({'success': False, 'message': f'Documento {label} no encontrado.'}), 404

    m = dict(row._mapping)

    # Items de la factura con descripción
    items_rows = db.session.execute(text("""
        SELECT
            ii.item_code,
            COALESCE(it.item_name, ii.item_code, '')  AS item_name,
            COALESCE(it.sal_unit_msr, 'NIU')          AS uom,
            COALESCE(ii.quantity, 1)                  AS quantity
        FROM   invoice_item ii
        LEFT   JOIN items it ON it.item_code = ii.item_code
        WHERE  ii.invoice_id = :inv_id
        ORDER  BY ii.item_code
    """), {'inv_id': m['invoice_id']}).fetchall()

    items = [
        {
            'codigo_interno': r[0] or '',
            'descripcion':    r[1] or '',
            'unidad_medida':  (r[2] or 'NIU').strip(),
            'cantidad':       float(r[3]) if r[3] is not None else 1.0,
        }
        for r in items_rows
    ]

    # Dirección fiscal del destinatario
    card_code = m.get('card_code') or ''
    fiscal_row = db.session.execute(text("""
        SELECT TRIM(COALESCE(street,'')) ||
               CASE WHEN COALESCE(street_no,'') <> '' THEN ' ' || street_no ELSE '' END
               AS direccion
        FROM   business_partners_addresses
        WHERE  bp_code      = :bp_code
          AND  address_name = 'DIRECCION FISCAL'
        LIMIT  1
    """), {'bp_code': card_code}).fetchone()
    dest_direccion = (fiscal_row[0] or '') if fiscal_row else ''

    # Todas las direcciones del destinatario para el select de llegada
    addr_rows = db.session.execute(text("""
        SELECT address_name,
               TRIM(COALESCE(street,'')) ||
               CASE WHEN COALESCE(street_no,'') <> '' THEN ' ' || street_no ELSE '' END
               AS direccion,
               COALESCE(ubigeo, '') AS ubigeo
        FROM   business_partners_addresses
        WHERE  bp_code = :bp_code
        ORDER  BY address_name
    """), {'bp_code': card_code}).fetchall()
    direcciones = [
        {'label': r[0] or '', 'direccion': r[1] or '', 'ubigeo': r[2] or ''}
        for r in addr_rows
    ]

    return jsonify({
        'success': True,
        'factura': {
            'invoice_id':      m.get('invoice_id'),
            'dest_tipo_doc':   m.get('bp_tipo_doc') or '6',
            'dest_num_doc':    m.get('bp_ruc') or '',
            'dest_nombre':     m.get('bp_name') or '',
            'dest_direccion':  dest_direccion,
            'direcciones':     direcciones,
        },
        'items': items,
    })


# ── Buscar transportista desde socios_negocio ─────────────────

@main.route('/api/gr/buscar-transportista')
@login_required
def api_gr_buscar_transportista():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'success': False, 'message': 'Ingrese RUC o nombre.'}), 400

    row = db.session.execute(text("""
        SELECT card_code, card_name, federal_tax_id
        FROM   business_partners
        WHERE  TRIM(federal_tax_id) = :q
           OR  UPPER(card_name) LIKE UPPER(:like)
        ORDER  BY federal_tax_id = :q DESC
        LIMIT  1
    """), {'q': q, 'like': f'%{q}%'}).fetchone()

    if not row:
        return jsonify({'success': False, 'message': 'Transportista no encontrado.'}), 404

    m = dict(row._mapping)
    return jsonify({
        'success': True,
        'transportista': {
            'ruc':          m.get('federal_tax_id') or '',
            'denominacion': m.get('card_name') or '',
        }
    })


# ── Datos de la empresa emisora ───────────────────────────────

@main.route('/api/gr/empresa')
@login_required
def api_gr_empresa():
    try:
        row = db.session.execute(text("""
            SELECT ruc, descripcion, direccion
            FROM   empresa
            LIMIT  1
        """)).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Sin registro en tabla empresa.'}), 404
        m = dict(row._mapping)
        return jsonify({
            'success':     True,
            'ruc':         (m.get('ruc') or '').strip(),
            'descripcion': (m.get('descripcion') or '').strip(),
            'direccion':   (m.get('direccion') or '').strip(),
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Series de GR disponibles (invoce_doc_number idtype=7) ────

@main.route('/api/gr/series')
@login_required
def api_gr_series():
    try:
        rows = db.session.execute(text("""
            SELECT *
            FROM   invoce_doc_number
            WHERE  idtype = 7
            ORDER  BY 1
        """)).fetchall()
        if not rows:
            return jsonify({'success': False, 'message': 'No hay registros con idtype=7.',
                            'debug_cols': []}), 404
        # Extraer nombres de columna del primer resultado
        cols = list(rows[0]._mapping.keys())
        raw  = [dict(r._mapping) for r in rows]

        # Detectar columnas de serie y número de forma flexible
        def _find_col(candidates, row):
            for c in candidates:
                if c in row:
                    return c
            return None

        serie_col  = _find_col(['serie', 'series', 'invoice_serie', 'doc_serie',  'prefix'], raw[0])
        number_col = _find_col(['invoice_number', 'numero', 'number', 'doc_number',
                                 'last_number', 'current_number', 'nro'], raw[0])

        if not serie_col or not number_col:
            return jsonify({
                'success':    False,
                'message':    f'No se pudo detectar las columnas. Columnas encontradas: {cols}',
                'debug_cols': cols,
                'debug_rows': raw,
            }), 500

        return jsonify({
            'success': True,
            'series': [
                {
                    'serie':          (str(r[serie_col] or '')).strip(),
                    'invoice_number': int(r[number_col] or 0),
                }
                for r in raw
            ],
            'debug_cols': cols,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
