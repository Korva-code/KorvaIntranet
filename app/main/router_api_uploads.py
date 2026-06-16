"""
Endpoint genérico de carga de imágenes.
POST /api/upload-imagen
  Form-data: file=<archivo>, modulo=<nombre_carpeta>
Requiere: pip install Pillow
"""
import os
import uuid

from flask import current_app, request, jsonify
from flask_login import login_required

from app.main import main

MAX_SIZE = (900, 900)   # px máximo en cualquier dimensión
QUALITY  = 78           # calidad JPEG (0-95)
ALLOWED  = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}


def _ext(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


@main.route('/api/upload-imagen', methods=['POST'])
@login_required
def api_upload_imagen():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No se recibió archivo.'}), 400

    if _ext(file.filename) not in ALLOWED:
        return jsonify({'success': False,
                        'message': f'Formato no permitido. Use: {", ".join(sorted(ALLOWED))}.'}), 400

    modulo = request.form.get('modulo', 'general').strip().lower()
    modulo = ''.join(c for c in modulo if c.isalnum() or c == '_') or 'general'

    carpeta = os.path.join(current_app.static_folder, 'uploads', modulo)
    os.makedirs(carpeta, exist_ok=True)

    nombre = f"{uuid.uuid4().hex}.jpg"
    ruta   = os.path.join(carpeta, nombre)

    try:
        from PIL import Image
        img = Image.open(file.stream)
        img.thumbnail(MAX_SIZE, Image.LANCZOS)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.save(ruta, 'JPEG', quality=QUALITY, optimize=True)
    except ImportError:
        # Pillow no instalado: guardar sin redimensionar
        file.stream.seek(0)
        file.save(ruta)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error procesando imagen: {e}'}), 400

    url = f'/static/uploads/{modulo}/{nombre}'
    return jsonify({'success': True, 'filename': nombre, 'url': url})
