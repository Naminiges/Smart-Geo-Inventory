from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email


class SupplierForm(FlaskForm):
    """Form for creating/editing suppliers"""
    name = StringField('Nama Supplier', validators=[DataRequired(), Length(min=2, max=200)])
    contact_person = StringField('Kontak Person', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Telepon', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = TextAreaField('Alamat', validators=[DataRequired()])
    submit = SubmitField('Simpan')
