import re
from datetime import datetime
import numbers
import types

from sqlalchemy.orm import synonym
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for
from flask_login import UserMixin
from sqlalchemy import func

from app import db, login_manager

from sqlalchemy import exc

EMAIL_REGEX = re.compile(r'^\S+@\S+\.\S+$')
USERNAME_REGEX = re.compile(r'^\S+$')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def check_length(attribute, length):
    """Checks the attribute's length."""
    return bool(attribute) and len(attribute) <= length


class BaseModel:

    def __commit(self):

        try:
            db.session.commit()
        except exc.SQLAlchemyError:
            db.session.rollback()

    def delete(self):
        db.session.delete(self)
        self.__commit()

    def save(self):
        db.session.add(self)
        self.__commit()
        return self

    @classmethod
    def from_dict(cls, model_dict):
        return cls(**model_dict).save()


class User(UserMixin, db.Model, BaseModel):

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    _username = db.Column('username', db.String(64), unique=True)
    _email = db.Column('email', db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    accounts = db.relationship('Account', backref='user', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def __repr__(self):
        if self.is_admin:
            return '<Admin {0}>'.format(self.username)
        return '<User {0}>'.format(self.username)

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        is_valid_length = check_length(username, 64)
        if not is_valid_length or not bool(USERNAME_REGEX.match(username)):
            raise ValueError('{} is not a valid username'.format(username))
        self._username = username

    username = synonym('_username', descriptor=username)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        if not check_length(email, 64) or not bool(EMAIL_REGEX.match(email)):
            raise ValueError('{} is not a valid email address'.format(email))
        self._email = email

    email = synonym('_email', descriptor=email)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        if not bool(password):
            raise ValueError('no password given')

        hashed_password = generate_password_hash(password)
        if not check_length(hashed_password, 128):
            raise ValueError('not a valid password, hash is too long')
        self.password_hash = hashed_password

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def seen(self):
        self.last_seen = datetime.utcnow()
        return self.save()

    def to_dict(self):
        return {
            'username': self.username,
            'user_url': url_for(
                'api.get_user', username=self.username, _external=True
            ),
            # 'member_since': self.member_since,
            'last_seen': self.last_seen,
            'accounts': url_for(
                'api.get_user_accounts',
                username=self.username, _external=True
            ),
            'account_count': self.accounts.count()
        }

    def promote_to_admin(self):
        self.is_admin = True
        return self.save()


class Account(db.Model, BaseModel):

    __tablename__ = 'account'

    id = db.Column(db.Integer, primary_key=True)
    _name = db.Column('name', db.String(128))
    _number = db.Column('number', db.Integer)
    holder = db.Column(db.String(64), db.ForeignKey('user.username'))
    _currency = db.Column('currency', db.String(64))
    _balance = db.Column('balance', db.Float())
    _created_on = db.Column('created', db.DateTime, default=datetime.now().date())

    # one account can have many transactions
    transactions = db.relationship('Transaction', backref='account',
                                    lazy='dynamic')

    # one account can have many scheduled transactions
    scheduled_transactions = db.relationship('ScheduledTransaction',
                                             backref='account', lazy='dynamic')

    # one account can have many db transactions
    dbtransactions = db.relationship('DbTransaction', backref='account', lazy='dynamic')

    # one account can have many category types
    #category_types = db.relationship('CategoryType', backref='account',
    #                             lazy='dynamic')

    # one account can have many category types
    #subcategory_types = db.relationship('SubCategoryType', backref='account',
    #                                lazy='dynamic')

    def __init__(self, name=None, number=None, currency=None,
        balance=None, holder=None):

        self.name = name
        self.number = number
        self.currency = currency
        self.balance = balance
        self.holder = holder
        self.created_on = datetime.now().date()

    def __repr__(self):
        return '<Account: {0}>'.format(self.name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if not check_length(name, 128):
            raise ValueError('{} is not a valid name'.format(name))
        self._name = name

    name = synonym('_name', descriptor=name)

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, number):
        if not isinstance(number, int):
            raise ValueError('{} is not a valid number'.format(number))
        self._number = number

    number = synonym('_number', descriptor=number)

    @property
    def currency(self):
        return self._currency

    @currency.setter
    def currency(self, currency):
        if not check_length(currency, 64):
            raise ValueError('{} is not a valid currency'.format(currency))
        self._currency = currency

    currency = synonym('_currency', descriptor=currency)

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, balance):
        if not isinstance(balance, numbers.Number):
            raise ValueError('{} is not a valid balance'.format(balance))
        self._balance = balance

    balance = synonym('_balance', descriptor=balance)

    def to_dict(self):
        return {
            'name': self.name,
            'number': self.number,
            'currency': self.currency,
            'balance': self.balance,
            'holder': self.holder,
            'created_on': self.created_on,
        }

    # additional operations/methods to follow...
    @property
    def total_transactions_count(self):
        return self.transactions.count()

    @property
    def completed_transactions_count(self):
        return self.transactions.filter_by(status=True).count()

    @property
    def open_transactions_count(self):
        return self.transactions.filter_by(status=False).count()


    def closing_balance(self, id):
        if self.transactions.order_by(None).count() == 0:
            return self._balance
        else:
            #return db.session.query(func.sum(Transaction.amount)).scalar()
            cb = db.session.query(func.sum(Transaction.amount)) \
                    .filter(Transaction.status == True, Transaction.account_id == id).scalar()

            if cb is None:
                return self._balance
            else:
                return cb + self._balance


class TransactionType(db.Model, BaseModel):

    __tablename__ = 'transactiontype'

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    ttype = db.Column('ttype', db.String(128))


class CategoryType(db.Model, BaseModel):

    __tablename__ = 'categorytype'

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    cattype = db.Column('cattype', db.String(128))


class SubCategoryType(db.Model, BaseModel):

    __tablename__ = 'subcategorytype'

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    subcattype = db.Column('subcattype', db.String(128))


class ScheduledTransaction(db.Model, BaseModel):

    __tablename__ = 'scheduled_transaction'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))

    _frequency = db.Column('frequency', db.String(128))
    _interval = db.Column('interval', db.Integer)
    _day = db.Column('day', db.Integer)

    _start = db.Column('start', db.DateTime, default=datetime.now().date())
    _end = db.Column('end', db.DateTime, default=datetime.now().date())

    created = db.Column('created', db.DateTime, default=datetime.now().date())
    _active = db.Column('active', db.Boolean)
    _last_approved = db.Column('last_approved', db.DateTime, default=datetime.now().date())

    #transaction fields as template
    _amount = db.Column('amount', db.Float)
    _description = db.Column('description', db.String(128))
    _type = db.Column('type', db.String(128))
    _category = db.Column('category', db.String(128))
    _subcategory = db.Column('subcategory', db.String(128))
    _tag = db.Column('tag', db.String(64))
    _payee = db.Column('payee', db.String(128))

    def __init__(self, accountid, frequency, interval, day, start, end,
                active, approved, amount, description,
                type, category, subcategory, tag, payee):

            self.account_id = accountid
            self.frequency = frequency
            self.interval = interval
            self.day = day
            self.start = start
            self.end = end
            self.active = active
            self.last_approved = approved
            self.amount = amount
            self.description = description
            self.type = type
            self.category = category
            self.subcategory = subcategory
            self.tag = tag
            self.payee = payee

    #type = db.relationship('TransactionType', foreign_keys=type_id)

    def __repr__(self):
        return '<Scheduled Transaction: Start {0}, End {1}, frequency {2}, Interval {3}>, Day {4}, Amount {5}' \
                .format(self.start, self.end, self.frequency, self.interval, self.day, self.amount)

    @property
    def created(self):
        return datetime.today()

    created = synonym('_created', descriptor=created)

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        if not check_length(frequency, 128):
            self._frequency = 'monthly'
        else:
            self._frequency = frequency

    frequency = synonym('_frequency', descriptor=frequency)

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, interval):
        if not isinstance(interval, numbers.Number):
            self._interval = 1
        else:
            self._interval = interval

    interval = synonym('_interval', descriptor=interval)

    @property
    def day(self):
        return self._day

    @day.setter
    def day(self, day):
        if not isinstance(day, numbers.Number):
            self._day = 16
        else:
            self._day = day

    day = synonym('_day', descriptor=day)

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start):
        if not (datetime(1900, 1, 1).date() <= start <= datetime(2100, 12, 31).date()):
            self._start = datetime.today().date()
        else:
            self._start = start

    start = synonym('_start', descriptor=start)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        if not (datetime(1900, 1, 1).date() <= end <= datetime(2100, 12, 31).date()):
            self._end = datetime.today().date()
        else:
            self._end = end

    end = synonym('_end', descriptor=end)

    @property
    def active(self):
        return bool(self._active)

    @active.setter
    def active(self, active):
        if not (type(active) == types.BooleanType):
            self._active = False
        else:
            self._active = active

    active = synonym('_active', descriptor=active)

    @property
    def last_approved(self):
        return self._last_approved

    @last_approved.setter
    def last_approved(self, last_approved):
        if not (datetime(1900, 1, 1).date() <= last_approved <= datetime(2100, 12, 31).date()):
            raise ValueError('Date out of range')
        self._last_approved = last_approved

    last_approved = synonym('_last_approved', descriptor=last_approved)

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, amount):
        if not isinstance(amount, numbers.Number):
            self._amount = 0.00
        else:
            self._amount = amount

    amount = synonym('_amount', descriptor=amount)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        if not check_length(type, 128):
            self._type = 'not provided'
        else:
            self._type = type

    type = synonym('_type', descriptor=type)

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        if not check_length(description, 128):
            self._description = 'not provided'
        else:
            self._description = description

    description = synonym('_description', descriptor=description)

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, category):
        if not check_length(category, 128):
            self._category = 'not provided'
        else:
            self._category = category

    category = synonym('_category', descriptor=category)

    @property
    def subcategory(self):
        return self._subcategory

    @subcategory.setter
    def subcategory(self, subcategory):
        if not check_length(subcategory, 128):
            self._subcategory = 'not provided'
        else:
            self._subcategory = subcategory

    subcategory = synonym('_subcategory', descriptor=subcategory)

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        if not check_length(tag, 64):
            self._tag = 'Todo'
        else:
            self._tag = tag

    tag = synonym('_tag', descriptor=tag)

    @property
    def payee(self):
        return self._payee

    @payee.setter
    def payee(self, payee):
        if not check_length(payee, 128):
            self._payee = 'not provided'
        else:
            self._payee = payee

    payee = synonym('_payee', descriptor=payee)

    def to_dict(self):
        return {
            'id': self.id,
            'created_on': self.created,
            'frequency': self.frequency,
            'interval': self.interval,
            'day': self.day,
            'start': self.start,
            'end': self.end,
            'approved': self.last_approved,
            'amount': self.amount,
            'category': self.category,
            'subcategory': self.subcategory,
            'payee': self.payee,
            'description': self.description,
            'active': self.active,
        }


class Transaction(db.Model, BaseModel):

    __tablename__ = 'transaction'
    __table_args__ = (UniqueConstraint('date', 'amount', 'type', 'description', 'category', 'subcategory', name='unique_transactions'),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))

    _date = db.Column('date', db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    _amount = db.Column('amount', db.Float, nullable=False)
    _type = db.Column('type', db.String(128))
    _description = db.Column('description', db.String(128), nullable=True)
    _category = db.Column('category', db.String(128), nullable=True)
    _subcategory = db.Column('subcategory', db.String(128), nullable=True)
    _tag = db.Column('tag', db.String(64))
    _status = db.Column('status', db.Boolean)
    _payee = db.Column('payee', db.String(128))

    def __init__(self, accountid, date=None, amount=None, type=None,
        description=None, category=None, subcategory=None,
        tag=None, status=None, payee=None):

        self.account_id = accountid
        self.date = date
        self.amount = amount
        self.type = type
        self.description = description
        self.category = category
        self.subcategory = subcategory
        self.tag = tag
        self.status = status
        self.payee = payee


    def __repr__(self):
        return '<Transaction: Date {0}, Amount {1}, Description {2}, Status {3}>'.format(self.date, self.amount, self.description, self.status)

    @property
    def date(self):
        return self._date #.date()

    @date.setter
    def date(self, date):
        if not (datetime(1900, 1, 1).date() <= date <= datetime(2100, 12, 31).date()):
            self._date = datetime.today().date()
        else:
            self._date = date

    date = synonym('_date', descriptor=date)

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, amount):
        if not isinstance(amount, numbers.Number):
            self._amount = 0.00
        else:
            self._amount = amount

    amount = synonym('_amount', descriptor=amount)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        if not check_length(type, 128):
            self._type = 'not provided'
        else:
            self._type = type

    type = synonym('_type', descriptor=type)

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        if not check_length(description, 128):
            self._description = 'not provided'
        else:
            self._description = description

    description = synonym('_description', descriptor=description)

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, category):
        if not check_length(category, 128):
            self._category = 'not provided'
        else:
            self._category = category

    category = synonym('_category', descriptor=category)

    @property
    def subcategory(self):
        return self._subcategory

    @subcategory.setter
    def subcategory(self, subcategory):
        if not check_length(subcategory, 128):
            self._subcategory = 'not provided'
        else:
            self._subcategory = subcategory

    subcategory = synonym('_subcategory', descriptor=subcategory)

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        if not check_length(tag, 64):
            self._tag = 'not provided'
        else:
            self._tag = tag

    tag = synonym('_tag', descriptor=tag)

    @property
    def status(self):
        return bool(self._status)

    @status.setter
    def status(self, status):
        if not (isinstance(status, bool)):
            self._status = False
        else:
            self._status = status

    status = synonym('_status', descriptor=status)

    @property
    def payee(self):
        return self._payee

    @payee.setter
    def payee(self, payee):
        if not check_length(payee, 128):
            self._payee = 'not provided'
        else:
            self._payee = payee

    payee = synonym('_payee', descriptor=payee)

    def to_dict(self):
        return {
            'tid': self.id,
            'date': self.date,
            'amount': self.amount,
            'type': self.type,
            'description': self.description,
            'category': self.category,
            'subcategory': self.subcategory,
            'tag': self.tag,
            'status': self.status,
            'payee': self._payee,
        }


class CategorySettings(db.Model, BaseModel):

    __tablename__ = 'category_settings'
    __table_args__ = (UniqueConstraint('account_id','category', name='unique_categoryname'),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    _category = db.Column('category', db.String(128), nullable=True)
    _limit = db.Column('limit', db.Float, nullable=False)
    _last_month = db.Column('last_month', db.Float, default=0)
    _avg_month = db.Column('avg_month', db.Float, default=0)
    _unit = db.Column('unit', db.String(128), nullable=True)
    _apply = db.Column('apply', db.Boolean)

    def __init__(self, accountid, category=None, limit=None,
                unit=None,apply=None):

        self.account_id = accountid
        self.category = category
        self.limit = limit
        self.unit = unit
        self.apply=apply

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, category):
        if not check_length(category, 128):
            self._category = 'not provided'
        else:
            self._category = category

    category = synonym('_category', descriptor=category)

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit):
        if not isinstance(limit, numbers.Number):
            self._limit = 123
        else:
            self._limit = limit

    limit = synonym('_limit', descriptor=limit)

    @property
    def last_month(self):
        return self._last_month

    @last_month.setter
    def last_month(self, last_month):
        if not isinstance(last_month, numbers.Number):
            self._last_month = 0.00
        else:
            self._last_month = last_month

    last_month = synonym('_last_month', descriptor=last_month)

    @property
    def avg_month(self):
        return self._avg_month

    @avg_month.setter
    def avg_month(self, avg_month):
        if not isinstance(avg_month, numbers.Number):
            self._avg_month= 0.00
        else:
            self._avg_month = avg_month

    avg_month = synonym('_avg_month', descriptor=avg_month)

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, unit):
        if not check_length(unit, 128):
            self._unit = 'not provided'
        else:
            self._unit = unit

    unit = synonym('_unit', descriptor=unit)

    @property
    def apply(self):
        return bool(self._apply)

    @apply.setter
    def apply(self, apply):
        if not (isinstance(apply, bool)):
            self._apply = False
        else:
            self._apply = apply

    apply = synonym('_apply', descriptor=apply)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'category': self.category,
            'limit': self.limit,
            'last_month': self.last_month,
            'avg_month': self.avg_month,
            'unit': self.unit,
            'apply': self.apply
        }


class SubCategorySettings(db.Model, BaseModel):

    __tablename__ = 'subcategory_settings'
    __table_args__ = (UniqueConstraint('account_id','subcategory', name='unique_subcategoryname'),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    _subcategory = db.Column('subcategory', db.String(128), nullable=True)
    _limit = db.Column('limit', db.Float, nullable=False)
    _last_month = db.Column('last_month', db.Float, default=0)
    _avg_month = db.Column('avg_month', db.Float, default=0)
    _unit = db.Column('unit', db.String(128), nullable=True)
    _apply = db.Column('apply', db.Boolean)

    def __init__(self, accountid, subcategory=None, limit=None,
                unit=None,apply=None):

        self.account_id = accountid
        self.subcategory = subcategory
        self.limit = limit
        self.unit = unit
        self.apply=apply

    @property
    def subcategory(self):
        return self._subcategory

    @subcategory.setter
    def subcategory(self, subcategory):
        if not check_length(subcategory, 128):
            self._subcategory = 'not provided'
        else:
            self._subcategory = subcategory

    subcategory = synonym('_subcategory', descriptor=subcategory)

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit):
        if not isinstance(limit, numbers.Number):
            self._limit = 123
        else:
            self._limit = limit

    limit = synonym('_limit', descriptor=limit)

    @property
    def last_month(self):
        return self._last_month

    @last_month.setter
    def last_month(self, last_month):
        if not isinstance(last_month, numbers.Number):
            self._last_month = 0.00
        else:
            self._last_month = last_month

    last_month = synonym('_last_month', descriptor=last_month)

    @property
    def avg_month(self):
        return self._avg_month

    @avg_month.setter
    def avg_month(self, avg_month):
        if not isinstance(avg_month, numbers.Number):
            self._avg_month= 0.00
        else:
            self._avg_month = avg_month

    avg_month = synonym('_avg_month', descriptor=avg_month)

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, unit):
        if not check_length(unit, 128):
            self._unit = 'not provided'
        else:
            self._unit = unit

    unit = synonym('_unit', descriptor=unit)

    @property
    def apply(self):
        return bool(self._apply)

    @apply.setter
    def apply(self, apply):
        if not (isinstance(apply, bool)):
            self._apply = False
        else:
            self._apply = apply

    apply = synonym('_apply', descriptor=apply)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'subcategory': self.subcategory,
            'limit': self.limit,
            'last_month': self.last_month,
            'avg_month': self.avg_month,
            'unit': self.unit,
            'apply': self.apply
        }


class DbTransaction(db.Model, BaseModel):

    __tablename__ = 'dbtransaction'
    #__table_args__ = (UniqueConstraint('account_id','date', 'amount', 'type', 'description', 'beneficiary', name='unique_dbtransactions'),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    _date = db.Column('date', db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    _amount = db.Column('amount', db.Float, nullable=False)
    _type = db.Column('type', db.String(128))
    _description = db.Column('description', db.String(128), nullable=True)
    _beneficiary = db.Column('beneficiary', db.String(128), nullable=True)

    def __init__(self, accountid, date=None, amount=None, type=None, description=None, beneficiary=None):

        self.account_id = accountid
        self.date = date
        self.amount = amount
        self.type = type
        self.description = description
        self.beneficiary = beneficiary

    def __repr__(self):
        return '<Transaction: Date {0}, Amount {1}, Description {2}, beneficiary {3}>'.format(self.date, self.amount, self.description, self.beneficiary)

    @property
    def date(self):
        return self._date #.date()

    @date.setter
    def date(self, date):
        if not (datetime(1900, 1, 1).date() <= date <= datetime(2100, 12, 31).date()):
            self._date = datetime.today().date()
        else:
            self._date = date

    date = synonym('_date', descriptor=date)

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, amount):
        if not isinstance(amount, numbers.Number):
            self._amount = 0.00
        else:
            self._amount = amount

    amount = synonym('_amount', descriptor=amount)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        if not check_length(type, 128):
            self._type = 'not provided'
        else:
            self._type = type

    type = synonym('_type', descriptor=type)

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        if not check_length(description, 128):
            self._description = ''
        else:
            self._description = description

    description = synonym('_description', descriptor=description)

    @property
    def beneficiary(self):
        return self._beneficiary

    @beneficiary.setter
    def beneficiary(self, beneficiary):
        if not check_length(beneficiary, 128):
            self._beneficiary = ''
        else:
            self._beneficiary = beneficiary

    beneficiary = synonym('_beneficiary', descriptor=beneficiary)


    def to_dict(self):
        return {
            'tid': self.id,
            'accountid' : self.account_id,
            'date': self.date,
            'amount': self.amount,
            'type': self.type,
            'description': self.description,
            'beneficiary': self.beneficiary
        }
