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

price = pd.read_excel('Product_Pricing.xlsx')

'''
created clean dataframe to get unique list of products
'''

clean = df[['product_name','product_options','product_weight','product_price']].drop_duplicates().sort_values('product_weight')
clean['product_name'] = clean['product_name'].replace('\s+', ' ', regex=True)
clean['normalized_product'] = np.nan
clean['brand'] = np.nan
clean['normalized_units'] = np.nan



print(clean)
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

'''
This is to pull info for Andrew
'''
x = df.loc[df['transaction_date'].ge('2020')]

a = x.groupby(['transaction_id','transaction_date','product_name']).agg(Retail_Amount = ('product_price','sum'), Quantity = ('product_quantity','sum'))

b = x[['transaction_id','transaction_date','shipping_total','customer_state','customer_postal_code']].drop_duplicates()
c = pd.merge(a.reset_index('product_name'),b.set_index(['transaction_id','transaction_date']), left_index=True, right_index=True)

c.set_index('product_name',append=True)
c = c.assign(shipping_discount = lambda x: round(x['shipping_total'] * .85,2))
c['flat_shipping'] = 10
c['shipping_difference'] = c['shipping_total'] - c['flat_shipping']
c['Distributor_Amount'] = np.nan
c['Retail-Distributor'] = np.nan
c = c[['Quantity','customer_state','customer_postal_code','Retail_Amount','Distributor_Amount','Retail-Distributor','shipping_total','shipping_discount','flat_shipping','shipping_difference']]

'''
Night of 3/18/20 Stuff
'''
#merging 2020 dataframe with price spreadsheet that has distributor price
y = pd.merge(x,price,how='left',on=['product_name','product_options','product_price','product_weight'])
y['combined'] = y['product_name'].astype(str) + "-" + y['product_quantity'].astype(str) + " Units"


#creating dataframe with details
order_details = y.groupby(['transaction_id','transaction_date','product_name','product_quantity','product_weight','product_options'])\
    .agg({'product_price':'sum','Distributor_Price':'sum','product_total':'sum'})\
    .assign(Margin_Per_Product = lambda x: x['product_price'] - x['Distributor_Price'])\
    .reset_index('product_quantity')\
    .assign(Total_Margin_Order = lambda x: x['product_quantity'] * x['Margin_Per_Product'])

order_summary_margin = order_details[['product_price','Total_Margin_Order']].groupby(level=[0,1]).sum()
order_summary_units = y.groupby(['transaction_id','transaction_date'])['combined'].apply(','.join)

order_total = pd.concat([order_summary_margin,order_summary_units],axis=1)
order_total = order_total[['combined','product_price','Total_Margin_Order']]

print(df)

