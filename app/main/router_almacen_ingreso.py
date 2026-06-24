import json
from datetime import date as _date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Usuario

TIPOS_INGRESO = ['COMPRA', 'AJUSTE', 'DEVOLUCION', 'TRANSFERENCIA', 'OTROS']

def _col_imagen_existe():
    try:
        from app import db
        from sqlalchemy import text
        r = db.session.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='ingreso_c' AND column_name='imagen'
        """)).fetchone()
        db.session.commit()
        return r is not None
    except Exception:
        return False


def _cab_to_dict(r):
    m = dict(r._mapping)
    return {
        'id':               m.get('id'),
        'tipo_ingreso':     m.get('tipo_ingreso') or '',
        'fecha_ingreso':    m['fecha_ingreso'].isoformat() if m.get('fecha_ingreso') else '',
        'almacen':          m.get('almacen') or '',
        'whs_name':         m.get('whs_name') or '',
        'nro_orden_compra': m.get('nro_orden_compra') or '',
        'observaciones':    m.get('observaciones') or '',
        'id_estado':        m.get('id_estado') if m.get('id_estado') is not None else 1,
        'user_code':           m.get('user_code') or '',
        'user_nombre':         m.get('user_nombre') or '',
        'fecha_registro':      m['fecha_registro'].isoformat()     if m.get('fecha_registro')     else '',
        'fecha_modificacion':  m['fecha_modificacion'].isoformat() if m.get('fecha_modificacion') else '',
        'total_items':         int(m.get('total_items') or 0),
        'total_costo':         float(m.get('total_costo') or 0),
    }


@main.route('/almacen/ingresos')
@login_required
def almacen_ingresos():
    rows     = db.session.execute(text("SELECT * FROM sp_ingreso_listar(200)")).fetchall()
    ingresos = [_cab_to_dict(r) for r in rows]

    # Obtener timestamps directamente de ingreso_c (independiente del SP)
    if ingresos:
        ts_rows = db.session.execute(text("""
            SELECT id,
                   fecha_registro,
                   fecha_modificacion
            FROM ingreso_c
        """)).fetchall()
        ts_map = {r[0]: r for r in ts_rows}
        for ing in ingresos:
            r = ts_map.get(ing['id'])
            if r:
                ing['fecha_registro']    = r[1].isoformat() if r[1] else ''
                ing['fecha_modificacion']= r[2].isoformat() if r[2] else ''

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
        'main/almacen_ingreso.html',
        title='Ingresos de Mercadería',
        section='Almacén', page='Ingresos',
        ingresos_json=json.dumps(ingresos, ensure_ascii=False),
        warehouses_json=json.dumps(warehouses, ensure_ascii=False),
        items_json=json.dumps(items_cat, ensure_ascii=False),
        tipos_json=json.dumps(TIPOS_INGRESO, ensure_ascii=False),
        usuarios_json=json.dumps(usuarios, ensure_ascii=False),
        current_user_code=str(current_user.id_usuario),
        total=len(ingresos),
    )


@main.route('/almacen/ingresos/<int:ingreso_id>/timestamps')
@login_required
def almacen_ingreso_timestamps(ingreso_id):
    row = db.session.execute(text("""
        SELECT fecha_registro, fecha_modificacion, user_code
        FROM ingreso_c WHERE id = :id
    """), {'id': ingreso_id}).fetchone()
    if not row:
        return jsonify({'success': False}), 404
    return jsonify({
        'success':            True,
        'fecha_registro':     row[0].isoformat() if row[0] else '',
        'fecha_modificacion': row[1].isoformat() if row[1] else '',
        'user_code':          row[2] or '',
    })


@main.route('/almacen/ingresos/<int:ingreso_id>/imagen')
@login_required
def almacen_ingreso_imagen(ingreso_id):
    if not _col_imagen_existe():
        return jsonify({'success': True, 'imagen': ''})
    row = db.session.execute(text(
        "SELECT imagen FROM ingreso_c WHERE id = :id"
    ), {'id': ingreso_id}).fetchone()
    return jsonify({'success': True, 'imagen': row[0] if row and row[0] else ''})


@main.route('/almacen/ingresos/items/<int:ingreso_id>')
@login_required
def almacen_ingreso_items(ingreso_id):
    rows = db.session.execute(
        text("SELECT * FROM sp_ingreso_items_listar(:id)"), {'id': ingreso_id}
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


@main.route('/almacen/ingresos/guardar', methods=['POST'])
@login_required
def almacen_ingresos_guardar():
    data         = request.get_json(force=True)
    ingreso_id   = int(data.get('ingreso_id') or 0)
    tipo_ingreso = (data.get('tipo_ingreso') or '').strip()
    fecha_str    = (data.get('fecha_ingreso') or '').strip()
    almacen      = (data.get('almacen') or '').strip()
    nro_oc       = (data.get('nro_orden_compra') or '').strip() or None
    observaciones= (data.get('observaciones') or '').strip() or None
    items        = data.get('items') or []
    user_code    = (data.get('user_code') or '').strip() or str(current_user.id_usuario)
    imagen       = data.get('imagen') or None

    if not tipo_ingreso:
        return jsonify({'success': False, 'message': 'Seleccione el tipo de ingreso.'}), 400
    if not fecha_str:
        return jsonify({'success': False, 'message': 'Ingrese la fecha de ingreso.'}), 400
    if not almacen:
        return jsonify({'success': False, 'message': 'Seleccione el almacén.'}), 400
    if not items:
        return jsonify({'success': False, 'message': 'Agregue al menos un artículo.'}), 400

    try:
        fecha_obj = _date.fromisoformat(fecha_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Fecha inválida.'}), 400

    tiene_imagen = _col_imagen_existe()
    try:
        if ingreso_id:
            if tiene_imagen:
                db.session.execute(text("""
                    UPDATE ingreso_c
                       SET tipo_ingreso        = :tipo,
                           fecha_ingreso       = :fecha,
                           almacen             = :almacen,
                           nro_orden_compra    = :nro_oc,
                           observaciones       = :obs,
                           user_code           = :user,
                           fecha_modificacion  = NOW(),
                           imagen              = COALESCE(:img, imagen)
                     WHERE id = :id
                """), {'tipo': tipo_ingreso, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_oc': nro_oc, 'obs': observaciones, 'user': user_code,
                       'img': imagen, 'id': ingreso_id})
            else:
                db.session.execute(text("""
                    UPDATE ingreso_c
                       SET tipo_ingreso        = :tipo,
                           fecha_ingreso       = :fecha,
                           almacen             = :almacen,
                           nro_orden_compra    = :nro_oc,
                           observaciones       = :obs,
                           user_code           = :user,
                           fecha_modificacion  = NOW()
                     WHERE id = :id
                """), {'tipo': tipo_ingreso, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_oc': nro_oc, 'obs': observaciones, 'user': user_code,
                       'id': ingreso_id})
            db.session.execute(text("DELETE FROM ingreso_d WHERE ingreso_id = :id"), {'id': ingreso_id})
            db.session.execute(text(
                "DELETE FROM movimientos_almacen WHERE invoice_id = :id AND origen = 'INGRESO'"
            ), {'id': ingreso_id})
        else:
            if tiene_imagen:
                row = db.session.execute(text("""
                    INSERT INTO ingreso_c
                        (tipo_ingreso, fecha_ingreso, almacen, nro_orden_compra,
                         observaciones, user_code, imagen, fecha_registro, fecha_modificacion)
                    VALUES (:tipo, :fecha, :almacen, :nro_oc,
                            :obs, :user, :img, NOW(), NOW())
                    RETURNING id
                """), {'tipo': tipo_ingreso, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_oc': nro_oc, 'obs': observaciones, 'user': user_code,
                       'img': imagen}).fetchone()
            else:
                row = db.session.execute(text("""
                    INSERT INTO ingreso_c
                        (tipo_ingreso, fecha_ingreso, almacen, nro_orden_compra,
                         observaciones, user_code, fecha_registro, fecha_modificacion)
                    VALUES (:tipo, :fecha, :almacen, :nro_oc,
                            :obs, :user, NOW(), NOW())
                    RETURNING id
                """), {'tipo': tipo_ingreso, 'fecha': fecha_obj, 'almacen': almacen,
                       'nro_oc': nro_oc, 'obs': observaciones, 'user': user_code}).fetchone()
            ingreso_id = row[0]

        for it in items:
            item_code  = (it.get('item_code') or '').strip()
            if not item_code:
                continue
            quantity   = float(it.get('quantity') or 0)
            price_cost = float(it.get('price_cost') or 0)
            subtotal   = round(quantity * price_cost, 2)

            db.session.execute(text("""
                INSERT INTO ingreso_d
                    (ingreso_id, item_code, item_name, quantity, uom, price_cost, subtotal)
                VALUES (:cid, :code, :name, :qty, :uom, :pc, :sub)
            """), {
                'cid':  ingreso_id,
                'code': item_code,
                'name': (it.get('item_name') or item_code),
                'qty':  quantity,
                'uom':  (it.get('uom') or '').strip() or None,
                'pc':   price_cost,
                'sub':  subtotal,
            })

            db.session.execute(text("""
                INSERT INTO movimientos_almacen
                    (invoice_id, card_code, invoice_type, doc_date,
                     item_code, item_name, quantity, avg_price, price_cost, subtotal,
                     almacen, tipo_movimiento, origen, user_code)
                VALUES
                    (:cid, '', 'INGRESO', CAST(:fecha AS DATE),
                     :code, :name, :qty, :pc, :pc, :sub,
                     :alm, 'ENT', 'INGRESO', :user)
            """), {
                'cid':   ingreso_id,
                'fecha': fecha_obj,
                'code':  item_code,
                'name':  (it.get('item_name') or item_code),
                'qty':   quantity,
                'pc':    price_cost,
                'sub':   subtotal,
                'alm':   almacen,
                'user':  user_code,
            })

        db.session.commit()
        accion = 'actualizado' if data.get('ingreso_id') else 'registrado'
        return jsonify({'success': True,
                        'message': f'Ingreso {accion} correctamente.',
                        'ingreso_id': ingreso_id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main.route('/almacen/ingresos/<int:ingreso_id>/anular', methods=['POST'])
@login_required
def almacen_ingresos_anular(ingreso_id):
    try:
        db.session.execute(text(
            "UPDATE ingreso_c SET id_estado = 0 WHERE id = :id"
        ), {'id': ingreso_id})
        db.session.execute(text(
            "DELETE FROM movimientos_almacen WHERE invoice_id = :id AND origen = 'INGRESO'"
        ), {'id': ingreso_id})
        db.session.commit()
        return jsonify({'success': True, 'message': 'Ingreso anulado correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
