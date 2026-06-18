import os
from dotenv import load_dotenv

load_dotenv(override=True)

_SUNAT_BASE = {
    'sandbox':    'https://sandbox.apisunat.pe/api/v3',
    'produccion': 'https://app.apisunat.pe/api/v3',
}


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///intranet.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = os.getenv('APP_NAME', 'Intranet')
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Mi Empresa')
    COMPANY_LOGO = os.getenv('COMPANY_LOGO', 'img/logo.png')
    WTF_CSRF_ENABLED = True

    # ── SUNAT / apisunat.pe ───────────────────────────────────────────────────
    APISUNAT_MODO  = os.getenv('APISUNAT_MODO', 'sandbox')
    APISUNAT_TOKEN = os.getenv('APISUNAT_TOKEN', '')
    _base = _SUNAT_BASE.get(os.getenv('APISUNAT_MODO', 'sandbox'), _SUNAT_BASE['sandbox'])
    APISUNAT_URL      = os.getenv('APISUNAT_URL')      or f'{_base}/documents'
    APISUNAT_VOID_URL = os.getenv('APISUNAT_VOID_URL') or f'{_base}/voided'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_ENABLED = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
