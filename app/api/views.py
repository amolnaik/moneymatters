from flask import jsonify, request, abort, url_for

from app.api import api
from app.models import User, Transaction, Account
from app.decorators import admin_required

from datetime import datetime

@api.route('/')
def get_routes():
    return jsonify({
        'users': url_for('api.get_users', _external=True)
    })

@api.route('/users/')
def get_users():
    return jsonify({
        'users': [user.to_dict() for user in User.query.all()]
    })

@api.route('/user/<string:username>/')
def get_user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return jsonify(user.to_dict())

@api.route('/user/', methods=['POST'])
def add_user():
    try:
        user = User(
            username=request.json.get('username'),
            email=request.json.get('email'),
            password=request.json.get('password')
        ).save()
    except:
        abort(400)
    return jsonify(user.to_dict()), 201

@api.route('/user/<string:username>/accounts')
def get_user_accounts(username):
    user = User.query.filter_by(username=username).first_or_404()
    accounts = user.accounts
    return jsonify({
        'accounts': [account.to_dict() for account in accounts]
    })

@api.route('/user/<string:username>/account/<string:accountname>/')
def get_user_account(username, accountname):
    user = User.query.filter_by(username=username).first()
    account = Account.query.get_or_404(accountname)

    if not user or username != account.holder:
        abort(404)
    return jsonify(account.to_dict())

@api.route('/user/<string:username>/account/', methods=['POST'])
def add_user_account(username):
    user = User.query.filter_by(username=username).first_or_404()
    try:
        account = Account(
            name=request.json.get('name'),
            number=request.json.get('number'),
            holder=user.username,
            currency=request.json.get('currency'),
            balance=request.json.get('balance')
        ).save()
    except:
        abort(400)
    return jsonify(account.to_dict()), 201

@api.route('/user/<string:username>/account/<int:accountid>/transactions')
def get_user_account_transactions(username, accountid):

    account = Account.query.get_or_404(accountid)
    if account.holder != username:
        abort(404)
    return jsonify({
        'transactions': [transaction.to_dict() for transaction in account.transactions]
    })


@api.route('/user/<string:username>/account/<int:accountid>/',
            methods=['POST'])
def add_user_account_transaction(username, accountid):
    user = User.query.filter_by(username=username).first_or_404()
    account = Account.query.get_or_404(accountid)

    try:
        transaction = Transaction(
            date = datetime.strptime(request.json.get('date'), '%Y-%m-%d').date(),
            amount = request.json.get('amount'),
            type = request.json.get('type'),
            description = request.json.get('description'),
            category = request.json.get('category'),
            tag = request.json.get('tag'),
            status = request.json.get('status'),
            accountid = account.id,
            payee=request.json.get('payee')
        ).save()
    except:
        abort(400)

    return jsonify(transaction.to_dict()), 201


@api.route('/account/<int:accountid>/', methods=['PUT'])
def change_account_name(accountid):
    account = Account.query.get_or_404(accountid)
    try:
        account.name = request.json.get('name')
        account.save()
    except:
        abort(400)
    return jsonify(account.to_dict())


@api.route('/transaction/<int:transactionid>/', methods=['PUT'])
def update_transaction_status(transactionid):
    transaction = Transaction.query.get_or_404(transactionid)
    try:
        if request.json.get('status'):
            transaction.status = True
        else:
            transaction.status = False
    except:
        abort(400)
    return jsonify(transaction.to_dict())
