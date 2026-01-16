from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class StockForm(FlaskForm):
    """Form for managing stock levels"""
    item_id = SelectField('Barang', coerce=int, validators=[DataRequired()])
    warehouse_id = SelectField('Gudang', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Jumlah', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Simpan')


class StockTransactionForm(FlaskForm):
    """Form for recording stock transactions"""
    item_id = SelectField('Barang', coerce=int, validators=[DataRequired()])
    warehouse_id = SelectField('Gudang', coerce=int, validators=[DataRequired()])
    transaction_type = SelectField('Tipe Transaksi', choices=[
        ('IN', 'Masuk'),
        ('OUT', 'Keluar')
    ], validators=[DataRequired()])
    quantity = IntegerField('Jumlah', validators=[DataRequired(), NumberRange(min=1)])
    note = TextAreaField('Catatan', validators=[Optional()])
    submit = SubmitField('Simpan')
