import pytz
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_compress import Compress
from flask_cors import CORS
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
import atexit
 
# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()
compress = Compress()
cors = CORS()
mail = Mail()
email_check_lock = Lock()
scheduler = BackgroundScheduler(timezone=pytz.timezone('Africa/Nairobi'))

def init_login_manager(app):
    login_manager.session_protection = "strong"
    login_manager.login_view = 'authentication_blueprint.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

def init_scheduler(app):
    try:
        def scheduled_license_check():
            with app.app_context():
                from functions.licenses import check_license_expirations
                check_license_expirations()
        
        if not scheduler.running:
            scheduler.add_job(
                scheduled_license_check, 
                'interval', 
                minutes=1, 
                max_instances=1,
                id='license_check'
            )
            scheduler.start()
            atexit.register(lambda: scheduler.shutdown(wait=False))
            app.logger.info('Scheduler started successfully')
    except Exception as e:
        app.logger.error(f'Failed to start scheduler: {str(e)}')
        
        
# Use this below for production to check twice a day. The one above is for testing at 1 minute intervals.  
# def init_scheduler(app):
#     try:
#         def scheduled_license_check():
#             with app.app_context():
#                 from functions.licenses import check_license_expirations
#                 check_license_expirations()
        
#         if not scheduler.running:
#             # Run at 9am
#             scheduler.add_job(
#                 scheduled_license_check,
#                 'cron',
#                 hour=9,
#                 minute=0,
#                 id='license_check_morning'
#             )
#             # Run at 4pm
#             scheduler.add_job(
#                 scheduled_license_check,
#                 'cron',
#                 hour=16,
#                 minute=0,
#                 id='license_check_afternoon'
#             )
#             scheduler.start()
#             atexit.register(lambda: scheduler.shutdown(wait=False))
#             app.logger.info('Scheduler started successfully')
#     except Exception as e:
#         app.logger.error(f'Failed to start scheduler: {str(e)}')