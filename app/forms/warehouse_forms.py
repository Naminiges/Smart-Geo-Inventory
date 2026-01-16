from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class WarehouseForm(FlaskForm):
    """Form for creating/editing warehouses"""
    name = StringField('Nama Gudang', validators=[DataRequired(), Length(min=2, max=200)])
    address = TextAreaField('Alamat', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
    submit = SubmitField('Simpan')


class UnitForm(FlaskForm):
    """Form for creating/editing units"""
    name = StringField('Nama Unit/Gedung', validators=[DataRequired(), Length(min=2, max=200)])
    address = TextAreaField('Alamat', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
    submit = SubmitField('Simpan')


class UnitDetailForm(FlaskForm):
    """Form for creating/editing unit details"""
    unit_id = SelectField('Unit', coerce=int, validators=[DataRequired()])
    room_name = StringField('Nama Ruangan', validators=[DataRequired(), Length(min=2, max=200)])
    floor = StringField('Lantai', validators=[Optional(), Length(max=50)])
    description = TextAreaField('Deskripsi', validators=[Optional()])
    submit = SubmitField('Simpan')
