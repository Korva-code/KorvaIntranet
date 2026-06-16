import json
from flask import render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_tipo':   m.get('id_tipo'),
        'nombre':    m.get('nombre') or '',
        'id_estado': m.get('id_estado') if m.get('id_estado') is not None else 1,
    }


@main.route('/maestras/tipos-compra')
@login_required
def maestras_tipos_compra():
    rows = db.session.execute(text("SELECT * FROM sp_tipos_compra_listar_todos()")).fetchall()
    tipos = [_row_to_dict(r) for r in rows]
    return render_template('main/maestras_tipos_compra.html',
                           title='Tipos de Compra',
                           section='Maestras', page='Tipos de Compra',
                           tipos_json=json.dumps(tipos, ensure_ascii=False),
                           total=len(tipos))


@main.route('/maestras/tipos-compra/guardar', methods=['POST'])
@login_required
def maestras_tipos_compra_guardar():
    data    = request.get_json(force=True)
    id_tipo = int(data.get('id_tipo') or 0)
    nombre  = (data.get('nombre') or '').strip()

    try:
        row = db.session.execute(text("""
            SELECT success, message, id_tipo
            FROM sp_tipos_compra_guardar(:id, :nombre)
        """), {'id': id_tipo, 'nombre': nombre}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1], 'id_tipo': row[2]})
        else:
            db.session.rollback()
            return jsonify({'success': False, 'message': row[1] if row else 'Error desconocido'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@main.route('/maestras/tipos-compra/<int:id_tipo>/estado', methods=['POST'])
@login_required
def maestras_tipos_compra_estado(id_tipo):
    data      = request.get_json(force=True)
    id_estado = int(data.get('id_estado', 0))

    try:
        row = db.session.execute(text("""
            SELECT success, message
            FROM sp_tipos_compra_estado(:id, :estado)
        """), {'id': id_tipo, 'estado': id_estado}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1]})
        else:
            db.session.rollback()
            return jsonify({'success': False, 'message': row[1] if row else 'Error'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
