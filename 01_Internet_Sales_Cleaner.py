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

'''
Cleaning for Online Orders Sheet
'''
df['transaction_date'] = pd.to_datetime(df.transaction_date)

#dropping duplicates in case dates of pulls are messed up
df = df.drop_duplicates()
#have to sort to ffill
df = df.sort_values(['transaction_id','transaction_date'])
#way to fillna only based on transaction_id
df.loc[:,:'category_code'] = df.loc[:,:'category_code'].fillna(df.groupby('transaction_id').ffill())
#cleaning product_name
df['product_name'] = df['product_name'].replace('\s+', ' ', regex=True)

#added in because
df['product_price_x_quantity'] = df['product_price'] * df['product_quantity']

'''
Cleaning FedEx File
'''
fed = pd.concat([pd.read_csv(f) for f in glob ('./FedEx_Files/*.csv')])

def date_cleaner(df):
    #fixes dates for fedex file
    cols = ['Shipment Date(mm/dd/yyyy)','Shipment Delivery Date (mm/dd/yyyy)','Invoice Date (mm/dd/yyyy)']
    for col in cols:
        fed[col] = pd.to_datetime(fed[col],format="%m/%d/%Y")

    return fed

fed = date_cleaner(fed)

fed = fed.rename(columns={'Shipment Date(mm/dd/yyyy)':'Date_Shipment',
                              'Shipment Delivery Date (mm/dd/yyyy)':'Date_Delivery',
                              'Invoice Date (mm/dd/yyyy)':'Date_Invoice'})
fed = fed.drop_duplicates().sort_values('Date_Invoice')

'''
Pricing Spreadsheet to Pull up Distributor Pricing
'''
price = pd.read_excel('Product_Pricing.xlsx')

'''
Shipping Document - where we pull in from the office sheet
'''
ship_log =pd.read_excel(os.path.join(os.getenv('HOME'),
                                     'Dropbox/Shared Folder - Birkett Mills Office/Fedex Shipping Log (SRTWP 11.06.06).xlsx'))
# '''
# created clean dataframe to get unique list of products
# '''
#
# clean = df[['product_name','product_options','product_weight','product_price']].drop_duplicates().sort_values('product_weight')
# clean['product_name'] = clean['product_name'].replace('\s+', ' ', regex=True)
# clean['normalized_product'] = np.nan
# clean['brand'] = np.nan
# clean['normalized_units'] = np.nan
#
#
#
# print(clean)
# #read in product map that was created by clean
# lookup = pd.read_excel('product_map_final.xlsx')
#
# kg = pd.merge(df,lookup, how='left',on=['product_name','product_options','product_weight'])
#
#
# '''
# add columns to get total units, total weight, total product sale price for each row
# '''
# kg['total_units'] = kg['normalized_units'] * kg['product_quantity']
# kg['total_weight'] = kg['product_weight'] * kg['product_quantity']
# kg['product_rev'] = kg['product_price'] * kg['product_quantity']
#
# '''
# couple of transforms to summarize by transaction
# '''
# kg['total_weight_order'] = kg.groupby('transaction_id')['total_weight'].transform('sum')
# kg['total_units_order'] = kg.groupby('transaction_id')['total_units'].transform('sum')
#
#
# '''
# Cuttting into bins
# '''
# #bin for revenue of entire order
# bins_rev = np.arange(0,kg['product_total'].max()+10,10)
# kg['rev_bins'] = pd.cut(kg['product_total'],bins=bins_rev)
#
#
# #get dataframe of transactions that have only had Wolff's or Pocono
# y = kg.loc[kg.brand.isin(["Wolff's","Pocono"])]['transaction_id'].unique()
#
# wop = kg.loc[kg.transaction_id.isin(y) & kg.transaction_date.ge('2017')]
#
# '''
# what i was working on that shows
#
# #TODO: fix bins to make them make sense
# #TODO: create heatmap of shipping cost vs. product cost; shipping cost vs. weight
#
# y = wop[['transaction_id','transaction_date','shipping_total','product_total','total_weight_order','total_units_order']].drop_duplicates()
#
#
# wop.groupby([pd.cut(wop['product_total'],bins=[0,10,20,50,100]),pd.cut(wop['shipping_total'],bins=[0,10,20,30,40,91])])['transaction_id'].nunique().unstack()
#
# '''

'''
This is to pull info for Andrew
'''
# x is just filtered dataframe
x = df.loc[df['transaction_date'].ge('2020')]

'''
Night of 3/18/20 Stuff
'''
#merging 2020 dataframe with price spreadsheet that has distributor price
y = pd.merge(x,price,how='left',on=['product_name','product_options','product_price','product_weight'])
y['combined'] = y['product_name'].astype(str) + "-" + y['product_quantity'].astype(str) + " Units"


#creating dataframe with details
order_details = y.groupby(['transaction_id','transaction_date','customer_last_name','customer_state',
                           'customer_postal_code','product_name','product_quantity','product_weight','product_options'])\
    .agg({'product_price_x_quantity':'sum','Distributor_Price':'sum','product_total':'sum','product_price':'sum'})\
    .assign(Margin_Per_Product = lambda x: x['product_price'] - x['Distributor_Price'])\
    .reset_index('product_quantity')\
    .assign(Total_Margin_Order = lambda x: x['product_quantity'] * x['Margin_Per_Product'])

order_details = order_details[['product_quantity','product_price','product_price_x_quantity','Distributor_Price','Margin_Per_Product','Total_Margin_Order']]

order_summary_margin = order_details[['product_price_x_quantity','Total_Margin_Order']].groupby(level=[0,1]).sum()
order_summary_units = y.groupby(['transaction_id','transaction_date'])['combined'].apply(','.join)

order_total = pd.concat([order_summary_margin,order_summary_units],axis=1)
order_total = order_total[['combined','product_price_x_quantity','Total_Margin_Order']]

order_total_ship_log = pd.merge(order_total.reset_index().set_index('transaction_id'),
                                ship_log[['Order #','Actual Freight Expense']].drop_duplicates().set_index('Order #'),
                                how='left',
                                left_index=True,
                                right_index=True)

order_total_ship_log.index = order_total_ship_log.index.set_names('Order #')
order_total_ship_log = order_total_ship_log.set_index('transaction_date',append=True)

order_total_ship_log['Net_Margin'] = \
    order_total_ship_log['Total_Margin_Order'] + \
    10 - \
    order_total_ship_log['Actual Freight Expense']

order_total_ship_log['Positive/Negative'] = np.where(order_total_ship_log['Net_Margin'].ge(0),'Good','Bad')


today = dt.datetime.today().strftime("%m/%d/%Y - %H:%M")
df_list = [order_total_ship_log, order_details, order_total ]
df_names = ['Final', 'Details','Backup']
workbook_name = 'Online Orders as of ' + today + '.xlsx'

#merge good

a_fun.dfs_tab(df_list,df_names,workbook_name )

print(df)

