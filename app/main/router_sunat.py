from datetime import datetime, date
import requests
from flask import jsonify, current_app
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


# ── Helpers de mapeo ──────────────────────────────────────────────────────────

def _tipo_documento(invoice_serie: str) -> str:
    s = (invoice_serie or '').strip().upper()
    if s.startswith('F'):
        return 'factura'
    if s.startswith('B'):
        return 'boleta'
    return 'factura'


def _tipo_doc_cliente(tipo_documento: str) -> str:
    """Factura → RUC (6), Boleta → DNI (1)."""
    return '1' if tipo_documento == 'boleta' else '6'


def _moneda(doc_currency: str) -> str:
    return 'USD' if (doc_currency or '').upper() == 'USD' else 'PEN'


# ── Construir payload SUNAT desde invoice_id ─────────────────────────────────

def _build_payload(invoice_id: int) -> dict:
    inv = db.session.execute(text("""
        SELECT
            i.invoice_id,
            i.invoice_serie,
            i.invoice_number,
            i.doc_date,
            i.doc_due_date,
            i.doc_currency,
            i.doc_total,
            i.comments,
            i.card_code,
            bp.card_name,
            COALESCE(bp."Creditday", 0)                             AS creditday,
            COALESCE(NULLIF(TRIM(bp.federal_tax_id), ''), i.card_code) AS federal_tax_id,
            COALESCE(
                (SELECT TRIM(COALESCE(street,'')) ||
                        CASE WHEN COALESCE(street_no,'') <> ''
                             THEN ' ' || street_no ELSE '' END
                 FROM   business_partners_addresses
                 WHERE  bp_code = i.card_code
                 LIMIT  1),
                ''
            ) AS direccion
        FROM  invoice i
        LEFT  JOIN business_partners bp ON bp.card_code = i.card_code
        WHERE i.invoice_id = :id
    """), {'id': invoice_id}).fetchone()

    if not inv:
        raise ValueError(f'Factura #{invoice_id} no encontrada.')

    inv = dict(inv._mapping)

    items_rows = db.session.execute(text("""
        SELECT
            ii.quantity,
            ii.price_after_vat,
            COALESCE(it.item_name, ii.item_code, 'Producto')  AS descripcion,
            COALESCE(NULLIF(TRIM(it.sal_unit_msr), ''), 'NIU') AS unidad
        FROM  invoice_item ii
        LEFT  JOIN items it ON it.item_code = ii.item_code
        WHERE ii.invoice_id = :id
        ORDER BY ii.item_code
    """), {'id': invoice_id}).fetchall()

    igv_factor = 1.18

    sunat_items = []
    for r in items_rows:
        r = dict(r._mapping)
        pav = float(r['price_after_vat'] or 0)
        qty = float(r['quantity'] or 1)
        val_unit = pav / igv_factor          # precio sin IGV
        sunat_items.append({
            'unidad_de_medida':              r['unidad'],
            'descripcion':                   r['descripcion'],
            'cantidad':                      str(qty),
            'valor_unitario':                f'{val_unit:.6f}',
            'porcentaje_igv':                '18',
            'codigo_tipo_afectacion_igv':    '10',
            'nombre_tributo':                'IGV',
        })

    doc_date      = (inv['doc_date'].isoformat()
                     if inv.get('doc_date') else datetime.now().strftime('%Y-%m-%d'))
    tipo_doc      = _tipo_documento(inv.get('invoice_serie', ''))

    payload = {
        'documento':                    tipo_doc,
        'serie':                        (inv.get('invoice_serie') or '').strip(),
        'numero':                       int(inv.get('invoice_number') or 0),
        'fecha_de_emision':             doc_date,
        'hora_de_emision':              datetime.now().strftime('%H:%M:%S'),
        'moneda':                       _moneda(inv.get('doc_currency', '')),
        'tipo_operacion':               '0101',
        'cliente_tipo_de_documento':    _tipo_doc_cliente(tipo_doc),
        'cliente_numero_de_documento':  (inv.get('federal_tax_id') or '').strip(),
        'cliente_denominacion':         (inv.get('card_name') or '').strip(),
        'cliente_direccion':            (inv.get('direccion') or '').strip(),
        'items':                        sunat_items,
        'total':                        f"{float(inv.get('doc_total') or 0):.2f}",
    }

    if inv.get('comments'):
        payload['observacion'] = inv['comments'].strip()

    creditday = int(inv.get('creditday') or 0)
    if creditday > 0 and inv.get('doc_due_date'):
        due_date = (inv['doc_due_date'].isoformat()
                    if hasattr(inv['doc_due_date'], 'isoformat')
                    else str(inv['doc_due_date']))
        payload['cuotas'] = [{
            'importe':        f"{float(inv.get('doc_total') or 0):.2f}",
            'fecha_de_pago':  due_date,
        }]

    return payload


# ── Construir payload de anulación desde invoice_id ──────────────────────────

def _build_anulacion_payload(invoice_id: int) -> dict:
    inv = db.session.execute(text("""
        SELECT invoice_serie, invoice_number, sunat_estado
        FROM   invoice
        WHERE  invoice_id = :id
    """), {'id': invoice_id}).fetchone()

    if not inv:
        raise ValueError(f'Factura #{invoice_id} no encontrada.')

    inv = dict(inv._mapping)

    if inv.get('sunat_estado') != 'ACEPTADO':
        raise ValueError('Solo se pueden anular documentos con estado ACEPTADO.')

    tipo_doc = _tipo_documento(inv.get('invoice_serie', ''))
    serie    = (inv.get('invoice_serie') or '').strip()
    numero   = str(int(inv.get('invoice_number') or 0))
    hoy      = date.today().isoformat()

    if tipo_doc == 'boleta':
        return {
            'documento':          'resumen_diario',
            'fecha_de_referencia': hoy,
            'documentos_afectados': [{
                'accion_resumen': 'anular',
                'documento':      'boleta',
                'serie':          serie,
                'numero':         numero,
            }]
        }
    return {
        'documento': 'comunicacion_baja',
        'motivo':    'ANULACIÓN DE OPERACIÓN',
        'documento_afectado': {
            'documento': 'factura',
            'serie':     serie,
            'numero':    numero,
        }
    }


# ── Rutas ─────────────────────────────────────────────────────────────────────

@main.route('/api/sunat/enviar/<int:invoice_id>', methods=['POST'])
@login_required
def sunat_enviar_factura(invoice_id):
    """Envía la factura a la API de SUNAT y guarda el resultado."""
    try:
        payload = _build_payload(invoice_id)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al preparar datos: {e}'}), 500

    token = current_app.config['APISUNAT_TOKEN']
    url   = current_app.config['APISUNAT_URL']

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

    ok = resp.status_code in (200, 201)

    # Parsear el formato de respuesta de apisunat.pe
    # { success, message, payload: { estado, hash, xml, pdf: { ticket, a4 } } }
    inner   = resp_data.get('payload') or {}
    estado  = inner.get('estado') or ('ACEPTADO' if ok else f'ERROR_{resp.status_code}')
    hash_   = inner.get('hash', '')
    xml_url = inner.get('xml', '')
    cdr_url = inner.get('cdr', '')
    pdf     = inner.get('pdf') or {}
    ticket  = pdf.get('ticket', '')
    a4_url  = pdf.get('a4', '')
    msg_api = resp_data.get('message', '')

    # Persistir todos los campos SUNAT en la factura
    try:
        db.session.execute(text("""
            UPDATE invoice
               SET sunat_estado = :estado,
                   sunat_hash   = :hash,
                   sunat_xml    = :xml,
                   sunat_cdr    = :cdr,
                   sunat_ticket = :ticket,
                   sunat_a4     = :a4
             WHERE invoice_id   = :id
        """), {
            'estado': estado,
            'hash':   hash_,
            'xml':    xml_url,
            'cdr':    cdr_url,
            'ticket': ticket,
            'a4':     a4_url,
            'id':     invoice_id,
        })
        db.session.commit()
    except Exception:
        db.session.rollback()

    if ok:
        return jsonify({
            'success':      True,
            'message':      msg_api or f'Factura #{invoice_id} enviada correctamente a SUNAT.',
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
        'response':     resp_data,
    }), resp.status_code


@main.route('/api/sunat/preview/<int:invoice_id>')
@login_required
def sunat_preview_factura(invoice_id):
    """Devuelve el JSON que se enviaría a SUNAT sin enviarlo (útil para debug)."""
    try:
        payload = _build_payload(invoice_id)
        return jsonify({'success': True, 'payload': payload})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/sunat/config')
@login_required
def sunat_config_info():
    """Muestra la configuración SUNAT activa (modo y URL)."""
    return jsonify({
        'modo': current_app.config.get('APISUNAT_MODO'),
        'url':  current_app.config.get('APISUNAT_URL'),
    })


@main.route('/api/sunat/debug/<int:invoice_id>')
@login_required
def sunat_debug_factura(invoice_id):
    """Envía la factura a SUNAT y devuelve el payload enviado + respuesta completa."""
    try:
        payload = _build_payload(invoice_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    token = current_app.config['APISUNAT_TOKEN']
    url   = current_app.config['APISUNAT_URL']

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        resp_data = resp.json() if resp.content else {}
    except Exception as e:
        return jsonify({'error': str(e)}), 502

    return jsonify({
        'url_enviada':  url,
        'payload':      payload,
        'status_http':  resp.status_code,
        'respuesta':    resp_data,
    })


@main.route('/api/sunat/anular/debug/<int:invoice_id>')
@login_required
def sunat_anular_debug(invoice_id):
    """Envía la anulación a SUNAT y devuelve payload enviado + respuesta completa."""
    try:
        payload = _build_anulacion_payload(invoice_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    token = current_app.config['APISUNAT_TOKEN']
    url   = current_app.config['APISUNAT_VOID_URL']

    try:
        resp = requests.post(
            url, json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        resp_data = resp.json() if resp.content else {}
    except Exception as e:
        return jsonify({'error': str(e)}), 502

    return jsonify({
        'url_enviada': url,
        'payload':     payload,
        'status_http': resp.status_code,
        'respuesta':   resp_data,
    })


@main.route('/api/sunat/anular/preview/<int:invoice_id>')
@login_required
def sunat_anular_preview(invoice_id):
    """Devuelve el JSON de anulación sin enviarlo."""
    try:
        payload = _build_anulacion_payload(invoice_id)
        return jsonify({'success': True, 'payload': payload})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/sunat/anular/<int:invoice_id>', methods=['POST'])
@login_required
def sunat_anular_factura(invoice_id):
    """Envía la anulación a SUNAT y actualiza el estado."""
    try:
        payload = _build_anulacion_payload(invoice_id)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al preparar datos: {e}'}), 500

    token = current_app.config['APISUNAT_TOKEN']
    url   = current_app.config['APISUNAT_VOID_URL']

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
    msg_api = resp_data.get('message', '')
    ticket  = inner.get('ticket', '')

    if ok:
        try:
            db.session.execute(text("""
                UPDATE invoice SET sunat_estado = 'ANULADO' WHERE invoice_id = :id
            """), {'id': invoice_id})
            db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({
            'success':       True,
            'message':       msg_api or f'Documento #{invoice_id} anulado en SUNAT.',
            'sunat_ticket':  ticket,
        })

    return jsonify({
        'success':  False,
        'message':  msg_api or f'SUNAT respondió con error {resp.status_code}.',
        'response': resp_data,
    }), resp.status_code
