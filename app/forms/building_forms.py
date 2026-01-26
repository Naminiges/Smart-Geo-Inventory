from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, Optional


class BuildingForm(FlaskForm):
    """Form untuk创建和编辑 gedung"""
    code = StringField('Kode Gedung', validators=[
        DataRequired(message='Kode gedung wajib diisi'),
        Length(min=2, max=50, message='Kode gedung harus 2-50 karakter')
    ], description='Contoh: GD.A, GD.B, GD.C')

    name = StringField('Nama Gedung', validators=[
        DataRequired(message='Nama gedung wajib diisi'),
        Length(min=3, max=200, message='Nama gedung harus 3-200 karakter')
    ], description='Contoh: Gedung A, Gedung B, Gedung C')

    address = TextAreaField('Alamat', validators=[
        Optional()
    ], description='Alamat lengkap gedung')

    floor_count = IntegerField('Jumlah Lantai', validators=[
        Optional()
    ], default=1, description='Jumlah lantai gedung')

    # Hidden fields for zone data
    zone_kode = HiddenField('Kode Zona')
    zone_deskripsi = HiddenField('Deskripsi Zona')
    zone_coordinates = HiddenField('Koordinat Zona')
