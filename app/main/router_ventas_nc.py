import json
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


def _nc_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_nc':          m.get('id_nc'),
        'nc_serie':       m.get('nc_serie') or '',
        'nc_number':      m.get('nc_number'),
        'nc_type':        m.get('nc_type') or '',
        'card_code':      m.get('card_code') or '',
        'bp_name':        m.get('bp_name') or '',
        'doc_date':       m['doc_date'].isoformat() if m.get('doc_date') else '',
        'doc_currency':   m.get('doc_currency') or 'PEN',
        'doc_total':      float(m['doc_total']) if m.get('doc_total') is not None else 0.0,
        'motivo_code':    m.get('motivo_code') or '',
        'motivo_desc':    m.get('motivo_desc') or '',
        'comments':       m.get('comments') or '',
        'sunat_estado':   m.get('sunat_estado') or '',
        'sunat_a4':       m.get('sunat_a4') or '',
        'sunat_ticket':   m.get('sunat_ticket') or '',
        'sunat_hash':     m.get('sunat_hash') or '',
        'sunat_xml':      m.get('sunat_xml') or '',
        'sunat_cdr':      m.get('sunat_cdr') or '',
        'id_estado':      m.get('id_estado') if m.get('id_estado') is not None else 1,
        'user_code':      m.get('user_code') or '',
        'user_nombre':    m.get('user_nombre') or '',
        'invoice_id':     m.get('invoice_id'),
        'ref_serie':      m.get('ref_serie') or '',
        'ref_number':     m.get('ref_number') or '',
        'fecha_registro': m['fecha_registro'].isoformat() if m.get('fecha_registro') else '',
    }


@main.route('/ventas/notas-credito')
@login_required
def ventas_notas_credito():
    rows    = db.session.execute(text("SELECT * FROM sp_nc_listar(60)")).fetchall()
    nc_list = [_nc_to_dict(r) for r in rows]

    mot_rows  = db.session.execute(text("SELECT * FROM sp_motivos_nc_listar()")).fetchall()
    motivos   = [{'code': r[0], 'description': r[1]} for r in mot_rows]

    tipo_rows = db.session.execute(text("SELECT * FROM sp_nc_tipos_listar()")).fetchall()
    tipos     = [{'idtype': r[0], 'invoice_type': r[1]} for r in tipo_rows]

    return render_template(
        'main/nota_credito.html',
        title='Notas de Crédito',
        section='Ventas', page='Notas de Crédito',
        nc_json=json.dumps(nc_list, ensure_ascii=False),
        motivos_json=json.dumps(motivos, ensure_ascii=False),
        tipos_json=json.dumps(tipos, ensure_ascii=False),
        total=len(nc_list),
        user_code=str(current_user.id_usuario),
    )


@main.route('/api/nc-buscar-factura')
@login_required
def api_nc_buscar_factura():
    serie  = request.args.get('serie',  '').strip()
    numero = request.args.get('numero', '').strip()
    if not serie or not numero:
        return jsonify({'success': False, 'message': 'Ingrese serie y número.'}), 400
    try:
        num = int(numero)
    except ValueError:
        return jsonify({'success': False, 'message': 'Número inválido.'}), 400
    try:
        cab = db.session.execute(
            text("SELECT * FROM fn_nc_buscar_factura(:serie, :num)"),
            {'serie': serie, 'num': num}
        ).fetchone()
        if not cab:
            return jsonify({'success': False, 'message': f'No se encontró la factura {serie}-{num}.'}), 404

        extra = db.session.execute(
            text("SELECT COALESCE(doc_status,1), COALESCE(sunat_estado,'') FROM invoice WHERE invoice_id = :id"),
            {'id': cab[0]}
        ).fetchone()

        items_rows = db.session.execute(
            text("SELECT * FROM fn_nc_buscar_factura_items(:id)"),
            {'id': cab[0]}
        ).fetchall()

        return jsonify({
            'success':       True,
            'invoice_id':    cab[0],
            'card_code':     cab[1],
            'bp_name':       cab[2],
            'invoice_type':  cab[3],
            'invoice_serie': cab[4],
            'invoice_number':cab[5],
            'doc_date':      cab[6].isoformat() if cab[6] else '',
            'doc_currency':  cab[7],
            'doc_total':     float(cab[8] or 0),
            'doc_status':    int(extra[0]) if extra else 1,
            'sunat_estado':  str(extra[1]) if extra else '',
            'items': [{
                'item_code':       r[0],
                'item_name':       r[1],
                'quantity':        float(r[2] or 0),
                'price_after_vat': float(r[3] or 0),
                'tax_code':        r[4],
                'warehouse_code':  r[5],
            } for r in items_rows],
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/api/nc-doc-number/<int:idtype>')
@login_required
def api_nc_doc_number(idtype):
    try:
        row = db.session.execute(
            text("SELECT * FROM fn_nc_get_doc_number(:idtype)"),
            {'idtype': idtype}
        ).fetchone()
        if row:
            return jsonify({'success': True, 'invoice_serie': row[0], 'next_number': row[1]})
        return jsonify({'success': False, 'message': 'No se encontró serie para este tipo.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/ventas/notas-credito/<int:id_nc>/items')
@login_required
def ventas_nc_items(id_nc):
    try:
        rows = db.session.execute(
            text("SELECT * FROM sp_nc_items_listar(:id)"), {'id': id_nc}
        ).fetchall()
        items = [{
            'id_nc_item':      r[0],
            'item_code':       r[1],
            'description':     r[2],
            'quantity':        float(r[3] or 0),
            'price_after_vat': float(r[4] or 0),
            'tax_code':        r[5],
            'warehouse_code':  r[6],
        } for r in rows]
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/ventas/notas-credito/nueva', methods=['POST'])
@login_required
def ventas_nc_nueva():
    data = request.get_json(silent=True) or {}
    try:
        invoice_id   = int(data.get('invoice_id') or 0)
        nc_serie     = (data.get('nc_serie') or '').strip()
        nc_number    = int(data.get('nc_number') or 0)
        nc_type      = (data.get('nc_type') or '').strip()
        idtype       = int(data.get('idtype') or 0)
        card_code    = (data.get('card_code') or '').strip()
        doc_date     = (data.get('doc_date') or '').strip()
        doc_currency = (data.get('doc_currency') or 'PEN').strip()
        doc_total    = float(data.get('doc_total') or 0)
        motivo_code  = (data.get('motivo_code') or '').strip()
        comments     = (data.get('comments') or '').strip()
        user_code    = str(current_user.id_usuario)
        items        = data.get('items') or []

        if not nc_serie:
            return jsonify({'success': False, 'message': 'Seleccione el tipo para obtener la serie.'}), 400
        if not nc_number:
            return jsonify({'success': False, 'message': 'No se pudo obtener el número correlativo.'}), 400
        if not nc_type:
            return jsonify({'success': False, 'message': 'Seleccione el tipo de documento.'}), 400
        if not motivo_code:
            return jsonify({'success': False, 'message': 'Seleccione el motivo.'}), 400
        if not doc_date:
            return jsonify({'success': False, 'message': 'Ingrese la fecha.'}), 400

        from datetime import date as _date
        try:
            fecha_obj = _date.fromisoformat(doc_date)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Fecha inválida.'}), 400

        row = db.session.execute(text("""
            SELECT success, message, id_nc
            FROM fn_nc_insertar(
                :inv_id,
                CAST(:serie    AS TEXT),
                :num,
                CAST(:tipo     AS TEXT),
                :idtype,
                CAST(:card     AS TEXT),
                :fecha,
                CAST(:cur      AS TEXT),
                :total,
                CAST(:mot_code AS TEXT),
                CAST(:comm     AS TEXT),
                CAST(:user     AS TEXT),
                CAST(:items    AS JSONB)
            )
        """), {
            'inv_id':   invoice_id,
            'serie':    nc_serie,
            'num':      nc_number,
            'tipo':     nc_type,
            'idtype':   idtype,
            'card':     card_code,
            'fecha':    fecha_obj,
            'cur':      doc_currency,
            'total':    doc_total,
            'mot_code': motivo_code,
            'comm':     comments,
            'user':     user_code,
            'items':    json.dumps(items, ensure_ascii=False),
        }).fetchone()

        if row and row[0]:
            if invoice_id:
                db.session.execute(text("""
                    UPDATE invoice
                       SET nota_credito_serie  = :nc_serie,
                           nota_credito_numero = :nc_number,
                           nota_credito_total  = :nc_total,
                           doc_status          = 3,
                           doc_total           = 0
                     WHERE invoice_id = :inv_id
                """), {
                    'nc_serie':  nc_serie,
                    'nc_number': nc_number,
                    'nc_total':  doc_total,
                    'inv_id':    invoice_id,
                })
                db.session.execute(text(
                    "DELETE FROM movimientos_almacen WHERE invoice_id = :inv_id"
                ), {'inv_id': invoice_id})
            db.session.execute(text("""
                UPDATE invoce_doc_number
                   SET invoice_number = :num
                 WHERE idtype = :idtype
                   AND TRIM(invoice_serie) = :serie
            """), {'num': nc_number, 'idtype': idtype, 'serie': nc_serie})
            db.session.commit()
            return jsonify({'success': True, 'message': row[1], 'id_nc': row[2]})
        db.session.rollback()
        return jsonify({'success': False, 'message': row[1] if row else 'Error al guardar.'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/ventas/notas-credito/<int:id_nc>/anular', methods=['POST'])
@login_required
def ventas_nc_anular(id_nc):
    try:
        row = db.session.execute(
            text("SELECT success, message FROM fn_nc_anular(:id)"),
            {'id': id_nc}
        ).fetchone()
        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1]})
        db.session.rollback()
        return jsonify({'success': False, 'message': row[1] if row else 'Error al anular.'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
