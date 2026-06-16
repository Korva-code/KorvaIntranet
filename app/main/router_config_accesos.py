import json
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


# ── Helper: construye el árbol de menú para un perfil ─────────────

def get_user_menu(id_perfil):
    """Devuelve lista de secciones con sus hijos permitidos.
    Usada por el context_processor en cada request autenticado.
    """
    if not id_perfil:
        return []
    try:
        rows = db.session.execute(
            text("SELECT * FROM sp_menu_perfil(:p)"),
            {'p': id_perfil}
        ).fetchall()
    except Exception:
        return []

    sections = {}
    orphans  = []
    for r in rows:
        m = dict(r._mapping)
        item = {
            'id_menu':  m['id_menu'],
            'label':    m['label']    or '',
            'icon':     m['icon']     or 'bi-circle',
            'endpoint': m['endpoint'] or '',
            'orden':    m['orden']    or 0,
            'children': [],
        }
        if m['id_parent'] is None:
            sections[m['id_menu']] = item
        else:
            orphans.append((m['id_parent'], item))

    for pid, child in orphans:
        if pid in sections:
            sections[pid]['children'].append(child)

    for s in sections.values():
        s['children'].sort(key=lambda x: x['orden'])

    return sorted(sections.values(), key=lambda x: x['orden'])


# ── Vista principal ────────────────────────────────────────────────

@main.route('/config/accesos')
@login_required
def config_accesos():
    # Usuarios con perfil
    u_rows = db.session.execute(text("SELECT * FROM sp_usuarios_con_perfil()")).fetchall()
    usuarios = [dict(r._mapping) for r in u_rows]
    for u in usuarios:
        u['id_usuario']    = u.get('id_usuario') or ''
        u['nombres']       = u.get('nombres') or ''
        u['id_perfil']     = u.get('id_perfil')
        u['perfil_nombre'] = u.get('perfil_nombre') or '—'
        u['id_estado']     = u.get('id_estado') if u.get('id_estado') is not None else 1

    # Todos los ítems del menú (para el árbol de checkboxes)
    m_rows = db.session.execute(text("SELECT * FROM sp_menu_items_listar()")).fetchall()
    menu_items = [dict(r._mapping) for r in m_rows]

    # Perfiles disponibles
    p_rows = db.session.execute(text("SELECT * FROM sp_perfiles_listar()")).fetchall()
    perfiles = [{'id_perfil': dict(r._mapping)['id_perfil'],
                 'nombre':    dict(r._mapping)['nombre']}
                for r in p_rows]

    return render_template('main/config_accesos.html',
                           title='Accesos al Menú',
                           section='Configuración', page='Accesos al Menú',
                           usuarios_json=json.dumps(usuarios,    ensure_ascii=False),
                           menu_items_json=json.dumps(menu_items, ensure_ascii=False),
                           perfiles_json=json.dumps(perfiles,    ensure_ascii=False),
                           total=len(usuarios))


# ── API: permisos actuales de un perfil ───────────────────────────

@main.route('/api/config/perfil-menu-ids')
@login_required
def api_perfil_menu_ids():
    try:
        id_perfil = int(request.args.get('id_perfil', 0))
    except (ValueError, TypeError):
        return jsonify([])
    rows = db.session.execute(
        text("SELECT id_menu FROM sp_perfil_menu_ids(:p)"),
        {'p': id_perfil}
    ).fetchall()
    return jsonify([r[0] for r in rows])


# ── API: guardar perfil del usuario + permisos ────────────────────

@main.route('/api/config/accesos/guardar', methods=['POST'])
@login_required
def api_config_accesos_guardar():
    data = request.get_json(force=True)
    id_usuario = str(data.get('id_usuario') or '')
    try:
        id_perfil = int(data.get('id_perfil') or 0) or None
    except (ValueError, TypeError):
        id_perfil = None
    menu_ids = data.get('menu_ids') or []

    if not id_usuario or not id_perfil:
        return jsonify({'success': False, 'message': 'Usuario y perfil son requeridos.'})

    try:
        db.session.execute(
            text("SELECT sp_usuario_acceso_guardar(:u, :p, CAST(:m AS JSONB))"),
            {'u': id_usuario, 'p': id_perfil, 'm': json.dumps(menu_ids)}
        )
        db.session.commit()
        return jsonify({'success': True, 'message': 'Accesos guardados correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
