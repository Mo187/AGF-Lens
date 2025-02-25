
from flask import render_template, redirect, request, url_for, jsonify, abort, flash
from flask_login import (
    current_user,
    login_user,
    logout_user,login_required
)

from flask import current_app
from flask_mail import Message


import pandas as pd

import random, string

from apps.authentication.util import hash_pass

import logging
from datetime import date
from apps import cache
from functools import lru_cache

import concurrent.futures
from functools import wraps

from apps.extensions import db, login_manager

from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import Users, Inventory, Permission

from apps.authentication.util import verify_pass
import os
import requests
import math

## Local imports from Functions.py (Bitdefenfer, freshdesk etc...)
from api.functions import get_company_details, get_endpoints_list, get_network_inventory_items, create_report, process_ticket, get_requesters, get_ticket_volume_over_time, get_ticket_status_distribution, get_average_resolution_time, get_agent_data
from functions.licenses import send_email_reminder
from apps.authentication.models import License, EmailLog, Category
from apps.extensions import mail
from apps.authentication.models import Users, Department, Permission

#Freshdesk API creds
fresh_url = os.getenv('fresh_url')
fresh_key = os.getenv('fresh_key')
fresh_passw = os.getenv('fresh_passw')





@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login'))

@blueprint.route("/check-ip")
def check_ip():
    try:
        ip = requests.get("https://api.ipify.org").text
        return jsonify({"outbound_ip": ip})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Login & Registration

# @blueprint.route('/login', methods=['GET', 'POST'])
# def login():
#     login_form = LoginForm(request.form)
#     if 'login' in request.form:

#         # read form data
#         username = request.form['username']
#         password = request.form['password']

#         # Locate user
#         user = Users.query.filter_by(username=username).first()

#         # Check the password
#         if user and verify_pass(password, user.password):

#             login_user(user)
#             return redirect(url_for('authentication_blueprint.route_default'))

#         # Something (user or pass) is not ok
#         return render_template('accounts/customlogin.html',
#                                msg='Wrong Username or password!',
#                                form=login_form)

#     if not current_user.is_authenticated:
#         return render_template('accounts/customlogin.html',
#                                form=login_form)
#     return redirect(url_for('home_blueprint.index'))

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    
    try:
        if 'login' in request.form:
            try:
                email = request.form['email']
                password = request.form['password']
                # Locate user by email
                user = Users.query.filter_by(email=email).first()
                # Check the password
                if user and verify_pass(password, user.password):
                    login_user(user)
                    # Check if password change is required
                    if user.force_password_change:
                        flash('Please change your password.', 'warning')
                        return redirect(url_for('authentication_blueprint.change_password'))
                    return redirect(url_for('authentication_blueprint.route_default'))
                return render_template('accounts/customlogin.html',
                                    msg='Wrong email or password',
                                    form=login_form)
            except Exception as e:
                print(f"Database error during login attempt: {e}")
                return render_template('accounts/customlogin.html',
                                    msg='Unable to process login. Please try again.',
                                    form=login_form)
        
        if not current_user.is_authenticated:
            return render_template('accounts/customlogin.html',
                                form=login_form)
        return redirect(url_for('home_blueprint.index'))
    
    except Exception as e:
        print(f"Critical login page error: {e}")
        # Ensure login page is always accessible
        return render_template('accounts/customlogin.html',
                            form=login_form,
                            msg='System temporarily unavailable. Please try again later.')



# Admin decorator
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        try:
            if not current_user.has_permission('admin'):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('home_blueprint.index'))
        except Exception as e:
            print(f"> Error checking admin permissions: {e}")
            flash('Error verifying permissions. Please try again.', 'danger')
            return redirect(url_for('home_blueprint.index'))
            
        return f(*args, **kwargs)
    return decorated_function


# Register route - admin only
@blueprint.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    from apps.authentication.forms import CreateAccountForm
    from apps.authentication.models import Users, Department, Permission
    
    create_form = CreateAccountForm(request.form)
    
    if 'register' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        department_id = int(request.form['department']) if request.form['department'] else None
        permissions_ids = request.form.getlist('permissions')
        
        # Check if user exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register.html',
                                  msg='Username already registered',
                                  success=False,
                                  form=create_form)
        
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register.html',
                                  msg='Email already registered',
                                  success=False,
                                  form=create_form)
        
        # Create the user
        try:
            # Create user with provided password
            user = Users(
                username=username,
                email=email,
                password=password,  # __init__ method will hash this
                force_password_change=True
            )
            
            # Add department if provided
            if department_id:
                user.department_id = department_id
            
            # Add selected permissions
            if permissions_ids:
                for perm_id in permissions_ids:
                    permission = Permission.query.get(int(perm_id))
                    if permission:
                        user.permissions.append(permission)
            
            db.session.add(user)
            db.session.commit()
            
            return render_template('accounts/register.html',
                                  msg='User created successfully.',
                                  success=True,
                                  form=create_form)
        except Exception as e:
            db.session.rollback()
            print(f"> Error creating user: {e}")
            return render_template('accounts/register.html',
                                  msg='Error creating user: ' + str(e),
                                  success=False,
                                  form=create_form)
    
    return render_template('accounts/register.html',
                          form=create_form,
                          success=False)
                          
                                 
@blueprint.route('/admin/manage-permissions', methods=['GET', 'POST'])
@admin_required
def manage_permissions():
    
    # Get selected user if provided
    selected_user_id = request.args.get('user_id', None)
    selected_user = None
    
    if selected_user_id:
        try:
            selected_user = Users.query.get(int(selected_user_id))
        except Exception as e:
            print(f"> Error fetching selected user: {e}")
            flash('Error fetching user details.', 'danger')
    
    # Handle permission update if POST request
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            if not user_id:
                flash('User ID is required.', 'danger')
                return redirect(url_for('authentication_blueprint.manage_permissions'))
            
            user = Users.query.get(int(user_id))
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('authentication_blueprint.manage_permissions'))
            
            # Update permissions
            selected_permission_ids = request.form.getlist('permissions')
            
            # Clear existing permissions
            user.permissions = []
            
            # Add selected permissions
            if selected_permission_ids:
                for perm_id in selected_permission_ids:
                    permission = Permission.query.get(int(perm_id))
                    if permission:
                        user.permissions.append(permission)
            
            db.session.commit()
            flash('Permissions updated successfully.', 'success')
            
            # Redirect to the same page with the user selected
            return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"> Error updating permissions: {e}")
            flash(f'Error updating permissions: {str(e)}', 'danger')
    
    # Get all users, departments and permissions for display
    try:
        users = Users.query.all()
        departments = Department.query.all()
        permissions = Permission.query.all()
    except Exception as e:
        print(f"> Error fetching data: {e}")
        users = []
        departments = []
        permissions = []
    
    return render_template('accounts/permissions.html',
                          users=users,
                          departments=departments,
                          permissions=permissions,
                          selected_user=selected_user)

@blueprint.route('/admin/edit-user', methods=['POST'])
@admin_required
def edit_user():
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            flash('User ID is required.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        user = Users.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        # Update user details
        username = request.form.get('username')
        email = request.form.get('email')
        department_id = request.form.get('department_id')
        
        if username:
            # Check if username is already taken by another user
            existing_user = Users.query.filter(Users.username == username, Users.id != user.id).first()
            if existing_user:
                flash('Username already exists.', 'danger')
                return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user.id))
            user.username = username
            
        if email:
            # Check if email is already taken by another user
            existing_user = Users.query.filter(Users.email == email, Users.id != user.id).first()
            if existing_user:
                flash('Email already exists.', 'danger')
                return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user.id))
            user.email = email
            
        # Update department
        if department_id:
            user.department_id = int(department_id)
        else:
            user.department_id = None
        
        db.session.commit()
        flash('User updated successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"> Error updating user: {e}")
        flash(f'Error updating user: {str(e)}', 'danger')
        
    return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user_id))

@blueprint.route('/admin/reset-password', methods=['POST'])
@admin_required
def reset_password():
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            flash('User ID is required.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        user = Users.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        temp_pass = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))
        
        # Set the new password
        user.password = temp_pass  # Your Users model __init__ will hash this
        user.force_password_change = True
        
        db.session.commit()
        
        # Try to send email notification
        try:
          
            
            if current_app.config.get('MAIL_USERNAME') and current_app.config.get('MAIL_PASSWORD'):
                msg = Message(
                    subject="Your Password Has Been Reset",
                    recipients=[user.email],
                    body=f"Your password has been reset by an administrator.\n\nYour temporary password is: {temp_pass}\n\nYou will be required to change your password after logging in.",
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER')
                )
                mail.send(msg)
                flash(f'Password reset successfully. Temporary password: {temp_pass}', 'success')
            else:
                flash(f'Password reset successfully. Temporary password: {temp_pass}', 'success')
        except Exception as mail_error:
            print(f"> Error sending email: {mail_error}")
            flash(f'Password reset successfully, but email notification failed. Temporary password: {temp_pass}', 'warning')
        
    except Exception as e:
        db.session.rollback()
        print(f"> Error resetting password: {e}")
        flash(f'Error resetting password: {str(e)}', 'danger')
        
    return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user_id))

@blueprint.route('/admin/toggle-user-status', methods=['POST'])
@admin_required
def toggle_user_status():
    try:
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        
        if not user_id or not action:
            flash('User ID and action are required.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        user = Users.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        # Toggle status based on action
        if action == 'activate':
            user.is_active = True
            message = 'User activated successfully.'
        elif action == 'deactivate':
            user.is_active = False
            message = 'User deactivated successfully.'
        else:
            flash('Invalid action.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user.id))
        
        db.session.commit()
        flash(message, 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"> Error toggling user status: {e}")
        flash(f'Error updating user status: {str(e)}', 'danger')
        
    return redirect(url_for('authentication_blueprint.manage_permissions', user_id=user_id))

@blueprint.route('/admin/delete-user', methods=['POST'])
@admin_required
def delete_user():
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            flash('User ID is required.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        user = Users.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        # Don't allow deletion of the user's own account
        if user.id == current_user.id:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('authentication_blueprint.manage_permissions'))
        
        username = user.username
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User "{username}" deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"> Error deleting user: {e}")
        flash(f'Error deleting user: {str(e)}', 'danger')
        
    return redirect(url_for('authentication_blueprint.manage_permissions'))


########################################################################

def insert_data_from_excel(file_path):
    data = pd.read_excel(file_path)
    for _, row in data.iterrows():
        inventory_item = Inventory(
            employee_name=row['Employee Name'],
            department=row['Department'],
            laptop_model=row['Laptop Model'],
            serial_number=row['Serial']
        )
        db.session.add(inventory_item)
    db.session.commit()

@blueprint.route('/insert-data')
def insert_data():
    # Already inside app context because this is a view function
    insert_data_from_excel('data/laptopexcel.xlsx')
    return "Data inserted successfully"


# For ICT Inventory management table of workstations and laptops
@blueprint.route('/ict-ims.html')
@login_required
def inventory():
    inventories = Inventory.query.all()
    missing_serial_count = Inventory.query.filter(Inventory.serial_number == None).count()
    total_workstations_count = Inventory.query.count()
    return render_template('home/ict-ims.html', segment='ict-ims', inventories=inventories,  missing_serial_count=missing_serial_count, total_workstations_count=total_workstations_count)




@blueprint.route('/inventory/add', methods=['POST'])
@login_required
def add_inventory():
    employee_name = request.form['employee_name']
    laptop_model = request.form['laptop_model']
    serial_number = request.form['serial_number']
    department = request.form['department']
    
    new_inventory = Inventory(
        employee_name=employee_name,
        laptop_model=laptop_model,
        serial_number=serial_number,
        department=department
    )
    db.session.add(new_inventory)
    db.session.commit()
    return redirect(url_for('authentication_blueprint.inventory'))


@blueprint.route('/inventory/edit/<int:id>', methods=['POST'])
@login_required
def edit_inventory(id):
    inventory = Inventory.query.get_or_404(id)
    inventory.employee_name = request.form['employee_name']
    inventory.laptop_model = request.form['laptop_model']
    inventory.serial_number = request.form['serial_number']
    inventory.department = request.form['department']
    
    db.session.commit()
    return redirect(url_for('authentication_blueprint.inventory'))


@blueprint.route('/inventory/delete/<int:id>', methods=['POST'])
@login_required
def delete_inventory(id):
    inventory = Inventory.query.get_or_404(id)
    db.session.delete(inventory)
    db.session.commit()
    return redirect(url_for('authentication_blueprint.inventory'))


@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('authentication_blueprint.login'))




# # # # # # # # # # APIs for Dashboards

def fetch_inventory_page(parent_id, page, per_page, filters, options):
    """Fetch a single page of inventory"""
    try:
        result = get_network_inventory_items(parent_id, page, per_page, filters, options)
        if result and 'items' in result:
            logging.info(f"Successfully fetched page {page} with {len(result['items'])} items")
            return result['items']
        logging.warning(f"No items found in page {page}")
        return []
    except Exception as e:
        logging.error(f"Error fetching page {page}: {str(e)}")
        return []

@cache.cached(timeout=300)
@blueprint.route('/bitdefender_data', methods=['GET'])
@login_required
def get_dashboard_data():
    logging.info("Fetching dashboard data...")
    
    try:
        # Get company details
        company_details = get_company_details()
        if not company_details:
            logging.error("Failed to fetch company details")
            return jsonify({"error": "Failed to get company details"}), 500

        parent_id = company_details.get('id')
        logging.info(f"Using parent_id: {parent_id}")

        # Define filters and options
        filters = {
            "type": {"computers": True, "virtualMachines": True},
            "depth": {"allItemsRecursively": True},
            "security": {"management": {
                "managedWithBest": True,
                "managedExchangeServers": True,
                "securityServers": True,
                "managedRelays": True
            }},
        }
        
        options = {
            "companies": {"returnAllProducts": True},
            "endpoints": {"returnProductOutdated": True, "includeScanLogs": True}
        }

        # Get first page to determine total pages
        first_page_result = get_network_inventory_items(parent_id, 1, 100, filters, options)
        if first_page_result is None:
            logging.error("Failed to fetch first page")
            return jsonify({"error": "Failed to get inventory items"}), 500

        all_inventory_items = first_page_result.get('items', [])
        total_items = first_page_result.get('total', 0)
        
        if total_items > 100:  # If we have more pages
            remaining_pages = range(2, (total_items + 99) // 100 + 1)
            
            # Fetch remaining pages in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_page = {
                    executor.submit(
                        fetch_inventory_page, 
                        parent_id, 
                        page, 
                        100,  # Keep original page size
                        filters, 
                        options
                    ): page for page in remaining_pages
                }
                
                for future in concurrent.futures.as_completed(future_to_page):
                    try:
                        items = future.result()
                        all_inventory_items.extend(items)
                        logging.info(f"Added {len(items)} items to total")
                    except Exception as e:
                        logging.error(f"Error processing page: {str(e)}")

        total_endpoints = len(all_inventory_items)
        logging.info(f"Final total endpoints count: {total_endpoints}")

        # Prepare response data
        response_data = {
            "riskScore": {
                "value": company_details.get('riskScore', {}).get('value', '0%'),
                "impact": company_details.get('riskScore', {}).get('impact', 'Unknown'),
                "appVulnerabilities": company_details.get('riskScore', {}).get('appVulnerabilities', '0%'),
                "humanRisks": company_details.get('riskScore', {}).get('humanRisks', '0%'),
                "industryModifier": company_details.get('riskScore', {}).get('industryModifier', '0%'),
                "misconfigurations": company_details.get('riskScore', {}).get('misconfigurations', '0%')
            },
            "totalEndpoints": total_endpoints
        }

        return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error in dashboard_data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@blueprint.route('/get_company_id', methods=['GET'])
@login_required
def get_company_id():
    details = get_company_details()
    if details is None:
        logging.error('Failed to get company details.')
        return {"error": "Failed to get company details"}, 500
    return {"company_id": details['id']}

@blueprint.route('/get_endpoint_ids', methods=['GET'])
@login_required
def get_endpoint_ids():
    parent_id = request.args.get('parent_id')
    endpoints = get_endpoints_list(parent_id, is_managed=True)
    if endpoints is None:
        logging.error('Failed to get endpoints.')
        return {"error": "Failed to get endpoints"}, 500
    endpoint_ids = [endpoint['id'] for endpoint in endpoints]
    return {"endpoint_ids": endpoint_ids}


# Freshdesk routes and endpoints
#################################################################
##########################################################################

from urllib.parse import quote_plus

@blueprint.route('/ict-helpdesk', methods=['GET'])
@login_required
def ict_helpdesk():
    """Main route that returns the initial template without data"""
    return render_template(
        'home/ict-helpdesk.html',
        segment='ict-helpdesk'
    )

@blueprint.route('/api/helpdesk/basic-stats', methods=['GET'])
@login_required
@cache.cached(timeout=300)
def get_basic_stats():
    try:
        session = requests.Session()
        
        # Using your existing query logic
        query_for_stats = 'status:2 OR status:3'
        query_with_quotes = f'"{query_for_stats}"'
        encoded_query_stats = quote_plus(query_with_quotes)
        search_url_stats = f"{fresh_url}search/tickets?query={encoded_query_stats}"
        
        tickets_response_stats = session.get(
            search_url_stats,
            headers={'Content-Type': 'application/json'},
            auth=(fresh_key, fresh_passw)
        )
        tickets_response_stats.raise_for_status()
        tickets_data_stats = tickets_response_stats.json()['results']
        
        # Calculate average resolution time
        avg_resolution_time = get_average_resolution_time(session)
        
        stats = {
            'total_unresolved': len(tickets_data_stats),
            'total_open': sum(1 for ticket in tickets_data_stats if ticket.get('status') == 2),
            'total_on_hold': sum(1 for ticket in tickets_data_stats if ticket.get('status') == 3),
            'average_resolution_time': avg_resolution_time
        }
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error in basic stats: {str(e)}")  # Debug logging
        return jsonify({'error': str(e)}), 500

@blueprint.route('/api/helpdesk/detailed-stats', methods=['GET'])
@login_required
@cache.cached(timeout=300)
def get_detailed_stats():
    try:
        session = requests.Session()
        
        # Get ticket volume data
        dates, ticket_counts = get_ticket_volume_over_time(session)
        
        # Get status distribution
        statuses, status_counts = get_ticket_status_distribution(session)
        
        data = {
            'ticket_volume': {
                'dates': dates,
                'counts': ticket_counts
            },
            'status_distribution': {
                'statuses': statuses,
                'counts': status_counts,
                'days_back': 30
            }
        }
        
        print("Detailed stats data:", data)  # Debug logging
        return jsonify(data)
    except Exception as e:
        print(f"Error in detailed stats: {str(e)}")  # Debug logging
        return jsonify({'error': str(e)}), 500

@blueprint.route('/api/helpdesk/recent-activity', methods=['GET'])
@login_required
@cache.cached(timeout=300)
def get_recent_activity():
    try:
        session = requests.Session()
        
        # Get agents data
        agents_data = get_agent_data(session)
        agent_id_to_name = {
            agent['id']: agent['contact']['name']
            for agent in agents_data
            if 'contact' in agent and 'name' in agent['contact']
        }
        
        # Fetch recent tickets
        tickets_response_recent = session.get(
            f"{fresh_url}tickets",
            params={
                'per_page': 10,
                'order_by': 'created_at',
                'order_type': 'desc'
            },
            headers={'Content-Type': 'application/json'},
            auth=(fresh_key, fresh_passw)
        )
        tickets_response_recent.raise_for_status()
        tickets_data_recent = tickets_response_recent.json()
        
        # Get requester details
        requester_ids = {ticket.get('requester_id') for ticket in tickets_data_recent if ticket.get('requester_id')}
        requesters = get_requesters(requester_ids, session)
        
        # Process tickets
        recent_tickets = [
            process_ticket(ticket, requesters, agent_id_to_name)
            for ticket in tickets_data_recent
        ]
        
        activity_data = {
            'recent_tickets': recent_tickets,
            'agent_names': list(agent_id_to_name.values())
        }
        
        print("Recent activity data:", activity_data)  # Debug logging
        return jsonify(activity_data)
    except Exception as e:
        print(f"Error in recent activity: {str(e)}")  # Debug logging
        return jsonify({'error': str(e)}), 500

# Error handler for API routes
@blueprint.errorhandler(500)
def handle_500_error(e):
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500

# Error handler for API routes
@blueprint.errorhandler(404)
def handle_404_error(e):
    return jsonify({
        'error': 'Not found',
        'message': str(e)
    }), 404
    

# AGF LICENSE REMINDER ROUTES
########################################################################################
#############################################################################################

@blueprint.route('/ict-license')
@login_required
def index():
    return render_template('home/licenses.html', segment='ict-license')

@blueprint.route('/ict-license/test_email/<int:license_id>/<interval>', methods=['GET'])
@login_required
def test_email(license_id, interval):
    lic = License.query.get_or_404(license_id)
    send_email_reminder(lic, interval)
    return jsonify({"message": f"Test email sent for license {license_id} with interval {interval}."}), 200

# CATEGORY ROUTES
@blueprint.route('/ict-license/categories', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def handle_categories():
    if request.method == 'GET':
        categories = Category.query.all()
        result = []
        for cat in categories:
            total = len(cat.licenses)
            active_count = sum(1 for lic in cat.licenses if lic.computed_status.lower() == 'active')
            expiring_count = sum(1 for lic in cat.licenses if lic.computed_status.lower() == 'expiring soon')
            expired_count = sum(1 for lic in cat.licenses if lic.computed_status.lower() == 'expired')
            cat_dict = cat.to_dict()
            cat_dict['total'] = total
            cat_dict['active'] = active_count
            cat_dict['expiring'] = expiring_count
            cat_dict['expired'] = expired_count
            result.append(cat_dict)
        return jsonify(result), 200

    elif request.method == 'POST':
        data = request.json
        if not data.get('name'):
            abort(400, description="Category name is required")
        category = Category(name=data['name'], is_default=data.get('is_default', False))
        db.session.add(category)
        db.session.commit()
        return jsonify(category.to_dict()), 201

    elif request.method == 'PUT':
        data = request.json
        cat_id = data.get('id')
        category = Category.query.get_or_404(cat_id)
        if 'name' in data:
            category.name = data['name']
        if 'is_default' in data:
            category.is_default = data['is_default']
        db.session.commit()
        return jsonify(category.to_dict()), 200

    elif request.method == 'DELETE':
        cat_id = request.args.get('id')
        if not cat_id:
            abort(400, description="Category id is required")
        category = Category.query.get_or_404(cat_id)
        # Reassign licenses to default category (or create one if not exists)
        default_category = Category.query.filter_by(is_default=True).first()
        if not default_category:
            default_category = Category(name="Uncategorized", is_default=True)
            db.session.add(default_category)
            db.session.commit()
        for lic in category.licenses:
            lic.category_id = default_category.id
        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': f'Category {cat_id} deleted and licenses reassigned.'}), 200



@blueprint.route('/ict-license/licenses', methods=['GET', 'POST'])
@login_required
def manage_licenses():
    if request.method == 'GET':
        # Filtering by category, type, computed_status
        category_filter = request.args.get('category')  # e.g., "M365"
        type_filter = request.args.get('type')           # e.g., "Subscription"
        status_filter = request.args.get('status')       # e.g., "Active" or "Expiring Soon"
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        query = License.query

        if category_filter:
            query = query.join(Category).filter(Category.name == category_filter)
        if type_filter:
            query = query.filter(License.license_type == type_filter)

        # When filtering by computed status (which is done in Python),
        # we must manually paginate because it's not part of the SQL query.
        if status_filter:
            licenses = query.all()
            filtered = [lic.to_dict() for lic in licenses if lic.computed_status.lower() == status_filter.lower()]
            total_licenses = len(filtered)
            total_pages = math.ceil(total_licenses / limit)
            start = (page - 1) * limit
            end = start + limit
            paginated = filtered[start:end]
            return jsonify({
                'licenses': paginated,
                'totalPages': total_pages,
                'totalLicenses': total_licenses
            }), 200
        else:
            # If no status filter is applied, we can paginate at the database level.
            paginated = query.paginate(page=page, per_page=limit, error_out=False)
            licenses = [lic.to_dict() for lic in paginated.items]
            return jsonify({
                'licenses': licenses,
                'totalPages': paginated.pages,
                'totalLicenses': paginated.total
            }), 200

    elif request.method == 'POST':
        data = request.json
        # Expected: name, category, license_type, assigned_to, expiry_date, is_perpetual, purchase_date (optional)
        cat_name = data.get('category')
        if not cat_name:
            abort(400, description="Category is required")
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            # Auto-create category if it doesn't exist
            category = Category(name=cat_name, is_default=False)
            db.session.add(category)
            db.session.commit()
        expiry_date = None
        if not data.get('is_perpetual', False) and data.get('expiry_date'):
            expiry_date = date.fromisoformat(data['expiry_date'])
        purchase_date = None
        if data.get('purchase_date'):
            purchase_date = date.fromisoformat(data['purchase_date'])
        new_license = License(
            name=data['name'],
            category_id=category.id,
            license_type=data['license_type'],
            assigned_to=data.get('assigned_to'),
            expiry_date=expiry_date,
            is_perpetual=data.get('is_perpetual', False),
            purchase_date=purchase_date
        )
        db.session.add(new_license)
        db.session.commit()
        return jsonify(new_license.to_dict()), 201

@blueprint.route('/ict-license/licenses/<int:license_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def single_license(license_id):
    lic = License.query.get_or_404(license_id)
    if request.method == 'GET':
        return jsonify(lic.to_dict()), 200

    elif request.method == 'PUT':
        data = request.json
        if 'name' in data:
            lic.name = data['name']
        if 'category' in data:
            cat_name = data['category']
            category = Category.query.filter_by(name=cat_name).first()
            if not category:
                category = Category(name=cat_name)
                db.session.add(category)
                db.session.commit()
            lic.category_id = category.id
        if 'license_type' in data:
            lic.license_type = data['license_type']
        if 'assigned_to' in data:
            lic.assigned_to = data['assigned_to']
        if 'expiry_date' in data and not lic.is_perpetual:
            lic.expiry_date = date.fromisoformat(data['expiry_date'])
        if 'is_perpetual' in data:
            lic.is_perpetual = data['is_perpetual']
            if lic.is_perpetual:
                lic.expiry_date = None
        if 'purchase_date' in data:
            lic.purchase_date = date.fromisoformat(data['purchase_date'])
        db.session.commit()
        return jsonify(lic.to_dict()), 200

    elif request.method == 'DELETE':
        db.session.delete(lic)
        db.session.commit()
        return jsonify({'message': f'License {license_id} deleted.'}), 200

# BULK UPDATE ENDPOINT
@blueprint.route('/ict-license/licenses/bulk_update', methods=['POST'])
@login_required
def bulk_update_licenses():
    """
    Expect JSON payload:
    {
        "license_ids": [1,2,3],
        "update_fields": {
            "category": "New Category",
            "license_type": "Annual",
            "assigned_to": "new.email@example.com",
            "expiry_date": "2025-12-31",
            "is_perpetual": false
        }
    }
    """
    data = request.json
    license_ids = data.get("license_ids", [])
    update_fields = data.get("update_fields", {})
    if not license_ids or not update_fields:
        abort(400, description="license_ids and update_fields are required")
    
    # Handle category update separately
    if "category" in update_fields:
        cat_name = update_fields.pop("category")
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            category = Category(name=cat_name)
            db.session.add(category)
            db.session.commit()
        update_fields["category_id"] = category.id

    licenses = License.query.filter(License.id.in_(license_ids)).all()
    for lic in licenses:
        for key, value in update_fields.items():
            if key == "expiry_date" and value:
                setattr(lic, key, date.fromisoformat(value))
            else:
                setattr(lic, key, value)
    db.session.commit()
    return jsonify({"message": "Bulk update successful."}), 200
    
    
# Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500
