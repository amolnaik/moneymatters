# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, SubmitField
from wtforms import SelectField
from wtforms import widgets
from wtforms.validators import Required, Length, Optional
import logging


class NewCategoryForm(FlaskForm):

    category = StringField('Category', validators=[Required()])
    limit = FloatField('Limit', validators=[Optional()])
    unit = SelectField('Unit', validators=[Optional()], choices=[
                                            ('default', 'currency'),
                                            ('percent', 'percent')])
    apply = BooleanField('Apply', validators=[Optional()], default=False)
    submit = SubmitField('Submit')

class NewSubCategoryForm(FlaskForm):

    subcategory = StringField('SubCategory', validators=[Required()])
    limit = FloatField('Limit', validators=[Optional()])
    unit = SelectField('Unit', validators=[Optional()], choices=[
                                            ('default', 'currency'),
                                            ('percent', 'percent')])
    apply = BooleanField('Apply', validators=[Optional()], default=False)
    submit = SubmitField('Submit')
