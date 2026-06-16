from datetime import datetime
import requests
from flask import jsonify, current_app
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db

# Configuración SUNAT — mover a config.py / variable de entorno en producción
_APISUNAT_URL   = 'https://sandbox.apisunat.pe/api/v3/documents'
_APISUNAT_TOKEN = ('530.byrieOPL2IhMi1WxT7dZVKYvjtc69uQFKQbObxwxAJPeTdmqytQQCrVuEYP2'
                   'lOGl1BXO0TBu5Y04YR4u52X250ExXvdq5UPuqO99nAazD13iPs7wNzk6LWgl')


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
            i.doc_currency,
            i.doc_total,
            i.comments,
            bp.card_name,
            bp.federal_tax_id,
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

    return payload


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

    token = current_app.config.get('APISUNAT_TOKEN', _APISUNAT_TOKEN)
    url   = current_app.config.get('APISUNAT_URL',   _APISUNAT_URL)

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
