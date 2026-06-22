from app import db


class Invoice(db.Model):
    __tablename__ = 'invoice'
    __table_args__ = {'extend_existing': True}

    invoice_id    = db.Column(db.Integer, primary_key=True)
    card_code     = db.Column(db.Text)
    doc_date      = db.Column(db.Date)
    tax_date      = db.Column(db.Date)
    doc_due_date  = db.Column(db.Date)
    doc_total     = db.Column(db.Numeric(18, 4))
    doc_currency  = db.Column(db.Text)
    comments      = db.Column(db.Text)
    num_at_card   = db.Column(db.Text)
    journal_memo  = db.Column(db.Text)
    invoice_type  = db.Column(db.Text)
    invoice_serie = db.Column(db.Text)
    invoice_wh    = db.Column(db.Text)
    invoice_pos   = db.Column(db.Integer)
    user_code       = db.Column(db.Text)
    sunat_estado    = db.Column(db.Text)
    doc_total_aply       = db.Column(db.Numeric(18, 2), default=0)
    doc_status           = db.Column(db.Integer, default=1)
    nota_credito_serie   = db.Column(db.Text)
    nota_credito_numero  = db.Column(db.Integer)
    nota_credito_total   = db.Column(db.Numeric(18, 4))

    bp = db.relationship(
        'BusinessPartner',
        primaryjoin='Invoice.card_code == foreign(BusinessPartner.card_code)',
        uselist=False,
        viewonly=True,
    )

    @property
    def bp_name(self) -> str:
        return self.bp.card_name if self.bp else (self.card_code or '')

    def as_dict(self) -> dict:
        def dt(v): return v.isoformat() if v else ''
        return {
            'invoice_id':    self.invoice_id,
            'card_code':     self.card_code or '',
            'bp_name':       self.bp_name,
            'doc_date':      dt(self.doc_date),
            'tax_date':      dt(self.tax_date),
            'doc_due_date':  dt(self.doc_due_date),
            'doc_total':     float(self.doc_total) if self.doc_total is not None else None,
            'doc_currency':  self.doc_currency or '',
            'comments':      self.comments or '',
            'num_at_card':   self.num_at_card or '',
            'journal_memo':  self.journal_memo or '',
            'invoice_type':  self.invoice_type or '',
            'invoice_serie': self.invoice_serie or '',
            'invoice_wh':    self.invoice_wh or '',
            'invoice_pos':   self.invoice_pos,
            'user_code':     self.user_code or '',
            'sunat_estado':  self.sunat_estado or '',
        }

    def __repr__(self) -> str:
        return f'<Invoice {self.invoice_id}>'
