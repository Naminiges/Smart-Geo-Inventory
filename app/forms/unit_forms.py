from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class UnitForm(FlaskForm):
    """Form for creating/editing units"""
    name = StringField('Nama Unit/Gedung', validators=[DataRequired(), Length(min=2, max=200)])
    address = TextAreaField('Alamat', validators=[DataRequired(), Length(min=5, max=500)])
    status = SelectField('Status', choices=[
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Maintenance')
    ], validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
