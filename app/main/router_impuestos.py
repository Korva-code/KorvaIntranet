from flask import jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


@main.route('/api/impuestos')
@login_required
def api_impuestos():
    rows = db.session.execute(text(
        "SELECT codigo, descripcion FROM impuestos ORDER BY codigo"
    )).fetchall()
    return jsonify([{'codigo': r[0], 'descripcion': r[1]} for r in rows])
