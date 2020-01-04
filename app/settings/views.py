
import pandas as pd
import numpy as np
import json
from flask import render_template, redirect, url_for,request
from app.models import Account, CategoryType, CategorySettings, SubCategoryType, SubCategorySettings, Transaction
from app.settings import settings
from app.settings.forms import NewCategoryForm, NewSubCategoryForm
from sqlalchemy import func, desc
from datetime import datetime
from app import db



@settings.route('/<string:name>/data/', methods=['GET', 'POST'])
def get_data_for_bullets(name):

    account = Account.query.filter_by(name=name).first_or_404()

    cols = ['date', 'amount', 'category', 'description', 'payee',
    'status', 'subcategory', 'tag', 'tid', 'type',
    'year', 'month', 'yearmonth']

    # simple pandas based group_by should work to get average monthly spent
    transactions = [transaction.to_dict()
    for transaction in account.transactions.filter_by(status=True).order_by('date')]
    df = pd.DataFrame.from_dict(transactions)

    # check if user has sufficient transaction history
    if df.empty:
        print ("user does not sufficient transaction history")
        results = get_spent(pd.DataFrame(columns = cols), 0, account)
    else:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['yearmonth'] = df['date'].apply(lambda x: x.strftime('%Y-%m'))
        # take max. 2 years of average monthly income
        df_avg = df.set_index('date').last('24m').reset_index()
        mask = ((df_avg.amount > 0) & (df_avg.tag != 'Superfuture'))
        df_ = df_avg.loc[mask]
        #check if user has any income in this month
        average_income = df_.groupby('yearmonth')['amount'].sum().mean()
        if average_income == np.nan:
            print ("user has no income in this month")
            results = get_spent(pd.DataFrame(columns = cols), 0, account)
        else:
            # get this month's spent
            d = datetime.today().strftime('%Y-%m')
            try:
                df_current = df.groupby('yearmonth').get_group(d)
                results = get_spent(df_current, average_income, account)
            except KeyError as error:
                print(error)
                df_current = df.groupby('yearmonth').get_group(df.yearmonth.max())
                results = get_spent(df_current, average_income, account)

    return results

def get_spent(df_current, average_income, account):

    if df_current.empty:
        print ("user has no transactions in the current month")
        average_income = 1 #default to avoid divide-by-zero
        spent_this_month = 0
        this_tag = ''
        tag_this_month = 0
        tag_this_month_percent = 0
        this_category = ''
        category_this_month_percent = 0
        this_subcategory = ''
        subcategory_this_month_percent = 0

    else:

        mask = (df_current.amount < 0)
        df_spent = df_current.loc[mask]
        spent_this_month = abs(df_spent.amount.sum())

        # this months spent in last tag
        this_tag = df_current.loc[df_current.date
                    == df_current.date.max(),'tag'] \
                    .values[0]

        tag_this_month = abs(df_current[df_current.tag
                            == this_tag].amount.sum())

        if average_income > 0:
            tag_this_month_percent = \
                (tag_this_month*100)/average_income
        else:
            # todo:needs more logical default
            tag_this_month_percent = 0

        # this months spent in last category
        this_category = df_current.loc[df_current.date
                        == df_current.date.max(),'category'] \
                        .values[0]

        set = CategorySettings.query.filter_by(
                account_id = account.id,
                category = this_category).first()

        category_this_month = abs(df_current[df_current.category
                                == this_category].amount.sum())

        if set:
            if set.apply:
                this_category_budget = set.limit
                category_this_month_percent = \
                    (category_this_month*100)/this_category_budget
            else:
                this_category_budget = 100
                if average_income > 0:
                    category_this_month_percent = \
                        (category_this_month*100)/average_income
                else:
                    category_this_month_percent = 0

        # this months spent in last category
        this_subcategory = df_current.loc[df_current.date
                            == df_current.date.max(),'subcategory'] \
                            .values[0]

        set = SubCategorySettings.query.filter_by(
                account_id = account.id,
                subcategory = this_subcategory).first()

        subcategory_this_month = abs(df_current[df_current.subcategory
                                    == this_subcategory].amount.sum())

        if set:
            if set.apply:
                this_subcategory_budget = set.limit
                subcategory_this_month_percent = \
                    (subcategory_this_month*100)/this_subcategory_budget
            else:
                this_subcategory_budget = 100
                if average_income > 0:
                    subcategory_this_month_percent = \
                        (subcategory_this_month*100)/average_income
                else:
                    subcategory_this_month_percent = 0

    return json.dumps({
    'expense': {'total': 100,
                 'spent': (spent_this_month*100)/(average_income),
                 'budget': 75},
    'tag': {'name': this_tag,
            'total': 100,
            'spent': tag_this_month_percent,
            'budget': 100},
    'category': {'name': this_category,
                 'total': 100,
                 'spent': category_this_month_percent,
                 'budget': 100},
    'subcategory':{'name': this_subcategory,
                   'total': 100,
                   'spent': subcategory_this_month_percent,
                   'budget': 100}
    });

@settings.route('/<string:name>/settings/', methods=['GET'])
def show_account_settings(name):

    account = Account.query.filter_by(name=name).first_or_404()

    # create categories and sub-categories table
    get_categories(account)
    get_subcategories(account)

    # simple pandas based group_by should work to get average monthly spent
    transactions = [transaction.to_dict()
    for transaction in account.transactions.filter_by(status=True)]
    df = pd.DataFrame.from_dict(transactions)

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['yearmonth'] = df['date'].apply(lambda x: x.strftime('%Y-%m'))

        # populate spent characteristics for categories and sub-categories
        get_cat_details(df, account)
        get_subcat_details(df, account)

    return render_template('transaction_attributes.html', account=account,
                            form=NewCategoryForm(), subcategoryform=NewSubCategoryForm())

def get_categories(account):

    if db.session.query(CategorySettings.query.filter(
    CategorySettings.account_id == account.id).exists()).scalar():
        print "category settings already exist"

    else:
        # get all transactions from the account
        categories = [c.cattype for c in CategoryType.query.all()]

        for c in categories:
            set = CategorySettings(accountid=account.id,
            category=c,
            limit=100,
            unit=account.currency,
            apply=False)
            set.save()

def get_cat_details(df, account):

    df_last = df.set_index('date').last('1m').reset_index()\
                .groupby(['yearmonth', 'category'])['amount'] \
                .agg('sum').fillna(0).reset_index()

    df_avg = df.set_index('date').last('12m').reset_index()\
               .groupby(['yearmonth', 'category'])['amount']\
               .agg('sum').fillna(0).reset_index()\
               .groupby(['category'])['amount'].mean().reset_index()

    #print df_avg[['category','amount']]
    for r in df_last.itertuples():

        set = CategorySettings.query.filter_by(
        account_id = account.id,
        category=r[2]).first()
        if set:
            set.last_month = r[3]
            set.save()

    for r in df_avg.itertuples():
        set = CategorySettings.query.filter_by(
        account_id = account.id,
        category=r[1]).first()
        if set:
            set.avg_month = r[2]
            set.save()

def get_subcategories(account):

    if db.session.query(SubCategorySettings.query.filter(
    SubCategorySettings.account_id == account.id).exists()).scalar():
        # move to app logger
        print ("subcategories already exist!")
    else:
        # get all subcategories from the account
        subcategories = [s.subcattype for s in SubCategoryType.query.all()]

        for s in subcategories:
            set = SubCategorySettings(accountid=account.id,
            subcategory=s,
            limit=100,
            unit=account.currency,
            apply=False)
            set.save()

def get_subcat_details(df, account):

    df_last = df.set_index('date').last('1m').reset_index()\
                .groupby(['yearmonth', 'subcategory'])['amount'] \
                .agg('sum').fillna(0).reset_index()

    df_avg = df.set_index('date').last('12m').reset_index()\
               .groupby(['yearmonth', 'subcategory'])['amount']\
               .agg('sum').fillna(0).reset_index()\
               .groupby(['subcategory'])['amount'].mean().reset_index()

    for r in df_last.itertuples():

        set = SubCategorySettings.query.filter_by(
        account_id = account.id,
        subcategory=r[2]).first()
        if set:
            set.last_month = r[3]
            set.save()

    for r in df_avg.itertuples():
        set = SubCategorySettings.query.filter_by(
        account_id = account.id,
        subcategory=r[1]).first()
        if set:
            set.avg_month = r[2]
            set.save()

@settings.route('/<string:name>/get_settings_data/', methods=['GET'])
def get_settings_data(name):

    account = Account.query.filter_by(name=name).first_or_404()

    cat_settings = [cs.to_dict() for cs in CategorySettings.query
                    .filter(CategorySettings.account_id == account.id).all()]

    subcat_settings = [scs.to_dict() for scs in SubCategorySettings.query
                    .filter(SubCategorySettings.account_id == account.id).all()]

    #df = pd.DataFrame.from_dict(cat_settings)
    #return df.to_json(orient='records')

    df_cat = pd.DataFrame.from_dict(cat_settings)
    df_subcat = pd.DataFrame.from_dict(subcat_settings)

    return json.dumps({'categories': df_cat.to_dict(orient='records'),
                    'subcategories': df_subcat.to_dict(orient='records')
                    })

@settings.route('/<string:name>/edit_settings/', methods=['POST'])
def edit_settings(name):

    account = Account.query.filter_by(name=name).first_or_404()

    if request.method == "POST":

        try:

            data = json.loads(request.data)

            if data.get('category') is not None:

                # get required settings
                set = CategorySettings.query.filter_by(
                account_id = account.id,
                category = data.get('category')).first()

                set.category = data.get('category')
                set.limit = float(data.get('limit'))
                set.apply = data.get('apply')
                set.save()

            elif data.get('subcategory') is not None:

                # get required settings
                set = SubCategorySettings.query.filter_by(
                account_id = account.id,
                subcategory = data.get('subcategory')).first()

                set.subcategory = data.get('subcategory')
                set.limit = float(data.get('limit'))
                set.apply = data.get('apply')
                set.save()

        except:
            print ("Settings had an error!")

    return redirect(url_for('settings.show_account_settings', name=account.name))

@settings.route('/<string:name>/add_new_category/', methods=['POST'])
def add_new_category(name):

    account = Account.query.filter_by(name=name).first_or_404()

    form = NewCategoryForm()
    if form.validate_on_submit() and form.submit.data:

        set = CategorySettings(accountid=account.id,
        category=form.category.data,
        limit=form.limit.data,
        unit=form.unit.data,
        apply=form.apply.data)
        set.save()



    return redirect(url_for('settings.show_account_settings', name=account.name))

@settings.route('/<string:name>/add_new_subcategory/', methods=['POST'])
def add_new_subcategory(name):
    account = Account.query.filter_by(name=name).first_or_404()

    form = NewSubCategoryForm()
    if form.validate_on_submit() and form.submit.data:

        set = SubCategorySettings(accountid=account.id,
        subcategory=form.subcategory.data,
        limit=form.limit.data,
        unit=form.unit.data,
        apply=form.apply.data)
        set.save()

    return redirect(url_for('settings.show_account_settings', name=account.name))
