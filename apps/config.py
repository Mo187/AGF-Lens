# -*- encoding: utf-8 -*-
import os
import random
import string

class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Set up the App SECRET_KEY
    SECRET_KEY = os.getenv('SECRET_KEY', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice(string.ascii_lowercase) for i in range(32))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database settings - MySQL only
    DB_ENGINE   = os.getenv('DB_ENGINE', 'mysql+pymysql')
    DB_USERNAME = os.getenv('DB_USERNAME', None)
    DB_PASS     = os.getenv('DB_PASS', None)
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_PORT     = os.getenv('DB_PORT', '3306')
    DB_NAME     = os.getenv('DB_NAME', None)

    # Set MySQL URI
    SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
        DB_ENGINE,
        DB_USERNAME,
        DB_PASS,
        DB_HOST,
        DB_PORT,
        DB_NAME
    )

    # Mail settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True') == 'True'
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', None)
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', None)

    # Cache settings
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 60 * 60  # 1 hour

    # Add these to your Config class
    SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,  # Recycle connections after 5 minutes
    'pool_timeout': 10,   # Timeout after 10 seconds
    'pool_size': 20,      # Increase connection pool size
    'max_overflow': 30,   # Allow more concurrent connections
    # These timeouts will make connection errors appear faster
    'connect_args': {
        'connect_timeout': 5  # MySQL connection timeout in seconds
    }
}

class ProductionConfig(Config):
    DEBUG = False
    
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

class DebugConfig(Config):
    DEBUG = True

# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}