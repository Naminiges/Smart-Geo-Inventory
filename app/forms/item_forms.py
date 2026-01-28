from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class CategoryForm(FlaskForm):
    """Form for creating/editing categories"""
    name = StringField('Nama Kategori', validators=[DataRequired(), Length(min=2, max=100)])
    code = StringField('Kode Kategori', validators=[DataRequired(), Length(min=2, max=10)], description='Kode untuk prefix item code (contoh: JAR, ELE, SRV, MEB, LNY)')
    description = TextAreaField('Deskripsi', validators=[Optional()])
    submit = SubmitField('Simpan')


class ItemForm(FlaskForm):
    """Form for creating/editing items"""
    name = StringField('Nama Barang', validators=[DataRequired(), Length(min=2, max=200)])
    item_code = StringField('Kode Barang', validators=[DataRequired(), Length(min=2, max=50)])
    unit = StringField('Satuan', validators=[DataRequired(), Length(min=1, max=50)])
    category_id = SelectField('Kategori', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Simpan')


class ItemDetailForm(FlaskForm):
    """Form for creating/editing item details"""
    serial_number = StringField('Nomor Seri', validators=[DataRequired(), Length(min=2, max=100)])
    item_id = SelectField('Barang', coerce=int, validators=[DataRequired()])
    warehouse_id = SelectField('Gudang', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('available', 'Tersedia'),
        ('processing', 'Dalam Proses'),
        ('maintenance', 'Pemeliharaan'),
        ('used', 'Terpakai')
    ], validators=[DataRequired()])
    specification_notes = TextAreaField('Spesifikasi', validators=[Optional()])
    submit = SubmitField('Simpan')
