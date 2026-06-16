from app import db


class Banco(db.Model):
    __tablename__ = 'bancos'
    __table_args__ = {'extend_existing': True}

    id_banco   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cod_banco  = db.Column(db.String(20))
    nombre     = db.Column(db.Text)
    nro_cuenta = db.Column(db.String(50))
    cci        = db.Column(db.String(50))
    moneda     = db.Column(db.String(10), default='SOL')
    id_estado  = db.Column(db.Integer, default=1)

    def as_dict(self):
        return {
            'id_banco':   self.id_banco,
            'cod_banco':  self.cod_banco  or '',
            'nombre':     self.nombre     or '',
            'nro_cuenta': self.nro_cuenta or '',
            'cci':        self.cci        or '',
            'moneda':     self.moneda     or 'SOL',
            'id_estado':  self.id_estado if self.id_estado is not None else 1,
        }

    def __repr__(self):
        return f'<Banco {self.id_banco} {self.nombre}>'
