import json
import re as _re
from datetime import date
from flask import render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db

try:
    from playwright.sync_api import sync_playwright as _sync_playwright
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False

try:
    import requests as _req
    from bs4 import BeautifulSoup
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

_SCRAPING_OK = _PLAYWRIGHT_OK or _REQUESTS_OK

_MESES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

_BASE_URL    = 'https://e-consulta.sunat.gob.pe'
_SUNAT_URL   = f'{_BASE_URL}/cl-at-ittipcam/tcS01Alias'
_API_LISTAR  = f'{_BASE_URL}/cl-at-ittipcam/tcS01Alias/listarTipoCambio'


# ── Parsers ───────────────────────────────────────────────────

def _parse_json_tc(data):
    """
    Parsea la respuesta real de SUNAT:
    [{"codTipo":"C","fecPublica":"DD/MM/YYYY","valTipo":"3.412"}, ...]
    Agrupa por día y retorna [{dia, tc_compra, tc_venta}, ...].
    """
    if isinstance(data, dict):
        for key in ('data', 'tipoCambio', 'tipo_cambio', 'result',
                    'items', 'lista', 'listaTipoCambio'):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        return []

    by_dia: dict = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            cod   = str(item.get('codTipo', '')).upper().strip()
            fecha = str(item.get('fecPublica') or item.get('fecha') or '')
            valor_raw = item.get('valTipo') or item.get('valor')

            if cod not in ('C', 'V') or not fecha or valor_raw is None:
                continue

            dia   = int(fecha.split('/')[0])
            valor = float(valor_raw)

            if not (1 <= dia <= 31 and 1.0 < valor < 20.0):
                continue

            entry = by_dia.setdefault(dia, {'dia': dia})
            if cod == 'C':
                entry['tc_compra'] = valor
            else:
                entry['tc_venta'] = valor
        except (TypeError, ValueError, IndexError):
            pass

    return [v for v in sorted(by_dia.values(), key=lambda x: x['dia'])
            if 'tc_compra' in v and 'tc_venta' in v]


# ── Playwright scraper (Chrome real, pasa el WAF) ─────────────

# Parámetros confirmados: {anio, mes} con mes 0-indexed (igual que JS getMonth())
_AJAX_JS = """
() => new Promise((resolve) => {{
    $.ajax({{
        url        : CONTEXT_APP + '/tcS01Alias/listarTipoCambio',
        type       : 'POST',
        contentType: 'application/json; charset=UTF-8',
        data       : JSON.stringify({{ anio: {anio}, mes: {mes0} }}),
        dataType   : 'json',
        success    : function(r) {{ resolve(r); }},
        error      : function(x) {{ resolve({{ _err: x.status, _text: x.responseText }}); }}
    }});
}})
"""

def _launch_browser(p):
    _offscreen  = ['--window-position=-10000,-10000', '--window-size=800,600']
    _clean_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--ignore-certificate-errors',
        '--no-first-run',
        '--no-default-browser-check',
    ]
    # Quitar --enable-automation que Playwright inyecta por defecto
    _no_auto = ['--enable-automation']

    configs = [
        # Sistema Chrome, sin flag de automatización (mejor huella TLS)
        {'channel': 'chrome',  'headless': False,
         'args': _offscreen + _clean_args, 'ignore_default_args': _no_auto},
        # Sistema Edge
        {'channel': 'msedge',  'headless': False,
         'args': _offscreen + _clean_args, 'ignore_default_args': _no_auto},
        # Chrome sin ignore_default_args (fallback)
        {'channel': 'chrome',  'headless': False, 'args': _offscreen + _clean_args},
        # Edge sin ignore_default_args
        {'channel': 'msedge',  'headless': False, 'args': _offscreen + _clean_args},
        # Chromium Playwright headless=new
        {'headless': False,
         'args': _offscreen + _clean_args + ['--headless=new'],
         'ignore_default_args': _no_auto},
        # Último recurso
        {'headless': True,
         'args': ['--disable-http2'] + _clean_args},
    ]
    for cfg in configs:
        try:
            return p.chromium.launch(**cfg)
        except Exception:
            continue
    return None


def _make_context(browser):
    return browser.new_context(
        locale='es-PE',
        ignore_https_errors=True,
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
    )


def _goto_and_wait(page):
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page.goto(_SUNAT_URL, wait_until='domcontentloaded', timeout=60_000)
    page.wait_for_function(
        "typeof $ !== 'undefined' && typeof CONTEXT_APP !== 'undefined'",
        timeout=20_000,
    )


def _scrape_sunat_playwright(anio, mes):
    """
    Intercepta la llamada automática de la página a listarTipoCambio,
    mantiene el token de sesión original y solo cambia anio/mes.
    """
    def _inject(route):
        try:
            body = json.loads(route.request.post_data or '{}')
        except Exception:
            body = {}
        # Mantener token y cualquier otro campo; solo cambiar año y mes
        body['anio'] = anio
        body['mes']  = mes - 1   # 0-indexed
        headers = {**route.request.headers,
                   'content-type': 'application/json; charset=UTF-8'}
        route.continue_(post_data=json.dumps(body), headers=headers)

    with _sync_playwright() as p:
        browser = _launch_browser(p)
        if not browser:
            raise RuntimeError('No se pudo iniciar ningún navegador compatible.')

        context = _make_context(browser)
        page    = context.new_page()
        page.route('**/listarTipoCambio', _inject)

        try:
            with page.expect_response(
                lambda r: 'listarTipoCambio' in r.url,
                timeout=25_000,
            ) as resp_info:
                page.goto(_SUNAT_URL, wait_until='domcontentloaded', timeout=60_000)

            resp = resp_info.value
            try:
                raw = resp.json()
            except Exception:
                raw = []
        finally:
            browser.close()

    return _parse_json_tc(raw)


# ── Main scraper ──────────────────────────────────────────────

def _scrape_sunat(anio, mes):
    if _PLAYWRIGHT_OK:
        return _scrape_sunat_playwright(anio, mes)
    return []



# ── API pública ───────────────────────────────────────────────

@main.route('/api/tipo-cambio')
@login_required
def api_tipo_cambio():
    """Devuelve tc_compra y tc_venta para una fecha dada (YYYY-MM-DD).
    Si no hay registro exacto busca el día hábil anterior más cercano
    dentro del mismo mes. Parámetro: ?fecha=YYYY-MM-DD
    """
    fecha_str = request.args.get('fecha', date.today().isoformat())
    try:
        from datetime import datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Fecha inválida. Use YYYY-MM-DD.'}), 400

    row = db.session.execute(text("""
        SELECT tc_compra, tc_venta, anio, mes, dia
        FROM   tipos_cambio
        WHERE  anio = :a AND mes = :m AND dia = :d
        LIMIT  1
    """), {'a': fecha.year, 'm': fecha.month, 'd': fecha.day}).fetchone()

    if not row:
        # Fallback 1: día anterior en el mismo mes
        row = db.session.execute(text("""
            SELECT tc_compra, tc_venta, anio, mes, dia
            FROM   tipos_cambio
            WHERE  anio = :a AND mes = :m AND dia < :d
            ORDER  BY dia DESC
            LIMIT  1
        """), {'a': fecha.year, 'm': fecha.month, 'd': fecha.day}).fetchone()

    if not row:
        # Fallback 2: registro más reciente disponible (cualquier fecha anterior)
        row = db.session.execute(text("""
            SELECT tc_compra, tc_venta, anio, mes, dia
            FROM   tipos_cambio
            WHERE  (anio < :a)
               OR  (anio = :a AND mes < :m)
               OR  (anio = :a AND mes = :m AND dia < :d)
            ORDER  BY anio DESC, mes DESC, dia DESC
            LIMIT  1
        """), {'a': fecha.year, 'm': fecha.month, 'd': fecha.day}).fetchone()

    if not row:
        return jsonify({'found': False, 'tc_compra': None, 'tc_venta': None, 'fecha': fecha_str})

    tc_fecha = f"{int(row[4]):02d}/{int(row[3]):02d}/{int(row[2])}"
    return jsonify({
        'found':     True,
        'tc_compra': float(row[0]),
        'tc_venta':  float(row[1]),
        'fecha':     tc_fecha,
    })


# ── DB helpers ────────────────────────────────────────────────

def _row_to_dict(r):
    m = dict(r._mapping)
    return {
        'id_tipo_cambio': m.get('id_tipo_cambio'),
        'anio':      m.get('anio'),
        'mes':       m.get('mes'),
        'dia':       m.get('dia'),
        'tc_compra': float(m['tc_compra']) if m.get('tc_compra') is not None else None,
        'tc_venta':  float(m['tc_venta'])  if m.get('tc_venta')  is not None else None,
    }


# ── Routes ────────────────────────────────────────────────────

@main.route('/maestras/tipos-cambio')
@login_required
def maestras_tipos_cambio():
    hoy  = date.today()
    anio = int(request.args.get('anio', hoy.year))
    mes  = int(request.args.get('mes',  hoy.month))
    rows = db.session.execute(
        text("SELECT * FROM sp_tipos_cambio_listar(:a, :m)"),
        {'a': anio, 'm': mes}
    ).fetchall()
    datos = [_row_to_dict(r) for r in rows]
    anios = list(range(hoy.year, 2014, -1))
    return render_template(
        'main/maestras_tipos_cambio.html',
        title='Tipos de Cambio',
        section='Maestras', page='Tipos de Cambio',
        datos_json=json.dumps(datos, ensure_ascii=False),
        total=len(datos),
        anios=anios,
        meses=_MESES,
        sel_anio=anio,
        sel_mes=mes,
        scraping_ok=_SCRAPING_OK,
    )


@main.route('/maestras/tipos-cambio/importar-sunat', methods=['POST'])
@login_required
def maestras_tipos_cambio_importar():
    if not _PLAYWRIGHT_OK:
        return jsonify({'success': False,
                        'message': 'Playwright no instalado. Ejecute: pip install playwright && playwright install chromium'})

    data = request.get_json(force=True)
    try:
        anio = int(data.get('anio', 0))
        mes  = int(data.get('mes',  0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Parámetros inválidos.'})

    if not (1900 < anio < 2100 and 1 <= mes <= 12):
        return jsonify({'success': False, 'message': 'Año o mes fuera de rango.'})

    try:
        rates = _scrape_sunat(anio, mes)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al consultar SUNAT: {e}'})

    if not rates:
        return jsonify({'success': False,
                        'message': (f'SUNAT no tiene datos publicados para {_MESES[mes-1]} {anio}. '
                                    'Pruebe con un mes anterior que ya esté completo.')})

    nuevos = 0
    try:
        for r in rates:
            result = db.session.execute(text("""
                INSERT INTO tipos_cambio (anio, mes, dia, tc_compra, tc_venta)
                VALUES (:anio, :mes, :dia, :compra, :venta)
                ON CONFLICT (anio, mes, dia) DO NOTHING
            """), {'anio': anio, 'mes': mes, 'dia': r['dia'],
                   'compra': r['tc_compra'], 'venta': r['tc_venta']})
            nuevos += result.rowcount
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar: {e}'})

    existentes = len(rates) - nuevos
    msg = f'{nuevos} registro(s) importado(s) correctamente.'
    if existentes:
        msg += f' {existentes} ya existían (no se modificaron).'
    return jsonify({'success': True, 'message': msg, 'nuevos': nuevos, 'total': len(rates)})


@main.route('/maestras/tipos-cambio/debug-pw')
@login_required
def maestras_tipos_cambio_debug_pw():
    """Debug: prueba la inyección de ruta para el mes/año pedido."""
    if not _PLAYWRIGHT_OK:
        return jsonify({'error': 'Playwright no instalado'})

    hoy  = date.today()
    anio = int(request.args.get('anio', hoy.year))
    mes  = int(request.args.get('mes',  hoy.month))

    target_body   = json.dumps({'anio': anio, 'mes': mes - 1})
    inject_log    = {}

    def _inject_debug(route):
        inject_log['original_body'] = route.request.post_data
        try:
            body = json.loads(route.request.post_data or '{}')
        except Exception:
            body = {}
        body['anio'] = anio
        body['mes']  = mes - 1
        final_body = json.dumps(body)
        inject_log['final_body'] = final_body
        headers = {**route.request.headers,
                   'content-type': 'application/json; charset=UTF-8'}
        route.continue_(post_data=final_body, headers=headers)

    with _sync_playwright() as p:
        browser = _launch_browser(p)
        if not browser:
            return jsonify({'error': 'No se pudo iniciar ningún navegador'})
        context = _make_context(browser)
        page    = context.new_page()
        page.route('**/listarTipoCambio', _inject_debug)

        try:
            with page.expect_response(
                lambda r: 'listarTipoCambio' in r.url,
                timeout=25_000,
            ) as resp_info:
                page.goto(_SUNAT_URL, wait_until='domcontentloaded', timeout=60_000)

            resp = resp_info.value
            inject_log['status'] = resp.status
            try:
                inject_log['json'] = resp.json()
            except Exception:
                inject_log['text'] = resp.text()[:800]
        except Exception as e:
            inject_log['error'] = str(e)
        finally:
            browser.close()

    return jsonify({
        'anio': anio, 'mes': mes, 'mes0': mes - 1,
        'injected_body': target_body,
        'inject_result': inject_log,
        'parsed_rates':  _parse_json_tc(inject_log.get('json') or []),
    })
