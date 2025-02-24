# -*- encoding: utf-8 -*-"""

import os, random, string
import pymysql

class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Set up the App SECRET_KEY
    SECRET_KEY = os.getenv('SECRET_KEY', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice(string.ascii_lowercase) for i in range(32))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database settings
    DB_ENGINE   = os.getenv('DB_ENGINE', 'mysql+pymysql')
    DB_USERNAME = os.getenv('DB_USERNAME', None)
    DB_PASS     = os.getenv('DB_PASS', None)
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_PORT     = os.getenv('DB_PORT', '3306')
    DB_NAME     = os.getenv('DB_NAME', None)

     # Default to SQLite path
    SQLITE_DB = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
    
    # Try MySQL first, fallback to SQLite
    try:
        if all([DB_ENGINE, DB_USERNAME, DB_PASS, DB_HOST, DB_NAME]):
            SQLALCHEMY_DATABASE_URI = f'{DB_ENGINE}://{DB_USERNAME}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
            # Test the connection
            conn = pymysql.connect(
                host=DB_HOST,
                user=DB_USERNAME,
                password=DB_PASS,
                database=DB_NAME
            )
            conn.close()
        else:
            raise ValueError("Missing MySQL credentials")
    except Exception as e:
        print(f'> MySQL Connection Error: {str(e)}')
        print('> Falling back to SQLite')
        SQLALCHEMY_DATABASE_URI = SQLITE_DB


class ProductionConfig(Config):
    DEBUG = False
    
    # Security settings
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600
    
    # Production database settings
    DB_ENGINE = os.getenv('DB_ENGINE', 'mysql+pymysql')
    
    # Cache settings
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 60 * 60  # 1 hour cache timeout


class DebugConfig(Config):
    DEBUG = True
    
    # Development database settings (can fallback to SQLite more easily)
    USE_SQLITE = os.getenv('USE_SQLITE', 'False') == 'True'
    
    # Development cache settings
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 0  # Disable cache in development


# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}