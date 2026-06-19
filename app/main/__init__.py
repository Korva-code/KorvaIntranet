from flask import Blueprint
from flask_login import current_user

main = Blueprint('main', __name__)

from app.main import router_dashboard        # noqa: E402, F401
from app.main import router_ventas_facturas  # noqa: E402, F401
from app.main import router_compras_facturas # noqa: E402, F401
from app.main import router_articulos        # noqa: E402, F401
from app.main import router_grupos_articulos # noqa: E402, F401
from app.main import router_socios_negocio   # noqa: E402, F401
from app.main import router_usuarios         # noqa: E402, F401
from app.main import router_finanzas         # noqa: E402, F401
from app.main import router_bancos                      # noqa: E402, F401
from app.main import router_abonos                      # noqa: E402, F401
from app.main import router_invoice_cancelaciones       # noqa: E402, F401
from app.main import router_compras_cancelaciones       # noqa: E402, F401
from app.main import router_almacen_kardex              # noqa: E402, F401
from app.main import router_almacen_stock               # noqa: E402, F401
from app.main import router_maestras_tipos_compra       # noqa: E402, F401
from app.main import router_maestras_tipos_cambio       # noqa: E402, F401
from app.main import router_bancos_estado_cuenta        # noqa: E402, F401
from app.main import router_config_accesos              # noqa: E402, F401
from app.main import router_ordenes_compra              # noqa: E402, F401
from app.main import router_cotizaciones                # noqa: E402, F401
from app.main import router_finanzas_gastos             # noqa: E402, F401
from app.main import router_api_uploads                 # noqa: E402, F401
from app.main import router_sunat                       # noqa: E402, F401
from app.main import router_ventas_parte_diario         # noqa: E402, F401
from app.main import router_ventas_nc                   # noqa: E402, F401
from app.main import router_sunat_nota_credito          # noqa: E402, F401
from app.main import router_ventas_lista_precios        # noqa: E402, F401
from app.main import router_impuestos                   # noqa: E402, F401


@main.context_processor
def inject_user_menu():
    if not current_user.is_authenticated:
        return {'user_menu': []}
    from app.main.router_config_accesos import get_user_menu
    return {'user_menu': get_user_menu(current_user.id_perfil)}


@main.context_processor
def inject_tipo_cambio():
    """Inyecta tc_ultimo en todos los templates: {tc_compra, tc_venta, fecha}."""
    if not current_user.is_authenticated:
        return {'tc_ultimo': None}
    from sqlalchemy import text
    from app import db
    try:
        row = db.session.execute(text("""
            SELECT tc_compra, tc_venta, anio, mes, dia
            FROM   tipos_cambio
            ORDER  BY anio DESC, mes DESC, dia DESC
            LIMIT  1
        """)).fetchone()
        if row and row[0] is not None:
            return {'tc_ultimo': {
                'tc_compra': float(row[0]),
                'tc_venta':  float(row[1]),
                'fecha':     f"{int(row[4]):02d}/{int(row[3]):02d}/{int(row[2])}",
            }}
    except Exception:
        pass
    return {'tc_ultimo': None}
