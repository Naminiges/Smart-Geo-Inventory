from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class DistributionForm(FlaskForm):
    """Form for creating/editing distributions"""
    item_detail_id = SelectField('Barang', coerce=int, validators=[DataRequired()])
    warehouse_id = SelectField('Gudang Asal', coerce=int, validators=[DataRequired()])
    field_staff_id = SelectField('Petugas Lapangan', coerce=int, validators=[DataRequired()])
    unit_id = SelectField('Unit Tujuan', coerce=int, validators=[DataRequired()])
    unit_detail_id = SelectField('Detail Unit', coerce=int, validators=[DataRequired()])
    address = TextAreaField('Alamat Lengkap', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
    status = SelectField('Status', choices=[
        ('installing', 'Sedang Dipasang'),
        ('installed', 'Terpasang'),
        ('broken', 'Rusak'),
        ('maintenance', 'Pemeliharaan')
    ], validators=[DataRequired()])
    note = TextAreaField('Catatan', validators=[Optional()])
    submit = SubmitField('Simpan')


class InstallationForm(FlaskForm):
    """Form for creating installation requests"""
    item_detail_id = SelectField('Barang', coerce=int, validators=[DataRequired()])
    field_staff_id = SelectField('Petugas Lapangan', coerce=int, validators=[DataRequired()])
    unit_id = SelectField('Unit Tujuan', coerce=int, validators=[DataRequired()])
    unit_detail_id = SelectField('Detail Unit', coerce=int, validators=[DataRequired()])
    address = TextAreaField('Alamat Lengkap', validators=[DataRequired()])
    note = TextAreaField('Catatan', validators=[Optional()])
    submit = SubmitField('Buat Permintaan Instalasi')
