from flask_login import UserMixin
from app import db, login_manager
from app.models.model_almacenes import Warehouse


class Perfil(db.Model):
    __tablename__ = 'w_perfil'
    __table_args__ = {'extend_existing': True}

    id_perfil   = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(256))
    id_estado   = db.Column(db.Integer)
    tipo_menu   = db.Column(db.Integer)

    @property
    def nombre(self) -> str:
        return (self.descripcion or '').strip()

    def __repr__(self) -> str:
        return f'<Perfil {self.id_perfil} {self.descripcion}>'


class Usuario(UserMixin, db.Model):
    __tablename__ = 'w_usuarios'
    __table_args__ = {'extend_existing': True}

    id_usuario  = db.Column(db.String(20), primary_key=True)
    nombres     = db.Column(db.Text)
    contrasena  = db.Column(db.Text)
    id_perfil   = db.Column(db.Integer)
    id_estado   = db.Column(db.Integer)
    id_empresa  = db.Column(db.Integer)
    ubicacion   = db.Column(db.Text)
    wap         = db.Column(db.Integer)
    id_rol      = db.Column(db.Integer, nullable=False)
    id_almacen  = db.Column(db.Integer)
    id_anexo    = db.Column(db.Integer)
    whs_code    = db.Column(db.String(2))
    correo      = db.Column(db.String(60))
    id_caja     = db.Column(db.Integer)

    perfil_rel = db.relationship(
        'Perfil',
        primaryjoin='Usuario.id_perfil == foreign(Perfil.id_perfil)',
        uselist=False,
        viewonly=True,
        lazy='select',
    )

    warehouse = db.relationship(
        'Warehouse',
        primaryjoin='func.trim(foreign(Usuario.whs_code)) == func.trim(Warehouse.whs_code)',
        uselist=False,
        viewonly=True,
        lazy='select',
    )

    def get_id(self) -> str:
        return str(self.id_usuario)

    def check_password(self, password: str) -> bool:
        return (self.contrasena or '') == password

    @property
    def is_active(self) -> bool:
        return self.id_estado == 1

    @property
    def username(self) -> str:
        return self.id_usuario

    @property
    def full_name(self) -> str:
        return (self.nombres or '').strip().title()

    @property
    def email(self) -> str:
        return (self.correo or '').strip()

    @property
    def department(self) -> str:
        return (self.ubicacion or '').strip()

    @property
    def perfil_nombre(self) -> str:
        if self.perfil_rel:
            return self.perfil_rel.nombre
        return f'Perfil {self.id_perfil}' if self.id_perfil else '—'

    @property
    def role(self) -> str:
        return self.perfil_nombre

    @property
    def initials(self) -> str:
        parts = (self.nombres or self.id_usuario).split()
        return ''.join(p[0].upper() for p in parts[:2]) or '?'

    @property
    def is_admin(self) -> bool:
        return self.id_perfil == 1 or self.id_rol == 1

    @property
    def whs_name(self) -> str:
        if self.warehouse:
            return self.warehouse.name
        if self.whs_code:
            w = Warehouse.query.filter(
                db.func.trim(Warehouse.whs_code) == self.whs_code.strip()
            ).first()
            return w.name if w else self.whs_code.strip()
        return ''

    def __repr__(self) -> str:
        return f'<Usuario {self.id_usuario}>'


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(Usuario, str(user_id))
