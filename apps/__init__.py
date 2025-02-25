
import os
from flask import Flask
from importlib import import_module
from flask_caching import Cache

from sqlalchemy import inspect

## local imports
from apps.authentication.models import Department, Permission
from apps.extensions import db, login_manager, cache, compress, cors, mail, init_scheduler, init_login_manager
from apps.authentication.models import Users, Permission
from apps.authentication.util import hash_pass

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
            print("> Database tables created successfully")
        except Exception as e:
            print(f"> Database initialization error: {str(e)}")
            print("> App will continue to run but some features may be limited")

    @app.teardown_request
    def shutdown_session(exception=None):
        try:
            db.session.remove()
        except Exception as e:
            print(f"> Session removal error: {str(e)}")


def init_default_data(app):
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            # Check if tables exist using the proper inspection method
            if not inspector.has_table('departments'):
                print("> Tables don't exist. Creating tables...")
                db.create_all()
            
            # Only proceed with data initialization if we can connect
            if Department.query.first() is None:
                try:
                    departments = [
                        Department(name='ICT', description='Information and Communications Technology'),
                        Department(name='HR', description='Human Resources'),
                        Department(name='Risk', description='Risk')
                    ]
                    for dept in departments:
                        db.session.add(dept)
                    
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
                    print("> Successfully initialized default data")
                except Exception as e:
                    print(f"> Error initializing default data: {e}")
                    db.session.rollback()
        except Exception as e:
            print(f"> Database feature check skipped: {e}")
            print("> App will continue to run but with limited database functionality")
            
            

def init_admin_user(app):

    
    with app.app_context():
        try:
            # Check if admin user exists
            admin_email = os.getenv('ADMIN_EMAIL')
            
            if not admin_email:
                print("> ADMIN_EMAIL not set in environment variables. Skipping admin user creation.")
                return
                
            admin_username = os.getenv('ADMIN_USER', 'admin')
            admin_password = os.getenv('ADMIN_PASSW')
            
            if not admin_password:
                print("> ADMIN_PASSWORD not set in environment variables. Skipping admin user creation.")
                return
                
            # Check if admin user already exists
            existing_admin = Users.query.filter_by(email=admin_email).first()
            
            if existing_admin:
                print(f"> Admin user with email {admin_email} already exists.")
                return
                
            # Get admin permission
            admin_permission = Permission.query.filter_by(name='admin').first()
            
            if not admin_permission:
                print("> Admin permission does not exist in the database. Make sure to run init_default_data first.")
                return
                
            # Create admin user
            admin_user = Users(
                username=admin_username,
                email=admin_email,
                password=admin_password,  # The model's __init__ will hash this
                is_active=True
            )
            
            # Add admin permission
            admin_user.permissions.append(admin_permission)
            
            # Save to database
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"> Admin user '{admin_username}' created successfully with email '{admin_email}'")
            
        except Exception as e:
            db.session.rollback()
            print(f"> Error creating admin user: {e}")
            
# def init_default_data(app):
#     with app.app_context():
#         try:
#             # Create tables first
#             db.create_all()
            
#             # Check if data already exists
#             if Department.query.first() is None:
#                 print("> No existing departments found. Creating default data...")
#                 # Add departments
#                 departments = [
#                     Department(name='ICT', description='Information and Communications Technology'),
#                     Department(name='HR', description='Human Resources'),
#                     Department(name='Risk', description='Risk')
#                 ]
#                 for dept in departments:
#                     db.session.add(dept)
                
#                 # Add permissions
#                 permissions = [
#                     Permission(name='view_ict_dashboard', description='Can view ICT dashboard'),
#                     Permission(name='view_bitdefender', description='Can view Bitdefender section'),
#                     Permission(name='view_ict_assets', description='Can view ICT assets'),
#                     Permission(name='view_ict_google', description='Can view Google Analytics'),
#                     Permission(name='view_ict_freshdesk', description='Can view ICT Freshdesk'),
#                     Permission(name='view_ict_license', description='Can view ICT License Hub'),
#                     Permission(name='view_hr_dashboard', description='Can view HR dashboard'),
#                     Permission(name='view_hr_risk', description='Can view RISK dashboard'),
#                     Permission(name='admin', description='Administrator privileges')
#                 ]
#                 for perm in permissions:
#                     db.session.add(perm)
                
#                 try:
#                     db.session.commit()
#                     print("Successfully initialized default departments and permissions")
#                 except Exception as e:
#                     db.session.rollback()
#                     print(f"Error committing default data: {e}")
#             else:
#                 print("> Default data already exists. Skipping initialization.")
                
#         except Exception as e:
#             db.session.rollback()
#             print(f"Error initializing default data: {e}")


def create_app(config):
    app = Flask(__name__)
    
    app.config.from_object(config)

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    app.config['IT_TEAM_EMAILS'] = os.getenv('IT_TEAM_EMAILS')
    app.config['CACHE_TYPE'] = 'SimpleCache'  # Use 'RedisCache' for production
    app.config['CACHE_DEFAULT_TIMEOUT'] = 400  # Cache timeout in seconds (adjust as needed)
    
    register_extensions(app)
    register_blueprints(app)
    
    try:
        configure_database(app)
    except Exception as e:
        print(f"> Database setup error (app will continue): {e}")
    
    # Try to initialize data but don't let failures stop the app
    try:
        with app.app_context():
            init_default_data(app) ## creating default departments and perms
            init_admin_user(app) ## for creating admin automatically
    except Exception as e:
        print(f"> Data initialization error (app will continue): {e}")
            
    return app


