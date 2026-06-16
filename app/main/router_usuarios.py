from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.main import main
from app import db
from app.models import Usuario, Warehouse, Perfil
from sqlalchemy import text


@main.route('/mi-perfil')
@login_required
def mi_perfil():
    whs_name = current_user.whs_name
    return render_template('main/mi_perfil.html', title='Mi Perfil',
                           section='', page='Mi Perfil', whs_name=whs_name)


@main.route('/mi-perfil/cambiar-contrasena', methods=['POST'])
@login_required
def cambiar_contrasena():
    actual       = request.form.get('contrasena_actual', '')
    nueva        = request.form.get('contrasena_nueva', '')
    confirmacion = request.form.get('contrasena_confirmar', '')

    if not current_user.check_password(actual):
        flash('La contraseña actual es incorrecta.', 'danger')
    elif nueva != confirmacion:
        flash('Las contraseñas nuevas no coinciden.', 'warning')
    elif len(nueva) < 4:
        flash('La contraseña debe tener al menos 4 caracteres.', 'warning')
    else:
        current_user.contrasena = nueva
        db.session.commit()
        flash('Contraseña actualizada correctamente.', 'success')

    return redirect(url_for('main.mi_perfil'))


@main.route('/admin/usuarios')
@login_required
def admin_usuarios():
    todos      = Usuario.query.order_by(Usuario.id_usuario).all()
    warehouses = Warehouse.query.order_by(Warehouse.whs_name).all()
    perfiles   = Perfil.query.order_by(Perfil.id_perfil).all()
    return render_template('main/admin_usuarios.html', title='Administrar Usuarios',
                           section='Administrador', page='Usuarios del Sistema',
                           usuarios=todos, warehouses=warehouses, perfiles=perfiles)


@main.route('/admin/usuarios/<id_usuario>/editar', methods=['POST'])
@login_required
def admin_editar_usuario(id_usuario):
    u = db.session.get(Usuario, str(id_usuario))
    if not u:
        flash(f'Usuario {id_usuario} no encontrado.', 'danger')
        return redirect(url_for('main.admin_usuarios'))

    u.nombres   = request.form.get('nombres', '').strip() or u.nombres
    u.correo    = request.form.get('correo', '').strip() or None
    u.ubicacion = request.form.get('ubicacion', '').strip() or None
    u.id_perfil = int(request.form['id_perfil']) if request.form.get('id_perfil') else u.id_perfil
    u.id_rol    = int(request.form['id_rol'])    if request.form.get('id_rol')    else u.id_rol
    u.id_estado = int(request.form['id_estado']) if request.form.get('id_estado') else u.id_estado
    whs = request.form.get('whs_code', '').strip()
    u.whs_code  = whs if whs else None

    db.session.commit()
    flash(f'Usuario {u.id_usuario} — {u.full_name} actualizado correctamente.', 'success')
    return redirect(url_for('main.admin_usuarios'))


@main.route('/api/usuarios-lista')
@login_required
def api_usuarios_lista():
    p_perfil = request.args.get('perfil', '0').strip()
    p_perfil = int(p_perfil) if p_perfil.isdigit() else 0
    rows = db.session.execute(
        text("SELECT * FROM sp_usuario_listado(:p)"),
        {'p': p_perfil}
    ).fetchall()
    return jsonify([{
        'id_usuario': r[0] or '',
        'nombres':    r[1] or '',
        'id_perfil':  r[2],
        'id_estado':  r[3],
        'id_rol':     r[4],
        'whs_code':   r[5] or '',
        'correo':     r[6] or '',
        'ubicacion':  r[7] or '',
    } for r in rows])
