from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, FloatField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


class ProcurementRequestForm(FlaskForm):
    """Form for warehouse staff to create procurement requests (Step 1-2)"""
    item_id = SelectField('Pilih Barang', coerce=int, validators=[Optional()])
    item_name = StringField('Nama Barang Baru', validators=[Optional()])
    item_category_id = SelectField('Kategori Barang', coerce=int, validators=[Optional()])
    item_unit = StringField('Satuan (contoh: pcs, unit)', validators=[Optional()])
    quantity = IntegerField('Kuantitas', validators=[DataRequired(), NumberRange(min=1)])
    request_notes = TextAreaField('Alasan Permohonan', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Ajukan Permohonan')


class ProcurementApprovalForm(FlaskForm):
    """Form for admin to approve and select supplier (Step 3)"""
    supplier_id = SelectField('Pilih Supplier', coerce=int, validators=[DataRequired()])
    unit_price = FloatField('Harga Satuan', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Catatan Admin', validators=[Optional()])
    submit = SubmitField('Setujui dan Pilih Supplier')


class GoodsReceiptForm(FlaskForm):
    """Form for recording goods receipt with serial numbers (Step 4-5)"""
    receipt_number = StringField('Nomor Tanda Terima', validators=[DataRequired(), Length(min=3)])
    actual_quantity = IntegerField('Jumlah Barang Diterima', validators=[DataRequired(), NumberRange(min=1)])
    serial_numbers = TextAreaField('Serial Numbers (satu per baris)', validators=[Optional()])
    submit = SubmitField('Konfirmasi Penerimaan Barang')


class ProcurementCompleteForm(FlaskForm):
    """Form for completing procurement and adding to stock (Step 6)"""
    warehouse_id = SelectField('Gudang Tujuan', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Konfirmasi dan Masukkan ke Stok')


# Legacy form for backward compatibility
class ProcurementForm(FlaskForm):
    """Form for creating procurement requests (Legacy)"""
    supplier_id = SelectField('Supplier', coerce=int, validators=[Optional()])
    item_id = SelectField('Barang', coerce=int, validators=[Optional()])
    quantity = IntegerField('Jumlah', validators=[DataRequired(), NumberRange(min=1)])
    unit_price = FloatField('Harga Satuan', validators=[Optional(), NumberRange(min=0)])
    request_notes = TextAreaField('Alasan Permohonan', validators=[Optional()])
    notes = TextAreaField('Catatan', validators=[Optional()])
    submit = SubmitField('Ajukan Permintaan')
