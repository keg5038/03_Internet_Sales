'''

Import & normalize retail sales data

'''

from os.path import join
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
import weekly_transactions
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

#import df from all csv files from internet transactions
df = pd.concat([pd.read_csv(f) for f in glob ('./CSV_Files_2020-02/*.csv')])

def clean_df(df=df):
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

    #add in coupons used to make sense of discount
    df['coupon_normalized'] = df['coupons_used'].str.split(":").str[0]
    
    #needed to fill in blanks
    df = df.apply(lambda x: x.fillna(0) if x.dtype.kind in 'biufc' else x.fillna('-'))
    df['coupon_used?'] = np.where(df['coupon_normalized'].eq('-'),'No','Yes')
    # #pre_post = email blast, not when shipping changes were implemented
    # df['Pre_Post'] = np.where(df['transaction_date'].ge('2020-03-17'),"Post","Pre")

    return df

def clean_fed():
    '''
    Cleaning FedEx File

    '''
    fed = pd.concat([pd.read_csv(f) for f in glob ('./FedEx_Files/*.csv')])

    cols = ['Shipment Date(mm/dd/yyyy)','Shipment Delivery Date (mm/dd/yyyy)','Invoice Date (mm/dd/yyyy)']
    for col in cols:
        fed[col] = pd.to_datetime(fed[col],format="%m/%d/%Y")

    fed = fed.rename(columns={'Shipment Date(mm/dd/yyyy)':'Date_Shipment',
                              'Shipment Delivery Date (mm/dd/yyyy)':'Date_Delivery',
                              'Invoice Date (mm/dd/yyyy)':'Date_Invoice'})
    fed = fed.drop_duplicates().sort_values('Date_Invoice')

    return fed

df = clean_df()

fed = clean_fed()


'''
Pricing Spreadsheet to Pull up Distributor Pricing
'''
#will need to update price if pricing has been updated
#update the 
price = pd.read_excel('Product_Pricing.xlsx')

def check_pricing_spreadsheet():
    #check for new products / price combo
    x = df.loc[df['transaction_date'].ge('2020-04-01')][['product_name','product_options','product_price','product_weight']].drop_duplicates()
    y = price[['product_name','product_options','product_price','product_weight']].drop_duplicates()

    return x.merge(y, how='outer',indicator=True).loc[lambda x: x['_merge'].isin(['left_only'])]
    # .to_excel('Discrepancies.xlsx')
check_pricing_spreadsheet()


'''
Shipping Document - where we pull in from the office sheet
'''
ship_log =pd.read_excel(os.path.join(os.getenv('HOME'),
                                     'Dropbox/Shared Folder - Birkett Mills Office/Fedex Shipping Log (SRTWP 11.06.06).xlsx'))

date_to_test = '2020-08-01'

def combine_df_price(df=df, start=date_to_test):
    """Return dataframe combined with transaction log & product df'

    Args:
        df ([type], optional): [description]. Defaults to df.
        start (str, optional): [description]. Defaults to '2018-01-01'.

    Returns:
        [type]: [description]
    """    
    x = df.loc[df['transaction_date'].ge(start)]
    '''
    y - 
    Dataframe shows all transactions since 2018, merged with pricing spreadsheet (price)
    '''
    y = pd.merge(x,price,how='left',on=['product_name','product_options','product_price','product_weight'])
    
    return y


def order_details(df=combine_df_price()):
    #order details
    y = df
    #product_price_x_quantity - multiples product_price x product_quantity from original dataframe
    y['product_price_x_quantity'] = y['product_price'] * y['product_quantity']

    y['product_units'] = y['product_name'].astype(str) + "-" + y['product_quantity'].astype(str) + " Units"
    y['units_total'] = y['product_quantity'] * y['units_normalized']

    #this was wrong - make sure weight_total was right
    y['weight_total'] = y['product_quantity'] * y['product_weight']

    y['net_margin_per_item'] = y['product_quantity'] * (y['product_price'] - y['distributor_price'])

    return y

def order_summary(df=order_details()):
    x = df[['transaction_id','transaction_date','customer_last_name','shipping_total','discount_total','customer_state','customer_postal_code',
            'shipping_state','shipping_postal_code','coupon_normalized','coupon_used?']].drop_duplicates()

    #put in shipping info - free, tier 1, tier 2 etc.
    conditions = [x['shipping_total'].eq(0), \
                x['shipping_total'].eq(5),\
                x['shipping_total'].eq(10)]
    choices = ['Free','$5','$10']  

    x['Shipping_Tier'] = np.select(conditions, choices,default='Other')
    x = x.set_index('transaction_id')
    return x

def order_details_agg(df=order_details()):
    x = df
    
    x = x.groupby('transaction_id').agg(Order_Weight=('weight_total','sum'),
            Order_Revenue=('product_price_x_quantity','sum'),
            Order_Margin=('net_margin_per_item','sum'))
    return x

def combine_detail_order_fedex():
    c = pd.merge(order_details_agg(),order_summary(),left_index=True, right_index=True)
    d = ship_log[['Order #','Actual Freight Expense']].drop_duplicates().rename(columns = {'Order #':'transaction_id'}).set_index('transaction_id')
    
    e = order_details()
    e = e.groupby('transaction_id')['product_units'].apply(list)
    
    m = pd.merge(c,d, how='left',left_index=True,right_index=True)
    
    m = pd.merge(m,e, how='left',left_index=True,right_index=True)

    m['Order_Margin_Minus_Shipping'] = m['Order_Margin'] + m['shipping_total'] - m['Actual Freight Expense']

    m['Net_Order_Margin'] = m['Order_Margin_Minus_Shipping'] + m['discount_total']

    m['Good_v_Bad'] = np.where(m['Net_Order_Margin'].ge(0),'Good','Bad')

    return m


#sanity check this get it right order
x = combine_detail_order_fedex()
x.iloc[3]

sns.scatterplot(x='Order_Revenue',y='Net_Order_Margin',hue='coupon_normalized',data=x)

'''
DataFrame for plotting scatterplots
'''
plot_df = order_total_ship_log.loc[order_total_ship_log['Actual Freight Expense'].notnull()].reset_index()

plot = pd.merge(plot_df, kkk[['Recipient State/Province_x','Zone-State']], left_on=['customer_state'], right_on=['Recipient State/Province_x']).drop('Recipient State/Province_x', axis=1)

def joint_plot_function(df_master=plot, x='product_price_x_quantity', y='Net_Margin', hue='Shipping_Discount?', hue_option='No'):
    '''

    Parameters
    ----------
    df_master : df to pass that has all data; ususally plot
    x: data for x-axis
    y: data for y-axis
    hue : column to split data on
    hue_option : one of two values to filter df_master on; 'No' or 'Good' depending on hue column

    Returns
    -------
    creates plot with scatterplot & histograms; allows for 'hue' argument

    '''
    df_master = df_master.loc[df_master['weight_total'].lt(45)]
    g = sns.JointGrid(x=x, y=y, data=df_master)
    g_1 = df_master.loc[df_master[hue].eq(hue_option)]
    g_2 = df_master.loc[df_master[hue].ne(hue_option)]

    sns.scatterplot(x=g_1[x], y=g_1[y],
                    color='r',
                    label=df_master.loc[df_master[hue].eq(hue_option)][hue].unique(),
                    ax=g.ax_joint)
    sns.scatterplot(x=g_2[x], y=g_2[y],
                    color='b',
                    label=df_master.loc[df_master[hue].ne(hue_option)][hue].unique(),
                    ax=g.ax_joint)
    sns.distplot(g_1[x], kde=False, color='r', ax=g.ax_marg_x)
    sns.distplot(g_2[x], kde=False, color='b', ax=g.ax_marg_x)
    sns.distplot(g_1[y], kde=False, color='r', ax=g.ax_marg_y, vertical=True)
    sns.distplot(g_2[y], kde=False, color='b', ax=g.ax_marg_y, vertical=True)
    plt.suptitle('Impact of ' + hue + ' on ' + x + ' and ' + y)
    plt.savefig('Impact of ' + hue + ' on ' + x + ' and ' + y)

joint_plot_function()
#:TODO have to set fig size


# sns.pairplot(plot[['customer_state','weight_total','product_price_x_quantity','Total_Margin_Order','Net_Margin','Actual Freight Expense','Positive/Negative','new_v_old']], kind='scatter', diag_kind = 'hist',hue='New_v_Old_Pricing')

# sns.pairplot(plot[['weight_total','product_price_x_quantity','Total_Margin_Order','Actual Freight Expense','Positive/Negative']], kind='scatter', diag_kind = 'hist',hue='Positive/Negative')

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
    email = df_use.groupby(['customer_email','Pre_Post']).agg(Count = ('transaction_id','nunique'),\
             Last_Date = ('transaction_date','max'), \
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



#:TODO turn this into a function

# New plotting:

'''
df['Year'] = df.transaction_date.dt.year
df['WeekofYear'] = df.transaction_date.dt.weekofyear
p = df.loc[df.transaction_date.ge('2017-01-01')]

pa = p.groupby(['Year','WeekofYear'], dropna=False).agg(Unique_Transactions=('transaction_id','nunique'),Sales =('order_total','sum')).unstack(0).fillna(0).stack().fillna(0).reset_index()
fig,(ax1, ax2, ax3) = plt.subplots(nrows=3,ncols=1, sharex=True, sharey=True, constrained_layout=True, figsize =(12,9))
ax1.yaxis.set_major_formatter('${x:,.0f}')
ax1.set_ylim((0,6000))

pa.loc[pa['Year'].eq(2018)].plot(kind='bar',x='WeekofYear',y='Sales', ax=ax1)
ax1.set_title('2018')

pa.loc[pa['Year'].eq(2019)].plot(kind='bar',x='WeekofYear',y='Sales', ax=ax2)
ax2.set_title('2019')

pa.loc[pa['Year'].eq(2020)].plot(kind='bar',x='WeekofYear',y='Sales', ax=ax3)
ax3.set_title('2020')
ax3.set_xlabel('Week of Year')
fig.suptitle("Online Sales Revenue by Week",fontsize=16)
plt.savefig('Weekly Sales by Revenue.jpg')
plt.show()

#weekly transactions:
fig,(ax1, ax2, ax3) = plt.subplots(nrows=3,ncols=1, sharex=True, sharey=True, constrained_layout=True, figsize =(12,9))

pa.loc[pa['Year'].eq(2018)].plot(kind='bar',x='WeekofYear',y='Unique_Transactions', ax=ax1, color='green')
ax1.set_title('2018')

pa.loc[pa['Year'].eq(2019)].plot(kind='bar',x='WeekofYear',y='Unique_Transactions', ax=ax2,color='green')
ax2.set_title('2019')

pa.loc[pa['Year'].eq(2020)].plot(kind='bar',x='WeekofYear',y='Unique_Transactions', ax=ax3,color='green')
ax3.set_title('2020')
ax3.set_xlabel('Week of Year')
fig.suptitle("Online Weekly Unique Transactions",fontsize=16)
plt.savefig('Weekly Unique Transactions.jpg')
plt.show()
'''

'''
#look at Thanksgiving holidays
#2018: 11/22 - 11/25 2018 -
#2019: 11/28 - 12/01
#2020: 11/26 - 11/29

mask1 = df['transaction_date'].ge('2018-11-22') & df['transaction_date'].le('2018-11-26')
mask2 = df['transaction_date'].ge('2019-11-28') & df['transaction_date'].le('2019-12-02')
mask3 = df['transaction_date'].ge('2020-11-26') & df['transaction_date'].le('2020-11-30')
p = df.loc[mask1 | mask2 | mask3]
p.groupby(['Year']).agg(Unique_Transactions=('transaction_id','nunique'),Sales=('product_price_x_quantity','sum'))
p.iloc[3]
'''# a_fun.dfs_tab(df_list,df_names,workbook_name )


