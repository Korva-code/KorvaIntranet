import json
from datetime import date as _date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Usuario

TIPOS_SALIDA = ['VENTA', 'AJUSTE', 'DEVOLUCION', 'TRANSFERENCIA', 'CONSUMO', 'MERMA']


def _col_imagen_salida_existe():
    try:
        r = db.session.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='salidas_c' AND column_name='imagen'
        """)).fetchone()
        db.session.commit()
        return r is not None
    except Exception:
        return False


def _cab_to_dict(r):
    m = dict(r._mapping)
    return {
        'id':              m.get('id'),
        'tipo_salida':     m.get('tipo_salida') or '',
        'fecha_salida':    m['fecha_salida'].isoformat() if m.get('fecha_salida') else '',
        'almacen':         m.get('almacen') or '',
        'whs_name':        m.get('whs_name') or '',
        'nro_referencia':  m.get('nro_referencia') or '',
        'observaciones':   m.get('observaciones') or '',
        'id_estado':       m.get('id_estado') if m.get('id_estado') is not None else 1,
        'user_code':          m.get('user_code') or '',
        'user_nombre':        m.get('user_nombre') or '',
        'fecha_registro':     m['fecha_registro'].isoformat()     if m.get('fecha_registro')     else '',
        'fecha_modificacion': m['fecha_modificacion'].isoformat() if m.get('fecha_modificacion') else '',
        'total_items':        int(m.get('total_items') or 0),
        'total_costo':        float(m.get('total_costo') or 0),
    }


@main.route('/almacen/salidas')
@login_required
def almacen_salidas():
    rows   = db.session.execute(text("SELECT * FROM sp_salida_listar(200)")).fetchall()
    salidas = [_cab_to_dict(r) for r in rows]

    if salidas:
        ts_rows = db.session.execute(text("""
            SELECT id, fecha_registro, fecha_modificacion FROM salidas_c
        """)).fetchall()
        ts_map = {r[0]: r for r in ts_rows}
        for sal in salidas:
            r = ts_map.get(sal['id'])
            if r:
                sal['fecha_registro']    = r[1].isoformat() if r[1] else ''
                sal['fecha_modificacion']= r[2].isoformat() if r[2] else ''

    whs_rows = db.session.execute(text(
        "SELECT DISTINCT TRIM(whs_code) AS whs_code, whs_name FROM warehouses ORDER BY whs_name"
    )).fetchall()
    warehouses = [{'whs_code': dict(r._mapping).get('whs_code') or '',
                   'whs_name': dict(r._mapping).get('whs_name') or ''}
                  for r in whs_rows]

    usuarios = [{'id_usuario': u.id_usuario, 'nombres': (u.nombres or u.id_usuario or '').strip()}
                for u in Usuario.query.order_by(Usuario.nombres).all()]

    items_rows = db.session.execute(text("""
        SELECT item_code, item_name,
               COALESCE(avg_price, 0)     AS avg_price,
               COALESCE(ultimo_costo, avg_price, 0) AS price_cost,
               COALESCE(sal_unit_msr, '') AS uom
        FROM items
        WHERE COALESCE(invnt_item, 'N') = 'Y'
        ORDER BY item_name
    """)).fetchall()
    items_cat = []
    for r in items_rows:
        m = dict(r._mapping)
        items_cat.append({
            'item_code':  (m.get('item_code') or '').strip(),
            'item_name':  (m.get('item_name') or '').strip(),
            'avg_price':  float(m.get('avg_price') or 0),
            'price_cost': float(m.get('price_cost') or 0),
            'uom':        (m.get('uom') or '').strip(),
        })

    return render_template(
        'main/almacen_salida.html',
        title='Salidas de Mercadería',
        section='Almacén', page='Salidas',
        salidas_json=json.dumps(salidas, ensure_ascii=False),
        warehouses_json=json.dumps(warehouses, ensure_ascii=False),
        items_json=json.dumps(items_cat, ensure_ascii=False),
        tipos_json=json.dumps(TIPOS_SALIDA, ensure_ascii=False),
        usuarios_json=json.dumps(usuarios, ensure_ascii=False),
        current_user_code=str(current_user.id_usuario),
        total=len(salidas),
    )


@main.route('/almacen/salidas/<int:salida_id>/timestamps')
@login_required
def almacen_salida_timestamps(salida_id):
    row = db.session.execute(text("""
        SELECT fecha_registro, fecha_modificacion, user_code
        FROM salidas_c WHERE id = :id
    """), {'id': salida_id}).fetchone()
    if not row:
        return jsonify({'success': False}), 404
    return jsonify({
        'success':            True,
        'fecha_registro':     row[0].isoformat() if row[0] else '',
        'fecha_modificacion': row[1].isoformat() if row[1] else '',
        'user_code':          row[2] or '',
    })


@main.route('/almacen/salidas/<int:salida_id>/imagen')
@login_required
def almacen_salida_imagen(salida_id):
    if not _col_imagen_salida_existe():
        return jsonify({'success': True, 'imagen': ''})
    row = db.session.execute(text(
        "SELECT imagen FROM salidas_c WHERE id = :id"
    ), {'id': salida_id}).fetchone()
    return jsonify({'success': True, 'imagen': row[0] if row and row[0] else ''})


@main.route('/almacen/salidas/items/<int:salida_id>')
@login_required
def almacen_salida_items(salida_id):
    rows = db.session.execute(
        text("SELECT * FROM sp_salida_items_listar(:id)"), {'id': salida_id}
    ).fetchall()
    items = []
    for r in rows:
        m = dict(r._mapping)
        items.append({
            'id':         m.get('id'),
            'item_code':  m.get('item_code') or '',
            'item_name':  m.get('item_name') or '',
            'quantity':   float(m.get('quantity') or 0),
            'uom':        m.get('uom') or '',
            'price_cost': float(m.get('price_cost') or 0),
            'subtotal':   float(m.get('subtotal') or 0),
        })
    return jsonify({'success': True, 'items': items})


@main.route('/almacen/salidas/guardar', methods=['POST'])
@login_required
def almacen_salidas_guardar():
    data        = request.get_json(force=True)
    salida_id   = int(data.get('salida_id') or 0)
    tipo_salida = (data.get('tipo_salida') or '').strip()
    fecha_str   = (data.get('fecha_salida') or '').strip()
    almacen     = (data.get('almacen') or '').strip()
    nro_ref     = (data.get('nro_referencia') or '').strip() or None
    observaciones = (data.get('observaciones') or '').strip() or None
    items       = data.get('items') or []
    user_code   = (data.get('user_code') or '').strip() or str(current_user.id_usuario)
    imagen      = data.get('imagen') or None

    if not tipo_salida:
        return jsonify({'success': False, 'message': 'Seleccione el tipo de salida.'}), 400
    if not fecha_str:
        return jsonify({'success': False, 'message': 'Ingrese la fecha de salida.'}), 400
    if not almacen:
        return jsonify({'success': False, 'message': 'Seleccione el almacén.'}), 400
    if not items:
        return jsonify({'success': False, 'message': 'Agregue al menos un artículo.'}), 400

    try:
        fecha_obj = _date.fromisoformat(fecha_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Fecha inválida.'}), 400

    tiene_imagen = _col_imagen_salida_existe()
    try:
        if salida_id:
            if tiene_imagen:
                db.session.execute(text("""
                    UPDATE salidas_c
                       SET tipo_salida         = :tipo,
                           fecha_salida        = :fecha,
                           almacen             = :almacen,
                           nro_referencia      = :nro_ref,
                           observaciones       = :obs,
                           user_code           = :user,
                           fecha_modificacion  = NOW(),
                           imagen              = COALESCE(:img, imagen)
                     WHERE id = :id
                """), {'tipo': tipo_salida, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_ref': nro_ref, 'obs': observaciones, 'user': user_code,
                       'img': imagen, 'id': salida_id})
            else:
                db.session.execute(text("""
                    UPDATE salidas_c
                       SET tipo_salida         = :tipo,
                           fecha_salida        = :fecha,
                           almacen             = :almacen,
                           nro_referencia      = :nro_ref,
                           observaciones       = :obs,
                           user_code           = :user,
                           fecha_modificacion  = NOW()
                     WHERE id = :id
                """), {'tipo': tipo_salida, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_ref': nro_ref, 'obs': observaciones, 'user': user_code,
                       'id': salida_id})
            db.session.execute(text("DELETE FROM salidas_d WHERE salida_id = :id"), {'id': salida_id})
            db.session.execute(text(
                "DELETE FROM movimientos_almacen WHERE invoice_id = :id AND origen = 'SALIDA'"
            ), {'id': salida_id})
        else:
            if tiene_imagen:
                row = db.session.execute(text("""
                    INSERT INTO salidas_c
                        (tipo_salida, fecha_salida, almacen, nro_referencia,
                         observaciones, user_code, imagen, fecha_registro, fecha_modificacion)
                    VALUES (:tipo, :fecha, :almacen, :nro_ref,
                            :obs, :user, :img, NOW(), NOW())
                    RETURNING id
                """), {'tipo': tipo_salida, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_ref': nro_ref, 'obs': observaciones, 'user': user_code,
                       'img': imagen}).fetchone()
            else:
                row = db.session.execute(text("""
                    INSERT INTO salidas_c
                        (tipo_salida, fecha_salida, almacen, nro_referencia,
                         observaciones, user_code, fecha_registro, fecha_modificacion)
                    VALUES (:tipo, :fecha, :almacen, :nro_ref,
                            :obs, :user, NOW(), NOW())
                    RETURNING id
                """), {'tipo': tipo_salida, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_ref': nro_ref, 'obs': observaciones, 'user': user_code}).fetchone()
            salida_id = row[0]

        for it in items:
            item_code  = (it.get('item_code') or '').strip()
            if not item_code:
                continue
            quantity   = float(it.get('quantity') or 0)
            price_cost = float(it.get('price_cost') or 0)
            subtotal   = round(quantity * price_cost, 2)

            db.session.execute(text("""
                INSERT INTO salidas_d
                    (salida_id, item_code, item_name, quantity, uom, price_cost, subtotal)
                VALUES (:cid, :code, :name, :qty, :uom, :pc, :sub)
            """), {
                'cid':  salida_id,
                'code': item_code,
                'name': (it.get('item_name') or item_code),
                'qty':  quantity,
                'uom':  (it.get('uom') or '').strip() or None,
                'pc':   price_cost,
                'sub':  subtotal,
            })

            # Cantidad negativa en movimientos (salida de stock)
            db.session.execute(text("""
                INSERT INTO movimientos_almacen
                    (invoice_id, card_code, invoice_type, doc_date,
                     item_code, item_name, quantity, avg_price, price_cost, subtotal,
                     almacen, tipo_movimiento, origen, user_code)
                VALUES
                    (:cid, '', 'SALIDA', CAST(:fecha AS DATE),
                     :code, :name, :qty_neg, :pc, :pc, :sub_neg,
                     :alm, 'SAL', 'SALIDA', :user)
            """), {
                'cid':     salida_id,
                'fecha':   fecha_obj,
                'code':    item_code,
                'name':    (it.get('item_name') or item_code),
                'qty_neg': -quantity,
                'pc':      price_cost,
                'sub_neg': -subtotal,
                'alm':     almacen,
                'user':    user_code,
            })

        db.session.commit()
        accion = 'actualizada' if data.get('salida_id') else 'registrada'
        return jsonify({'success': True,
                        'message': f'Salida {accion} correctamente.',
                        'salida_id': salida_id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/almacen/salidas/<int:salida_id>/anular', methods=['POST'])
@login_required
def almacen_salidas_anular(salida_id):
    try:
        db.session.execute(text(
            "UPDATE salidas_c SET id_estado = 0 WHERE id = :id"
        ), {'id': salida_id})
        db.session.execute(text(
            "DELETE FROM movimientos_almacen WHERE invoice_id = :id AND origen = 'SALIDA'"
        ), {'id': salida_id})
        db.session.commit()
        return jsonify({'success': True, 'message': 'Salida anulada correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
