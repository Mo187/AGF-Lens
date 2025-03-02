from flask_login import UserMixin
from apps.extensions import db, login_manager
from datetime import datetime, date, timezone
from apps.authentication.util import hash_pass

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))

# Association table with named constraints
user_permissions = db.Table('user_permissions',
    db.Column('user_id', db.Integer, db.ForeignKey('Users.id', name='fk_user_permissions_user')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', name='fk_user_permissions_permission')),
    db.UniqueConstraint('user_id', 'permission_id', name='uq_user_permission')
)

class Users(db.Model, UserMixin):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.LargeBinary)
    force_password_change = db.Column(db.Boolean, default=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', name='fk_user_department'))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    department = db.relationship('Department', backref='users')
    permissions = db.relationship('Permission', secondary=user_permissions, backref='users')

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            if property == 'password':
                value = hash_pass(value)
            setattr(self, property, value)

    def __repr__(self):
        return str(self.email)  # Changed to email since it's our primary identifier

    # Flask-Login required methods
    def is_authenticated(self):
        return True

    def is_active(self):
        return self.is_active

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    # Your permission methods
    def has_permission(self, permission_name):
        return any(p.name == permission_name for p in self.permissions)

    def has_any_permission(self, permission_names):
        return any(self.has_permission(name) for name in permission_names)

    def is_in_department(self, department_name):
        return self.department and self.department.name == department_name

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@login_manager.request_loader
def load_user_from_request(request):
    email = request.form.get('email')
    if email:
        return Users.query.filter_by(email=email).first()
    return None

### ICT ASSSETS INVENTORY MODELAS

class Inventory(db.Model):
    __tablename__ = 'Inventory'
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(255))
    laptop_model = db.Column(db.String(255))
    serial_number = db.Column(db.String(100))
    department = db.Column(db.String(100))
    
    def __init__(self, employee_name, department, laptop_model, serial_number):
        self.employee_name = employee_name
        self.department = department
        self.laptop_model = laptop_model
        self.serial_number = serial_number
    

class Monitors(db.Model):
    __tablename__ = 'Monitors'
    id = db.Column(db.Integer, primary_key=True)
    monitor_total= db.Column(db.Integer)
    
    def __init__(self, monitor_total):
        self.monitor_total = monitor_total

### AGF LICENSE HUB MODELAS

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_default = db.Column(db.Boolean, default=False)  # default category flag
    
    def __init__(self,name, is_default):
        self.name=name
        self.is_default=is_default

    # Relationship to licenses
    licenses = db.relationship('License', backref='category', lazy=True)

    def to_dict(self, include_licenses=False):
        data = {
            'id': self.id,
            'name': self.name,
            'is_default': self.is_default
        }
        if include_licenses:
            data['licenses'] = [lic.to_dict() for lic in self.licenses]
        return data

class License(db.Model):
    __tablename__ = 'license'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    license_type = db.Column(db.String(50), nullable=False)  # e.g., "Subscription", "Annual"
    assigned_to = db.Column(db.String(100), nullable=True)  # freeform, could be an email
    expiry_date = db.Column(db.Date, nullable=True)  # Nullable if perpetual
    is_perpetual = db.Column(db.Boolean, default=False)
    purchase_date = db.Column(db.Date, nullable=True)
    notifications = db.relationship('LicenseNotification', backref='license',cascade='all, delete-orphan', lazy=True)
    # Additional metadata fields can be added here
    
    def __init__(self,name,category_id, license_type, assigned_to, expiry_date,is_perpetual,purchase_date):
        self.name=name
        self.category_id=category_id
        self.license_type=license_type
        self.assigned_to=assigned_to
        self.expiry_date=expiry_date
        self.is_perpetual=is_perpetual
        self.purchase_date=purchase_date

    # We do not store status; it is computed on the fly
    @property
    def computed_status(self):
        if self.is_perpetual:
            return "Perpetual"
        if not self.expiry_date:
            return "Unknown"
        today = date.today()
        diff = (self.expiry_date - today).days
        if diff < 0:
            return "Expired"
        elif diff <= 90:  # within 90 days: consider expiring soon
            return "Expiring Soon"
        else:
            return "Active"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'license_type': self.license_type,
            'assigned_to': self.assigned_to,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_perpetual': self.is_perpetual,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'computed_status': self.computed_status,
            'notifications': [notification.to_dict() for notification in self.notifications]
        }

class EmailLog(db.Model):
    __tablename__ = 'emaillog'
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False)
    interval = db.Column(db.String(10), nullable=False)  # e.g., "90", "60", "30", "7", "post"
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self,license_id,interval,sent_at):
        self.license_id=license_id
        self.interval=interval
        self.sent_at=sent_at
    
    __table_args__ = (
        db.UniqueConstraint('license_id', 'interval', name='uix_license_interval'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'license_id': self.license_id,
            'interval': self.interval,
            'sent_at': self.sent_at.isoformat()
        }


class LicenseNotification(db.Model):
    """
    Model for license notification recipients.
    Each license can have multiple notification recipients.
    """
    __tablename__ = 'license_notifications'
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=True)  # Optional name for the recipient
    is_primary = db.Column(db.Boolean, default=False)  # Whether this is a primary contact
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __init__(self, license_id, email, name=None, is_primary=False):
        self.license_id = license_id
        self.email = email
        self.name = name
        self.is_primary = is_primary
    
    def to_dict(self):
        return {
            'id': self.id,
            'license_id': self.license_id,
            'email': self.email,
            'name': self.name,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

