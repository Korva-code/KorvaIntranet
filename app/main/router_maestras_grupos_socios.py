import json
from flask import render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'group_code': (m.get('group_code') or '').strip(),
        'group_name': (m.get('group_name') or '').strip(),
        'id_estado':  m.get('id_estado') if m.get('id_estado') is not None else 1,
    }


@main.route('/maestras/grupos-socios')
@login_required
def maestras_grupos_socios():
    rows   = db.session.execute(text("SELECT * FROM sp_grupos_socios_listar()")).fetchall()
    grupos = [_row_to_dict(r) for r in rows]
    return render_template('main/maestras_grupos_socios.html',
                           title='Grupos de Socios de Negocio',
                           section='Maestras', page='Grupos de Socios',
                           grupos_json=json.dumps(grupos, ensure_ascii=False),
                           total=len(grupos))


@main.route('/maestras/grupos-socios/guardar', methods=['POST'])
@login_required
def maestras_grupos_socios_guardar():
    data       = request.get_json(force=True)
    group_code = (data.get('group_code') or '').strip()
    group_name = (data.get('group_name') or '').strip()
    es_nuevo   = bool(data.get('es_nuevo', True))

    try:
        row = db.session.execute(text("""
            SELECT success, message, group_code
            FROM sp_grupos_socios_guardar(:code, :name, :nuevo)
        """), {'code': group_code, 'name': group_name, 'nuevo': es_nuevo}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1], 'group_code': row[2]})
        else:
            db.session.rollback()
            return jsonify({'success': False, 'message': row[1] if row else 'Error desconocido'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@main.route('/maestras/grupos-socios/<group_code>/estado', methods=['POST'])
@login_required
def maestras_grupos_socios_estado(group_code):
    data      = request.get_json(force=True)
    id_estado = int(data.get('id_estado', 0))

    try:
        row = db.session.execute(text("""
            SELECT success, message
            FROM sp_grupos_socios_estado(:code, :estado)
        """), {'code': group_code, 'estado': id_estado}).fetchone()

        if row and row[0]:
            db.session.commit()
            return jsonify({'success': True, 'message': row[1]})
        else:
            db.session.rollback()
            return jsonify({'success': False, 'message': row[1] if row else 'Error'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
