from datetime import datetime
import requests
from flask import jsonify, current_app
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


def _tipo_documento_serie(serie: str) -> str:
    s = (serie or '').strip().upper()
    if s.startswith('F'):
        return 'factura'
    if s.startswith('B'):
        return 'boleta'
    return 'factura'


def _tipo_doc_cliente(tipo_doc: str) -> str:
    return '1' if tipo_doc == 'boleta' else '6'


def _moneda(doc_currency: str) -> str:
    return 'USD' if (doc_currency or '').upper() == 'USD' else 'PEN'


def _build_nc_payload(id_nc: int) -> dict:
    # Cabecera NC + cliente + factura referenciada
    nc = db.session.execute(text("""
        SELECT
            nc.id_nc,
            nc.nc_serie,
            nc.nc_number,
            nc.nc_type,
            nc.doc_date,
            nc.doc_currency,
            nc.doc_total,
            nc.motivo_code,
            nc.card_code,
            nc.invoice_id,
            COALESCE(mn.description, nc.motivo_code, '')    AS motivo_desc,
            COALESCE(bp.card_name, nc.card_code, '')         AS card_name,
            COALESCE(bp.federal_tax_id, '')                  AS federal_tax_id,
            COALESCE(
                (SELECT TRIM(COALESCE(street,'')) ||
                        CASE WHEN COALESCE(street_no,'') <> ''
                             THEN ' ' || street_no ELSE '' END
                 FROM   business_partners_addresses
                 WHERE  bp_code = nc.card_code
                 LIMIT  1),
                ''
            )                                                AS direccion,
            -- Factura referenciada
            COALESCE(i.invoice_serie::TEXT, '')              AS ref_serie,
            COALESCE(i.invoice_number::TEXT, '')             AS ref_number
        FROM  invoice_nc nc
        LEFT  JOIN motivos_nc       mn ON mn.code      = nc.motivo_code
        LEFT  JOIN business_partners bp ON bp.card_code = nc.card_code
        LEFT  JOIN invoice           i  ON i.invoice_id = nc.invoice_id
        WHERE nc.id_nc = :id
    """), {'id': id_nc}).fetchone()

    if not nc:
        raise ValueError(f'Nota de Crédito #{id_nc} no encontrada.')

    nc = dict(nc._mapping)

    # Verificar que no esté ya aceptada
    if (nc.get('sunat_estado') or '').upper() == 'ACEPTADO':
        raise ValueError('Esta nota de crédito ya fue aceptada por SUNAT.')

    # Ítems
    items_rows = db.session.execute(text("""
        SELECT
            it2.quantity,
            it2.price_after_vat,
            it2.tax_code,
            COALESCE(NULLIF(TRIM(it2.description), ''),
                     it.item_name,
                     it2.item_code, 'Servicio')              AS descripcion,
            COALESCE(NULLIF(TRIM(it.sal_unit_msr), ''), 'ZZ') AS unidad
        FROM  invoice_item_nc it2
        LEFT  JOIN items it ON it.item_code = it2.item_code
        WHERE it2.id_nc = :id
        ORDER BY it2.id_nc_item
    """), {'id': id_nc}).fetchall()

    if not items_rows:
        raise ValueError('La nota de crédito no tiene ítems.')

    igv_factor  = 1.18
    sunat_items = []
    for r in items_rows:
        r         = dict(r._mapping)
        pav       = float(r['price_after_vat'] or 0)
        qty       = float(r['quantity'] or 1)
        tax_code  = (r['tax_code'] or '').strip().upper()

        # Determinar afectación IGV según tax_code
        if tax_code in ('IGV', 'IVA', '10', 'GRAVADO', ''):
            cod_igv   = '10'
            nom_trib  = 'IGV'
            pct_igv   = '18'
            val_unit  = pav / igv_factor
        elif tax_code in ('EXO', 'EXONERADO', '20'):
            cod_igv   = '20'
            nom_trib  = 'EXO'
            pct_igv   = '0'
            val_unit  = pav
        else:  # inafecto u otros
            cod_igv   = '30'
            nom_trib  = 'INA'
            pct_igv   = '0'
            val_unit  = pav

        sunat_items.append({
            'unidad_de_medida':           r['unidad'],
            'descripcion':                r['descripcion'],
            'cantidad':                   str(qty),
            'valor_unitario':             f'{val_unit:.6f}',
            'porcentaje_igv':             pct_igv,
            'codigo_tipo_afectacion_igv': cod_igv,
            'nombre_tributo':             nom_trib,
        })

    doc_date = (nc['doc_date'].isoformat()
                if nc.get('doc_date') else datetime.now().strftime('%Y-%m-%d'))

    tipo_nc     = _tipo_documento_serie(nc.get('nc_serie', ''))
    ref_serie   = (nc.get('ref_serie') or '').strip()
    ref_number  = nc.get('ref_number') or '0'
    tipo_ref    = _tipo_documento_serie(ref_serie) if ref_serie else 'factura'

    payload = {
        'documento':                   'nota_credito',
        'serie':                       (nc.get('nc_serie') or '').strip(),
        'numero':                      int(nc.get('nc_number') or 0),
        'fecha_de_emision':            doc_date,
        'moneda':                      _moneda(nc.get('doc_currency', '')),
        'cliente_tipo_de_documento':   _tipo_doc_cliente(tipo_nc),
        'cliente_numero_de_documento': (nc.get('federal_tax_id') or '').strip(),
        'cliente_denominacion':        (nc.get('card_name') or '').strip(),
        'cliente_direccion':           (nc.get('direccion') or '').strip(),
        'items':                       sunat_items,
        'total':                       f"{float(nc.get('doc_total') or 0):.2f}",
        'nota_credito_codigo_tipo':    (nc.get('motivo_code') or '01').strip(),
        'nota_credito_motivo':         (nc.get('motivo_desc') or '').strip(),
        'documento_afectado': {
            'documento': tipo_ref,
            'serie':     ref_serie,
            'numero':    int(ref_number) if str(ref_number).isdigit() else 0,
        },
    }

    return payload


@main.route('/api/sunat/nc/enviar/<int:id_nc>', methods=['POST'])
@login_required
def sunat_nc_enviar(id_nc):
    try:
        payload = _build_nc_payload(id_nc)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
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

    ok      = resp.status_code in (200, 201)
    inner   = resp_data.get('payload') or {}
    estado  = inner.get('estado') or ('ACEPTADO' if ok else f'ERROR_{resp.status_code}')
    hash_   = inner.get('hash', '')
    xml_url = inner.get('xml', '')
    cdr_url = inner.get('cdr', '')
    pdf     = inner.get('pdf') or {}
    ticket  = pdf.get('ticket', '')
    a4_url  = pdf.get('a4', '')
    # Capturar mensaje de error de SUNAT (incluye casos 400 con body JSON)
    msg_api = (resp_data.get('message') or '').strip()

    # Persistir estado en invoice_nc siempre (éxito o error)
    try:
        db.session.execute(text("""
            UPDATE invoice_nc
               SET sunat_estado = :estado,
                   sunat_hash   = :hash,
                   sunat_xml    = :xml,
                   sunat_cdr    = :cdr,
                   sunat_ticket = :ticket,
                   sunat_a4     = :a4
             WHERE id_nc        = :id
        """), {
            'estado': estado,
            'hash':   hash_,
            'xml':    xml_url,
            'cdr':    cdr_url,
            'ticket': ticket,
            'a4':     a4_url,
            'id':     id_nc,
        })
        db.session.commit()
    except Exception:
        db.session.rollback()

    if ok:
        return jsonify({
            'success':      True,
            'message':      msg_api or f'NC #{id_nc} enviada y aceptada por SUNAT.',
            'sunat_estado': estado,
            'sunat_hash':   hash_,
            'sunat_xml':    xml_url,
            'sunat_cdr':    cdr_url,
            'sunat_ticket': ticket,
            'sunat_a4':     a4_url,
        })

    # Siempre HTTP 200 al frontend para que fetch() pueda leer el JSON correctamente
    return jsonify({
        'success':      False,
        'message':      msg_api or f'SUNAT respondió con error {resp.status_code}.',
        'sunat_estado': estado,
    })


@main.route('/api/sunat/nc/preview/<int:id_nc>')
@login_required
def sunat_nc_preview(id_nc):
    try:
        payload = _build_nc_payload(id_nc)
        return jsonify({'success': True, 'payload': payload})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
