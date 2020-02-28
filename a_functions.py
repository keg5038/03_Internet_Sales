'''
File to put functions in
Created 2019-10-08

'''

import pandas as pd
import numpy as np
import os
import datetime as dt
from xlsxwriter.utility import xl_rowcol_to_cell

idx = pd.IndexSlice


''''
this is copy & pasted in each document
#TODO - probably a better way to do this at some point

idx = pd.IndexSlice
today = dt.datetime.today().strftime("%m-%d-%Y")

include = ['Buckwheat','Wheat','Feed']
include_all = ['Buckwheat','Seed','Feed','Pancake Mix','Wheat','Hulls']

year_end = 'A-SEP'
qtr_end = 'Q-SEP'
month_end = '2019-09-30'
month_end_digit = pd.to_datetime(month_end).month
month_filt = 'Sep'

month_begin = pd.to_datetime(month_end) - MonthEnd(3)
month_begin = month_begin.strftime('%Y-%m-%d')

as_of = df["Date"].max().strftime("%m-%d-%Y")

last_month = 'Sep 2019'
ytd_months_in = [1,2,3,4,5,6,7,8,9,10,11,12]
non_retail = (~df["Pocono vs. Wolff's"].isin(["Wolff's Case", 'Pocono Case']))
'''
month_dict = {1:'Jan', 2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
col_units = {'Diff':'Difference in Units','Diff_Perc':'Difference %'}
col_pounds = {'Diff':'Difference in Pounds','Diff_Perc':'Difference %'}
col_rev = {'Diff':'Difference in $$','Diff_Perc':'Difference %'}
col3 = {'diff':'Difference','diff_perc':'Difference %'}


def print_test(x):
    '''
    this is a test
    '''
    print(x)


'''
Groupby functions for subtotals
'''

def subtotal_master(DF,agg_fun, myList=[], *args):
    '''
    Creating generic subtotals depending on number of levels passed to it.

    Parameters
    ----------
    DF : dataframe to use
    agg_fun : function to pass to dataframe; doing it this way so can pass multiple agg columns to it
    myList : list to do groupby on
    args

    Returns
    -------
    Returns df with subtotals
    '''
    num_levels = len(myList) - 1

    while num_levels > 0:
        pd.concat(
            DF.groupby(myList).agg(agg_fun)
        )
    #there may be a way to loop through with a while loop to create appending until you run out of lenght of the list
    #three levels would have x, x1, x2 for subtotals



def subtotal_gen(DF, agg_column, myList=[], *args):
    '''
    Function for generic subtotals with NO DATES
    :param DF: dataframe to use
    :param agg_column: column to add, etc.
    :param myList: unlimited number of things to pass to groupby; pass like ['x','y','z']
    :param args: allows it
    :return: DataFrame to return
    '''
    data_sub = pd.concat([
    DF.assign(**{x: '[Total]' for x in myList[i:]}) \
                .groupby(myList).agg(SUM=(agg_column, 'sum')) for i in range(1, len(myList) + 1)]).sort_index().unstack(0)

    data_sub = data_sub.droplevel(0, axis=1)
    data_sub.columns.name = agg_column
    return data_sub


def subtotal_dates(DF, date_switch,date_column, date_month,agg_column, myList=[], *args):
    '''
    Function to perform subtotals for dates in first index
    :param DF: dataframe to use
    :param date: ytd or yoy
    :param agg_column: column to add, etc.
    :param myList: unlimited number of things to pass to groupby; pass like ['x','y','z']
    :param args: allows it
    :return: DataFrame to return
    '''
    if date_switch == 'yoy':
        DF2 = DF

    elif date_switch == 'ytd':
        DF2 = DF.loc[DF[date_column].dt.month.le(date_month)]

    data_sub = pd.concat([
        DF2.assign(**{x: '[Total]' for x in myList[i:]}) \
                .groupby(myList).agg(SUM=(agg_column, 'sum')) for i in range(1, len(myList) + 1)]).sort_index().unstack(0)

    data_sub = data_sub.droplevel(0,axis=1)
    data_sub.columns.name = agg_column
    return data_sub

'''
Function to rename date columns as YOY & YTD
'''
#TODO create function to rename columns YTD & YOY

'''
Function to compute difference & percent difference of last two columns
'''
def diff_and_perc(df_use):
    '''
    Takes DataFrame, figures out difference in last columns, then percent difference
    :param df_use: DataFrame to use
    :return: returns DataFrame
    '''
    df_use = df_use.fillna(0)
    df_use['diff'] = df_use.iloc[:,-1] - df_use.iloc[:,-2]
    df_use['diff_perc'] = (df_use.iloc[:,-2] / df_use.iloc[:,-3]) - 1
    df_use = df_use.rename(columns=col3)
    return df_use



'''
Printing
'''
def print_multi(df_use, list_iterate, date_print):
    '''
    Takes multi index & prints level 0 to separate tab
    :param df_use: dataframe to use
    :param list_iterate: list to iterate through
    :param date_print - pass it date to include in renaming
    :return: separate excel sheets for everything in first index; second index will print to separate tab
    '''
    for a in list_iterate:
        writer = pd.ExcelWriter('{}.xlsx'.format(a + ' as of ' + date_print), engine='xlsxwriter')
        temp = df_use.loc[idx[a,:],idx[:]]
        temp = temp.groupby(temp.index.get_level_values(1))
        for d,s in temp:
            s.reset_index(level=[0],drop=True).to_excel(writer, sheet_name=d)
            worksheet=writer.sheets[d]
        writer.save()


def dfs_tab(df_list, sheet_list, file_name):
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
    for dataframe, sheet in zip(df_list, sheet_list):
        dataframe.to_excel(writer, sheet_name=sheet, startrow=0, startcol=0)
    writer.save()

f = {'Customer_Abbr':'nunique', 'Customer': lambda x: ', \n'.join(sorted(x.unique().tolist())),'Units_Sold':'sum','Date':'max'}

'''
BELOW IS ALL INVENTORY TRANSACTIONS
'''


''''
Creating packaging_used & packaging_used_retail columns that account for
Will use function from a_functions so it can be used across the board as necessary
II- Inventory Issued; simple one to one to record scrap of PO
IR - Made - as simple as one to one for non retail packaging; 6 to one for retail
Creates new columns


'''
#TODO: add normalize_transaction_units & normalize_transaction_units_retail to original 01 file for Inventory/ should be on every single DF

def normalize_transaction_units(df_use):
    '''
    :param df_use:
    :return: returns column when combined with apply that normalizes II, IR
    '''
    if df_use["packaging"] == '-':
        return 0
    elif df_use.product_num.startswith('P0'):
        if df_use['transfer_code'] == "II":
            return abs(df_use['transaction_units'] * -1)
        else:
            return 0

    elif df_use.product_num.startswith('A'):
        if df_use["transfer_code"] == "IR":
            return df_use['transaction_units'] * 1
        else:
            return 0
    # PR is for product 3/4
    elif df_use.product_num.startswith('PR'):
        if df_use["transfer_code"] == "IR":
            return df_use['transaction_units'] * 1
        else:
            return 0

''''
Creating packaging_used & packaging_used_retail columns that account for
Will use function from a_functions so it can be used across the board as necessary
II- Inventory Issued; simple one to one to record scrap of PO
IR - Made - as simple as one to one for non retail packaging; 6 to one for retail
Creates new columns:

'''
def normalize_transaction_units_retail(df_use):
    '''
    :param df_use:
    :return: returns column when combined with apply that normalizes II, IR for RETAIL
    '''
    if df_use["packaging_retail"] == '-':
        return 0
    elif df_use.product_num.startswith('P0'):
        if df_use['transfer_code'] == "II":
            return abs(df_use['transaction_units'] * -1)
        else:
            return 0

    elif df_use.product_num.startswith('A'):
        if df_use["transfer_code"] == "IR":
            return df_use['transaction_units'] * 6
        else:
            return 0

def inventory_summary(df_use):
    ''''
    This function creates two dataframes, one for Retail Pack one for bulk.
    :param df_use - dataframe to use in analysis from 'Inventory File' that is hand typed from Employee counts each month
    :returns pack_count returns inventory of packaging counted by employees at end of the month
    :returns retail_count returns inventory of retail packaging counted by employees at end of the month
    '''
    pack_count = df_use.loc[(df_use['packaging'] != '-') & (df_use['type'] == 'packaging')] \
        .groupby(['packaging', 'item_code', 'date']).agg({'inventory_count': 'sum'}) \
        .unstack() \
        .sort_index(axis=1) \
        .assign(Used_Last_Month=lambda x: x.iloc[:, -1] - x.iloc[:, -2]) \
        .sort_values("Used_Last_Month") \
        .loc[lambda x: x.index.get_level_values(0) != '-'] \
        .rename(columns={'': 'Used Last Month According to Employee Count'})
    pack_count = pack_count.droplevel(level=0, axis=1)

    retail_count = df_use.loc[(df_use['packaging_retail'] != '-') & (df_use['type'] == 'packaging')] \
        .groupby(['packaging_retail', 'item_code','date']).agg({'inventory_count': 'sum'}) \
        .unstack() \
        .sort_index(axis=1) \
        .assign(Used_Last_Month=lambda x: x.iloc[:, -1] - x.iloc[:, -2]) \
        .sort_values("Used_Last_Month") \
        .loc[lambda x: x.index.get_level_values(0) != '-'] \
        .rename(columns={'': 'Used Last Month According to Employee Count'})
    retail_count = retail_count.droplevel(level=0, axis=1)

    return pack_count, retail_count

def calc_production(df_use, month_digit, year_digit):
    '''

    Parameters
    ----------
    df_use : DataFrame to use
    month_digit : used for filtering inside df_use - will pass it as variable from main script
    year_digit : used for filtering inside df_use - will pass it as variable from main script

    Returns
    -------
    Calculates production for both Retail & Non-Retail Packaging based on what's typed in Sage100 each month
    '''
    f = {'packaging_used': 'sum', 'product': lambda x: ', \n'.join(sorted(x.unique().tolist()))}
    g = {'packaging_used_retail': 'sum', 'product': lambda x: ', \n'.join(sorted(x.unique().tolist()))}
    r_name = {'packaging_used':'Packaging Used in ' + str(month_digit) + ' - Production Paperwork'}

    mask_date = (df_use.date_transaction.dt.month.eq(month_digit) |
                 df_use.date_production.dt.month.eq(month_digit)) & \
                (df_use.date_transaction.dt.year.eq(year_digit) |
                 df_use.date_production.dt.year.eq(year_digit))

    sage_calc = \
        df_use.loc[mask_date & df_use['packaging'].ne('-')]\
            .groupby(['packaging']).agg(f)\
            .rename(columns=r_name)

    sage_calc_retail = \
        df_use.loc[mask_date & df_use['packaging_retail'].ne('-')] \
            .groupby(['packaging_retail']).agg(g) \
            .rename(columns=r_name)

    return sage_calc, sage_calc_retail


#TODO: have to test calc_production function