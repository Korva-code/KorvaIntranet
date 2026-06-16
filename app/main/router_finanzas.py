from flask import render_template
from flask_login import login_required
from app.main import main


@main.route('/ventas/boletas')
@login_required
def ventas_boletas():
    return render_template('main/placeholder.html', title='Boletas de Venta',
                           section='Ventas', page='Boletas',
                           icon='bi-file-earmark-text')


@main.route('/finanzas/presupuesto')
@login_required
def presupuesto():
    return render_template('main/placeholder.html', title='Presupuesto',
                           section='Finanzas', page='Presupuesto',
                           icon='bi-cash-stack')



@main.route('/finanzas/reportes')
@login_required
def reportes_finanzas():
    return render_template('main/placeholder.html', title='Reportes Financieros',
                           section='Finanzas', page='Reportes',
                           icon='bi-bar-chart-line')


@main.route('/configuracion/usuarios')
@login_required
def usuarios():
    return render_template('main/placeholder.html', title='Usuarios',
                           section='Configuración', page='Usuarios',
                           icon='bi-person-gear')


@main.route('/configuracion/sistema')
@login_required
def sistema():
    return render_template('main/placeholder.html', title='Sistema',
                           section='Configuración', page='Sistema',
                           icon='bi-gear')
