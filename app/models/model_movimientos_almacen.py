from app import db


class MovimientoAlmacen(db.Model):
    __tablename__ = 'movimientos_almacen'
    __table_args__ = {'extend_existing': True}

    id              = db.Column(db.Integer, primary_key=True)
    invoice_id      = db.Column(db.Integer)
    card_code       = db.Column(db.Text)
    invoice_type    = db.Column(db.Text)
    id_tipo         = db.Column(db.Integer)
    doc_date        = db.Column(db.Date)
    item_code       = db.Column(db.Text)
    item_name       = db.Column(db.Text)
    quantity        = db.Column(db.Numeric(18, 4))
    avg_price       = db.Column(db.Numeric(18, 4))
    subtotal        = db.Column(db.Numeric(18, 2))
    almacen         = db.Column(db.Text)
    tipo_movimiento = db.Column(db.Text, default='SAL')
    origen          = db.Column(db.Text)
    user_code       = db.Column(db.Text)
    fecha_registro  = db.Column(db.DateTime, server_default=db.func.now())
