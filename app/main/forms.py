# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, FloatField, BooleanField, SubmitField, IntegerField
from wtforms import SelectField, SelectMultipleField
from wtforms import widgets
from wtforms.validators import Required, Length, Optional
from datetime import datetime
import logging


class TransactionForm(FlaskForm):

    date = DateField('date', validators=[Required()], format="%d/%m/%Y")
    amount = FloatField('amount', validators=[Required()])
    type = SelectField('type', validators=[Optional()], coerce=int)
    description = StringField('description', validators=[Optional()])
    category = SelectField('category', validators=[Required()], coerce=int)
    subcategory = SelectField('subcategory', validators=[Required()], coerce=int)
    tag = StringField('tags', validators=[Optional()])
    payee = StringField('payee', validators=[Optional(), Length(1, 128)])
    status = BooleanField('status', validators=[Optional()], default=False)
    submit = SubmitField('Submit')


class AccountForm(FlaskForm):

    name = StringField('account name', validators=[Required(), Length(1, 128)])
    number = IntegerField('account number', validators=[Required()])
    currency = StringField('currency', validators=[Required(), Length(1, 128)])
    balance = FloatField('account balance', validators=[Required()])
    submit = SubmitField('Submit')

class ScheduledTransactionForm(FlaskForm):

    frequency = SelectField('frequency', validators=[Required()], coerce=int)
    interval = IntegerField('interval', validators=[Optional()])
    day = IntegerField('day', validators=[Optional()])
    start = DateField('start', validators=[Required()], format="%d/%m/%Y")
    end = DateField('end', validators=[Optional()], format="%d/%m/%Y")
    active = BooleanField('active', validators=[Optional()], default=True)
    amount = FloatField('amount', validators=[Required()])
    description = StringField('description', validators=[Optional()])
    type = SelectField('type', validators=[Optional()], coerce=int)
    category = SelectField('category', validators=[Optional()], coerce=int)
    subcategory = SelectField('subcategory', validators=[Optional()], coerce=int)
    tag = StringField('tags', validators=[Optional()])
    payee = StringField('payee', validators=[Optional(), Length(1, 128)])
    submit = SubmitField('Submit')


class FilterTransactionForm(FlaskForm):
    date_from = DateField('date from', validators=[Optional()], format="%d/%m/%Y")
    date_to = DateField('date to', validators=[Optional()], format="%d/%m/%Y")
    amount_ge = FloatField('amount ge', validators=[Optional()])
    amount_le = FloatField('amount le', validators=[Optional()])
    type_like = StringField('type like', validators=[Optional()])
    category_like = StringField('category like', validators=[Optional()])
    description_like = StringField('description like', validators=[Optional()])
    tags_like = StringField('tags like', validators=[Optional()])
    #tags_like = SelectMultipleField('tags like', choices= [('1', 'Routine'), ('2', 'Happy'), ('3', 'Smart'), ('4', 'Futures')],
    #                                validators=[Optional()], widget=widgets.ListWidget(prefix_label=True))
    payee_like = StringField('payee like', validators=[Optional()])
    status_equal = StringField('status equal', validators=[Optional()])
    filter = SubmitField('filter')
    show_by = SelectField('show by', choices= [ ('y', 'year'), \
                                                ('m', 'month'), \
                                                ('l3m','last 3 months'), \
                                                ('l12m','last 12 months')] ,
                                              validators=[Optional()])
