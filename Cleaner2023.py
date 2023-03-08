from heapq import merge
import pandas as pd
import numpy as np
import datetime as dt
import os
import matplotlib.pyplot as plt
import matplotlib.dates as md
from plotly.subplots import make_subplots
from sympy import group
from xlsxwriter.utility import xl_rowcol_to_cell
import matplotlib.ticker as ticker
import seaborn as sns
import calendar
from scipy import stats
from pandas.tseries.offsets import MonthBegin, MonthEnd
import pandas.io.formats.excel
import sidetable
import math
import plotly.express as px
import plotly
import pathlib
import sidetable as stb
import glob

#new to change width
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 20)

idx = pd.IndexSlice

today = dt.datetime.today().strftime("%m/%d/%Y - %H-%M")

os.chdir(os.path.join('/mnt/c/Users/keg5038/Dropbox/BKM - Marketing/Web Sales'))


def open_file():
    """[Read in CSV files from FoxyCart data ]
    """    
    df = pd.concat([pd.read_csv(f) for f in glob.glob('./CSV_Files_2020-02/*.csv')])

    #convert transaction_date to date
    
    df['transaction_date'] = pd.to_datetime(df.transaction_date)

    #have to do fillna here because otherwise it's getting wiped out
    #have to sort to ffill
    df = df.sort_values(['transaction_id','transaction_date'])
    #way to fillna only based on transaction_id
    df.loc[:,:'category_code'] = df.loc[:,:'category_code'].fillna(df.groupby('transaction_id').ffill())

    #filtering to look at things post 2018
    df = df.loc[df['transaction_date'].ge('2018')]

    df = df.drop_duplicates()

    #dropping duplicates in case dates of pulls are messed up
    # df = df.drop_duplicates()
    
    #cleaning product_name
    df['product_name'] = df['product_name'].replace('\s+', ' ', regex=True)

    #added in because
    #product_price_x_quantity - multiples product_price x product_quantity from original dataframe
    df['product_price_x_quantity'] = df['product_price'] * df['product_quantity']

    #needed to fill in blanks
    df = df.apply(lambda x: x.fillna(0) if x.dtype.kind in 'biufc' else x.fillna('-'))

    #pre_post = email blast, not when shipping changes were implemented
    df['Pre_Post'] = np.where(df['transaction_date'].ge('2020-03-17'),"Post","Pre")

    return df
# open_file().to_excel("sdfdlkjadfkj.xlsx")
df = open_file()


# (df.loc[df.transaction_date.ge('2022-10-01')].groupby(['product_name','product_code','product_options','product_weight','product_price'])
#     .agg(MaxDate = ('transaction_date','max'))
#     .sort_values(['product_name'])
#     .reset_index()).to_excel('ProductsSoldSMALL.xlsx')


df[['transaction_date','transaction_id','shipping_first_name','shipping_last_name','shipping_address1','shipping_city','shipping_state','shipping_postal_code','customer_email','shipping_phone','product_name','product_code','product_quantity']]

def ship_log():
    '''
    Shipping Document - where we pull in from the office sheet
    '''
    ship_log =pd.read_excel(os.path.join('/mnt/c/Users/keg5038/Dropbox/Shared Folder - Birkett Mills Office/Fedex Shipping Log.xlsx'))
    return ship_log


y = ship_log()

df.tail(10)
y.tail(10)

y['transaction_id']
df.loc[df['transaction_id'].isin([y['transaction_id']])]