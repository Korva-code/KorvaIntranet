from app import db


class TipoGasto(db.Model):
    __tablename__ = 'tipos_gasto'
    __table_args__ = {'extend_existing': True}

    id_tipo_gasto = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.Text, nullable=False)
    id_estado     = db.Column(db.Integer, default=1)

    def as_dict(self):
        return {
            'id_tipo_gasto': self.id_tipo_gasto,
            'nombre':        self.nombre or '',
            'id_estado':     self.id_estado if self.id_estado is not None else 1,
        }


class Gasto(db.Model):
    __tablename__ = 'gastos'
    __table_args__ = {'extend_existing': True}

    gasto_id       = db.Column(db.Integer, primary_key=True)
    id_tipo_gasto  = db.Column(db.Integer, db.ForeignKey('tipos_gasto.id_tipo_gasto'))
    card_code      = db.Column(db.Text)
    nro_documento  = db.Column(db.Text)
    doc_date       = db.Column(db.Date)
    doc_due_date   = db.Column(db.Date)
    doc_currency   = db.Column(db.Text, default='SOL')
    tipo_cambio    = db.Column(db.Numeric(12, 6), default=1)
    monto          = db.Column(db.Numeric(18, 4), default=0)
    id_banco       = db.Column(db.Integer, db.ForeignKey('bancos.id_banco'))
    referencia     = db.Column(db.Text)
    concepto       = db.Column(db.Text)
    journal_memo   = db.Column(db.Text)
    user_code      = db.Column(db.Text)
    id_estado      = db.Column(db.Integer, default=1)
    fecha_registro = db.Column(db.DateTime)

    def as_dict(self):
        return {
            'gasto_id':      self.gasto_id,
            'id_tipo_gasto': self.id_tipo_gasto,
            'card_code':     self.card_code    or '',
            'nro_documento': self.nro_documento or '',
            'doc_date':      self.doc_date.isoformat()     if self.doc_date     else '',
            'doc_due_date':  self.doc_due_date.isoformat() if self.doc_due_date else '',
            'doc_currency':  self.doc_currency or 'SOL',
            'tipo_cambio':   float(self.tipo_cambio)  if self.tipo_cambio  is not None else 1.0,
            'monto':         float(self.monto)        if self.monto        is not None else 0.0,
            'id_banco':      self.id_banco,
            'referencia':    self.referencia   or '',
            'concepto':      self.concepto     or '',
            'journal_memo':  self.journal_memo or '',
            'user_code':     self.user_code    or '',
            'id_estado':     self.id_estado if self.id_estado is not None else 1,
        }
