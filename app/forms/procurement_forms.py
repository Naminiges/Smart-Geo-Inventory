from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


class ProcurementRequestForm(FlaskForm):
    """Form for warehouse staff to create procurement requests with multiple items (Step 1-2)"""
    request_notes = TextAreaField('Alasan Permohonan', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Ajukan Permohonan')


class ProcurementApprovalForm(FlaskForm):
    """Form for admin to approve and select supplier (Step 3)"""
    supplier_id = SelectField('Pilih Supplier', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Catatan Admin', validators=[Optional()])
    submit = SubmitField('Setujui dan Pilih Supplier')


class GoodsReceiptForm(FlaskForm):
    """Form for recording goods receipt with serial numbers (Step 4-5)"""
    receipt_number = StringField('Nomor Tanda Terima', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField('Konfirmasi Penerimaan Barang')


class ProcurementCompleteForm(FlaskForm):
    """Form for completing procurement and adding to stock (Step 6)"""
    warehouse_id = SelectField('Gudang Tujuan', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Konfirmasi dan Masukkan ke Stok')
