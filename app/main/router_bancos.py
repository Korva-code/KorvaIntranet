import json
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import Banco


@main.route('/maestras/bancos')
@login_required
def bancos():
    rows = db.session.execute(text("SELECT * FROM sp_bancos_listar(0)")).fetchall()
    bancos_list = [{
        'id_banco':   r[0],
        'cod_banco':  r[1] or '',
        'nombre':     r[2] or '',
        'nro_cuenta': r[3] or '',
        'cci':        r[4] or '',
        'moneda':     r[5] or 'SOL',
        'id_estado':  r[6] if r[6] is not None else 1,
    } for r in rows]
    bancos_json = json.dumps(bancos_list, ensure_ascii=False)
    return render_template('main/bancos.html', title='Bancos',
                           section='Maestras', page='Bancos',
                           bancos_json=bancos_json,
                           total=len(bancos_list))


@main.route('/maestras/bancos/nuevo', methods=['POST'])
@login_required
def banco_nuevo():
    banco = Banco(
        cod_banco  = request.form.get('cod_banco',  '').strip() or None,
        nombre     = request.form.get('nombre',     '').strip() or None,
        nro_cuenta = request.form.get('nro_cuenta', '').strip() or None,
        cci        = request.form.get('cci',        '').strip() or None,
        moneda     = request.form.get('moneda', 'SOL').strip(),
        id_estado  = int(request.form.get('id_estado', 1) or 1),
    )
    db.session.add(banco)
    db.session.commit()
    flash(f'Banco «{banco.nombre}» registrado correctamente.', 'success')
    return redirect(url_for('main.bancos'))


@main.route('/maestras/bancos/<int:id_banco>/editar', methods=['POST'])
@login_required
def banco_editar(id_banco):
    banco = db.session.get(Banco, id_banco)
    if not banco:
        flash(f'Banco #{id_banco} no encontrado.', 'danger')
        return redirect(url_for('main.bancos'))
    banco.cod_banco  = request.form.get('cod_banco',  '').strip() or None
    banco.nombre     = request.form.get('nombre',     '').strip() or None
    banco.nro_cuenta = request.form.get('nro_cuenta', '').strip() or None
    banco.cci        = request.form.get('cci',        '').strip() or None
    banco.moneda     = request.form.get('moneda', 'SOL').strip()
    banco.id_estado  = int(request.form.get('id_estado', 1) or 1)
    db.session.commit()
    flash(f'Banco «{banco.nombre}» actualizado correctamente.', 'success')
    return redirect(url_for('main.bancos'))


@main.route('/api/bancos')
@login_required
def api_bancos():
    p = request.args.get('id_banco', '0').strip()
    p = int(p) if p.isdigit() else 0
    rows = db.session.execute(
        text("SELECT * FROM sp_bancos_listar(:p)"), {'p': p}
    ).fetchall()
    return jsonify([{
        'id_banco':   r[0],
        'cod_banco':  r[1] or '',
        'nombre':     r[2] or '',
        'nro_cuenta': r[3] or '',
        'cci':        r[4] or '',
        'moneda':     r[5] or 'SOL',
        'id_estado':  r[6] if r[6] is not None else 1,
    } for r in rows])
