from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class UnitForm(FlaskForm):
    """Form for creating/editing units"""
    name = StringField('Nama Unit', validators=[DataRequired(), Length(min=2, max=200)])
    address = TextAreaField('Alamat', validators=[Optional(), Length(max=500)])
    latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
