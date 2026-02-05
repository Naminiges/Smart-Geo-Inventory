from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError


def validate_room_name_format(form, field):
    """Validate that room_name starts with the correct building code"""
    from app.models import Building

    room_name = field.data.strip() if field.data else ""

    if not room_name:
        return

    # Extract building code from room name (first part)
    parts = room_name.split()
    if len(parts) < 2:
        raise ValidationError('Format nama ruangan tidak valid. Gunakan kode gedung yang sesuai.')

    building_code = parts[0]

    # Validate that the building code in room_name matches the selected building
    building_id = form.building_id.data
    if building_id:
        building = Building.query.get(building_id)
        if building and building.code != building_code:
            raise ValidationError('Format nama ruangan tidak valid. Gunakan kode gedung yang sesuai.')


def validate_floor_number(form, field):
    """Validate that floor number does not exceed building's floor count"""
    floor_value = field.data.strip() if field.data else ""

    # First validate that input is a number
    try:
        floor_num = int(floor_value)
    except ValueError:
        raise ValidationError('Nomor lantai harus berupa angka.')

    # Floor number must be at least 1
    if floor_num < 1:
        raise ValidationError('Nomor lantai tidak boleh kurang dari 1.')

    # Get max_floor_count from form (set by route handler)
    building_floor_counts = getattr(form, 'building_floor_counts', None)
    if building_floor_counts:
        # Get the selected building_id (for edit mode)
        building_id = form.building_id.data
        max_floor = building_floor_counts.get(building_id)
    else:
        # Fall back to max_floor_count (for create mode)
        max_floor = getattr(form, 'max_floor_count', None)

    # Check if floor number exceeds building's floor count
    if max_floor is not None and floor_num > max_floor:
        raise ValidationError(f'Nomor lantai tidak boleh melebihi jumlah lantai gedung ({max_floor}).')


class WarehouseForm(FlaskForm):
    """Form for creating/editing warehouses"""
    name = StringField('Nama Gudang', validators=[DataRequired(), Length(min=2, max=200)])
    address = TextAreaField('Alamat', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
    submit = SubmitField('Simpan')


class BuildingForm(FlaskForm):
    """Form for creating/editing buildings"""
    code = StringField('Kode Gedung', validators=[DataRequired(), Length(min=3, max=50)])
    name = StringField('Nama Gedung', validators=[DataRequired(), Length(min=2, max=200)])
    address = TextAreaField('Alamat', validators=[DataRequired()])
    floor_count = StringField('Jumlah Lantai', validators=[Optional(), Length(max=50)])
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
    building_id = SelectField('Gedung', coerce=int, validators=[DataRequired()])
    room_name = StringField('Nama Ruangan', validators=[
        DataRequired(),
        Length(min=2, max=200),
        validate_room_name_format
    ])
    floor = StringField('Lantai', validators=[Optional(), Length(max=50), validate_floor_number])
    description = TextAreaField('Deskripsi', validators=[Optional()])
    submit = SubmitField('Simpan')
