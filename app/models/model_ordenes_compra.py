from app import db


class InvoiceOC(db.Model):
    __tablename__ = 'invoice_oc'
    __table_args__ = {'extend_existing': True}

    oc_id          = db.Column(db.Integer, primary_key=True)
    card_code      = db.Column(db.Text, nullable=False)
    doc_date       = db.Column(db.Date)
    doc_due_date   = db.Column(db.Date)
    doc_currency   = db.Column(db.Text, default='SOL')
    tipo_cambio    = db.Column(db.Numeric(12, 6), default=1)
    doc_total      = db.Column(db.Numeric(18, 4), default=0)
    doc_subtotal   = db.Column(db.Numeric(18, 4), default=0)
    doc_igv        = db.Column(db.Numeric(18, 4), default=0)
    invoice_wh     = db.Column(db.Text)
    num_at_card    = db.Column(db.Text)
    comments       = db.Column(db.Text)
    journal_memo   = db.Column(db.Text)
    user_code      = db.Column(db.Text)
    id_estado      = db.Column(db.Integer, default=1)
    fecha_registro = db.Column(db.DateTime)

    items = db.relationship('InvoiceItemOC', backref='orden', lazy=True,
                            cascade='all, delete-orphan')

    def __repr__(self):
        return f'<InvoiceOC {self.oc_id}>'


class InvoiceItemOC(db.Model):
    __tablename__ = 'invoice_item_oc'
    __table_args__ = {'extend_existing': True}

    item_oc_id      = db.Column(db.Integer, primary_key=True)
    oc_id           = db.Column(db.Integer, db.ForeignKey('invoice_oc.oc_id'), nullable=False)
    item_code       = db.Column(db.Text)
    item_name       = db.Column(db.Text)
    quantity        = db.Column(db.Numeric(18, 4), default=0)
    price_after_vat = db.Column(db.Numeric(18, 4), default=0)
    tax_code        = db.Column(db.Text, default='I18')
    warehouse_code  = db.Column(db.Text)

    def __repr__(self):
        return f'<InvoiceItemOC {self.item_oc_id} oc={self.oc_id}>'
