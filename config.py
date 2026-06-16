import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///intranet.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = os.getenv('APP_NAME', 'Intranet')
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Mi Empresa')
    COMPANY_LOGO = os.getenv('COMPANY_LOGO', 'img/logo.png')
    WTF_CSRF_ENABLED = True


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
