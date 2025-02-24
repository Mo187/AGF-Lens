# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField
from wtforms.validators import Email, DataRequired

# login and registration
# Login Form
class LoginForm(FlaskForm):
    email = StringField('Email',
                     id='email_login',
                     validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                         id='pwd_login',
                         validators=[DataRequired()])

class CreateAccountForm(FlaskForm):
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                           id='pwd_create',
                           validators=[DataRequired()])
    department = SelectField('Department',
                         id='department_create',
                         coerce=int,
                         validators=[DataRequired()])
    permissions = SelectMultipleField('Permissions',
                                  id='permissions_create',
                                  coerce=int)

    def __init__(self, *args, **kwargs):
        super(CreateAccountForm, self).__init__(*args, **kwargs)
        # Dynamically load departments and permissions
        from apps.authentication.models import Department, Permission
        
        # Load departments
        self.department.choices = [(d.id, d.name) for d in Department.query.all()]
        
        # Load permissions
        self.permissions.choices = [(p.id, p.description) for p in Permission.query.all()]