from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, FileField, DateTimeLocalField
from wtforms.validators import DataRequired, Optional, NumberRange


class AssetLoanRequestForm(FlaskForm):
    """Form for unit staff to create asset loan request"""
    request_notes = TextAreaField('Alasan Peminjaman', validators=[DataRequired(message='Alasan peminjaman harus diisi')])


class AssetLoanApproveForm(FlaskForm):
    """Form for warehouse staff to approve loan request"""
    approval_notes = TextAreaField('Catatan Persetujuan', validators=[Optional()])


class AssetLoanShipForm(FlaskForm):
    """Form for warehouse staff to ship loaned items"""
    shipment_notes = TextAreaField('Catatan Pengiriman', validators=[Optional()])


class AssetLoanReceiveForm(FlaskForm):
    """Form for unit staff to confirm receipt of loaned items"""
    receipt_notes = TextAreaField('Catatan Penerimaan', validators=[Optional()])


class AssetLoanReturnRequestForm(FlaskForm):
    """Form for unit staff to request return of loaned items"""
    return_reason = TextAreaField('Alasan Pengembalian', validators=[Optional()])


class AssetLoanReturnApproveForm(FlaskForm):
    """Form for warehouse staff to approve return request"""
    return_notes = TextAreaField('Catatan Retur', validators=[Optional()])


class AssetLoanItemReturnVerifyForm(FlaskForm):
    """Form for warehouse staff to verify return of individual item"""
    action = SelectField('Aksi', choices=[('approve', 'Setujui'), ('reject', 'Tolak')], validators=[DataRequired()])
    rejection_reason = TextAreaField('Alasan Penolakan', validators=[Optional()])


class AssetLoanItemUploadProofForm(FlaskForm):
    """Form for unit staff to upload return proof photo"""
    return_photo = FileField('Foto Bukti Pengembalian', validators=[Optional()])
    return_notes = TextAreaField('Catatan Pengembalian', validators=[Optional()])


class VenueLoanForm(FlaskForm):
    """Form for admin to create venue loan directly"""
    unit_detail_id = SelectField('Ruangan/Tempat', coerce=int, validators=[DataRequired(message='Ruangan harus dipilih')])
    borrower_unit_id = SelectField('Unit Peminjam', coerce=int, validators=[DataRequired(message='Unit peminjam harus dipilih')])
    event_name = StringField('Nama Acara', validators=[DataRequired(message='Nama acara harus diisi')])
    start_datetime = DateTimeLocalField('Waktu Mulai', format='%Y-%m-%dT%H:%M', validators=[DataRequired(message='Waktu mulai harus diisi')])
    end_datetime = DateTimeLocalField('Waktu Selesai', format='%Y-%m-%dT%H:%M', validators=[DataRequired(message='Waktu selesai harus diisi')])
    notes = TextAreaField('Catatan', validators=[Optional()])
