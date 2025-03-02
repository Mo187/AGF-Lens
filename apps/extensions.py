import os
import pytz
import tempfile
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_compress import Compress
from flask_cors import CORS
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
import atexit
 
from datetime import datetime

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
    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    login_manager.login_view = 'authentication_blueprint.login'
    login_manager.login_message = None
    
    # Add these settings for better login persistence
    app.config.setdefault('REMEMBER_COOKIE_DURATION', 86400)  # 24 hours
    app.config.setdefault('REMEMBER_COOKIE_SECURE', False)  # Set to True with HTTPS
    app.config.setdefault('REMEMBER_COOKIE_HTTPONLY', True)
    app.config.setdefault('REMEMBER_COOKIE_REFRESH_EACH_REQUEST', True)


# def init_scheduler(app):
#     try:
#         def scheduled_license_check():
#             with app.app_context():
#                 from api.licenses import check_license_expirations
#                 check_license_expirations()
        
#         if not scheduler.running:
#             # Use misfire_grace_time to prevent misfires when the server is busy
#             # Use coalesce=True to prevent job queue buildup
#             scheduler.add_job(
#                 scheduled_license_check, 
#                 'interval', 
#                 minutes=1,  # Run hourly in production instead of every minute
#                 max_instances=1,  # Prevent concurrent jobs
#                 misfire_grace_time=3600,  # Allow misfires up to 1 hour
#                 coalesce=True,  # Collapse missed executions
#                 id='license_check'
#             )
            
#             # For production use these cron jobs instead:
#             # scheduler.add_job(
#             #     scheduled_license_check,
#             #     'cron',
#             #     hour=9,
#             #     minute=0,
#             #     max_instances=1,
#             #     misfire_grace_time=3600,
#             #     coalesce=True,
#             #     id='license_check_morning'
#             # )
#             # 
#             # scheduler.add_job(
#             #     scheduled_license_check,
#             #     'cron',
#             #     hour=16,
#             #     minute=0,
#             #     max_instances=1,
#             #     misfire_grace_time=3600,
#             #     coalesce=True,
#             #     id='license_check_afternoon'
#             # )
            
#             scheduler.start()
#             atexit.register(lambda: scheduler.shutdown(wait=False))
#             app.logger.info('Scheduler started successfully')
#     except Exception as e:
#         app.logger.error(f'Failed to start scheduler: {str(e)}')

def init_scheduler(app):
    """Initialize scheduler for license expiry checks"""
    try:
        # Define the job function
        def scheduled_license_check():
            app.logger.info("Scheduled license check starting...")
            
            with app.app_context():
                try:
                    # Import and call the function
                    from api.licenses import check_license_expirations
                    check_license_expirations()
                    app.logger.info("License check completed successfully")
                except ImportError as e:
                    app.logger.error(f"Import error: Could not import check_license_expirations: {e}")
                except Exception as e:
                    app.logger.error(f"Error running license check: {e}")
            
            app.logger.info("Scheduled license check completed")
        
        # Register and start the job
        if not scheduler.running:
            scheduler.add_job(
                scheduled_license_check, 
                'interval', 
                minutes=1,  # For testing; use higher value in production
                id='license_check'
            )
            
            scheduler.start()
            atexit.register(lambda: scheduler.shutdown(wait=False))
            app.logger.info('Scheduler started successfully with 1-minute interval')
            
    except Exception as e:
        app.logger.error(f'Failed to start scheduler: {e}')

# def init_scheduler(app):
#     try:
#         def scheduled_license_check():
#             with app.app_context():
#                 from api.licenses import check_license_expirations
#                 check_license_expirations()
        
#         if not scheduler.running:
#             scheduler.add_job(
#                 scheduled_license_check, 
#                 'interval', 
#                 minutes=1, 
#                 max_instances=1,
#                 id='license_check'
#             )
#             scheduler.start()
#             atexit.register(lambda: scheduler.shutdown(wait=False))
#             app.logger.info('Scheduler started successfully')
#     except Exception as e:
#         app.logger.error(f'Failed to start scheduler: {str(e)}')
        
        
# Use this below for production to check twice a day. The one above is for testing at 1 minute intervals.  
# def init_scheduler(app):
#     try:
#         def scheduled_license_check():
#             with app.app_context():
#                 from api.licenses import check_license_expirations
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