# -*- coding: utf-8 -*-

import os
import random
import string

BASEDIR = os.path.abspath(os.path.dirname(__file__))


def create_sqlite_uri(db_name):
    return 'sqlite:///' + os.path.join(BASEDIR, db_name)

def create_mysql_uri(rds_username, rds_password, rds_hostname, rds_port, rds_db_name):
    return 'mysql://' + rds_username + ':' + rds_password + \
           '@' + rds_hostname + ':' + rds_port + '/' + rds_db_name

class Config(object):
    #SECRET_KEY = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
    SECRET_KEY = 'secret' # gunicorn workers fail to start app without it
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    #SQLALCHEMY_DATABASE_URI = 'mysql://mm_admin:mm_8_9435@localhost/money_db'
    SQLALCHEMY_DATABASE_URI = create_sqlite_uri('money-dev.db')
    UPLOAD_FOLDER = os.path.dirname(__file__) + '/upload'
    SESSION_TYPE = 'filesystem'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = create_sqlite_uri('money-test.db')
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    #if os.environ['BASE']:
    #    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.environ['BASE'], 'money.db')
    #else:
    SQLALCHEMY_DATABASE_URI = create_sqlite_uri('/data/money.db')

    #print(SQLALCHEMY_DATABASE_URI)
    #SQLALCHEMY_DATABASE_URI = 'mysql://mm_admin:mm_8_9435@localhost/money_db'
    #SQLALCHEMY_DATABASE_URI = create_mysql_uri(os.environ['RDS_USERNAME'],
    #                                          os.environ['RDS_PASSWORD'],
    #                                          os.environ['RDS_HOSTNAME'],
    #                                          os.environ['RDS_PORT'],
    #                                          os.environ['RDS_DB_NAME'])
    #print SQLALCHEMY_DATABASE_URI
    UPLOAD_FOLDER = os.path.dirname(__file__) + '/upload'
    #SESSION_TYPE = 'filesystem'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
