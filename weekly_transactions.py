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

def week_review(df, start, end)

    x = df.loc[df.transaction_date.ge(start) & df.transaction_date.ge(end)]

    daily_backup = x.groupby(pd.Grouper(key='transaction_date', freq='d'))\
        .agg(NumOfTransactions=('transaction_id', 'nunique'),
             RevenueByDay=('order_total', 'sum'))

    daily_summary = daily_backup.describe()

    weekly_backup = x.groupby(pd.Grouper(key='transaction_date',freq='W'))\
        .agg(NumOfTransactions = ('transaction_id','nunique'), RevenueByDay = ('order_total','sum'))

    weekly_summary = weekly_backup.describe()

    return daily_backup, daily_summary, weekly_backup,weekly_summary


#:TODO add in function calls to make spreadsheet


