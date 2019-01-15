# -*- coding: utf-8 -*-

import random
import forgery_py

from datetime import datetime

from app import db
from app.models import User, Account, Transaction


class FakeGenerator(object):

    def __init__(self):
        # in case the tables haven't been created already
        db.drop_all()
        db.create_all()

    def generate_fake_users(self, count):
        for _ in range(count):
            User(email=forgery_py.internet.email_address(),
                 username=forgery_py.internet.user_name(True),
                 password='correcthorsebatterystaple').save()


    def generate_fake_data(self, count):
        # generation must follow this order, as each builds on the previous
        self.generate_fake_users(count)

    def start(self, count=1):
        self.generate_fake_data(count)
