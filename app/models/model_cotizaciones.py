from app import db


class InvoiceCotizacion(db.Model):
    __tablename__  = 'invoice_cotizaciones'
    __table_args__ = {'extend_existing': True}

    cot_id         = db.Column(db.Integer,      primary_key=True)
    card_code      = db.Column(db.Text,          nullable=False)
    doc_date       = db.Column(db.Date)
    doc_due_date   = db.Column(db.Date)
    doc_currency   = db.Column(db.Text,          default='SOL')
    tipo_cambio    = db.Column(db.Numeric(12, 6), default=1)
    doc_total      = db.Column(db.Numeric(18, 4), default=0)
    doc_subtotal   = db.Column(db.Numeric(18, 4), default=0)
    doc_igv        = db.Column(db.Numeric(18, 4), default=0)
    invoice_wh     = db.Column(db.Text)
    num_at_card    = db.Column(db.Text)
    comments       = db.Column(db.Text)
    journal_memo   = db.Column(db.Text)
    user_code      = db.Column(db.Text)
    id_estado      = db.Column(db.Integer,       default=1)
    fecha_registro = db.Column(db.DateTime,      server_default=db.func.now())

    items = db.relationship(
        'InvoiceItemCotizacion',
        backref='cotizacion',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<InvoiceCotizacion {self.cot_id}>'


class InvoiceItemCotizacion(db.Model):
    __tablename__  = 'invoice_item_cotizaciones'
    __table_args__ = {'extend_existing': True}

    item_cot_id     = db.Column(db.Integer,       primary_key=True)
    cot_id          = db.Column(db.Integer,       db.ForeignKey('invoice_cotizaciones.cot_id'), nullable=False)
    item_code       = db.Column(db.Text)
    item_name       = db.Column(db.Text)
    quantity        = db.Column(db.Numeric(18, 4), default=0)
    price_after_vat = db.Column(db.Numeric(18, 4), default=0)
    tax_code        = db.Column(db.Text,           default='I18')
    warehouse_code  = db.Column(db.Text)

    def __repr__(self):
        return f'<InvoiceItemCotizacion {self.item_cot_id}>'
