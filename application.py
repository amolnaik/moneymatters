# -*- coding: utf-8 -*-
from app import create_app
from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.serving import run_simple
import logging
from logging.handlers import RotatingFileHandler
from app import db


app = create_app('default')


@app.cli.command()
def test():
    """Runs the unit tests."""
    import unittest
    import sys
    tests = unittest.TestLoader().discover('tests')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.errors or result.failures:
        sys.exit(1)

@app.cli.command()
def fill_db():
    """Fills database with random data.
    By default 10 users, 40 todolists and 160 todos.
    WARNING: will delete existing data. For testing purposes only.
    """
    from utils.fake_generator import FakeGenerator
    FakeGenerator().start()  # side effect: deletes existing data

# application dispatcher
if __name__ == '__main__':
    handler = RotatingFileHandler('moneymatters.log', maxBytes=10000, backupCount=1)

    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)

    app.run(debug=True, use_reloader=False)
