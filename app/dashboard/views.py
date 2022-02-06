import json
import pandas as pd
import numpy as np

from flask import request
from flask import current_app
from app.models import Account

from datetime import datetime

from app.dashboard import dashboard

@dashboard.route('/<string:name>/chart_data/', methods=['GET', 'POST'])
def get_chart_data(name):

    account = Account.query.filter_by(name=name).first_or_404()
    # get all transactions from the account
    transactions = [transaction.to_dict() for transaction in account.transactions.filter_by(status=True)]

    # format trasaction dataframe nicely
    df = pd.DataFrame.from_dict(transactions)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['yearmonth'] = df['date'].apply(lambda x: x.strftime('%Y-%m'))
        # identify expense or Income
        df['nature'] = np.where(df['amount'] > 0, 'income', 'outgo')
        # good place to add column for closing balance
        df['closing_balance'] = df.amount.cumsum() + account.balance
        # remove white spaces from tags
        df['tag'] = df['tag'].str.strip()

    #df_filtered = filterdata(df, request)
    df_filtered = df[df.nature == 'outgo']
    set_frequency = request.args.get('frequency', '', type=str)

    if set_frequency == 'm':

        df_balance = df_filtered.groupby('yearmonth')['closing_balance'].last().reset_index()

        df_tag_pivoted = pivotData(df_filtered, 'yearmonth', 'tag', '')
        df_cat_pivoted = pivotData(df_filtered, 'yearmonth', 'category', '')
        df_subcat_pivoted = pivotData(df_filtered, 'yearmonth', 'subcategory', '')

        df_tag_privoted_percent = pivotDataPercent(df_tag_pivoted, 'yearmonth')
        df_cat_privoted_percent = pivotDataPercent(df_cat_pivoted, 'yearmonth')
        df_subcat_privoted_percent = pivotDataPercent(df_subcat_pivoted, 'yearmonth')

    elif set_frequency == 'l12m':

        df_balance = df_filtered.set_index('date').last('12M').reset_index() \
                    .groupby('yearmonth')['closing_balance'].last().reset_index()

        df_tag_pivoted = pivotData(df_filtered, 'yearmonth', 'tag', '12m')
        df_cat_pivoted = pivotData(df_filtered, 'yearmonth', 'category', '12m')
        df_subcat_pivoted = pivotData(df_filtered, 'yearmonth', 'subcategory', '12m')

        df_tag_privoted_percent = pivotDataPercent(df_tag_pivoted, 'yearmonth')
        df_cat_privoted_percent = pivotDataPercent(df_cat_pivoted, 'yearmonth')
        df_subcat_privoted_percent = pivotDataPercent(df_subcat_pivoted, 'yearmonth')

    elif set_frequency == 'l3m':

        df_balance = df_filtered.set_index('date').last('3M').reset_index() \
                    .groupby('yearmonth')['closing_balance'].last().reset_index()

        df_tag_pivoted = pivotData(df_filtered, 'yearmonth', 'tag', '3m')
        df_cat_pivoted = pivotData(df_filtered, 'yearmonth', 'category', '3m')
        df_subcat_pivoted = pivotData(df_filtered, 'yearmonth', 'subcategory', '3m')

        df_tag_privoted_percent = pivotDataPercent(df_tag_pivoted, 'yearmonth')
        df_cat_privoted_percent = pivotDataPercent(df_cat_pivoted, 'yearmonth')
        df_subcat_privoted_percent = pivotDataPercent(df_subcat_pivoted, 'yearmonth')

    else:
        df_balance = df.groupby('year')['closing_balance'].last().reset_index()

        df_tag_pivoted = pivotData(df_filtered, 'year', 'tag', '')
        df_cat_pivoted = pivotData(df_filtered, 'year', 'category', '')
        df_subcat_pivoted = pivotData(df_filtered, 'year', 'subcategory', '')

        df_tag_privoted_percent = pivotDataPercent(df_tag_pivoted, 'year')
        df_cat_privoted_percent = pivotDataPercent(df_cat_pivoted, 'year')
        df_subcat_privoted_percent = pivotDataPercent(df_subcat_pivoted, 'year')


    return  json.dumps({
        'frequency' : set_frequency,
        'balance': df_balance.to_dict(orient='records'),
        'by_tags': df_tag_pivoted.to_dict(orient='records'),
        'by_category': df_cat_pivoted.to_dict(orient='records'),
        'by_subcategory': df_subcat_pivoted.to_dict(orient='records'),
        'tags_by_percent': df_tag_privoted_percent.to_dict(orient='records'),
        'cats_by_percent': df_cat_privoted_percent.to_dict(orient='records'),
        'subcats_by_percent': df_subcat_privoted_percent.to_dict(orient='records')
        })

def pivotDataPercent(df, frequency):
    # remove negative numbers to get income
    df_ = df.loc[:, df.columns != frequency]
    mask = df_ < 0
    df_[mask] = 0
    df_['Income'] = df_.sum(axis=1)
    mask = df.drop(frequency, axis=1) > 0
    df[mask] = np.NaN
    df.replace(np.NaN, 0, inplace=True)
    df.loc[df_.index, 'Income'] = df_['Income']

    # process columns
    selected_columns = df.columns.tolist()
    selected_columns.remove(frequency)
    selected_columns.remove('Income')

    # remove Nan and Inf
    df_percent = df.copy()
    df_percent.replace(0, np.nan, inplace=True)
    df_percent.loc[:, df_percent.columns.isin(selected_columns)] = \
    df_percent.loc[:, df_percent.columns.isin(selected_columns)] \
    .div(df_percent.loc[:, df_percent.columns == 'Income'] \
    .sum(axis=1), axis=0).abs() \
    .multiply(100).round(2)

    df_percent.drop(['Income'], axis= 1, inplace = True)

    if 'not provided' in df_percent.columns:
        df_percent.drop(['not provided'], axis= 1, inplace = True)

    df_percent.replace(np.nan, 0, inplace=True)
    df_percent.replace(np.Inf, 0, inplace=True)

    return df_percent

def pivotData(df, period, subject, frequency):

    if frequency != '':
        df_return = df.set_index('date').last(frequency).reset_index()\
            .groupby([period, subject])['amount'] \
            .agg('sum').reset_index() \
            .pivot(index=period, columns=subject, values='amount') \
            .reset_index().rename_axis(None, axis=1) \
            .fillna(0)
    else:
        df_return = df.set_index('date').reset_index()\
            .groupby([period, subject])['amount'] \
            .agg('sum').reset_index() \
            .pivot(index=period, columns=subject, values='amount') \
            .reset_index().rename_axis(None, axis=1) \
            .fillna(0)

    return df_return

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
