from flask import render_template, redirect, request, url_for, flash
from flask_login import current_user, login_required
from collections import defaultdict
from time import strftime
import sys
import os
from werkzeug.utils import secure_filename
from app.main import main
from app.main.forms import AccountForm, TransactionForm, ScheduledTransactionForm, FilterTransactionForm

from app.models import Account, Transaction, ScheduledTransaction, CategorySettings
from app.models import TransactionType, CategoryType, SubCategoryType
from app.models import CategorySettings, SubCategorySettings
from app.models import DbTransaction
from sqlalchemy.exc import SQLAlchemyError


import json
import pandas as pd
import numpy as np
from app import db
from flask import current_app
from datetime import datetime
from datetime import timedelta
from app.utils import run_scheduler
from app.utils import reformat
from sqlalchemy import exc

import csv

reload(sys)
sys.setdefaultencoding('utf8')
ALLOWED_EXTENSIONS = set(['csv', 'json', 'dbcsv'])

@main.route('/')
def index():

    if current_user.is_authenticated:
        return redirect(url_for('main.account_overview'))

    return render_template('index.html')

@main.route('/accounts/', methods=['GET'])
@login_required
def account_overview():
    # current user's accounts as json
    account_data = []
    for account in current_user.accounts:
        account_data.append({'account_id' : account.id,
                             'account_name': account.name,
                             'opening_balance': account.balance,
                             'total_transactions': account.total_transactions_count,
                             'pending_transactions':
                              (account.total_transactions_count - account.completed_transactions_count),
                             'closing_balance': account.closing_balance(account.id),
                             'account_currency':account.currency,
                             'account_view': str("view")})


    return render_template('overview.html', account_data=json.dumps(account_data))

@main.route('/accounts/new/', methods=['GET','POST'])
@login_required
def new_account():

    form = AccountForm()

    if request.method == "POST":
        if form.validate() and form.submit.data:
            current_app.logger.info('Creating new account for %s', _get_user())
            new_account = Account(name=form.name.data,
                              number=form.number.data,
                              currency=form.currency.data,
                              balance=form.balance.data,
                              holder=_get_user())
            new_account.save()
            # create account settings from default categories
            categories = [c.cattype for c in CategoryType.query.all()]

            for c in categories:
                set = CategorySettings(accountid=new_account.id,
                category=c,
                limit=100,
                unit=new_account.currency)
                # set default category limits
                set.save()
            return redirect(url_for('main.account_overview'))

    return render_template('new_account.html', form=form)

@main.route('/accounts/edit/<int:id>/', methods=['GET','POST'])
@login_required
def edit_account(id):

    account = Account.query.filter_by(id=id).first_or_404()

    if request.method == "POST":
        current_app.logger.info('Received request to edit data')
        data = json.loads(request.data)

        if account.name != data.get('account_name'):
            account.name = data.get('account_name')
            db.session.commit()

        if account.currency != data.get('account_currency'):
            account.currency = data.get('account_currency')
            db.session.commit()

        if account.balance != data.get('opening_balance'):
            account.balance = data.get('opening_balance')
            db.session.commit()

    return redirect(url_for("main.account_overview"))

@main.route('/accounts/<string:name>/', methods=['GET', 'POST'])
@login_required
def account(name):

    account = Account.query.filter_by(name=name).first_or_404()

    # get transaction types
    ttypechoices = [(ttp.id, ttp.ttype) for ttp
    in TransactionType.query.order_by(TransactionType.ttype).all()]


    catchoices = [(cat.id, cat.category) for cat
    in CategorySettings.query.filter_by(account_id = account.id).all()]

    # user has not yet created any settings for categories
    if catchoices == []:
        catchoices = [(cat.id, cat.cattype) for cat
        in CategoryType.query.order_by(CategoryType.cattype).all()]

    subcatchoices = [(subcat.id, subcat.subcategory) for subcat
    in SubCategorySettings.query.filter_by(account_id = account.id).all()]

    # user has not yet created any settings for subcategories
    if subcatchoices == []:
        subcatchoices = [(subcat.id, subcat.subcattype) for subcat
        in SubCategoryType.query.order_by(SubCategoryType.subcattype).all()]


    form = TransactionForm()
    form.type.choices = ttypechoices
    form.category.choices = catchoices
    form.subcategory.choices = subcatchoices

    if form.validate_on_submit() and form.submit.data:
        current_app.logger.info('Creating new transaction')
        try:
            ttype_name = TransactionType.query.filter_by(id=form.type.data).first().ttype

            cattype_name = [cattype for catid, cattype in catchoices
                                if catid == form.category.data][0]

            subcattype_name = [subcattype for subcatid, subcattype in subcatchoices
                                if subcatid == form.subcategory.data][0]

            new_transaction = Transaction(date=form.date.data,
                                      amount=form.amount.data,
                                      type=ttype_name,
                                      description=form.description.data,
                                      category=cattype_name,
                                      subcategory=subcattype_name,
                                      tag=form.tag.data,
                                      status=form.status.data,
                                      accountid=account.id,
                                      payee=form.payee.data)
            new_transaction.save()

            return redirect(url_for("main.account", name=name)) #check
        except:
            current_app.logger.info('Transaction form could not be completed')
    else:
        current_app.logger.info('Transaction form could not be validated')


    return render_template('transaction_overview.html',
                            account=account, form=form)

@main.route('/accounts/<string:name>/scheduled_this_month/', methods=['GET'])
@login_required
def get_scheduled_transactions(name):

    account = Account.query.filter_by(name=name).first_or_404()

    # show schedueld transactions
    today = datetime.today()
    schedueld_transactions = [st for st in account.scheduled_transactions]

    # ToDo: the scheduler runs the same rule again if the user logs
    # in multiple times in a day
    tt_ = defaultdict(list)

    s = run_scheduler.RunScheduler()
    for st in schedueld_transactions:

        if (st is not None):
            sd = s.get_template_transactions_with_start_end(st.day, st.frequency,
                                                        st.interval, st.start, st.end)
            try:
                if sd:
                    if st.active:
                        tt_['stid'].append(st.id)
                        tt_['date'].append(sd[0])
                        tt_['amount'].append(st.amount)
                        tt_['type'].append('electronic')
                        tt_['description'].append(st.description)
                        tt_['category'].append(st.category)
                        tt_['subcategory'].append(st.subcategory)
                        tt_['status'].append(False)
                        tt_['accountid'].append(account.id)
                        tt_['tag'].append(st.tag)
                        tt_['payee'].append(st.payee)
                    else:
                        current_app.logger.info('No active scheduled transactions found')
                else:
                    current_app.logger.info('No scheduled transactions found')
            except:
                current_app.logger.info('Error in calculating scheduled transactions')


    # create  dataframe out of tt_ or send empty
    df_tt = pd.DataFrame.from_dict(tt_)
    if not df_tt.empty:
        #df_tt['date'] = pd.to_datetime(df_tt['date'])
        #df_tt['date'] = pd.to_datetime(df_tt['date']).dt.strftime("%d/%m/%Y")
        df_tt['date'] = pd.to_datetime(df_tt['date'])
        df_tt = df_tt.sort_values(by=['date'], axis=0, ascending=False)
    else:
        df_tt = pd.DataFrame(columns = ['date', 'amount', 'type', 'category', 'subcategory',
                                                          'payee', 'description', 'tag', 'status'])
        current_app.logger.info('No scheduled transactions found')

    return df_tt.to_json(orient='records', date_format='iso')

@main.route('/accounts/<string:name>/latest/', methods=['GET'])
@login_required
def get_latest_transactions(name):

    account = Account.query.filter_by(name=name).first_or_404()

    transactions = [transaction.to_dict() for transaction in account.transactions]

    if account.total_transactions_count > 0:

        df = pd.DataFrame.from_dict(transactions)
        #df['date'] = pd.to_datetime(df['date']).dt.strftime("%m/%d/%Y")
        df['date'] = pd.to_datetime(df['date'])
        #df = df.sort_values(by='date', ascending=False)

        df = df.sort_values(by=['date'], axis=0, ascending=False)
        today = datetime.today().date()
        df_last = df[df['date'] > (today - pd.Timedelta(days=30)).isoformat()]

        if df_last.empty:
            lastday = df.date.max().date()
            df_last = df[df['date'] > (lastday - pd.Timedelta(days=7)).isoformat()]

        df_this_month = df_last

    else:

        df_this_month = pd.DataFrame(columns = ['date', 'amount', 'type', 'category', 'subcategory',
                                                          'payee', 'description', 'tag', 'status'])

        current_app.logger.info('No transactions for this month')

    return df_this_month.to_json(orient='records', date_format='iso')

@main.route('/accounts/<string:name>/scheduled_transactions/', methods=['GET','POST'])
@login_required
def show_template_transactions(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":
        data = json.loads(request.data)

        if data.get('approve') == True:

            current_app.logger.info('Received Post request to approve scheduled transaction')

            transaction = Transaction(date=datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S.%fZ").date(),
                                      amount=data.get('amount'),
                                      type=data.get('type'),
                                      description=data.get('description'),
                                      category=data.get('category'),
                                      subcategory=data.get('subcategory'),
                                      tag=data.get('tag'),
                                      status=True, #data.get('status'),
                                      accountid=account.id,
                                      payee=data.get('payee')).save()

            st = ScheduledTransaction.query.get(data.get('stid'))
            st.last_approved = datetime.today().date()

            restart = datetime.combine(transaction.date, datetime.min.time())
            st.start = restart.date() + timedelta(days=1)

        else:

            st = ScheduledTransaction.query.get(data.get('stid'))

            st.start = datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S.%fZ").date()


    return redirect(url_for("main.account", name=name))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/accounts/<string:name>/transactions/upload', methods=['GET', 'POST'])
@login_required
def upload_csv(name):

    account = Account.query.filter_by(name=name).first_or_404()

    # existing records from database
    transactions = [transaction.to_dict() for transaction in account.transactions]
    if len(transactions) > 0:
        df_from_db = pd.DataFrame.from_dict(transactions)
        df_from_db.drop('tid', axis=1, inplace=True)
        df_from_db['date'] = pd.to_datetime(df_from_db['date'], format="%d/%m/%Y")
        df_from_db['account_id'] = account.id
        df_from_db = df_from_db.sort_values(by='date', ascending=False)

    # existing records from database
    dbtransactions = [dbtransaction.to_dict() for dbtransaction in account.dbtransactions]

    if request.method == 'POST':

        current_app.logger.info('Received Post request to upload csv file')

        # check if the post request has the file part
        if 'file' not in request.files:
            current_app.logger.warn('No file found in the request')
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        # if user does not select file, browser also submit a empty part without filename
        if file.filename == '':
            current_app.logger.warn('File name found empty')
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):

            current_app.logger.info('Converting file to dataframe')

            try:
                filename = secure_filename(file.filename)
                file_extension = filename.split('.')[1]
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                except OSError:
                    pass
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            except:
                current_app.logger.error('Failed to save file here: '
                 + os.path.join(current_app.config['UPLOAD_FOLDER'], filename))


            if file_extension == 'json':
                current_app.logger.info('parsing json and inserting')

                df = pd.read_json(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), orient='records')
                df['date'] = pd.to_datetime(df['date'])

                df['account_id'] = account.id
                df.drop(['tid', 'closing_balance'], axis=1, inplace=True)
                #
                grouped = df.groupby(['date', 'amount', 'type', 'description', 'category', 'subcategory'])
                index = [gp_keys[0] for gp_keys in grouped.groups.values()]
                df_ = df.reindex(index)

                try:
                    if len(transactions) > 0:
                        df_from_json = df_[~df_.isin(df_from_db.to_dict('l')).all(1)]
                    else:
                        df_from_json = df_
                    df_from_json.to_sql(name='transaction', con=db.engine, index=False, if_exists='append')
                    return render_template("upload.html", table=df_from_json.to_html(classes='tablesorter', border=0, index=False), account=account)
                except exc as e:
                    current_app.logger.error(e)
                    return render_template("upload.html",account=account)

            # file is csv (homebank or deutche bank)
            elif file_extension == 'csv':

                current_app.logger.info('parsing csv and inserting')
                df = pd.read_csv(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), sep=';')
                df_ = parse_hb_csv(df, account)

                try:
                    if len(transactions) > 0:
                        df_from_csv = df_[~df_.isin(df_from_db.to_dict('l')).all(1)]
                    else:
                        df_from_csv = df_
                    # write records into database
                    df_from_csv.to_sql(name='transaction', con=db.engine, index=False, if_exists='append')
                    return render_template("upload.html", table=df_from_csv.to_html(classes='tablesorter', border=0, index=False), account=account)
                except exc as e:
                    current_app.logger.error(e)
                    return render_template("upload.html",account=account)

            else:
                with open(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), 'rb') as db_csv, open(os.path.join(current_app.config['UPLOAD_FOLDER'], 'mm_revised.csv'), 'wb') as mm_csv:
                    writer = csv.writer(mm_csv)
                    lc = 0
                    for row in csv.reader(db_csv):
                        lc = lc + 1
                        if lc >=5:
                            writer.writerow(row)

                # convert csv to dataframe
                df_db = pd.read_csv(os.path.join(current_app.config['UPLOAD_FOLDER'], 'mm_revised.csv'), \
                        delimiter=";", quoting=csv.QUOTE_NONE, engine='python', encoding='ISO-8859-1')

                df_ = parse_db_csv(df_db, account)
                try:
                    df_.to_sql(name='dbtransaction', con=db.engine, index=False, if_exists='append')
                    return render_template("edit_upload.html", table=df_.to_html(table_id="dbcv_table",index=False), account=account)
                except Exception as e:
                    current_app.logger.error(e)
                    df_ = pd.DataFrame(columns = ['id', 'account_id', 'date', 'amount', 'description',
                                                                      'beneficiary', 'type'])
                    return render_template("edit_upload.html", table=df_.to_html(table_id="dbcv_table",index=False), account=account)
                    #return render_template("upload.html",account=account)


    return render_template("upload.html",account=account)

def parse_hb_csv(df, account):

    # dataframe formatting
    df['date'] = pd.to_datetime(df['date'],format='%d/%m/%Y')
    df = df.drop(['info'], axis=1)
    df = df.rename({'paymode': 'type', 'wording': 'description', 'tags':'tag'}, axis='columns')
    df['account_id'] = account.id
    df['status'] = True
    df['payee'] = df['payee'].str.decode('utf-8').replace(np.nan, "not provided")
    df['description'] = df['description'].str.decode('utf-8').replace(np.nan, "not provided")
    df['category'] = df['category'].str.decode('utf-8').replace(np.nan, "not provided")
    df['tag'] = df['tag'].str.decode('utf-8').replace(np.nan, "not provided")

    df['category'] = df['category'].apply(lambda x: x+':' if ':' not in x else x)
    df['category'], df['subcategory'] = zip(*df['category'].str.split(':').tolist())
    df['subcategory'] = df['subcategory'].replace('', "not provided")

    # Test: Convert to new category and subcategory typeids
    r = reformat.Reformat()
    df_changed = r.category_and_subcategory(df)

    # map paymodes to types
    transactiontypes = dict(((ttp.id, ttp.ttype) for ttp in db.session.query(TransactionType).all()))
    df_changed['type'] = df_changed['type'].map(transactiontypes)

    grouped = df_changed.groupby(['date', 'amount', 'type', 'description', 'category', 'subcategory'])
    index = [gp_keys[0] for gp_keys in grouped.groups.values()]
    df_ = df_changed.reindex(index)

    return df_


def parse_db_csv(df, account):

    df_mod = df.drop(['Booking date','IBAN','BIC','Customer Reference','Mandate Reference','Creditor ID','Compensation amount', \
                 'Original Amount','Ultimate creditor', 'Number of transactions','Number of cheques', 'Currency'], axis=1)

    df_mod = df_mod.copy().replace(np.NAN, 0)

    #
    df_mod['nCredit'] = df_mod.Credit.map(lambda x: str(x).replace('",',''))
    df_mod['nDebit'] = df_mod.Debit.map(lambda x: str(x).replace('",',''))
    df_mod['nDebit'] = df_mod['nDebit'].str.replace(',', '')
    df_mod['nCredit'] = df_mod['nCredit'].str.replace(',', '')
    df_mod['nDebit'] = pd.to_numeric(df_mod.nDebit, errors='coerce')
    df_mod['nCredit'] = pd.to_numeric(df_mod.nCredit, errors='coerce')
    df_mod['amount'] = df_mod['nDebit'] + df_mod['nCredit']
    df_mod = df_mod.drop(df_mod[df_mod['amount'] == float(0)].index)
    df_mod['type'] = df_mod['Transaction Type'].str.replace('""', '')
    df_mod['date'] = pd.to_datetime(pd.to_datetime(df_mod['Value date']).dt.strftime('%m/%d/%Y')).dt.date
    df_mod['date'] = pd.to_datetime(df_mod['Value date'])
    df_mod.drop(['Debit', 'Credit', 'nCredit', 'nDebit', 'Value date', 'Transaction Type'], axis=1, inplace=True)

    #rename and rearrange
    df_mod = df_mod.rename(columns={'Beneficiary / Originator': 'beneficiary',  \
                                    'Payment Details': 'description'})

    # convert transaction types
    df_mod['type'] = df_mod['type'].map(lambda x: "Cash" if "Cash" in str(x) else x)
    df_mod['type'] = df_mod['type'].map(lambda x: "Electronic payment" if "Credit" in str(x) else x)
    df_mod['type'] = df_mod['type'].map(lambda x: "Debit card" if "Debit Card" in str(x) else x)
    df_mod['type'] = df_mod['type'].map(lambda x: "Electronic payment" if "Standing Order" in str(x) else x)
    df_mod['type'] = df_mod['type'].map(lambda x: "Electronic payment" if "Direct Debit" in str(x) else x)
    df_mod['account_id'] = account.id

    mod_cols = ['account_id', 'date', 'amount', 'description', 'beneficiary', 'type']

    return df_mod[mod_cols]

@main.route('/accounts/<string:name>/getdbtable/', methods=['GET'])
def get_db_table(name):

    account = Account.query.filter_by(name=name).first_or_404()

    dbtransactions = [dbtransaction.to_dict() for dbtransaction in account.dbtransactions]

    if dbtransactions != {}:
        df = pd.DataFrame.from_dict(dbtransactions)
        df['date'] = pd.to_datetime(df['date'])
    else:
        df = pd.DataFrame(columns = ['id', 'account_id', 'date', 'amount', 'description',
                                                          'beneficiary', 'type'])
        current_app.logger.info('No dbtransactions found')

    return df.to_json(orient='records', date_format='iso')

@main.route('/accounts/<string:name>/editdbtable/', methods=['GET','POST'])
def edit_db_table(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":

        current_app.logger.info('Received request to edit data')

        data = json.loads(request.data)

        t = account.dbtransactions.filter_by(id=data.get('tid')).first()

        # ToDo: Check if the whole record needs to be updated
        t.date = datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S.%fZ").date()
        t.amount = data.get('amount')
        t.description = data.get('description')
        t.beneficiary = data.get('beneficiary')
        t.type = data.get('type')

        db.session.commit()

        redirect(url_for('main.upload_csv', name=name))

    return render_template('upload.html', account=account)

@main.route('/accounts/<string:name>/storedbtable/', methods=['POST'])
def store_db_table(name):

    status = {}

    account = Account.query.filter_by(name=name).first_or_404()
    status['transactions_before'] = account.total_transactions_count

    dbtransactions = [dbtransaction.to_dict() for dbtransaction in account.dbtransactions]
    status['dbtransactions_to_be_added'] = len(dbtransactions)

    dbcnt = 0

    for i in range(len(dbtransactions)):
        new_transaction = Transaction(date=dbtransactions[i]['date'].date(),
                                  amount=dbtransactions[i]['amount'],
                                  type=dbtransactions[i]['type'],
                                  description=dbtransactions[i]['description'] + "  " + dbtransactions[i]['beneficiary'],
                                  category=" ",
                                  subcategory=" ",
                                  tag=" ",
                                  status=True,
                                  accountid=account.id,
                                  payee="not provided")

        try:
            new_transaction.save()
            DbTransaction.query.get(dbtransactions[i]['tid']).delete()
            dbcnt = dbcnt + 1
            status['dbtransactions_added'] = dbcnt
            status['transactions_after'] = account.total_transactions_count
        except:
            current_app.error("Error occured while storing DB transaction")
            return render_template('upload.html', account=account, status=report)

    report = "Added %d DB Transactions to %d previous Transactions!" % (status['dbtransactions_added'], status['transactions_before'])

    return render_template('upload.html', account=account, status=report)

@main.route('/accounts/<string:name>/deletedbtransaction/', methods=['POST'])
def delete_db_transactions(name):

    account = Account.query.filter_by(name=name).first_or_404()
    data = json.loads(request.data)
    if request.method == "POST":
        for record in data:
            DbTransaction.query.get(record.get('tid')).delete()

    return render_template('edit_upload.html', account=account)


def getitem(obj, item, default):
    if item not in obj:
        return default
    else:
        return obj[item]

@main.route('/accounts/<string:name>/transactions/log/', methods=['GET', 'POST'])
@login_required
def show_log(name):
    current_app.logger.info('Rendering transaction log page')

    account = Account.query.filter_by(name=name).first_or_404()
    return render_template('transaction_table.html', account=account)

@main.route('/accounts/<string:name>/data/', methods=['GET'])
def data(name):
    current_app.logger.info('Sending transaction log as json')

    account = Account.query.filter_by(name=name).first_or_404()

    transactions = [transaction.to_dict() for transaction in account.transactions]

    try:
        df = pd.DataFrame.from_dict(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date', ascending=False)

        df['closing_balance'] = df.amount.cumsum() + account.balance
    except:
        print ("some error!s")

    return df.to_json(orient='records', date_format='iso')

@main.route('/accounts/<string:name>/delete_data/', methods=['GET', 'POST'])
def delete_data(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":
        current_app.logger.info('Received request to delete data')

        data = json.loads(request.data)
        Transaction.query.get(data.get('tid')).delete()

    return render_template('transaction_table.html', account=account)


@main.route('/accounts/<string:name>/getcategories/', methods=['GET'])
def get_categories(name):

    categories = [c.cattype for c in CategoryType.query.all()]
    dictCategories = { categories[i] : categories[i] for i in range(0, len(categories) ) }

    return json.dumps(categories)


@main.route('/accounts/<string:name>/getsubcategories/', methods=['GET'])
def get_subcategories(name):

    subcategories = [c.subcattype for c in SubCategoryType.query.all()]
    return json.dumps(subcategories)

@main.route('/accounts/<string:name>/set_data/', methods=['GET', 'POST'])
def set_data(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":
        current_app.logger.info('Received request to edit data')

        data = json.loads(request.data)
        #print data.get('status')
        t = account.transactions.filter_by(id=data.get('tid')).first()
        # ToDo: Check if the whole record needs to be updated
        t.date = datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S.%fZ").date()
        #t.date = datetime.strptime(data.get('date'), "%d/%m/%Y").date()
        #print(data.get('date'))
        t.amount = data.get('amount')
        t.category = data.get('category')
        t.subcategory = data.get('subcategory')
        t.description = data.get('description')
        t.payee = data.get('payee')
        t.status = True if data.get('status') == True else False
        t.type = data.get('type')
        t.tag = data.get('tag')
        db.session.commit()
        redirect(url_for('main.set_data', name=name))


    return render_template('transaction_table.html', account=account)

@main.route('/accounts/<string:name>/transactions/dashboard/', methods=['GET'])
@login_required
def show_charts(name):

    account = Account.query.filter_by(name=name).first_or_404()
    form = FilterTransactionForm()

    return render_template('charts.html', account=account, form=form)

def _get_user():
    return current_user.username if current_user.is_authenticated else None

def _valid_date(d):
    if (datetime(1900, 1, 1) <= d <= datetime(2100, 12, 31)):
        return d
    else:
        return datetime.today().date()

def filterdata(df, request):

    current_app.logger.info('Filtering the dataframe')

    # filter according to dates
    if request.args.get('date_from', '') != '':
        if request.args.get('date_to', '') != '':
            if (datetime.strptime(request.args.get('date_from', ''), '%d/%m/%Y')) \
            < (datetime.strptime(request.args.get('date_to', ''), '%d/%m/%Y')):
                df_filtered = df[(df['date'] >=
                (datetime.strptime(request.args.get('date_from', ''), '%d/%m/%Y'))) &
                                 (df['date'] <=
                (datetime.strptime(request.args.get('date_to', ''), '%d/%m/%Y')))]
            else:
                current_app.logger.info('Date sequence is perhaps wrong')
                df_filtered = df
        else:
            current_app.logger.info('Date To is perhaps wrong')
            df_filtered = df[df['date'] >= (datetime.strptime(request.args.get('date_from', ''), '%d/%m/%Y'))]
    elif request.args.get('date_to', '') != '':
        current_app.logger.info('Date From is perhaps wrong')
        df_filtered = df[df['date'] <= (datetime.strptime(request.args.get('date_to', ''), '%d/%m/%Y'))]
    else:
        current_app.logger.info('Date fields are perhaps wrong')
        df_filtered = df


    # filter according to amount
    if request.args.get('amount_ge', '') != '':
        if request.args.get('amount_le', '') != '':
            if (request.args.get('amount_ge', '')) < (request.args.get('amount_le', '')):
                df_filtered = df_filtered[(df_filtered['amount'] >= request.args.get('amount_ge', '')) &
                                 (df_filtered['amount'] <= request.args.get('amount_le', ''))]
            else:
                current_app.logger.info('Amounts compared are in a wrong order')
        else:
            current_app.logger.info('Amount Less Than Equal is perhaps wrong')
            df_filtered = df_filtered[df_filtered['amount'] <= request.args.get('amount_ge', '')]
    else:
        if request.args.get('amount_le', '') != '':
            current_app.logger.info('Amount Greater Than Equal is perhaps wrong')
            df_filtered = df_filtered[df_filtered['amount'] <= request.args.get('amount_le', '')]

    # filter by category
    if request.args.get('category_like', '', type=str) != '':
        df_filtered = df_filtered[df_filtered['category'].str \
                    .contains(request.args.get('category_like', '', type=str))]

    # filter by tags
    if request.args.get('tags_like', '', type=str) != '':
        df_filtered = df_filtered[df_filtered['tag'].str \
                    .contains(request.args.get('tags_like', '', type=str))]

    # filter by description
    if request.args.get('description_like', '', type=str) != '':
        df_filtered = df_filtered[df_filtered['description'].str \
                    .contains(request.args.get('description_like', '', type=str))]


    return df_filtered

def _get_filtered_dataframe(form, df):

    current_app.logger.info('Filtering the dataframe')

    if ((form.date_from.data is not None) | (form.date_to.data is not None)):
        valid_date_from = _valid_date(form.date_from.data)
        valid_date_to = _valid_date(form.date_to.data)
    else:
        valid_date_from = df['date'].min()
        valid_date_to = df['date'].max()

    # this could be more generic
    if not (valid_date_from < valid_date_to):
        valid_date_from = df['date'].min()
        valid_date_to = df['date'].max()

    if not(form.amount_ge.data < form.amount_le.data):
        valid_amount_ge = df['amount'].min()
        valid_amount_le = df['amount'].max()
    else:
        valid_amount_ge = form.amount_ge.data
        valid_amount_le = form.amount_le.data

    df_filtered = df[(df['date'] >= valid_date_from) &
                        (df['date'] <= valid_date_to) &
                        (df['amount'] >= valid_amount_ge) &
                        (df['amount'] <= valid_amount_le)
                        ]

    return df_filtered

@main.route('/accounts/<string:name>/transactions/scheduled/', methods=['GET','POST'])
@login_required
def new_scheduled_transaction(name):

    account = Account.query.filter_by(name=name).first_or_404()
    s_transactions = [st.to_dict() for st in account.scheduled_transactions]

    df = pd.DataFrame.from_dict(s_transactions)
    if not df.empty:
        df['created_on'] = pd.to_datetime(df['created_on'])
        df = df.sort_values(by='created_on', ascending=False)


    ttypechoices = [(ttp.id, ttp.ttype) for ttp
    in TransactionType.query.order_by(TransactionType.ttype).all()]

    catchoices = [(cat.id, cat.cattype) for cat
    in CategoryType.query.order_by(CategoryType.cattype).all()]

    subcatchoices = [(subcat.id, subcat.subcattype) for subcat
    in SubCategoryType.query.order_by(SubCategoryType.subcattype).all()]

    form = ScheduledTransactionForm()
    form.type.choices = ttypechoices
    form.category.choices = catchoices
    form.subcategory.choices = subcatchoices
    form.frequency.choices = [(1, 'Yearly'),
                              (2, 'Quarterly'),  # NotImplemented
                              (3, 'Monthly'),
                              (4, 'Weekly')]

    if form.validate_on_submit():
        # ToDo: Strict check should be replace by regex type loose check
        current_app.logger.info('Creating a new scheduled transaction')

        frequency = [i[1] for i in form.frequency.choices if i[0]==form.frequency.data]
        ttype_name = TransactionType.query.filter_by(id=form.type.data).first().ttype
        cattype_name = CategoryType.query.filter_by(id=form.category.data).first().cattype
        subcattype_name = SubCategoryType.query.filter_by(id=form.subcategory.data).first().subcattype

        ScheduledTransaction(accountid=account.id,
                            frequency=frequency[0],
                            interval = form.interval.data,
                            day=form.day.data,
                            start = form.start.data,
                            end = form.end.data,
                            approved = datetime.today().date(),
                            active = form.active.data,
                            amount = form.amount.data,
                            description = form.description.data,
                            type = ttype_name,
                            category= cattype_name,
                            subcategory= subcattype_name,
                            tag = form.tag.data,
                            payee = form.payee.data).save()

        return redirect(url_for('main.new_scheduled_transaction', name=name))

    return render_template('scheduled_transactions.html', account=account,
                            data=df.to_json(orient='records', date_format='iso'),
                            form=form)

@main.route('/accounts/<string:name>/transactions/edit_scheduled/', methods=['POST'])
@login_required
def edit_scheduled_transaction(name):

    account = Account.query.filter_by(name=name).first_or_404()
    s_transactions = [st.to_dict() for st in account.scheduled_transactions]

    if request.method == "POST":
        current_app.logger.info('Received Post request to edit scheduled transaction')
        try:
            data = json.loads(request.data)
            st = account.scheduled_transactions.filter_by(id=data.get('id')).first()
            st.frequency = data.get('frequency')
            st.interval = data.get('interval')
            st.day = data.get('day')
            st.start = datetime.strptime(data.get('start'), "%Y-%m-%dT%H:%M:%S.%fZ").date()
            st.end = datetime.strptime(data.get('end'), "%Y-%m-%dT%H:%M:%S.%fZ").date()#
            #st.approved = data.get('approved')
            #print data.get('active')
            st.active = data.get('active')
            st.amount = data.get('amount')
            st.description = data.get('description')
            st.category = data.get('category')
            st.subcategory = data.get('subcategory')
            st.payee = data.get('payee')
            st.type = data.get('type')
            #st.tag = data.get('tag')
            db.session.commit()
        except:
            #print request
            current_app.logger.error('Received Post request with errors')

    return redirect(url_for('main.new_scheduled_transaction', name=name))

@main.after_request
def after_request(response):
    """ Logging after every request. """
    # This avoids the duplication of registry in the log,
    # since that 500 is already logged via @app.errorhandler.
    if response.status_code != 500:
        current_app.logger.info('%s - - [%s] %s %s %s %s',
                        request.remote_addr,
                        strftime('%d/%b/%Y %H:%M:%S'),
                        request.method,
                        request.scheme,
                        request.full_path,
                        response.status)
    return response
