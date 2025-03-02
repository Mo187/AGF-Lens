from flask import current_app
from datetime import datetime, date, timezone
from flask_mail import Message
from apps.authentication.models import License, EmailLog
from sqlalchemy.exc import IntegrityError
from apps import db
import logging
import os
import tempfile

from apps.extensions import email_check_lock, mail

def send_email_reminder(license_obj, interval):
    """
    Send an email reminder for a license at a specific interval.
    
    :param license_obj: License instance
    :param interval: String interval ("90", "60", "30", "7", "0", "post")
    :return: Boolean indicating success or failure
    """
    try:
        # Get license details
        license_name = license_obj.name
        category_name = license_obj.category.name if license_obj.category else "Uncategorized"
        license_type = license_obj.license_type
        assigned_to = license_obj.assigned_to or "Not assigned"
        expiry_date = license_obj.expiry_date.strftime("%Y-%m-%d") if license_obj.expiry_date else "N/A"
        status = license_obj.computed_status
        
        # Generate appropriate subject line
        if interval == "post":
            days_ago = abs((license_obj.expiry_date - date.today()).days)
            if days_ago == 1:
                subject = f"License '{license_name}' expired yesterday"
            else:
                subject = f"License '{license_name}' expired {days_ago} days ago"
        elif interval == "0":
            subject = f"License '{license_name}' expires TODAY"
        else:
            subject = f"License '{license_name}' expires in {interval} days"
        
        # Create message body
        body = f"""
Hello,

This is an automated reminder that the license for "{license_name}" is scheduled to expire.
Details:
- Category: {category_name}
- License Type: {license_type}
- Assigned To: {assigned_to}
- Expiry Date: {expiry_date}
- Status: {status}

Please take the necessary actions.

Regards,
AGF License Management System
    """
        
        # Determine recipients
        recipients = []
        
        # Check if the license has specific notification recipients
        for notification in license_obj.notifications:
            recipients.append(notification.email)
        
        # If no specific recipients, use default IT team emails
        if not recipients and current_app.config.get('IT_TEAM_EMAILS'):
            recipients = current_app.config['IT_TEAM_EMAILS']
            logging.info(f"No specific recipients found for license {license_obj.id}, using default IT team emails")
        
        if not recipients:
            logging.error(f"No recipients found for license {license_obj.id}")
            return False
        
        logging.info(f"Sending reminder for license {license_obj.id} to: {', '.join(recipients)}")
        
        # Create and send message
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True
        
    except Exception as e:
        logging.error(f"Failed to send email for license {license_obj.id}: {str(e)}")
        return False

def check_license_expirations():
    """
    Check for license expirations and send email reminders.
    """
    # Get the flask app logger for consistent logging
    logger = current_app.logger
    logger.info("Running scheduled license expiry check...")
    
    try:
        from apps.authentication.models import License, EmailLog
        
        # Get the current date for comparison
        current_date = date.today()
        
        # Get all licenses
        licenses = License.query.all()
        license_count = len(licenses)
        logger.info(f"Found {license_count} licenses to check")
        
        # Loop through each license
        for lic in licenses:
            try:
                # Skip perpetual licenses
                if lic.is_perpetual:
                    continue
                
                # Skip licenses without expiry dates
                if not lic.expiry_date:
                    continue
                
                # Calculate days until expiry
                expiry_diff = (lic.expiry_date - current_date).days
                logger.info(f"License {lic.id} has an expiry diff of {expiry_diff} days.")
                
                # Check for EXACT interval matches
                interval = None
                
                if expiry_diff < 0:
                    # Already expired
                    logger.info(f"License {lic.id} qualifies for a post-expiry reminder.")
                    interval = "post"
                elif expiry_diff == 0:
                    # Expires today
                    logger.info(f"License {lic.id} expires today.")
                    interval = "0"
                elif expiry_diff == 7:
                    # Exactly 7 days
                    logger.info(f"License {lic.id} qualifies for 7-day reminder.")
                    interval = "7"
                elif expiry_diff == 30:
                    # Exactly 30 days
                    logger.info(f"License {lic.id} qualifies for 30-day reminder.")
                    interval = "30"
                elif expiry_diff == 60:
                    # Exactly 60 days
                    logger.info(f"License {lic.id} qualifies for 60-day reminder.")
                    interval = "60"
                elif expiry_diff == 90:
                    # Exactly 90 days
                    logger.info(f"License {lic.id} qualifies for 90-day reminder.")
                    interval = "90"
                else:
                    # Not at a notification interval
                    continue
                
                # Check if we've already sent a notification for this interval
                existing_log = EmailLog.query.filter_by(
                    license_id=lic.id,
                    interval=interval
                ).first()
                
                if existing_log:
                    logger.info(f"Email log already exists for license {lic.id} interval {interval}. Skipping duplicate.")
                    continue
                
                # If we get here, we need to send a notification
                logger.info(f"Preparing to send reminder for license {lic.id} ({interval} interval)")
                
                # Send the email
                if send_email_reminder(lic, interval):
                    # Email sent successfully, log it
                    try:
                        log_entry = EmailLog(
                            license_id=lic.id,
                            interval=interval,
                            sent_at=datetime.now(timezone.utc)
                        )
                        db.session.add(log_entry)
                        db.session.commit()
                        logger.info(f"Sent reminder for license {lic.id} ({interval} interval).")
                    except IntegrityError:
                        # Another process might have logged it
                        db.session.rollback()
                        logger.info(f"Email log already exists for license {lic.id} interval {interval}. Skipping duplicate.")
                    except Exception as log_error:
                        db.session.rollback()
                        logger.error(f"Error creating email log for license {lic.id}: {str(log_error)}")
            
            except Exception as e:
                logger.error(f"Error processing license {lic.id}: {str(e)}")
                continue
        
        logger.info(f"License check completed, processed {license_count} licenses")
        return True
    
    except Exception as e:
        logger.error(f"Error in license expiration check: {str(e)}")
        return False


def send_email_reminder(license_obj, interval):
    """
    Send an email reminder for a license at a specific interval.
    
    :param license_obj: License instance
    :param interval: String interval ("90", "60", "30", "7", "0", "post")
    :return: Boolean indicating success or failure
    """
    logger = current_app.logger
    
    try:
        # Get license details
        license_name = license_obj.name
        category_name = license_obj.category.name if license_obj.category else "Uncategorized"
        license_type = license_obj.license_type
        assigned_to = license_obj.assigned_to or "Not assigned"
        expiry_date = license_obj.expiry_date.strftime("%Y-%m-%d") if license_obj.expiry_date else "N/A"
        status = license_obj.computed_status
        
        # Generate appropriate subject line
        if interval == "post":
            days_ago = abs((license_obj.expiry_date - date.today()).days)
            if days_ago == 1:
                subject = f"License '{license_name}' expired yesterday"
            else:
                subject = f"License '{license_name}' expired {days_ago} days ago"
        elif interval == "0":
            subject = f"License '{license_name}' expires TODAY"
        else:
            subject = f"License '{license_name}' expires in {interval} days"
        
        # Create message body
        body = f"""
Hello,

This is an automated reminder that the license for "{license_name}" is scheduled to expire.
Details:
- Category: {category_name}
- License Type: {license_type}
- Assigned To: {assigned_to}
- Expiry Date: {expiry_date}
- Status: {status}

Please take the necessary actions.

Regards,
AGF License Management System
    """
        
        # Determine recipients
        recipients = []
        
        # Check if the license has specific notification recipients
        for notification in license_obj.notifications:
            recipients.append(notification.email)
        
        # If no specific recipients, use default IT team emails
        if not recipients and current_app.config.get('IT_TEAM_EMAILS'):
            recipients = current_app.config['IT_TEAM_EMAILS']
            logger.info(f"No specific recipients found for license {license_obj.id}, using default IT team emails")
        
        if not recipients:
            logger.error(f"No recipients found for license {license_obj.id}")
            return False
        
        logger.info(f"Sending reminder for license {license_obj.id} to: {', '.join(recipients)}")
        
        # Create and send message
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        logger.info(f"Email sent successfully for license {license_obj.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email for license {license_obj.id}: {str(e)}")
        return False

## PREVIOUS ONE (IT WORKS)
# def send_email_reminder(license_obj, interval):
#     """
#     Send email reminder for license expiration.
#     Will send to specific recipients if defined for the license, otherwise falls back to
#     the IT_TEAM_EMAILS from config.
    
#     Args:
#         license_obj: The License object
#         interval: String indicating the notification interval (e.g., "90", "60", "30", "7", "post")
#     """
#     if interval == "post":
#         subject = f"License '{license_obj.name}' expired yesterday"
#     else:
#         subject = f"License '{license_obj.name}' will expire in {interval} days"
    
#     body = f"""
# Hello,

# This is an automated reminder that the license for "{license_obj.name}" is scheduled to expire.
# Details:
# - Category: {license_obj.category.name}
# - License Type: {license_obj.license_type}
# - Assigned To: {license_obj.assigned_to}
# - Expiry Date: {license_obj.expiry_date}
# - Status: {license_obj.computed_status}

# Please take the necessary actions.

# Regards,
# AGF License Management System
#     """
    
#     try:
#         # Get recipients for this license
#         recipients = []
        
#         # First, try to get the license-specific notification recipients
#         if hasattr(license_obj, 'notifications') and license_obj.notifications:
#             recipients = [notification.email for notification in license_obj.notifications]
        
#         # If no specific recipients, fall back to the default IT team emails
#         if not recipients:
#             recipients = current_app.config['IT_TEAM_EMAILS']
#             current_app.logger.info(f"No specific recipients found for license {license_obj.id}, using default IT team emails")
        
#         # Log the recipients for debugging
#         current_app.logger.info(f"Sending reminder for license {license_obj.id} to: {', '.join(recipients)}")
        
#         # Create and send the email
#         msg = Message(subject=subject,
#                       recipients=recipients,
#                       body=body)
#         mail.send(msg)
        
#         # Record the email log
#         current_app.logger.info(f"Sent reminder for license {license_obj.id} ({interval} days).")
#         log = EmailLog(license_id=license_obj.id, interval=interval, sent_at=datetime.now(timezone.utc))
#         db.session.add(log)
#         db.session.commit()
        
#     except IntegrityError as ie:
#         db.session.rollback()
#         current_app.logger.info(f"Email log already exists for license {license_obj.id} interval {interval}. Skipping duplicate.")
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Failed to send email for license {license_obj.id}: {e}")

        
def already_sent_reminder(license_id, interval):
    """Return True if an email for this interval was sent in the last 5 minutes."""
    entry = EmailLog.query.filter_by(license_id=license_id, interval=interval).order_by(EmailLog.sent_at.desc()).first()
    if entry:
        entry_time = entry.sent_at
        # If entry_time is offset-naive, assume it's UTC
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - entry_time).total_seconds() < 300:
            current_app.logger.info(
                f"Email already sent for license {license_id} for interval {interval} within last 5 minutes (sent at {entry_time})."
            )
            return True
    return False

# def check_license_expirations():
#     """Run scheduled job to check license expiries and send reminders."""
#     if not email_check_lock.acquire(blocking=False):
#         current_app.logger.info("check_license_expirations is already running; skipping this run.")
#         return
#     try:
#         current_app.logger.info("Running scheduled license expiry check...")
#         today = date.today()
#         licenses = License.query.filter(License.is_perpetual == False).all()
#         reminder_intervals = ["90", "60", "30", "7"]  # days before expiry
#         for lic in licenses:
#             if not lic.expiry_date:
#                 current_app.logger.info(f"Skipping license {lic.id} because expiry_date is not set.")
#                 continue
#             diff = (lic.expiry_date - today).days
#             current_app.logger.info(f"License {lic.id} has an expiry diff of {diff} days.")
            
#             # Pre-expiry reminders
#             for interval in reminder_intervals:
#                 if diff == int(interval):
#                     current_app.logger.info(f"License {lic.id} qualifies for a {interval}-day reminder.")
#                     if not already_sent_reminder(lic.id, interval):
#                         send_email_reminder(lic, interval)
#                     else:
#                         current_app.logger.info(f"Skipping sending {interval}-day reminder for license {lic.id} (already sent recently).")
            
#             # Post-expiry reminder: 1 day after expiry
#             if diff == -1:
#                 current_app.logger.info(f"License {lic.id} qualifies for a post-expiry reminder.")
#                 if not already_sent_reminder(lic.id, "post"):
#                     send_email_reminder(lic, "post")
#                 else:
#                     current_app.logger.info(f"Skipping sending post-expiry reminder for license {lic.id} (already sent recently).")
#     finally:
#         email_check_lock.release()