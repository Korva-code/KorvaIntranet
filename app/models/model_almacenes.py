from app import db


class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    __table_args__ = {'extend_existing': True}

    whs_code            = db.Column(db.String(2), primary_key=True)
    whs_name            = db.Column(db.Text)
    street              = db.Column(db.String(100))
    is_nettable         = db.Column(db.String(1))
    is_drop_ship        = db.Column(db.String(1))
    allow_bin_locations = db.Column(db.String(1))

    @property
    def code(self) -> str:
        return (self.whs_code or '').strip()

    @property
    def name(self) -> str:
        return (self.whs_name or '').strip()

    def __repr__(self) -> str:
        return f'<Warehouse {self.whs_code} {self.whs_name}>'
