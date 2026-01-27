"""
Forms for Asset Transfer functionality
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Optional
from wtforms import ValidationError


class DynamicSelectField(SelectField):
    """SelectField that accepts any choice without validation"""
    def pre_validate(self, form):
        # Disable choice validation
        pass


class AssetTransferForm(FlaskForm):
    """Form for transferring assets between units/rooms"""
    # Source - From where
    source_unit_id = DynamicSelectField('Unit Asal', coerce=int, choices=[(0, '')], validators=[DataRequired()])
    source_item_detail_id = DynamicSelectField('Barang yang Dipindahkan', coerce=int, choices=[(0, '')], validators=[DataRequired()])

    # Destination - To where
    target_same_unit = SelectField('Pindah ke Unit yang Sama', choices=[
        ('no', 'Tidak, beda unit'),
        ('yes', 'Ya, unit sama')
    ], validators=[DataRequired()])

    target_unit_id = DynamicSelectField('Unit Tujuan', coerce=int, choices=[(0, '')], validators=[Optional()])
    target_unit_detail_id = DynamicSelectField('Ruangan Tujuan', coerce=int, choices=[(0, '')], validators=[DataRequired()])

    notes = TextAreaField('Catatan', validators=[Optional()])
    submit = SubmitField('Pindahkan Barang')
