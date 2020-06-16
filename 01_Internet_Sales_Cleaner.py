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

today = dt.datetime.today().strftime("%m/%d/%Y - %H-%M")

os.chdir(os.path.join(os.getenv('HOME'),
    'Dropbox/BKM - Marketing/Web Sales'))


df = pd.concat([pd.read_csv(f) for f in glob ('./CSV_Files_2020-02/*.csv')])
print(df)
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

#needed to fill in blanks
df = df.apply(lambda x: x.fillna(0) if x.dtype.kind in 'biufc' else x.fillna('-'))

#pre_post = email blast, not when shipping changes were implemented
df['Pre_Post'] = np.where(df['transaction_date'].ge('2020-03-17'),"Post","Pre")


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

'''
Fedex sheet for labels
'''
'''label = pd.read_csv(os.path.join(os.getenv('HOME'),
                                     'Dropbox/BKM - Marketing/Web Sales/FedEx_Files/fedex_upload_master.csv'))'''


'''
This is to pull info for Andrew
'''
# x is just filtered dataframed
#changed 6/4
x = df.loc[df['transaction_date'].ge('2018')]

'''
Night of 3/18/20 Stuff
'''
#merging 2020 dataframe with price spreadsheet that has distributor price
y = pd.merge(x,price,how='left',on=['product_name','product_options','product_price','product_weight'])
y['combined'] = y['product_name'].astype(str) + "-" + y['product_quantity'].astype(str) + " Units"
y['units_total'] = y['product_quantity'] * y['units_normalized']
#this was wrong - make sure weight_total was right
y['weight_total'] = y['product_quantity'] * y['product_weight']

#creating dataframe with details
date_to_use = '2020-03-23'

order_details = y.loc[y.transaction_date.ge(date_to_use)]\
    .groupby(['transaction_id','transaction_date','customer_last_name','customer_state',
                           'customer_postal_code','product_name','product_quantity','product_weight','product_options'])\
    .agg({'product_price_x_quantity':'sum','distributor_price':'sum','product_total':'sum','product_price':'sum','weight_total':'sum'})\
    .assign(Margin_Per_Product = lambda x: x['product_price'] - x['distributor_price'])\
    .reset_index('product_quantity')\
    .assign(Total_Margin_Order = lambda x: x['product_quantity'] * x['Margin_Per_Product'])

order_details = order_details[['product_quantity','product_price','weight_total','product_price_x_quantity','distributor_price','Margin_Per_Product','Total_Margin_Order']]

order_summary_margin = order_details[['weight_total','product_price_x_quantity','Total_Margin_Order']].groupby(level=[0,1,2,3]).sum()
order_summary_units = y.loc[y.transaction_date.ge(date_to_use)].groupby(['transaction_id','transaction_date','customer_last_name','customer_state'])['combined'].apply(', \n'.join)

order_total = pd.concat([order_summary_margin,order_summary_units],axis=1)
order_total = order_total[['combined','weight_total','product_price_x_quantity','Total_Margin_Order']]

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

#summary of actions
summary = order_total_ship_log.loc[order_total_ship_log['Actual Freight Expense'].notnull()]

summary = summary[['product_price_x_quantity','Total_Margin_Order','Actual Freight Expense',"Net_Margin"]].sum()

summary = summary.rename({'product_price_x_quantity':'Total Revenue (not including shipping)',
                          'Total_Margin_Order':'Margin on Product v. Distributor Cost',
                          'Actual Freight Expense':'Actual Freight Expense',
                         "Net_Margin" : "Net Margin after Shipping"})




'''
DataFrame for plotting scatterplots
'''
p = order_total_ship_log.loc[order_total_ship_log['Actual Freight Expense'].notnull()].reset_index()

#:TODO look at how many pieces vs. shipping costs
# FedEx Part 2 - will replace above lookup stuff if figured out

#:TODO needs to be cleaned up
k = fed.loc[fed['Pricing zone'].notnull() &
            fed['Pricing zone'].ne('Non Zone')][['Pricing zone','Recipient State/Province','Shipment Tracking Number']].drop_duplicates()
k['Pricing zone'] = k['Pricing zone'].astype(int)
kk = k.groupby(['Recipient State/Province','Pricing zone']).agg(count = ('Shipment Tracking Number','size'))
kk = kk.sort_values(by=['Recipient State/Province','count'],ascending=[True,False]).groupby(level=0).head(1)
kk = kk.reset_index().drop('count',axis=1)
kl = kk.groupby('Pricing zone')['Recipient State/Province'].apply(list).reset_index()

kl.reset_index()
kl['Zone-State'] = kl['Pricing zone'].astype(str)+ "-" + kl['Recipient State/Province'].astype(str)
kkk = pd.merge(kk.set_index('Pricing zone'), kl.set_index('Pricing zone'), left_index=True, right_index=True).reset_index()
n = pd.merge(p, kkk[['Recipient State/Province_x','Zone-State']], left_on=['customer_state'], right_on=['Recipient State/Province_x']).drop('Recipient State/Province_x', axis=1)
n['New_v_Old_Pricing'] = np.where(n['transaction_date'].ge('2020-03-25'),'New Pricing','Old Pricing')

#THIS WORKS AS INTENDED
# sns.scatterplot(x='weight_total',y='Net_Margin', hue='Zone-State', style='New_v_Old_Pricing', data=n).set(title='Weight v Net Margin as of 2020-04-10')

# sns.pairplot(n[['customer_state','weight_total','product_price_x_quantity','Total_Margin_Order','Net_Margin','Actual Freight Expense','Positive/Negative','New_v_Old_Pricing']], kind='scatter', diag_kind = 'hist',hue='New_v_Old_Pricing').savefig('teest2.png')

# sns.pairplot(n[['customer_state','weight_total','product_price_x_quantity','Total_Margin_Order','Net_Margin','Actual Freight Expense','Positive/Negative']], kind='scatter', diag_kind = 'hist',hue='Positive/Negative').savefig('teest.png')

#:TODO figure out groupby to get max for each state
#:TODO delete all of below, including p1 p2


df_list = [summary, order_total_ship_log, order_details, order_total ]
df_names = ["Summary",'Margin per Order', 'Details','Backup']
workbook_name = "Web Orders as of .xlsx"

'''
Looking at repeat customers for shipping
'''
dupes = df.loc[df['transaction_date'].dt.year.ge(2012)]\
    [['transaction_id','shipping_last_name','customer_last_name','transaction_date','shipping_postal_code','customer_email',
      'customer_postal_code','Pre_Post']].drop_duplicates()

def unique_sales(df_use):
    '''
    :param df_use: dataframe to pass - dupes
    :type df_use: 
    :return: will return 3 dataframes
    :rtype: 
    '''

    #looking at email addresses
    email = df_use.groupby(['customer_email','Pre_Post']).agg(Count = ('transaction_id','nunique'),
             Last_Date = ('transaction_date','max'),
             First_Date = ('transaction_date','min')).unstack().fillna(0)

    e1 = email['Count','Pre'].ne(0)
    e2 = email['Count','Post'].ne(0)
    email_common = email.loc[e1 & e2].reorder_levels([1,0],axis=1)\
        .sort_index(level=[0,1],ascending=[False,True], axis=1)

    # looking at customer last name & customer postal code
    cust_post = df_use.groupby([df_use['customer_last_name'].str.lower(),'customer_postal_code', 'Pre_Post'])\
        .agg(Count=('transaction_id', 'nunique'),
            Last_Date=('transaction_date', 'max'),
            First_Date=('transaction_date', 'min')).unstack().fillna(0)

    c1 = cust_post['Count', 'Pre'].ne(0)
    c2 = cust_post['Count', 'Post'].ne(0)
    cust_post_common = cust_post.loc[c1 & c2].reorder_levels([1,0],axis=1)\
        .sort_index(level=[0,1],ascending=[False,True], axis=1)

    #looking at customer last name & shipping postal code
    ship_post = df_use.groupby([df_use['customer_last_name'].str.lower(), 'shipping_postal_code', 'Pre_Post']) \
        .agg(Count=('transaction_id', 'nunique'),
             Last_Date=('transaction_date', 'max'),
             First_Date=('transaction_date', 'min')).unstack().fillna(0)

    s1 = ship_post['Count', 'Pre'].ne(0)
    s2 = ship_post['Count', 'Post'].ne(0)
    ship_post_common = ship_post.loc[s1 & s2].reorder_levels([1,0],axis=1)\
        .sort_index(level=[0,1],ascending=[False,True], axis=1)

    #looking at shipping last name & shipping postal code
    ship_name = df_use.groupby([df_use['shipping_last_name'].str.lower(), 'shipping_postal_code', 'Pre_Post']) \
        .agg(Count=('transaction_id', 'nunique'),
             Last_Date=('transaction_date', 'max'),
             First_Date=('transaction_date', 'min')).unstack().fillna(0)

    n1 = ship_name['Count', 'Pre'].ne(0)
    n2 = ship_name['Count', 'Post'].ne(0)
    ship_name_common = ship_name.loc[n1 & n2].reorder_levels([1,0],axis=1)\
        .sort_index(level=[0,1],ascending=[False,True], axis=1)


    return email_common, cust_post_common, ship_post_common, ship_name_common

## Looking at unique email vs. unique transactions
# before = a.index.get_level_values(0)
# df['Repeat_v_New'] = np.where(df['customer_email'].isin(before),'Repeat_Customer','New_Customer')
# df.groupby(['Pre_Post','Repeat_v_New']).agg(uni_email = ('customer_email','nunique'), uniq_tran = ('transaction_id','nunique'))


#looking at sales of units
'''
s = y.loc[y['transaction_date'].ge('2020-03-16')]\
    .groupby(['product_normalized','case_v_unit',pd.Grouper(key='transaction_date',freq='W')])\
    .agg({'product_quantity':'sum','units_total':'sum','transaction_id':'nunique'})\
    .unstack().fillna(0).sort_index(1).sort_index(level=[0,1],ascending=[True,False])
    
poc = y.loc[(y['transaction_date'].le('2020-03-22') & y['transaction_date'].ge('2020-03-15')) & (y.product_normalized.str.contains('pocono cre',case=False))]

'''


def fedex_log_printout(start):
    '''

    :param start: date to use to filter everything after
    :type start:
    :return: file to excel to copy & paste
    :rtype:
    '''
    #create DF of what you need
    f = y[['transaction_id','transaction_date','shipping_first_name','shipping_last_name',
           'shipping_address1','shipping_address2','shipping_city','shipping_state','shipping_postal_code',
           'shipping_country','customer_phone','product_normalized','units_total','weight_total','item_code']]

    #look up transactions that are in FedEx log already; if in, not necessary to add in
    p = ship_log['Order #'].unique()

    f = f.loc[f['transaction_date'].ge(start) & ~f['transaction_id'].isin(p)]
    f['customer'] = f['shipping_first_name'] + " " + f['shipping_last_name']

    f[['transaction_id', 'customer', 'customer_phone', 'item_code', 'product_normalized', 'units_total']].to_excel(
        'To Add Fedex Log.xlsx')

    return f[['transaction_id','customer','customer_phone','item_code','product_normalized','units_total']]




#print(len(a),len(b),len(c),len(d))

'''
looking at new pricing on free shipping
2020/06/04

# :TODO do same math, but on what $5 shipping would look like on orders over a certain threshold;  
m = n.loc[n['weight_total'].lt(45)]
m['ship_thresh'] =np.where(m['product_price_x_quantity'].ge(59),'Free','Not_Free')
m['updated_margin'] = np.where(m['ship_thresh'].eq('Free'),m['Net_Margin']-10,m['Net_Margin'])
sns.pairplot(m[['product_price_x_quantity','updated_margin','Actual Freight Expense','ship_thresh']], kind='scatter', diag_kind = 'hist',hue='ship_thresh')

m2 = m.loc[m['ship_thresh'].eq('Free')]
m1= m.loc[m['ship_thresh'].eq('Not_Free')]
g = sns.jointplot(x=m1['product_price_x_quantity'],y=m1['updated_margin'], color='r')
g.x = m2['product_price_x_quantity']
g.y = m2['updated_margin']
g.plot_joint(plt.scatter,marker='x', c='b',s=50)
g.plot_marginals(plt.hist, c='b')

#this works as intended
g = sns.JointGrid(x='product_price_x_quantity',y='updated_margin',data=m)
sns.scatterplot(x =m2['product_price_x_quantity'], y= m2['updated_margin'], color='r', ax=g.ax_joint)
sns.scatterplot(x =m1['product_price_x_quantity'], y= m1['updated_margin'], color='b', ax=g.ax_joint)
sns.distplot(m2['product_price_x_quantity'],kde=False, color='r', ax=g.ax_marg_x)
sns.distplot(m1['product_price_x_quantity'],kde=False, color='b', ax=g.ax_marg_x)
sns.distplot(m2['updated_margin'],kde=False, color='r', ax=g.ax_marg_y, vertical=True)
sns.distplot(m1['updated_margin'],kde=False, color='b', ax=g.ax_marg_y, vertical=True)
'''

# '''
# put above in function
# def joint_plot_free_shipping(df, df1, df2, thresh):
#     '''
#
#     :param df: master df to pass; usually 'n'
#     :type df:
#     :param df1:
#     :type df1:
#     :param df2:
#     :type df2:
#     :param thresh:
#     :type thresh:
#     :return:
#     :rtype:
#     '''
#     #
#     df.loc
#
# '''

'''
new 2020-06-15
looking at weekend sales
k = y.loc[y.transaction_date.dt.year.ge(2020)].groupby([y['transaction_date'].dt.dayofweek,y['transaction_date'].dt.day_name(),y['transaction_date'].dt.weekofyear]).agg(UniqueTransactions=('transaction_id','nunique'), DollarSales = ('product_price_x_quantity','sum')).assign(AvgTicket = lambda x: x['DollarSales'] / x['UniqueTransactions'])

y.loc[y.transaction_date.dt.year.ge(2020)].groupby([y['transaction_date'].dt.dayofweek,y['transaction_date'].dt.day_name(),y['transaction_date'].dt.weekofyear]).agg(UniqueTransactions=('transaction_id','nunique'), DollarSales = ('product_price_x_quantity','sum')).assign(AvgTicket = lambda x: x['DollarSales'] / x['UniqueTransactions']).loc[idx[:,:,12:],idx[:]].unstack([-1])

a = y.loc[y.product_price_x_quantity.ge(59) & y.transaction_date.ge('2020-03-01')].groupby([pd.Grouper(key='transaction_date',freq='W-MON')]).agg(NumTransactions_over_59 = ('transaction_id','nunique'))
b = y.loc[y.product_price_x_quantity.lt(59) & y.transaction_date.ge('2020-03-01')].groupby([pd.Grouper(key='transaction_date',freq='W-MON')]).agg(NumTransactions_under_59 = ('transaction_id','nunique'))
pd.concat([a,b],join='outer', axis=1).assign(Percent_of_Total_Transactions = lambda x: x['NumTransactions_over_59'] / (x['NumTransactions_over_59'] + x['NumTransactions_under_59'] ))
'''

a_fun.dfs_tab(df_list,df_names,workbook_name )


print(df)