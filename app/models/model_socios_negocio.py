from app import db


class BusinessPartner(db.Model):
    __tablename__ = 'business_partners'
    __table_args__ = {'extend_existing': True}

    card_code      = db.Column(db.String(50),  primary_key=True)
    card_name      = db.Column(db.String(255))
    card_type      = db.Column(db.String(20))
    group_code     = db.Column(db.String(10))
    federal_tax_id = db.Column(db.String(20))
    currency       = db.Column(db.String(3))
    u_bpp_bptd     = db.Column(db.String(10))
    u_bpp_bpno     = db.Column(db.String(255))
    u_bpp_bpap     = db.Column(db.String(50))
    u_bpp_bptp     = db.Column(db.String(10))
    u_validc       = db.Column(db.String(1))
    u_vs_afprcp    = db.Column(db.String(1))
    u_cl_estmig    = db.Column(db.String(1))
    u_cl_resmig    = db.Column(db.Text)
    u_cl_fecmig    = db.Column(db.Date)
    email          = db.Column(db.Text)
    phone          = db.Column(db.Text)
    IsCredit              = db.Column('IsCredit',  db.Integer)
    Creditday             = db.Column('Creditday', db.Integer)
    transp_num_mtc        = db.Column(db.Text)
    transp_num_autorizacion = db.Column(db.Text)
    transp_cod_entidad    = db.Column(db.Text)

    TIPO_LABELS = {
        'cCustomer': 'Cliente',
        'cSupplier': 'Proveedor',
        'cLead':     'Prospecto',
    }

    @property
    def tipo_label(self) -> str:
        return self.TIPO_LABELS.get(self.card_type or '', self.card_type or '—')

    def _yn(self, v) -> str:
        return 'Y' if (v or '').strip().upper() == 'Y' else 'N'

    def as_dict(self) -> dict:
        def dt(v): return v.isoformat() if v else ''
        return {
            'card_code':      self.card_code or '',
            'card_name':      self.card_name or '',
            'card_type':      self.card_type or '',
            'group_code':     self.group_code or '',
            'federal_tax_id': self.federal_tax_id or '',
            'currency':       self.currency or '',
            'u_bpp_bptd':     self.u_bpp_bptd or '',
            'u_bpp_bpno':     self.u_bpp_bpno or '',
            'u_bpp_bpap':     self.u_bpp_bpap or '',
            'u_bpp_bptp':     self.u_bpp_bptp or '',
            'u_validc':       self._yn(self.u_validc),
            'u_vs_afprcp':    self._yn(self.u_vs_afprcp),
            'u_cl_estmig':    (self.u_cl_estmig or '').strip(),
            'u_cl_resmig':    self.u_cl_resmig or '',
            'u_cl_fecmig':    dt(self.u_cl_fecmig),
            'email':          self.email or '',
            'phone':          self.phone or '',
            'IsCredit':               self.IsCredit,
            'Creditday':              self.Creditday,
            'transp_num_mtc':         self.transp_num_mtc or '',
            'transp_num_autorizacion':self.transp_num_autorizacion or '',
            'transp_cod_entidad':     self.transp_cod_entidad or '',
        }

    def __repr__(self) -> str:
        return f'<BusinessPartner {self.card_code}>'
