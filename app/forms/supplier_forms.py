from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email


class SupplierForm(FlaskForm):
    """Form for creating/editing suppliers"""
    name = StringField('Nama Supplier', validators=[DataRequired(), Length(min=2, max=200)])
    contact_person = StringField('Kontak Person', validators=[Optional(), Length(max=100)])
    phone = StringField('Telepon', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    address = TextAreaField('Alamat', validators=[Optional()])
    submit = SubmitField('Simpan')
