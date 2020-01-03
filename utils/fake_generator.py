# -*- coding: utf-8 -*-

import random
import forgery_py

from datetime import datetime, timedelta

from app import db
from app.models import User, Account, Transaction, TransactionType


class FakeGenerator(object):

    def __init__(self):
        # in case the tables haven't been created already
        #db.drop_all()
        #db.create_all()
        pass

    def generate_fake_users(self, count):

        for _ in range(count):
            fake_user = forgery_py.internet.user_name(True)

            User(email=forgery_py.internet.email_address(),
                 username=fake_user,
                 password='correcthorsebatterystaple').save()

            fake_account = Account(name=forgery_py.name.company_name(),
                 number=1234,
                 currency=forgery_py.currency.code(),
                 balance=2000,
                 holder=fake_user
                 ).save()

        fake_date = datetime(2018,1,1).date()
        fake_amount = -100
        ttype_name = TransactionType.query.filter_by(id=1).first().ttype
        for _ in range(24):
            fake_date = fake_date + timedelta(days=15)
            fake_amount = fake_amount - 10
            Transaction(date=fake_date,
                          amount=fake_amount,
                          type=ttype_name,
                          description='fake groceries',
                          category='Household',
                          subcategory='Groceries',
                          tag='Routine',
                          status=True,
                          accountid=fake_account.id,
                          payee='').save()



    def generate_fake_data(self, count):
        # generation must follow this order, as each builds on the previous
        self.generate_fake_users(count)

    def start(self, count=1):
        self.generate_fake_data(count)
