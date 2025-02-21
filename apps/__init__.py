
import os
from flask import Flask
from importlib import import_module
from flask_caching import Cache

## local imports
from apps.authentication.models import Department, Permission
from apps.extensions import db, login_manager, cache, compress, cors, mail, init_scheduler, init_login_manager

cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 60*60  # 1 hour cache timeout
})

def register_extensions(app):
    db.init_app(app)
    init_login_manager(app)
    cache.init_app(app)
    mail.init_app(app)
    init_scheduler(app)
    compress.init_app(app)
    cors.init_app(app)
    
def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def configure_database(app):

    @app.before_first_request
    def initialize_database():
        try:
            db.create_all()
        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )

            # fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')

            print('> Fallback to SQLite ')
            db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

def init_default_data(app):
    with app.app_context():
        try:
            # Check if data already exists
            if Department.query.first() is None:
                # Add departments HERE OVER TIME
                departments = [
                    Department(name='ICT', description='Information and Communications Technology'),
                    Department(name='HR', description='Human Resources'),
                    Department(name='Risk', description='Risk')
                ]
                for dept in departments:
                    db.session.add(dept)
                
                # Add permissions HERE OVER TIME
                permissions = [
                    Permission(name='view_ict_dashboard', description='Can view ICT dashboard'),
                    Permission(name='view_bitdefender', description='Can view Bitdefender section'),
                    Permission(name='view_ict_assets', description='Can view ICT assets'),
                    Permission(name='view_ict_google', description='Can view Google Analytics'),
                    Permission(name='view_ict_freshdesk', description='Can view ICT Freshdesk'),
                    Permission(name='view_ict_license', description='Can view ICT License Hub'),
                    Permission(name='view_hr_dashboard', description='Can view HR dashboard'),
                    Permission(name='view_hr_risk', description='Can view RISK dashboard'),
                    Permission(name='admin', description='Administrator privileges')
                ]
                for perm in permissions:
                    db.session.add(perm)
                
                db.session.commit()
                print("Successfully initialized default departments and permissions")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing default data: {e}")


def create_app(config):
    app = Flask(__name__)
    
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    app.config['MAIL_DEFAULT_SENDER'] = ['tiffany.tirop@africanguaranteefund.com','intern.it@africanguaranteefund.com','job.chumo@africanguaranteefund.com','stephen.kibuci@africanguaranteefund.com']
    app.config.from_object(config)
    # app.config('CACHE_TYPE') = 'SimpleCache'  # Use 'RedisCache' for production
    # app.config('CACHE_DEFAULT_TIMEOUT') = 300  # Cache timeout in seconds (adjust as needed)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    
    with app.app_context():
        init_default_data(app)
        
    return app


