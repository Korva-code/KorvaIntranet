from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth
from app.models import Usuario
from app import db


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        id_usuario = request.form.get('username', '').strip()
        contrasena = request.form.get('password', '')
        remember   = bool(request.form.get('remember'))

        user = db.session.get(Usuario, id_usuario)

        if user and user.is_active and user.check_password(contrasena):
            login_user(user, remember=remember)
            flash(f'Bienvenido, {user.full_name or user.id_usuario}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))

        flash('Usuario o contraseña incorrectos. Intente de nuevo.', 'danger')

    return render_template('auth/login.html', title='Iniciar Sesión')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))
