import os
from app import create_app, db
from app.models import Usuario

app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Usuario': Usuario}


if __name__ == '__main__':
    with app.app_context():
        # Solo crea tablas que no existan — nunca toca w_usuarios
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
