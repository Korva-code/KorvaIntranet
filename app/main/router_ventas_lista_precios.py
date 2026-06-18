from flask import render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


# ── Vista principal ────────────────────────────────────────────────────

@main.route('/ventas/lista-precios')
@login_required
def ventas_lista_precios():
    try:
        socios_rows = db.session.execute(text("""
            SELECT
                bp.card_code,
                COALESCE(bp.card_name, bp.card_code)              AS card_name,
                COALESCE(bp.federal_tax_id, '')                   AS federal_tax_id,
                COALESCE(bp.card_type, '')                        AS card_type,
                COALESCE(at2.nm_tipo_anexo, bp.card_type, '')     AS tipo_nombre,
                COUNT(d.item_code)                                AS total_items
            FROM business_partners bp
            LEFT JOIN anexo_tipo at2
                   ON at2.id_tipo_anexo = bp.card_type
            LEFT JOIN business_partners_discount_item d
                   ON TRIM(d.federal_tax_id) = TRIM(bp.federal_tax_id)
            GROUP BY bp.card_code, bp.card_name, bp.federal_tax_id, bp.card_type, at2.nm_tipo_anexo
            ORDER BY bp.card_name
        """)).fetchall()
        socios = [dict(r._mapping) for r in socios_rows]
    except Exception:
        db.session.rollback()
        socios = []

    return render_template('main/ventas_lista_precios.html',
                           title='Lista de Precios',
                           section='Ventas',
                           socios=socios,
                           total=len(socios))


# ── API: obtener ítems de la lista de precios de un socio ─────────────

@main.route('/api/lista-precios/<card_code>')
@login_required
def api_lista_precios_get(card_code):
    try:
        bp = db.session.execute(text("""
            SELECT federal_tax_id, card_name, card_type
            FROM   business_partners
            WHERE  card_code = :cc
            LIMIT  1
        """), {'cc': card_code}).fetchone()

        if not bp or not bp[0]:
            return jsonify({'success': False, 'message': 'Socio sin RUC registrado.'}), 404

        ruc = bp[0].strip()
        rows = db.session.execute(text("""
            SELECT
                d.item_code,
                COALESCE(i.item_name, d.item_code)        AS item_name,
                COALESCE(i."PriceAfterVAT", 0)            AS catalog_price,
                COALESCE(d.avg_price_d, 0)                AS avg_price_d,
                COALESCE(d.priceaftervat_d, 0)            AS priceaftervat_d,
                COALESCE(d.status, 1)                     AS status
            FROM business_partners_discount_item d
            LEFT JOIN items i ON i.item_code = d.item_code
            WHERE TRIM(d.federal_tax_id) = :ruc
            ORDER BY i.item_name, d.item_code
        """), {'ruc': ruc}).fetchall()

        items = []
        for r in rows:
            m = dict(r._mapping)
            m['catalog_price']   = float(m['catalog_price'])
            m['avg_price_d']     = float(m['avg_price_d'])
            m['priceaftervat_d'] = float(m['priceaftervat_d'])
            items.append(m)

        return jsonify({
            'success':   True,
            'ruc':       ruc,
            'card_name': bp[1],
            'card_type': bp[2],
            'items':     items,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ── API: guardar lista completa (reemplaza todos los ítems) ───────────

@main.route('/api/lista-precios/guardar', methods=['POST'])
@login_required
def api_lista_precios_guardar():
    data  = request.get_json() or {}
    ruc   = (data.get('federal_tax_id') or '').strip()
    items = data.get('items', [])

    if not ruc:
        return jsonify({'success': False, 'message': 'RUC es obligatorio.'}), 400

    try:
        db.session.execute(text("""
            DELETE FROM business_partners_discount_item
            WHERE TRIM(federal_tax_id) = :ruc
        """), {'ruc': ruc})

        for it in items:
            item_code = (it.get('item_code') or '').strip()
            if not item_code:
                continue
            db.session.execute(text("""
                INSERT INTO business_partners_discount_item
                       (federal_tax_id, item_code, avg_price_d, priceaftervat_d, status)
                VALUES (:ruc, :item_code, :avg, :cigv, 1)
            """), {
                'ruc':       ruc,
                'item_code': item_code,
                'avg':       float(it.get('avg_price_d') or 0),
                'cigv':      float(it.get('priceaftervat_d') or 0),
            })

        db.session.commit()
        n = len([i for i in items if (i.get('item_code') or '').strip()])
        return jsonify({'success': True, 'message': f'Lista guardada ({n} ítems).'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
