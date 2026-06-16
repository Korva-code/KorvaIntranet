from app import db


class BancoEstadoCuenta(db.Model):
    __tablename__ = 'bancos_estado_cuenta'
    __table_args__ = {'extend_existing': True}

    id             = db.Column(db.Integer, primary_key=True)
    id_cancelacion = db.Column(db.Integer)
    id_invoice     = db.Column(db.Integer)
    fecha_pago     = db.Column(db.Date)
    moneda_pago    = db.Column(db.Text, default='SOL')
    referencia     = db.Column(db.Text)
    concepto       = db.Column(db.Text)
    monto_aplicado = db.Column(db.Numeric(18, 2))
    card_code      = db.Column(db.Text)
    nro_documento  = db.Column(db.Text)
    id_banco       = db.Column(db.Integer)
    nombre_banco   = db.Column(db.Text)
    user_code      = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now())
