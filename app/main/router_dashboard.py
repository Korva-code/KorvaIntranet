import json
from collections import OrderedDict, defaultdict
from flask import render_template
from flask_login import login_required
from sqlalchemy import text
from app.main import main
from app import db


def _safe_float(v, default=0.0):
    """Convierte a float de forma segura."""
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(v, default=0):
    """Convierte a int de forma segura."""
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():

    # ─── KPI Ventas ───────────────────────────────────────────────────────────
    ventas_kpi = {
        'total_mes_actual':    0.0,
        'total_mes_anterior':  0.0,
        'variacion_pct':       0.0,
        'docs_mes_actual':     0,
        'clientes_mes_actual': 0,
        'ticket_promedio':     0.0,
        'total_anio':          0.0,
        'docs_anio':           0,
    }
    try:
        row = db.session.execute(text("SELECT * FROM fn_dash_ventas_kpi()")).fetchone()
        if row:
            ventas_kpi = {
                'total_mes_actual':    _safe_float(row[0]),
                'total_mes_anterior':  _safe_float(row[1]),
                'variacion_pct':       _safe_float(row[2]),
                'docs_mes_actual':     _safe_int(row[3]),
                'clientes_mes_actual': _safe_int(row[4]),
                'ticket_promedio':     _safe_float(row[5]),
                'total_anio':          _safe_float(row[6]),
                'docs_anio':           _safe_int(row[7]),
            }
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_ventas_kpi error: {e}')

    # ─── Ventas Mensuales por Grupo de Artículo (12 meses) ───────────────────
    _CHART_COLORS = [
        'rgba(13,110,253,.75)',   # azul
        'rgba(25,135,84,.75)',    # verde
        'rgba(220,53,69,.75)',    # rojo
        'rgba(255,193,7,.80)',    # amarillo
        'rgba(111,66,193,.75)',   # púrpura
        'rgba(253,126,20,.75)',   # naranja
        'rgba(32,201,151,.75)',   # teal
        'rgba(214,51,132,.75)',   # rosa
        'rgba(13,202,240,.75)',   # cyan
        'rgba(102,16,242,.75)',   # índigo
    ]
    ventas_mensuales_json = json.dumps({'labels': [], 'datasets': []}, ensure_ascii=False)
    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_dash_ventas_mensuales_grupos(12)")
        ).fetchall()

        month_index = OrderedDict()
        group_index = OrderedDict()
        data_map    = defaultdict(lambda: defaultdict(float))

        for r in rows:
            mk = (int(r[0]), int(r[1]))
            month_index[mk] = str(r[2]) if r[2] else ''
            gc = int(r[3]) if r[3] is not None else 0
            group_index[gc] = str(r[4]) if r[4] else 'Sin Grupo'
            data_map[gc][mk] = _safe_float(r[5])

        labels  = list(month_index.values())
        mk_list = list(month_index.keys())

        if labels:
            datasets = []
            for i, (gc, gname) in enumerate(group_index.items()):
                color = _CHART_COLORS[i % len(_CHART_COLORS)]
                datasets.append({
                    'label':           gname,
                    'data':            [data_map[gc].get(mk, 0.0) for mk in mk_list],
                    'backgroundColor': color,
                    'borderColor':     color.replace('.75', '1').replace('.80', '1'),
                    'borderWidth':     1,
                    'borderRadius':    3,
                })
            ventas_mensuales_json = json.dumps(
                {'labels': labels, 'datasets': datasets}, ensure_ascii=False
            )
        else:
            raise ValueError('sin filas')

    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_ventas_mensuales_grupos error: {e}')
        # fallback: totales simples por mes sin desglose por grupo
        try:
            rows = db.session.execute(
                text("SELECT * FROM fn_dash_ventas_mensuales(12)")
            ).fetchall()
            fb_labels = [str(r[2]) for r in rows if r[2]]
            fb_data   = [_safe_float(r[3]) for r in rows]
            if fb_labels:
                ventas_mensuales_json = json.dumps({'labels': fb_labels, 'datasets': [{
                    'label': 'Ventas',
                    'data':  fb_data,
                    'backgroundColor': 'rgba(13,110,253,.75)',
                    'borderColor':     'rgba(13,110,253,1)',
                    'borderWidth': 1, 'borderRadius': 3,
                }]}, ensure_ascii=False)
        except Exception as e2:
            db.session.rollback()
            print(f'[dashboard] fn_dash_ventas_mensuales fallback error: {e2}')

    # ─── Top Artículos Vendidos ───────────────────────────────────────────────
    ventas_top_articulos = []
    try:
        rows = db.session.execute(text("SELECT * FROM fn_dash_ventas_top_articulos(10)")).fetchall()
        for r in rows:
            ventas_top_articulos.append({
                'item_code':      str(r[0]) if r[0] else '',
                'item_name':      str(r[1]) if r[1] else '',
                'total_cantidad': _safe_float(r[2]),
                'total_monto':    _safe_float(r[3]),
                'cant_facturas':  _safe_int(r[4]),
            })
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_ventas_top_articulos error: {e}')

    # ─── Top Clientes ─────────────────────────────────────────────────────────
    ventas_top_clientes = []
    try:
        rows = db.session.execute(text("SELECT * FROM fn_dash_ventas_top_clientes(8)")).fetchall()
        for r in rows:
            ventas_top_clientes.append({
                'card_code':   str(r[0]) if r[0] else '',
                'card_name':   str(r[1]) if r[1] else '',
                'total_monto': _safe_float(r[2]),
                'cant_docs':   _safe_int(r[3]),
            })
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_ventas_top_clientes error: {e}')

    # ─── KPI Compras ──────────────────────────────────────────────────────────
    compras_kpi = {
        'total_mes_actual':    0.0,
        'total_mes_anterior':  0.0,
        'variacion_pct':       0.0,
        'docs_mes_actual':     0,
        'clientes_mes_actual': 0,
        'ticket_promedio':     0.0,
        'total_anio':          0.0,
        'docs_anio':           0,
    }
    try:
        row = db.session.execute(text("SELECT * FROM fn_dash_compras_kpi()")).fetchone()
        if row:
            compras_kpi = {
                'total_mes_actual':    _safe_float(row[0]),
                'total_mes_anterior':  _safe_float(row[1]),
                'variacion_pct':       _safe_float(row[2]),
                'docs_mes_actual':     _safe_int(row[3]),
                'clientes_mes_actual': _safe_int(row[4]),
                'ticket_promedio':     _safe_float(row[5]),
                'total_anio':          _safe_float(row[6]),
                'docs_anio':           _safe_int(row[7]),
            }
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_compras_kpi error: {e}')

    # ─── Compras Mensuales por Grupo de Artículo (12 meses) ──────────────────
    _CHART_COLORS_C = [
        'rgba(253,126,20,.75)',   # naranja
        'rgba(220,53,69,.75)',    # rojo
        'rgba(25,135,84,.75)',    # verde
        'rgba(13,110,253,.75)',   # azul
        'rgba(111,66,193,.75)',   # púrpura
        'rgba(255,193,7,.80)',    # amarillo
        'rgba(32,201,151,.75)',   # teal
        'rgba(214,51,132,.75)',   # rosa
        'rgba(13,202,240,.75)',   # cyan
        'rgba(102,16,242,.75)',   # índigo
    ]
    compras_mensuales_json = json.dumps({'labels': [], 'datasets': []}, ensure_ascii=False)
    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_dash_compras_mensuales_grupos(12)")
        ).fetchall()

        c_month_index = OrderedDict()
        c_group_index = OrderedDict()
        c_data_map    = defaultdict(lambda: defaultdict(float))

        for r in rows:
            mk = (int(r[0]), int(r[1]))
            c_month_index[mk] = str(r[2]) if r[2] else ''
            gc = int(r[3]) if r[3] is not None else 0
            c_group_index[gc] = str(r[4]) if r[4] else 'Sin Grupo'
            c_data_map[gc][mk] = _safe_float(r[5])

        c_labels  = list(c_month_index.values())
        c_mk_list = list(c_month_index.keys())

        if c_labels:
            c_datasets = []
            for i, (gc, gname) in enumerate(c_group_index.items()):
                color = _CHART_COLORS_C[i % len(_CHART_COLORS_C)]
                c_datasets.append({
                    'label':           gname,
                    'data':            [c_data_map[gc].get(mk, 0.0) for mk in c_mk_list],
                    'backgroundColor': color,
                    'borderColor':     color.replace('.75', '1').replace('.80', '1'),
                    'borderWidth':     1,
                    'borderRadius':    3,
                })
            compras_mensuales_json = json.dumps(
                {'labels': c_labels, 'datasets': c_datasets}, ensure_ascii=False
            )
        else:
            raise ValueError('sin filas')

    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_compras_mensuales_grupos error: {e}')
        # fallback: totales simples por mes sin desglose
        try:
            rows = db.session.execute(
                text("SELECT * FROM fn_dash_compras_mensuales(12)")
            ).fetchall()
            fb_labels = [str(r[2]) for r in rows if r[2]]
            fb_data   = [_safe_float(r[3]) for r in rows]
            if fb_labels:
                compras_mensuales_json = json.dumps({'labels': fb_labels, 'datasets': [{
                    'label': 'Compras',
                    'data':  fb_data,
                    'backgroundColor': 'rgba(253,126,20,.75)',
                    'borderColor':     'rgba(253,126,20,1)',
                    'borderWidth': 1, 'borderRadius': 3,
                }]}, ensure_ascii=False)
        except Exception as e2:
            db.session.rollback()
            print(f'[dashboard] fn_dash_compras_mensuales fallback error: {e2}')

    # ─── Top Artículos Comprados ─────────────────────────────────────────────
    compras_top_articulos = []
    try:
        rows = db.session.execute(text("SELECT * FROM fn_dash_compras_top_articulos(10)")).fetchall()
        for r in rows:
            compras_top_articulos.append({
                'item_code':      str(r[0]) if r[0] else '',
                'item_name':      str(r[1]) if r[1] else '',
                'total_cantidad': _safe_float(r[2]),
                'total_monto':    _safe_float(r[3]),
                'cant_facturas':  _safe_int(r[4]),
            })
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_compras_top_articulos error: {e}')

    # ─── Top Proveedores ─────────────────────────────────────────────────────
    compras_top_proveedores = []
    try:
        rows = db.session.execute(text("SELECT * FROM fn_dash_compras_top_proveedores(8)")).fetchall()
        for r in rows:
            compras_top_proveedores.append({
                'card_code':        str(r[0]) if r[0] else '',
                'proveedor_nombre': str(r[1]) if r[1] else '',
                'total_monto':      _safe_float(r[2]),
                'cant_docs':        _safe_int(r[3]),
            })
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_compras_top_proveedores error: {e}')

    # ─── KPI Inventario ───────────────────────────────────────────────────────
    inv_kpi = {
        'cant_entradas_mes':  0.0, 'cant_salidas_mes':  0.0,
        'valor_entradas_mes': 0.0, 'valor_salidas_mes': 0.0,
        'items_activos':      0,   'almacenes_activos': 0,
        'stock_valor_total':  0.0, 'movimientos_hoy':   0,
    }
    try:
        row = db.session.execute(text("SELECT * FROM fn_dash_inv_kpi()")).fetchone()
        if row:
            inv_kpi = {
                'cant_entradas_mes':  _safe_float(row[0]),
                'cant_salidas_mes':   _safe_float(row[1]),
                'valor_entradas_mes': _safe_float(row[2]),
                'valor_salidas_mes':  _safe_float(row[3]),
                'items_activos':      _safe_int(row[4]),
                'almacenes_activos':  _safe_int(row[5]),
                'stock_valor_total':  _safe_float(row[6]),
                'movimientos_hoy':    _safe_int(row[7]),
            }
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_inv_kpi error: {e}')

    # ─── Inventario Mensual por Grupo (salidas, 24 meses) ────────────────────
    _CHART_COLORS_I = [
        'rgba(220,53,69,.75)',    # rojo
        'rgba(25,135,84,.75)',    # verde
        'rgba(13,110,253,.75)',   # azul
        'rgba(255,193,7,.80)',    # amarillo
        'rgba(111,66,193,.75)',   # púrpura
        'rgba(253,126,20,.75)',   # naranja
        'rgba(32,201,151,.75)',   # teal
        'rgba(214,51,132,.75)',   # rosa
        'rgba(13,202,240,.75)',   # cyan
        'rgba(102,16,242,.75)',   # índigo
    ]
    inv_mensuales_json = json.dumps({'labels': [], 'datasets': []}, ensure_ascii=False)
    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_dash_inv_mensuales_grupos(24)")
        ).fetchall()

        i_month_index = OrderedDict()
        i_group_index = OrderedDict()
        i_data_map    = defaultdict(lambda: defaultdict(float))

        for r in rows:
            mk = (int(r[0]), int(r[1]))
            i_month_index[mk] = str(r[2]) if r[2] else ''
            gc = int(r[3]) if r[3] is not None else 0
            i_group_index[gc] = str(r[4]) if r[4] else 'Sin Grupo'
            i_data_map[gc][mk] = _safe_float(r[5])

        i_labels  = list(i_month_index.values())
        i_mk_list = list(i_month_index.keys())

        if i_labels:
            i_datasets = []
            for idx, (gc, gname) in enumerate(i_group_index.items()):
                color = _CHART_COLORS_I[idx % len(_CHART_COLORS_I)]
                i_datasets.append({
                    'label':           gname,
                    'data':            [i_data_map[gc].get(mk, 0.0) for mk in i_mk_list],
                    'backgroundColor': color,
                    'borderColor':     color.replace('.75', '1').replace('.80', '1'),
                    'borderWidth':     1,
                    'borderRadius':    3,
                })
            inv_mensuales_json = json.dumps(
                {'labels': i_labels, 'datasets': i_datasets}, ensure_ascii=False
            )
        else:
            raise ValueError('sin filas')

    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_inv_mensuales_grupos error: {e}')
        # fallback: entradas vs salidas sin desglose
        try:
            rows = db.session.execute(
                text("SELECT * FROM fn_dash_inv_mensuales(24)")
            ).fetchall()
            if rows:
                inv_labels = [str(r[2]) for r in rows]
                inv_mensuales_json = json.dumps({'labels': inv_labels, 'datasets': [
                    {'label': 'Entradas', 'data': [_safe_float(r[3]) for r in rows],
                     'backgroundColor': 'rgba(25,135,84,.75)', 'borderColor': 'rgba(25,135,84,1)',
                     'borderWidth': 1, 'borderRadius': 3},
                    {'label': 'Salidas',  'data': [_safe_float(r[4]) for r in rows],
                     'backgroundColor': 'rgba(220,53,69,.75)', 'borderColor': 'rgba(220,53,69,1)',
                     'borderWidth': 1, 'borderRadius': 3},
                ]}, ensure_ascii=False)
        except Exception as e2:
            db.session.rollback()
            print(f'[dashboard] fn_dash_inv_mensuales fallback error: {e2}')

    # ─── Top Artículos por Rotación ───────────────────────────────────────────
    inv_top_rotacion = []
    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_dash_inv_top_rotacion(10)")
        ).fetchall()
        for r in rows:
            inv_top_rotacion.append({
                'item_code':      str(r[0]) if r[0] else '',
                'item_name':      str(r[1]) if r[1] else '',
                'group_name':     str(r[2]) if r[2] else '',
                'total_salidas':  _safe_float(r[3]),
                'total_entradas': _safe_float(r[4]),
                'stock_actual':   _safe_float(r[5]),
                'valor_stock':    _safe_float(r[6]),
            })
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_inv_top_rotacion error: {e}')

    # ─── Stock por Almacén ────────────────────────────────────────────────────
    inv_stock_almacen = []
    try:
        rows = db.session.execute(
            text("SELECT * FROM fn_dash_inv_stock_almacen()")
        ).fetchall()
        for r in rows:
            inv_stock_almacen.append({
                'almacen':        str(r[0]) if r[0] else '',
                'whs_name':       str(r[1]) if r[1] else '',
                'cant_items':     _safe_int(r[2]),
                'stock_positivo': _safe_int(r[3]),
                'stock_negativo': _safe_int(r[4]),
                'valor_total':    _safe_float(r[5]),
            })
    except Exception as e:
        db.session.rollback()
        print(f'[dashboard] fn_dash_inv_stock_almacen error: {e}')

    return render_template(
        'main/dashboard.html',
        title='Dashboard',
        # ventas
        ventas_kpi=ventas_kpi,
        ventas_mensuales_json=ventas_mensuales_json,
        ventas_top_articulos=ventas_top_articulos,
        ventas_top_clientes=ventas_top_clientes,
        # compras
        compras_kpi=compras_kpi,
        compras_mensuales_json=compras_mensuales_json,
        compras_top_articulos=compras_top_articulos,
        compras_top_proveedores=compras_top_proveedores,
        # inventario
        inv_kpi=inv_kpi,
        inv_mensuales_json=inv_mensuales_json,
        inv_top_rotacion=inv_top_rotacion,
        inv_stock_almacen=inv_stock_almacen,
    )
