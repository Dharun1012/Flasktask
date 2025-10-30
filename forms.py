from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ProductForm(FlaskForm):
    product_id = StringField('Product ID', validators=[DataRequired(), Length(max=20)])
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('Laptop', 'Laptop'),
        ('Phone', 'Phone'),
        ('Tablet', 'Tablet'),
        ('Accessories', 'Accessories'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])

class LocationForm(FlaskForm):
    location_id = StringField('Location ID', validators=[DataRequired(), Length(max=20)])
    name = StringField('Location Name', validators=[DataRequired(), Length(max=100)])
    address = StringField('Address', validators=[Optional(), Length(max=200)])

class MovementForm(FlaskForm):
    product_id = SelectField('Product', validators=[DataRequired()])
    from_location = SelectField('From Location', choices=[('', 'Select...')], validators=[Optional()])
    to_location = SelectField('To Location', choices=[('', 'Select...')], validators=[Optional()])
    qty = IntegerField('Quantity', validators=[DataRequired()])
    notes = StringField('Notes', validators=[Optional(), Length(max=200)])