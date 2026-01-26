from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, Optional, Length


class UnitProcurementRequestForm(FlaskForm):
    """Form for unit staff to create procurement requests"""
    request_notes = TextAreaField('Alasan Permohonan', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Ajukan Permohonan')


class UnitProcurementVerifyForm(FlaskForm):
    """Form for admin to verify unit procurement request"""
    verification_notes = TextAreaField('Catatan Verifikasi', validators=[Optional()])
    submit = SubmitField('Verifikasi Permohonan')


class UnitProcurementApproveForm(FlaskForm):
    """Form for admin to approve verified request and create warehouse procurement"""
    supplier_id = SelectField('Pilih Supplier', coerce=int, validators=[DataRequired()])
    admin_notes = TextAreaField('Catatan Admin', validators=[Optional()])
    submit = SubmitField('Setujui dan Buat Pengadaan')


class UnitProcurementRejectForm(FlaskForm):
    """Form for admin to reject unit procurement request"""
    rejection_reason = TextAreaField('Alasan Penolakan', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Tolak Permohonan')
