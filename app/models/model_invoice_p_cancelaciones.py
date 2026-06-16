from app import db


class InvoicePCancelacion(db.Model):
    __tablename__  = 'invoice_p_cancelaciones'
    __table_args__ = {'extend_existing': True}

    id_p_cancelacion = db.Column(db.Integer, primary_key=True)
    invoice_p_id     = db.Column(db.Integer, nullable=False)
    card_code        = db.Column(db.Text)
    id_banco         = db.Column(db.Integer)
    fecha_pago       = db.Column(db.Date)
    moneda_pago      = db.Column(db.Text, default='SOL')
    tipo_cambio      = db.Column(db.Numeric(18, 6), default=1)
    importe          = db.Column(db.Numeric(18, 2))
    referencia       = db.Column(db.Text)
    concepto         = db.Column(db.Text)
    monto_factura    = db.Column(db.Numeric(18, 2))
    moneda_factura   = db.Column(db.Text)
    monto_aplicado   = db.Column(db.Numeric(18, 2))
    user_code        = db.Column(db.Text)
    fecha_registro   = db.Column(db.DateTime, server_default=db.func.now())
    id_estado        = db.Column(db.Integer, default=1)
