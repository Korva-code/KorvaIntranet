from app import db


class ItemGroup(db.Model):
    __tablename__ = 'items_group'
    __table_args__ = {'extend_existing': True}

    item_group_code = db.Column(db.Integer, primary_key=True)
    item_group_name = db.Column(db.String(50))
    CostingCode     = db.Column(db.String(10))

    @property
    def nombre(self) -> str:
        return (self.item_group_name or '').strip()

    def as_dict(self) -> dict:
        return {
            'item_group_code': self.item_group_code,
            'item_group_name': self.item_group_name or '',
            'CostingCode':     (self.CostingCode or '').strip(),
        }

    def __repr__(self) -> str:
        return f'<ItemGroup {self.item_group_code} {self.item_group_name}>'


class ItemBarcode(db.Model):
    __tablename__ = 'items_barcode'
    __table_args__ = {'extend_existing': True}

    item_code    = db.Column(db.Text, primary_key=True)
    item_barcode = db.Column(db.Text)

    def __repr__(self) -> str:
        return f'<ItemBarcode {self.item_code} {self.item_barcode}>'


class Item(db.Model):
    __tablename__ = 'items'
    __table_args__ = {'extend_existing': True}

    item_code     = db.Column(db.Text,           primary_key=True)
    item_name     = db.Column(db.Text)
    frgn_name     = db.Column(db.Text)
    itms_grp_cod  = db.Column(db.Integer)
    itms_grp_nam  = db.Column(db.String(100))
    invnt_item    = db.Column(db.String(1))
    sell_item     = db.Column(db.String(1))
    prchse_item   = db.Column(db.String(1))
    on_hand       = db.Column(db.Numeric(18, 6))
    is_commited   = db.Column(db.Numeric(18, 6))
    on_order      = db.Column(db.Numeric(18, 6))
    avg_price     = db.Column(db.Numeric(18, 6))
    sal_unit_msr  = db.Column(db.String(50))
    buy_unit_msr  = db.Column(db.String(50))
    valid_for     = db.Column(db.String(1))
    frozen_for    = db.Column(db.String(1))
    tax_code_ar   = db.Column(db.String(20))
    tax_code_ap   = db.Column(db.String(20))
    create_date   = db.Column(db.Date)
    update_date   = db.Column(db.Date)
    PriceAfterVAT = db.Column(db.Numeric(18, 4))
    TipoBien      = db.Column(db.Integer)
    ultimo_costo  = db.Column(db.Numeric(18, 4))

    grupo = db.relationship(
        'ItemGroup',
        primaryjoin='Item.itms_grp_cod == foreign(ItemGroup.item_group_code)',
        uselist=False,
        viewonly=True,
        lazy='select',
    )

    barcode_obj = db.relationship(
        'ItemBarcode',
        primaryjoin='Item.item_code == foreign(ItemBarcode.item_code)',
        uselist=False,
        viewonly=True,
        lazy='select',
    )

    @property
    def grupo_nombre(self) -> str:
        if self.grupo:
            return self.grupo.nombre
        return (self.itms_grp_nam or '').strip()

    @property
    def barcode(self) -> str:
        return (self.barcode_obj.item_barcode if self.barcode_obj else '') or ''

    def _yn(self, field) -> str:
        return 'Y' if (field or '').strip().upper() == 'Y' else 'N'

    @property
    def sal_unit(self) -> str:
        return (self.sal_unit_msr or '').strip()

    @property
    def buy_unit(self) -> str:
        return (self.buy_unit_msr or '').strip()

    @property
    def tax_ar(self) -> str:
        return (self.tax_code_ar or '').strip()

    @property
    def tax_ap(self) -> str:
        return (self.tax_code_ap or '').strip()

    def as_dict(self) -> dict:
        def num(v): return float(v) if v is not None else None
        def dt(v):  return v.isoformat() if v else ''
        return {
            'item_code':     self.item_code or '',
            'item_name':     self.item_name or '',
            'frgn_name':     self.frgn_name or '',
            'itms_grp_cod':  self.itms_grp_cod or '',
            'invnt_item':    self._yn(self.invnt_item),
            'sell_item':     self._yn(self.sell_item),
            'prchse_item':   self._yn(self.prchse_item),
            'on_hand':       num(self.on_hand),
            'is_commited':   num(self.is_commited),
            'on_order':      num(self.on_order),
            'avg_price':     num(self.avg_price),
            'sal_unit_msr':  self.sal_unit,
            'buy_unit_msr':  self.buy_unit,
            'valid_for':     self._yn(self.valid_for),
            'frozen_for':    self._yn(self.frozen_for),
            'tax_code_ar':   self.tax_ar,
            'tax_code_ap':   self.tax_ap,
            'create_date':   dt(self.create_date),
            'update_date':   dt(self.update_date),
            'PriceAfterVAT': num(self.PriceAfterVAT),
            'TipoBien':      self.TipoBien,
            'ultimo_costo':  num(self.ultimo_costo),
            'barcode':       self.barcode,
        }

    def __repr__(self) -> str:
        return f'<Item {self.item_code}>'
