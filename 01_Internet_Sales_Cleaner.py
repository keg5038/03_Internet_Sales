'''
Import & normalize retail sales data

'''

import pandas as pd
import numpy as np
import datetime as dt
import os
import matplotlib.pyplot as plt
import matplotlib.dates as md
from xlsxwriter.utility import xl_rowcol_to_cell
import matplotlib.ticker as ticker
import seaborn as sns
import calendar
from pandas.tseries.offsets import MonthEnd
from numbers import Number
import a_functions as a_fun
import math
from glob import glob
sns.set_style('whitegrid')

#new to change width
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 20)

idx = pd.IndexSlice

os.chdir(os.path.join(os.getenv('HOME'),
    'Dropbox/1 BKM and CLM/Python/Misc/Online Sales'))


df = pd.concat([pd.read_csv(f) for f in glob ('./CSV_Files_2020-02/*.csv')])

df['transaction_date'] = pd.to_datetime(df.transaction_date)

df2 = df
#have to sort to ffill
df = df.sort_values(['transaction_id','transaction_date'])

#way to fillna only based on transaction_id
df.loc[:,:'category_code'] = df.loc[:,:'category_code'].fillna(df.groupby('transaction_id').ffill())

df['product_name'] = df['product_name'].replace('\s+', ' ', regex=True)

'''
created clean dataframe to get unique list of products
'''

clean = df[['product_name','product_options','product_weight']].drop_duplicates().sort_values('product_weight')
clean['product_name'] = clean['product_name'].replace('\s+', ' ', regex=True)
clean['normalized_product'] = np.nan
clean['brand'] = np.nan
clean['normalized_units'] = np.nan

#read in product map that was created by clean
lookup = pd.read_excel('product_map_final.xlsx')

kg = pd.merge(df,lookup, how='left',on=['product_name','product_options','product_weight'])


'''
add columns to get total units, total weight, total product sale price for each row
'''
kg['total_units'] = kg['normalized_units'] * kg['product_quantity']
kg['total_weight'] = kg['product_weight'] * kg['product_quantity']
kg['product_rev'] = kg['product_price'] * kg['product_quantity']

'''
couple of transforms to summarize by transaction
'''
kg['total_weight_order'] = kg.groupby('transaction_id')['total_weight'].transform('sum')
kg['total_units_order'] = kg.groupby('transaction_id')['total_units'].transform('sum')


'''
Cuttting into bins
'''
#bin for revenue of entire order
bins_rev = np.arange(0,kg['product_total'].max()+10,10)
kg['rev_bins'] = pd.cut(kg['product_total'],bins=bins_rev)


#get dataframe of transactions that have only had Wolff's or Pocono
y = kg.loc[kg.brand.isin(["Wolff's","Pocono"])]['transaction_id'].unique()

wop = kg.loc[kg.transaction_id.isin(y) & kg.transaction_date.ge('2017')]

'''
what i was working on that shows 

#TODO: fix bins to make them make sense
#TODO: create heatmap of shipping cost vs. product cost; shipping cost vs. weight

y = wop[['transaction_id','transaction_date','shipping_total','product_total','total_weight_order','total_units_order']].drop_duplicates()


wop.groupby([pd.cut(wop['product_total'],bins=[0,10,20,50,100]),pd.cut(wop['shipping_total'],bins=[0,10,20,30,40,91])])['transaction_id'].nunique().unstack()

'''

print(df)

