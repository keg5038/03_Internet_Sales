'''
Function to

'''
import pandas as pd
import numpy as np
import datetime as dt
import os
import matplotlib.pyplot as plt
import matplotlib.dates as md
from xlsxwriter.utility import xl_rowcol_to_cell
import matplotlib.ticker as ticker
import a_functions as a_fun

today = dt.datetime.today().strftime("%m/%d/%Y - %H-%M")

def week_review(df, start, end):
    '''

    Parameters
    ----------
    df: dataframe to use; y is best to use
    start: start date to use
    end: end date - should be the last day of month to include

    Returns
    -------
    Excel spreadsheet with four tabs
    '''

    x = df.loc[df.transaction_date.ge(start) & df.transaction_date.le(end)]

    daily_backup = x.groupby(pd.Grouper(key='transaction_date', freq='d'))\
        .agg(NumOfTransactions=('transaction_id', 'nunique'),
             RevenueByDay=('order_total', 'sum'))

    daily_summary = daily_backup.describe()

    weekly_backup = x.groupby(pd.Grouper(key='transaction_date',freq='W'))\
        .agg(NumOfTransactions = ('transaction_id','nunique'), RevenueByDay = ('order_total','sum'))

    weekly_summary = weekly_backup.describe()

    # return daily_backup, daily_summary, weekly_backup,weekly_summary
    dfs = [daily_summary,daily_backup, weekly_summary, weekly_backup]


    a_fun.dfs_tab(dfs,
                  ['Daily Summary','Daily Details','Weekly Summary','Weekly Details'],
                  'Summary Data as of.xlsx')



