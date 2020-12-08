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
