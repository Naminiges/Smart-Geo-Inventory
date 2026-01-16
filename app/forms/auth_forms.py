from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    """Login form for authentication"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Masuk')


class RegistrationForm(FlaskForm):
    """Registration form for new users"""
    name = StringField('Nama Lengkap', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Konfirmasi Password',
        validators=[DataRequired(), EqualTo('password', message='Password harus sama')]
    )
    submit = SubmitField('Daftar')
