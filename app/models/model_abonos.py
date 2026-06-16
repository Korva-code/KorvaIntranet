from app import db


class Abono(db.Model):
    __tablename__ = 'abonos'
    __table_args__ = {'extend_existing': True}

    id_abono   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_banco   = db.Column(db.Integer)
    fecha      = db.Column(db.Date)
    monto      = db.Column(db.Numeric(18, 2))
    moneda     = db.Column(db.String(10), default='SOL')
    referencia = db.Column(db.Text)
    concepto   = db.Column(db.Text)
    card_code  = db.Column(db.String(50))
    id_estado  = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<Abono {self.id_abono}>'
