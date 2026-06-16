from app import db


class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    __table_args__ = {'extend_existing': True}

    id_menu   = db.Column(db.Integer, primary_key=True)
    id_parent = db.Column(db.Integer, db.ForeignKey('menu_items.id_menu'))
    label     = db.Column(db.Text, nullable=False)
    endpoint  = db.Column(db.Text)
    icon      = db.Column(db.Text, default='bi-circle')
    orden     = db.Column(db.Integer, default=0)
    id_estado = db.Column(db.Integer, default=1)


class PerfilMenu(db.Model):
    __tablename__ = 'perfil_menu'
    __table_args__ = {'extend_existing': True}

    id        = db.Column(db.Integer, primary_key=True)
    id_perfil = db.Column(db.Integer, nullable=False)
    id_menu   = db.Column(db.Integer, db.ForeignKey('menu_items.id_menu'), nullable=False)
