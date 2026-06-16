import json
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db
from app.models import ItemGroup


@main.route('/maestras/grupos')
@login_required
def grupos_articulos():
    rows = db.session.execute(text("""
        SELECT ig.item_group_code,
               ig.item_group_name,
               TRIM(ig."CostingCode")            AS costing_code,
               COALESCE(cc.costingcodename, '')  AS costing_name
        FROM items_group ig
        LEFT JOIN costingcodes cc ON TRIM(cc.costingcode) = TRIM(ig."CostingCode")
        ORDER BY ig.item_group_code
    """)).fetchall()

    costings = db.session.execute(text(
        "SELECT TRIM(costingcode) AS costingcode, costingcodename FROM costingcodes ORDER BY costingcodename"
    )).fetchall()

    grupos_list = [
        {'item_group_code': r[0], 'item_group_name': r[1] or '',
         'CostingCode': r[2] or '', 'costing_name': r[3] or ''}
        for r in rows
    ]
    grupos_json = json.dumps(grupos_list, ensure_ascii=False)

    return render_template('main/grupos_articulos.html', title='Grupos de Artículos',
                           section='Maestras', page='Grupos de Artículos',
                           grupos=rows, grupos_json=grupos_json, costings=costings)


@main.route('/maestras/grupos/nuevo', methods=['POST'])
@login_required
def grupo_nuevo():
    code_str = request.form.get('item_group_code', '').strip()
    if not code_str:
        flash('El código del grupo es obligatorio.', 'danger')
        return redirect(url_for('main.grupos_articulos'))
    try:
        code = int(code_str)
    except ValueError:
        flash('El código debe ser un número entero.', 'danger')
        return redirect(url_for('main.grupos_articulos'))

    if db.session.get(ItemGroup, code):
        flash(f'Ya existe un grupo con el código {code}.', 'warning')
        return redirect(url_for('main.grupos_articulos'))

    g = ItemGroup(
        item_group_code=code,
        item_group_name=request.form.get('item_group_name', '').strip() or None,
        CostingCode=request.form.get('CostingCode', '').strip() or None,
    )
    db.session.add(g)
    db.session.commit()
    flash(f'Grupo {code} registrado correctamente.', 'success')
    return redirect(url_for('main.grupos_articulos'))


@main.route('/maestras/grupos/<int:grupo_code>/editar', methods=['POST'])
@login_required
def grupo_editar(grupo_code):
    g = db.session.get(ItemGroup, grupo_code)
    if not g:
        flash(f'Grupo {grupo_code} no encontrado.', 'danger')
        return redirect(url_for('main.grupos_articulos'))

    g.item_group_name = request.form.get('item_group_name', '').strip() or None
    g.CostingCode     = request.form.get('CostingCode', '').strip() or None
    db.session.commit()
    flash(f'Grupo {grupo_code} actualizado correctamente.', 'success')
    return redirect(url_for('main.grupos_articulos'))
