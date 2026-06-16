"""
Generador de CRUD básico para nuevos módulos del intranet.

Uso:
  python crud_generator.py --model Producto --fields "nombre:str precio:float activo:bool"

Genera:
  - app/models/<model>.py       (modelo SQLAlchemy)
  - app/<model_lower>/          (blueprint con rutas CRUD)
  - templates/<model_lower>/    (plantillas list, form, detail)
"""

import argparse
import os
import sys

MODELS_DIR    = os.path.join('app', 'models')
BLUEPRINTS_DIR = 'app'
TEMPLATES_DIR = 'templates'

TYPE_MAP = {
    'str':   'db.String(256)',
    'int':   'db.Integer',
    'float': 'db.Float',
    'bool':  'db.Boolean, default=True',
    'text':  'db.Text',
    'date':  'db.Date',
    'datetime': 'db.DateTime',
}


def parse_fields(raw: str) -> list[tuple[str, str]]:
    fields = []
    for token in raw.split():
        if ':' in token:
            name, ftype = token.split(':', 1)
            fields.append((name.strip(), ftype.strip()))
        else:
            fields.append((token.strip(), 'str'))
    return fields


def generate_model(model: str, fields: list[tuple[str, str]]) -> str:
    lines = [
        'from datetime import datetime',
        'from app import db',
        '',
        '',
        f'class {model}(db.Model):',
        f'    __tablename__ = \'{model.lower()}s\'',
        '',
        '    id         = db.Column(db.Integer, primary_key=True)',
    ]
    for name, ftype in fields:
        col_type = TYPE_MAP.get(ftype, f'db.String(256)')
        lines.append(f'    {name:<12} = db.Column({col_type})')
    lines += [
        '    created_at = db.Column(db.DateTime, default=datetime.utcnow)',
        '    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)',
        '',
        '    def __repr__(self):',
        f'        return f\'<{model} {{self.id}}>\'',
    ]
    return '\n'.join(lines)


def generate_routes(model: str, fields: list[tuple[str, str]]) -> str:
    ml = model.lower()
    field_names = [f[0] for f in fields]
    form_assigns = '\n    '.join(
        f'obj.{f} = request.form.get(\'{f}\', \'\').strip()' for f in field_names
    )
    return f'''from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.{ml} import {ml}
from app.models.{ml} import {model}
from app import db


@{ml}.route('/')
@login_required
def list_{ml}():
    items = {model}.query.order_by({model}.id.desc()).all()
    return render_template('{ml}/list.html', items=items, title='{model}s')


@{ml}.route('/nuevo', methods=['GET', 'POST'])
@login_required
def create_{ml}():
    if request.method == 'POST':
        obj = {model}()
        {form_assigns}
        db.session.add(obj)
        db.session.commit()
        flash('{model} creado correctamente.', 'success')
        return redirect(url_for('{ml}.list_{ml}'))
    return render_template('{ml}/form.html', obj=None, title='Nuevo {model}')


@{ml}.route('/<int:pk>/editar', methods=['GET', 'POST'])
@login_required
def update_{ml}(pk):
    obj = db.get_or_404({model}, pk)
    if request.method == 'POST':
        {form_assigns}
        db.session.commit()
        flash('{model} actualizado.', 'success')
        return redirect(url_for('{ml}.list_{ml}'))
    return render_template('{ml}/form.html', obj=obj, title='Editar {model}')


@{ml}.route('/<int:pk>/eliminar', methods=['POST'])
@login_required
def delete_{ml}(pk):
    obj = db.get_or_404({model}, pk)
    db.session.delete(obj)
    db.session.commit()
    flash('{model} eliminado.', 'info')
    return redirect(url_for('{ml}.list_{ml}'))
'''


def write_file(path: str, content: str, dry_run: bool = False):
    if dry_run:
        print(f'\n{"─"*60}\n  [DRY-RUN] {path}\n{"─"*60}')
        print(content)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        print(f'  [SKIP]  {path} ya existe.')
        return
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  [OK]    {path}')


def main():
    parser = argparse.ArgumentParser(description='Generador de CRUD para módulos del intranet')
    parser.add_argument('--model',  required=True, help='Nombre del modelo (ej: Producto)')
    parser.add_argument('--fields', required=True,
                        help='Campos: "nombre:str precio:float activo:bool"')
    parser.add_argument('--dry-run', action='store_true',
                        help='Muestra el código sin crear archivos')
    args = parser.parse_args()

    model  = args.model.capitalize()
    fields = parse_fields(args.fields)
    ml     = model.lower()
    dry    = args.dry_run

    print(f'\nGenerando CRUD para: {model}')
    print(f'Campos: {fields}\n')

    # Modelo
    write_file(
        os.path.join(MODELS_DIR, f'{ml}.py'),
        generate_model(model, fields),
        dry,
    )

    # Blueprint __init__
    write_file(
        os.path.join(BLUEPRINTS_DIR, ml, '__init__.py'),
        f'from flask import Blueprint\n\n{ml} = Blueprint(\'{ml}\', __name__)\n\nfrom app.{ml} import routes  # noqa\n',
        dry,
    )

    # Rutas
    write_file(
        os.path.join(BLUEPRINTS_DIR, ml, 'routes.py'),
        generate_routes(model, fields),
        dry,
    )

    # Templates básicos
    list_tpl = f'{{% extends \'maestras/base.html\' %}}\n{{% block content %}}\n<h4>{model}s</h4>\n<p>{{{{ items|length }}}} registros</p>\n{{% endblock %}}\n'
    form_tpl = f'{{% extends \'maestras/base.html\' %}}\n{{% block content %}}\n<h4>{{{{ title }}}}</h4>\n<form method="POST">\n'
    for name, _ in fields:
        form_tpl += f'  <input name="{name}" value="{{{{ obj.{name} if obj else \'\' }}}}" />\n'
    form_tpl += '  <button type="submit">Guardar</button>\n</form>\n{% endblock %}\n'

    write_file(os.path.join(TEMPLATES_DIR, ml, 'list.html'), list_tpl, dry)
    write_file(os.path.join(TEMPLATES_DIR, ml, 'form.html'), form_tpl, dry)

    if not dry:
        print(f'\n[!] Registre el blueprint en app/__init__.py:')
        print(f'    from app.{ml} import {ml} as {ml}_bp')
        print(f'    app.register_blueprint({ml}_bp, url_prefix=\'/{ml}s\')')


if __name__ == '__main__':
    main()
