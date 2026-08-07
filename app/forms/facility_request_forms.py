from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional


class SignatureFieldsMixin:
    signature_data = HiddenField('Data tanda tangan', validators=[DataRequired(message='Tanda tangan wajib diisi.')])
    password = PasswordField('Konfirmasi password', validators=[DataRequired(), Length(min=6, max=128)])
    consent = BooleanField('Saya menyetujui dokumen ini', validators=[DataRequired(message='Persetujuan wajib dicentang.')])


class FacilityRequestForm(SignatureFieldsMixin, FlaskForm):
    request_type = SelectField('Jenis formulir', choices=[
        ('new', 'Pengajuan fasilitas baru'),
        ('addition', 'Penambahan fasilitas'),
        ('repair_service', 'Perbaikan/servis'),
        ('return', 'Pengembalian fasilitas'),
        ('replacement', 'Penggantian fasilitas'),
        ('other', 'Lainnya'),
    ], validators=[DataRequired()])
    other_request_type = StringField('Jelaskan jenis kebutuhan lainnya', validators=[Optional(), Length(max=255)])
    priority = SelectField('Tingkat prioritas', choices=[
        ('normal', 'Normal'),
        ('important', 'Penting'),
        ('urgent', 'Mendesak'),
    ], validators=[DataRequired()])
    justification = TextAreaField('Uraian kebutuhan dan keterkaitan dengan tugas', validators=[DataRequired(), Length(min=5, max=5000)])
    impact_if_unavailable = TextAreaField('Dampak apabila fasilitas tidak tersedia', validators=[DataRequired(), Length(min=5, max=5000)])
    submit = SubmitField('Submit & Sign sebagai Pemohon/Atasan Langsung')


class FacilityAdministrationForm(SignatureFieldsMixin, FlaskForm):
    warehouse_id = SelectField('Warehouse sumber', choices=[], coerce=int, validators=[DataRequired()])
    availability = SelectField('Hasil verifikasi', choices=[
        ('available', 'Tersedia'),
        ('unavailable', 'Tidak tersedia'),
        ('procurement_required', 'Perlu pengadaan'),
    ], validators=[DataRequired()])
    device_condition = SelectField('Kondisi perangkat', choices=[
        ('new', 'Baru'),
        ('good', 'Baik'),
        ('repair_required', 'Perlu perbaikan'),
        ('not_applicable', 'Tidak berlaku'),
    ], validators=[DataRequired()])
    facility_source = SelectField('Sumber fasilitas', choices=[
        ('stock', 'Stok'),
        ('mutation', 'Mutasi'),
        ('procurement', 'Pengadaan'),
    ], validators=[DataRequired()])
    recommendation = SelectField('Rekomendasi', choices=[
        ('approved', 'Disetujui'),
        ('partially_approved', 'Disetujui sebagian'),
        ('postponed', 'Ditunda'),
        ('rejected', 'Ditolak'),
    ], validators=[DataRequired()])
    estimated_completion = DateField('Estimasi penyelesaian', validators=[Optional()])
    realization_priority = SelectField('Prioritas realisasi', choices=[
        ('normal', 'Normal'),
        ('important', 'Penting'),
        ('urgent', 'Mendesak'),
    ], validators=[DataRequired()])
    notes = TextAreaField('Catatan verifikasi', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Verifikasi & Sign sebagai Administrasi')


class FacilityLeadershipForm(SignatureFieldsMixin, FlaskForm):
    notes = TextAreaField('Catatan pimpinan', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Setujui & Sign sebagai Pimpinan')


class FacilityDecisionForm(FlaskForm):
    action = HiddenField(validators=[DataRequired()])
    reason = TextAreaField('Alasan', validators=[DataRequired(), Length(min=5, max=2000)])
    password = PasswordField('Konfirmasi password', validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField('Proses')


class FacilityReceiptForm(FlaskForm):
    receipt_notes = TextAreaField('Catatan penerimaan', validators=[Optional(), Length(max=3000)])
    user_statement_accepted = BooleanField('Saya menyatakan fasilitas telah diterima dan akan digunakan untuk kepentingan kedinasan.', validators=[DataRequired()])
    password = PasswordField('Konfirmasi password', validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField('Konfirmasi Penerimaan')


class FacilityOperationalForm(FlaskForm):
    notes = TextAreaField('Catatan operasional', validators=[Optional(), Length(max=3000)])
    password = PasswordField('Konfirmasi password', validators=[DataRequired(), Length(min=6, max=128)])
    confirmation = BooleanField('Saya mengonfirmasi tindakan operasional ini.', validators=[DataRequired(message='Konfirmasi wajib dicentang.')])
    submit = SubmitField('Konfirmasi Proses')
