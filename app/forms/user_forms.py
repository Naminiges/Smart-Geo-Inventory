from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional
from app.models import Warehouse, Unit


class UserForm(FlaskForm):
    """Form for creating/editing users"""
    name = StringField('Nama Lengkap', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('admin', 'Administrator'),
        ('warehouse_staff', 'Storeman'),
        ('unit_staff', 'Koordinator')
    ], validators=[DataRequired()])


class UserWarehouseAssignmentForm(FlaskForm):
    """Form for assigning warehouse to user (single selection)"""
    warehouse_id = SelectField('Warehouse', choices=[], coerce=int, validators=[Optional()])


class UserUnitAssignmentForm(FlaskForm):
    """Form for assigning unit to user (single selection)"""
    unit_id = SelectField('Unit', choices=[], coerce=int, validators=[Optional()])
