# Moneymatters

[![License][license-image]][license-url]

Moneymatters is a simple and smart way to manage your money. Written in Python, the repository gives you complete flexibility to build your money management App with local storage. Dashboard and tabular views are built-in.

---
CSS | [Skeleton](http://getskeleton.com/)
JS  | [jQuery](https://jquery.com/)
Charts | [Highcharts](https://highcharts.com/)
Analytics | [Pandas](https://pandas.pydata.org/)


## Explore
Try it out! (Works with Python 2, Python 3 is in progress)

### Local
You can simple run:
    flask run

And the application will run on http://localhost:5000/

(For deployment, it can be served using  [nginx](https://nginx.org/) instead of just running `flask run`.)

### Build and develope further
If you prefer to run it directly on your local machine, I suggest using
[virtualenv](https://virtualenv.pypa.io/en/stable/)

    pip install -r requirements.txt
    export FLASK_APP=application.py
    flask run

Now you can browse the API:
http://localhost:5000/

Create a user by signing up and start using the App after you create your account.

## Extensions
Flask offers many extension which are used in the code, e.g.

Usage               | Flask-Extension
------------------- | -----------------------
Model & ORM         | [Flask-SQLAlchemy](http://flask-sqlalchemy.pocoo.org/latest/)
Migration           | [Flaks-Migrate](http://flask-migrate.readthedocs.io/en/latest/)
Forms               | [Flask-WTF](https://flask-wtf.readthedocs.org/en/latest/)
Login               | [Flask-Login](https://flask-login.readthedocs.org/en/latest/)
Testing             | [Flask-Testing](https://pythonhosted.org/Flask-Testing/)
