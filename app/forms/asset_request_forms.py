from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


class AssetRequestForm(FlaskForm):
    """Form for unit staff to create asset requests"""
    request_notes = TextAreaField('Alasan Permohonan', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Ajukan Permohonan')


class AssetVerificationForm(FlaskForm):
    """Form for admin to verify asset request"""
    notes = TextAreaField('Catatan Verifikasi', validators=[Optional()])
    submit = SubmitField('Verifikasi & Setujui')
