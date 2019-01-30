from flask import render_template, redirect, request, url_for, flash
from flask_login import current_user, login_required
from collections import defaultdict
from time import strftime
import sys
import os
from werkzeug.utils import secure_filename
from app.main import main
from app.main.forms import AccountForm, TransactionForm, ScheduledTransactionForm, FilterTransactionForm
from app.models import Account, Transaction, ScheduledTransaction
from app.models import TransactionType, CategoryType, SubCategoryType
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

reload(sys)
sys.setdefaultencoding('utf8')
ALLOWED_EXTENSIONS = set(['csv'])

@main.route('/')
def index():

    if current_user.is_authenticated:
        return redirect(url_for('main.account_overview'))

    return render_template('index.html')

@main.route('/accounts/', methods=['GET'])
@login_required
def account_overview():

    return render_template('overview.html')

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
            return redirect(url_for('main.account_overview'))

    return render_template('new_account.html', form=form)

@main.route('/accounts/<string:name>/', methods=['GET', 'POST'])
@login_required
def account(name):

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
            sd = s.get_template_transactions_with_start(st.day, st.frequency,
                                                        st.interval, st.start)
            tt_['stid'].append(st.id)
            tt_['date'].append(sd[0])
            tt_['amount'].append(st.amount)
            tt_['type'].append('electronic')
            tt_['description'].append(st.description)
            tt_['category'].append(st.category)
            tt_['status'].append(False)
            tt_['accountid'].append(account.id)
            tt_['tag'].append(st.tag)
            tt_['payee'].append(st.payee)
        current_app.logger.info('Scheduled transactions found')


    # create  dataframe out of tt_ or send empty
    df_tt = pd.DataFrame.from_dict(tt_)
    if not df_tt.empty:
        df_tt['date'] = pd.to_datetime(df_tt['date'])
    else:
        current_app.logger.info('No scheduled transactions found')

    # get transaction types
    ttypechoices = [(ttp.id, ttp.ttype) for ttp
    in TransactionType.query.order_by(TransactionType.ttype).all()]

    catchoices = [(cat.id, cat.cattype) for cat
    in CategoryType.query.order_by(CategoryType.cattype).all()]

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
            cattype_name = CategoryType.query.filter_by(id=form.category.data).first().cattype
            subcattype_name = SubCategoryType.query.filter_by(id=form.subcategory.data).first().subcattype

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

    # show transaction for this month
    transactions = [transaction.to_dict() for transaction in account.transactions]

    if account.total_transactions_count > 0:
        df = pd.DataFrame.from_dict(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by=['date'], axis=0, ascending=False)

        today = datetime.today().date()
        df_last = df[df['date'] > (today - pd.Timedelta(days=30)).isoformat()]

        if df_last.empty:
            #print ("no transactions in the last 30 days")
            lastday = df.date.max().date()
            df_last = df[df['date'] > (lastday - pd.Timedelta(days=7)).isoformat()]
            #print df_last.head()

        df_this_month = df_last #.reindex(columns = ['date', 'amount', 'type', 'category', 'subcategory',
                                    #                'payee', 'description', 'tag', 'status'])
    else:
        df_this_month = pd.DataFrame(columns = ['date', 'amount', 'type', 'category', 'subcategory',
                                                          'payee', 'description', 'tag', 'status'])

        current_app.logger.info('No transactions for this month')

    #print df_this_month.head()
    return render_template('transaction_overview.html',
                            table=df_this_month.to_json(orient='records', date_format='iso'),
                            account=account, form=form, dataframe=df_tt.to_json(orient='records', date_format='iso'))

@main.route('/accounts/<string:name>/scheduled_transactions/', methods=['GET','POST'])
@login_required
def show_template_transactions(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":
        data = json.loads(request.data)
        if data.get('approve'):

            current_app.logger.info('Received Post request to approve scheduled transaction')

            #ttype = TransactionType.query.filter_by(ttype=data.get('typeid')).first()
            transaction = Transaction(date=datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S.%fZ").date(),
                                      amount=data.get('amount'),
                                      type=data.get('type'),
                                      description=data.get('description'),
                                      category=data.get('category'),
                                      subcategory=data.get('subcategory'),
                                      tag=data.get('tag'),
                                      status=data.get('status'),
                                      accountid=account.id,
                                      payee=data.get('payee')).save()

            st = ScheduledTransaction.query.get(data.get('stid'))
            st.last_approved = datetime.today().date()
            st.start = transaction.date.date() + timedelta(days=1)

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
        current_app.logger.info(df_from_db.shape)

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

            current_app.logger.info('Converting csv file to dataframe')

            try:
                filename = secure_filename(file.filename)
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                except OSError:
                    pass
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            except:
                current_app.logger.error('Failed to save file here: '
                 + os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

            # dataframe formatting
            df = pd.read_csv(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), sep=';')
            df['date'] = pd.to_datetime(df['date'],format='%d/%m/%Y')
            df = df.drop(['info'], axis=1)
            df = df.rename({'paymode': 'type', 'wording': 'description', 'tags':'tag'}, axis='columns')
            df['account_id'] = account.id
            df['status'] = True
            df['payee'] = df['payee'].str.decode('utf-8').replace(np.nan, "not provided")
            df['description'] = df['description'].str.decode('utf-8').replace(np.nan, "not provided")
            df['category'] = df['category'].str.decode('utf-8').replace(np.nan, "not provided")
            df['tag'] = df['tag'].str.decode('utf-8').replace(np.nan, "not provided")

            #df.replace({'type': {0:1}}, inplace=True)
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

            # combine records
            if len(transactions) > 0:
                current_app.logger.info("DB Dataframe: " + str(df_from_db.shape))
                current_app.logger.info("CSV Dataframe: " + str(df_.shape))

                df_from_csv = df_[~df_.isin(df_from_db.to_dict('l')).all(1)]

                current_app.logger.info("New Rows from CSV: " + str(df_from_csv.shape))
                current_app.logger.info("Concatenated Dataframe: " + str(df_from_csv.shape))
            else:
                df_from_csv = df_

            current_app.logger.info('Converting dataframe to sql records and inserting')
            #current_app.logger.info("engine: " + 'mysql+mysqldb://'+os.environ['RDS_USERNAME']+":"+os.environ['RDS_PASSWORD']+ \
            #                        '@'+os.environ['RDS_HOSTNAME']+'/'+os.environ['RDS_DB_NAME'])
            try:
                #engine = create_engine('mysql+mysqldb://mm_admin:mm_8_9435@localhost/money_db')
                #engine=create_engine('mysql+mysqldb://'+os.environ['RDS_USERNAME']+":"+os.environ['RDS_PASSWORD']+ \
                #                        '@'+os.environ['RDS_HOSTNAME']+'/'+os.environ['RDS_DB_NAME'])
                #current_app.logger.info(df_from_csv['type_id'].unique())
                df_from_csv.to_sql(name='transaction', con=db.engine, index=False, if_exists='append')
                #df_from_csv.to_csv(os.path.join(current_app.config['UPLOAD_FOLDER'],'test_with_subcategory.csv'),sep=';')
            except exc.SQLAlchemyError as e:
                current_app.logger.error(e)

            return render_template("upload.html",
                    table=df_from_csv.to_html(classes='tablesorter', border=0, max_rows=10, index=False), account=account)

    else:
        render_template('upload.html', account=account)

    return render_template('upload.html', account=account)

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

    df = pd.DataFrame.from_dict(transactions)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date', ascending=False)
    df['date'] = df['date'].dt.strftime('%d/%m/%Y')

    df['closing_balance'] = df.amount.cumsum() + account.balance
    return df.to_json(orient='records', date_format='iso')

@main.route('/accounts/<string:name>/delete_data/', methods=['GET', 'POST'])
def delete_data(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":
        current_app.logger.info('Received request to delete data')

        data = json.loads(request.data)
        Transaction.query.get(data.get('tid')).delete()

    return render_template('transaction_table.html', account=account)

@main.route('/accounts/<string:name>/set_data/', methods=['GET', 'POST'])
def set_data(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":
        current_app.logger.info('Received request to edit data')

        data = json.loads(request.data)
        t = account.transactions.filter_by(id=data.get('tid')).first()
        # ToDo: Check if the whole record needs to be updated
        #t.date = datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S.%fZ").date()
        t.date = datetime.strptime(data.get('date'), "%d/%m/%Y").date()
        #print(datetime.strptime(data.get('date'), "%d/%m/%Y").date())
        t.amount = data.get('amount')
        t.category = data.get('category')
        t.subcategory = data.get('subcategory')
        t.description = data.get('description')
        t.payee = data.get('payee')
        t.status = True if data.get('status') == 'true' else False
        t.type = data.get('type')
        t.tag = data.get('tag')
        db.session.commit()
        redirect(url_for('main.set_data', name=name))


    return render_template('transaction_table.html', account=account)

@main.route('/accounts/<string:name>/transactions/chart_data/', methods=['GET', 'POST'])
@login_required
def show_chart_data(name):

    account = Account.query.filter_by(name=name).first_or_404()
    # get all transactions from the account
    transactions = [transaction.to_dict() for transaction in account.transactions]

    # format trasaction dataframe nicely
    df = pd.DataFrame.from_dict(transactions)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['yearmonth'] = df['date'].apply(lambda x: x.strftime('%Y-%m'))
        # good place to add column for closing balance
        df['closing_balance'] = df.amount.cumsum() + account.balance

    df_filtered = filterdata(df, request)

    set_frequency = request.args.get('frequency', '', type=str)
    #print (set_frequency)
    if set_frequency == 'm':

        df_balance = df_filtered.groupby('yearmonth')['closing_balance'].last().reset_index()

        df_tag_pivoted = df_filtered.groupby(['yearmonth', 'tag'])['amount'].agg('sum').reset_index() \
                                    .pivot(index='yearmonth', columns='tag', values='amount') \
                                    .reset_index().rename_axis(None, axis=1) \
                                    .fillna(0)

        df_cat_pivoted = df_filtered.groupby(['yearmonth', 'category'])['amount'].agg('sum').reset_index() \
                                    .pivot(index='yearmonth', columns='category', values='amount') \
                                    .reset_index().rename_axis(None, axis=1) \
                                    .fillna(0)

        df_subcat_pivoted = df_filtered.groupby(['yearmonth', 'subcategory'])['amount'].agg('sum').reset_index() \
                                    .pivot(index='yearmonth', columns='subcategory', values='amount') \
                                    .reset_index().rename_axis(None, axis=1) \
                                    .fillna(0)

    elif set_frequency == 'l12m':

        df_balance = df_filtered.set_index('date').last('12M').reset_index() \
                    .groupby('yearmonth')['closing_balance'].last().reset_index()

        df_tag_pivoted = df_filtered.set_index('date').last('12M').reset_index()\
        .groupby(['yearmonth', 'tag'])['amount'].agg('sum').reset_index() \
        .pivot(index='yearmonth', columns='tag', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

        df_cat_pivoted =  df_filtered.set_index('date').last('12M').reset_index()\
        .groupby(['yearmonth', 'category'])['amount'].agg('sum').reset_index() \
        .pivot(index='yearmonth', columns='category', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

        df_subcat_pivoted = df_filtered.set_index('date').last('12M').reset_index()\
        .groupby(['yearmonth', 'subcategory'])['amount'].agg('sum').reset_index() \
        .pivot(index='yearmonth', columns='subcategory', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

    elif set_frequency == 'l3m':

        df_balance = df_filtered.set_index('date').last('3M').reset_index() \
                    .groupby('yearmonth')['closing_balance'].last().reset_index()

        df_tag_pivoted = df_filtered.set_index('date').last('3M').reset_index()\
        .groupby(['yearmonth', 'tag'])['amount'].agg('sum').reset_index() \
        .pivot(index='yearmonth', columns='tag', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

        df_cat_pivoted =  df_filtered.set_index('date').last('3M').reset_index()\
        .groupby(['yearmonth', 'category'])['amount'].agg('sum').reset_index() \
        .pivot(index='yearmonth', columns='category', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

        df_subcat_pivoted = df_filtered.set_index('date').last('3M').reset_index()\
        .groupby(['yearmonth', 'subcategory'])['amount'].agg('sum').reset_index() \
        .pivot(index='yearmonth', columns='subcategory', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

    else:

        df_balance = df.groupby('year')['closing_balance'].last().reset_index()

        df_tag_pivoted = df.groupby(['year', 'tag'])['amount'].agg('sum').reset_index() \
        .pivot(index='year', columns='tag', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

        df_cat_pivoted = df.groupby(['year', 'category'])['amount'].agg('sum').reset_index() \
        .pivot(index='year', columns='category', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

        df_subcat_pivoted = df.groupby(['year', 'subcategory'])['amount'].agg('sum').reset_index() \
        .pivot(index='year', columns='subcategory', values='amount') \
        .reset_index().rename_axis(None, axis=1) \
        .fillna(0)

    return  json.dumps({ 'frequency' : set_frequency,
        'balance': df_balance.to_dict(orient='records'),
        'by_tags': df_tag_pivoted.to_dict(orient='records'),
        'by_category': df_cat_pivoted.to_dict(orient='records'),
        'by_subcategory': df_subcat_pivoted.to_dict(orient='records')
        })


@main.route('/accounts/<string:name>/transactions/dashboard/', methods=['GET'])
@login_required
def show_charts(name):

    account = Account.query.filter_by(name=name).first_or_404()
    # get all transactions from the account
    transactions = [transaction.to_dict() for transaction in account.transactions]

    # format trasaction dataframe nicely
    df = pd.DataFrame.from_dict(transactions)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['yearmonth'] = df['date'].apply(lambda x: x.strftime('%Y-%m'))
        # good place to add column for closing balance
        df['closing_balance'] = df.amount.cumsum() + account.balance

    form = FilterTransactionForm()

    df_balance = df.groupby('year')['closing_balance'].last().reset_index()

    df_tag_pivoted = df.groupby(['year', 'tag'])['amount'].agg('sum').reset_index() \
    .pivot(index='year', columns='tag', values='amount') \
    .reset_index().rename_axis(None, axis=1) \
    .fillna(0)

    df_cat_pivoted = df.groupby(['year', 'category'])['amount'].agg('sum').reset_index() \
    .pivot(index='year', columns='category', values='amount') \
    .reset_index().rename_axis(None, axis=1) \
    .fillna(0)

    df_subcat_pivoted = df.groupby(['year', 'subcategory'])['amount'].agg('sum').reset_index() \
    .pivot(index='year', columns='subcategory', values='amount') \
    .reset_index().rename_axis(None, axis=1) \
    .fillna(0)

    return render_template('charts.html', account=account, form=form,
            data=df_balance.to_json(orient='records', date_format='iso'),
            data_by_tags = df_tag_pivoted.to_json(orient='records', date_format='iso'),
            data_by_category = df_cat_pivoted.to_json(orient='records', date_format='iso'),
            data_by_subcategory = df_subcat_pivoted.to_json(orient='records', date_format='iso'))

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

'''
@main.errorhandler(404)
def page_not_found(e):

    ts = strftime('[%Y-%b-%d %H:%M]')
    tb = traceback.format_exc()
    current_app.logger.error('%s %s %s %s %s 5xx INTERNAL SERVER ERROR\n%s',
                  ts,
                  request.remote_addr,
                  request.method,
                  request.scheme,
                  request.full_path,
                  tb)
    return render_template('404.html'), 404
'''

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


'''
@main.route('/accounts/<string:name>/transactions/dashboard/', methods=['GET', 'POST'])
#@login_required
def show_dashboard(name):

    account = Account.query.filter_by(name=name).first_or_404()
    transactions = [transaction.to_dict() for transaction in account.transactions]
    # Temp: convert type id to validate_on_submit
    #typeids = ['None', 'Credit Card', 'Cash', 'Transfer',
    #            'Debit Card', 'Electronic Payment', 'Deposit']

    df = pd.DataFrame.from_dict(transactions)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['yearmonth'] = df['date'].apply(lambda x: x.strftime('%Y-%m'))


    custom_style = BlueStyle(
                      background='transparent',
                      plot_background='transparent',
                      #foreground='#53E89B',
                      #foreground_strong='#53A0E8',
                      #foreground_subtle='#630C0D',
                      opacity='.6',
                      opacity_hover='.2',
                      font_family='googlefont:Raleway',
                      transition='50ms ease-in')

    bar_chart = pygal.StackedBar(style=custom_style, legend_at_bottom=True, show_minor_x_labels=False)
    line_chart = pygal.Line(style=custom_style, legend_at_bottom=True, fill=True, show_minor_x_labels=False)
    typeid_chart = pygal.StackedBar(style=custom_style, legend_at_bottom=True, show_minor_x_labels=False)

    #get filter parameters
    form = FilterTransactionForm()

    if form.validate_on_submit():
        # get filtered dataframe
        df_filtered = _get_filtered_dataframe(form, df)
        #df_filtered.replace(typeids, inplace = True)

        if form.show_by.data == 'm':

            current_app.logger.info('Showing monthly aggregated data')

            # Spend analysis: according to tag
            df_tag_pivoted = df_filtered.groupby(['yearmonth', 'tag'])['amount'].agg('sum').reset_index() \
                                        .pivot(index='yearmonth', columns='tag', values='amount') \
                                        .reset_index().rename_axis(None, axis=1) \
                                        .fillna(0)
            bar_chart.x_labels = df_tag_pivoted['yearmonth']
            bar_chart.x_label_rotation = -90
            bar_chart.x_labels_major = df_tag_pivoted['yearmonth'][0::6].tolist()

            tags = df_tag_pivoted.columns.tolist()
            tags.remove('yearmonth')
            # Spend analysis by type
            df_type_pivoted = df_filtered.groupby(['yearmonth', 'type'])['amount'].agg('sum').reset_index() \
                                        .pivot(index='yearmonth', columns='type', values='amount') \
                                        .reset_index().rename_axis(None, axis=1) \
                                        .fillna(0)
            typeid_chart.x_labels = df_type_pivoted['yearmonth']
            typeid_chart.x_label_rotation = -90
            typeid_chart.x_labels_major = df_type_pivoted['yearmonth'][0::6].tolist()

            typeids = df_type_pivoted.columns.tolist()
            typeids.remove('yearmonth')

            # closing balance
            df_balance = df_filtered.groupby('yearmonth')['amount'].sum() \
                                    .cumsum().reset_index()
            df_balance['amount'] = df_balance['amount'] + account.balance
            line_chart.x_labels = df_balance['yearmonth']
            line_chart.x_label_rotation = -90
            line_chart.x_labels_major = df_balance['yearmonth'][0::4].tolist()

        else:
            current_app.logger.info('Showing yearly aggregated data')

            df_tag_pivoted = df_filtered.groupby(['year', 'tag'])['amount'].agg('sum').reset_index() \
                                        .pivot(index='year', columns='tag', values='amount') \
                                        .reset_index().rename_axis(None, axis=1) \
                                        .fillna(0)
            bar_chart.x_labels = map(str, df_tag_pivoted['year'])
            tags = df_tag_pivoted.columns.tolist()
            tags.remove('year')

            # Spend analysis by type
            df_type_pivoted = df_filtered.groupby(['year', 'type'])['amount'].agg('sum').reset_index() \
                                        .pivot(index='year', columns='type', values='amount') \
                                        .reset_index().rename_axis(None, axis=1) \
                                        .fillna(0)

            typeid_chart.x_labels = map(str, df_type_pivoted['year'])

            typeids = df_type_pivoted.columns.tolist()
            typeids.remove('year')

            # closing balance
            df_balance = df_filtered.groupby('year')['amount'].sum() \
                                    .cumsum().reset_index() + account.balance
            line_chart.x_labels = bar_chart.x_labels

        bar_chart.title = 'Spend by Tags'
        if 'Salary' in tags: tags.remove('Salary')
        if 'not provided' in tags: tags.remove('not provided')
        for t in tags:
            bar_chart.add(t, df_tag_pivoted[t])

        typeid_chart.title = 'Spend by Type'
        for t in typeids:
            typeid_chart.add(t, df_type_pivoted[t])

        line_chart.add("Balance", df_balance['amount'])
        line_chart.title = 'Closing Balance'

    chart = bar_chart.render_data_uri()
    line = line_chart.render_data_uri()
    type_chart = typeid_chart.render_data_uri()

    return render_template('dashboard.html', account=account,
                            chart = chart, line=line, typechart = type_chart, form=form)

'''
