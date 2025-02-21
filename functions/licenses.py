from flask import current_app
from datetime import datetime, date, timezone
from flask_mail import Message
from apps.authentication.models import License, EmailLog
from sqlalchemy.exc import IntegrityError
from apps import db

from apps.extensions import email_check_lock, mail

def send_email_reminder(license_obj, interval):
    if interval == "post":
        subject = f"License '{license_obj.name}' expired yesterday"
    else:
        subject = f"License '{license_obj.name}' will expire in {interval} days"
    
    body = f"""
Hello AGF-ICT Team,

This is an automated reminder that the license for "{license_obj.name}" is scheduled to expire.
Details:
- Category: {license_obj.category.name}
- License Type: {license_obj.license_type}
- Assigned To: {license_obj.assigned_to}
- Expiry Date: {license_obj.expiry_date}
- Status: {license_obj.computed_status}

Please take the necessary actions.

Regards,
AGF License Management System
    """
    try:
        msg = Message(subject=subject,
                      recipients=current_app.config['IT_TEAM_EMAILS'],
                      body=body)
        mail.send(msg)
        current_app.logger.info(f"Sent reminder for license {license_obj.id} ({interval} days).")
        # Insert log record using new recommended time method:
        log = EmailLog(license_id=license_obj.id, interval=interval, sent_at=datetime.now(timezone.utc))
        db.session.add(log)
        db.session.commit()
    except IntegrityError as ie:
        db.session.rollback()
        current_app.logger.info(f"Email log already exists for license {license_obj.id} interval {interval}. Skipping duplicate.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to send email for license {license_obj.id}: {e}")



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

def check_license_expirations():
    """Run scheduled job to check license expiries and send reminders."""
    if not email_check_lock.acquire(blocking=False):
        current_app.logger.info("check_license_expirations is already running; skipping this run.")
        return
    try:
        current_app.logger.info("Running scheduled license expiry check...")
        today = date.today()
        licenses = License.query.filter(License.is_perpetual == False).all()
        reminder_intervals = ["90", "60", "30", "7"]  # days before expiry
        for lic in licenses:
            if not lic.expiry_date:
                current_app.logger.info(f"Skipping license {lic.id} because expiry_date is not set.")
                continue
            diff = (lic.expiry_date - today).days
            current_app.logger.info(f"License {lic.id} has an expiry diff of {diff} days.")
            
            # Pre-expiry reminders
            for interval in reminder_intervals:
                if diff == int(interval):
                    current_app.logger.info(f"License {lic.id} qualifies for a {interval}-day reminder.")
                    if not already_sent_reminder(lic.id, interval):
                        send_email_reminder(lic, interval)
                    else:
                        current_app.logger.info(f"Skipping sending {interval}-day reminder for license {lic.id} (already sent recently).")
            
            # Post-expiry reminder: 1 day after expiry
            if diff == -1:
                current_app.logger.info(f"License {lic.id} qualifies for a post-expiry reminder.")
                if not already_sent_reminder(lic.id, "post"):
                    send_email_reminder(lic, "post")
                else:
                    current_app.logger.info(f"Skipping sending post-expiry reminder for license {lic.id} (already sent recently).")
    finally:
        email_check_lock.release()