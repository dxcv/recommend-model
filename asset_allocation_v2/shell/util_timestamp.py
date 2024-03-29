#coding=utf-8
'''
Created on: Dec. 28, 2018
Modified on: Jun. 11, 2019
Author: Shixun Su
Contact: sushixun@licaimofang.com
'''

import sys
import logging
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from ipdb import set_trace
sys.path.append('shell')
from db import wind_aindexmembers
from trade_date import ATradeDate


logger = logging.getLogger(__name__)


# def last_year(date):

    # days_in_month = pd.Timestamp(date.year-1, date.month, 1).days_in_month
    # return pd.Timestamp(date.year-1, date.month, min(date.day, days_in_month))

# def last_quarter(date):

    # if date.month < 4:
        # days_in_month = pd.Timestamp(date.year-1, date.month+9, 1).days_in_month
        # return pd.Timestamp(date.year-1, date.month+9, min(date.day, days_in_month))
    # else:
        # days_in_month = pd.Timestamp(date.year, date.month-3, 1).days_in_month
        # return pd.Timestamp(date.year, date.month-3, min(date.day, days_in_month))

# def last_month(date):

    # if date.month < 2:
        # return pd.Timestamp(date.year-1, 12, date.day)
    # else:
        # days_in_month = pd.Timestamp(date.year, date.month-1, 1).days_in_month
        # return pd.Timestamp(date.year, date.month-1, min(date.day, days_in_month))

# def next_month(date):

    # if date.month < 12:
        # days_in_month = pd.Timestamp(date.year, date.month+1, 1).days_in_month
        # return pd.Timestamp(date.year, date.month+1, min(date.day, days_in_month))
    # else:
        # return pd.Timestamp(date.year+1, 1, date.day)

# def month_start(date):

    # return pd.Timestamp(date.year, date.month, 1)

def last_end_date_fund_skdetail_all_published(date):

    if date.month < 4:
        return pd.Timestamp(date.year-1, 6, 30)
    elif date.month < 9:
        return pd.Timestamp(date.year-1, 12, 31)
    else:
        return pd.Timestamp(date.year, 6, 30)

def last_end_date_fund_skdetail_ten_published(date):

    if date.month < 2:
        return pd.Timestamp(date.year-1, 9, 30)
    elif date.month < 5:
        return pd.Timestamp(date.year-1, 12, 31)
    elif date.month < 8:
        return pd.Timestamp(date.year, 3, 31)
    elif date.month < 11:
        return pd.Timestamp(date.year, 6, 30)
    else:
        return pd.Timestamp(date.year, 9, 30)

def trade_date_not_later_than(date):

    trade_dates = ATradeDate.trade_date()

    try:
        date = trade_dates[trade_dates.get_loc(date, method='pad')]
    except KeyError:
        return np.nan

    return date

def trade_date_before(date):

    date = date + relativedelta(days=-1)

    return trade_date_not_later_than(date)

# def trade_date_before_(date):

    # trade_dates = ATradeDate.trade_date()

    # if date <= trade_dates[0]:
        # raise ValueError('There is not trading day before the day.')

    # lo = 0
    # hi = trade_dates.shape[0]
    # while lo + 1 < hi:
        # mi = (lo + hi) // 2
        # if date < trade_dates[mi]:
            # hi = mi
        # else:
            # lo = mi

    # if date == trade_dates[lo]:
        # return trade_dates[lo-1]
    # else:
        # return trade_dates[lo]

# def trade_date_not_later_than_(date):

    # trade_dates = ATradeDate.trade_date()

    # if date < trade_dates[0]:
        # raise ValueError('It is before the first day of trading.')

    # lo = 0
    # hi = trade_dates.shape[0]
    # while lo + 1 < hi:
        # mi = (lo + hi) // 2
        # if date < trade_dates[mi]:
            # hi = mi
        # else:
            # lo = mi

    # return trade_dates[lo]

def trade_date_not_earlier_than(date):

    trade_dates = ATradeDate.trade_date()

    try:
        date = trade_dates[trade_dates.get_loc(date, method='backfill')]
    except KeyError:
        return np.nan

    return date

def trade_date_after(date):

    date = date + relativedelta(days=+1)

    return trade_date_not_earlier_than(date)

def closing_date_of_report_period(date):

    if date.month == 3:
        return pd.Timestamp(date.year, 4, 30)
    elif date.month == 6:
        return pd.Timestamp(date.year, 8, 31)
    elif date.month == 9:
        return pd.Timestamp(date.year, 10, 31)
    elif date.month == 12:
        return pd.Timestamp(date.year+1, 4, 30)
    else:
        raise ValueError('Invalid report period!')

class IndexAdjustmentDate:

    _adjustment_dates_dict = {}

    @staticmethod
    def load_adjustment_dates(index_id):

        if index_id in IndexAdjustmentDate._adjustment_dates_dict:
            return IndexAdjustmentDate._adjustment_dates_dict[index_id]
        else:
            df = wind_aindexmembers.load_a_index_historical_constituents(index_id)
            ser = df.in_date.groupby(df.in_date).count()
            IndexAdjustmentDate._adjustment_dates_dict[index_id] = ser.loc[ser>5].index.map(trade_date_before)
            return IndexAdjustmentDate._adjustment_dates_dict[index_id]

def last_adjustment_date(date, index_id):

    adjustment_dates = IndexAdjustmentDate.load_adjustment_dates(index_id)

    try:
        date = adjustment_dates[adjustment_dates.get_loc(date, method='pad')]
    except KeyError:
        return np.nan

    return date

