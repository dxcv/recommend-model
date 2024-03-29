#coding=utf8


import getopt
import string
import json
import os
import sys
sys.path.append('shell')
import click
import pandas as pd
import numpy as np
import LabelAsset
import EqualRiskAssetRatio
import EqualRiskAsset
import HighLowRiskAsset
import os
import DBData
import AllocationData
import time
import RiskHighLowRiskAsset
import ModelHighLowRisk
import GeneralizationPosition
import Const
import WeekFund2DayNav
import FixRisk
import CommandRiskManage

from datetime import datetime, timedelta
from dateutil.parser import parse
from Const import datapath
from db import database

import traceback, code

@click.command()
@click.option('--inst', 'optinst', type=int, default=None, help=u'instance id')
@click.option('--type', 'opttype', type=int, default=1, help=u'instance type(1:experimental;9:online)')
@click.option('--datadir', '-d', type=click.Path(exists=True), default='./tmp', help=u'dir used to store tmp data')
@click.option('--start-date', 'startdate', default='2012-07-27', help=u'start date to calc')
@click.option('--end-date', 'enddate', help=u'end date to calc')
@click.option('--label-asset/--no-label-asset', default=True)
@click.option('--reshape/--no-reshape', default=True)
@click.option('--markowitz/--no-markowitz', default=True)
@click.option('--riskmgr/--no-riskmgr', default=True)
@click.option('--exclude-category', 'excluded_category', help=u'category to excluded(e.g. rise,decline,SP500.SPI,GLNC,HSCI.HI')
@click.pass_context
def risk(ctx, optinst, opttype, datadir, startdate, enddate, label_asset, reshape, markowitz, riskmgr, excluded_category):
    '''run constant risk model
    '''
    Const.datadir = datadir

    if opttype != 9:
        opttype = 1

    if optinst is None:
        optinst = database.asset_allocation_instance_new_globalid(xtype=opttype)

    if not enddate:
        yesterday = (datetime.now() - timedelta(days=1)); 
        enddate = yesterday.strftime("%Y-%m-%d")

    if excluded_category is not None:
        excluded = [s.strip() for s in excluded_category.split(',')]
    else:
        excluded = []
        

    # 加载时间轴数据
    index = DBData.trade_date_index(startdate, end_date=enddate)
    start_date = index.min().strftime("%Y-%m-%d")


    allocationdata = AllocationData.allocationdata()
    allocationdata.start_date = index.min().strftime("%Y-%m-%d")
    allocationdata.end_date = index.max().strftime("%Y-%m-%d")

    allocationdata.all_dates()

    allocationdata.fund_measure_lookback                 = 52
    allocationdata.fund_measure_adjust_period            = 13
    allocationdata.jensen_ratio                          = 0.5
    allocationdata.sortino_ratio                         = 0.5
    allocationdata.ppw_ratio                             = 0.5
    allocationdata.stability_ratio                       = 0.5
    allocationdata.fixed_risk_asset_lookback             = 52
    allocationdata.fixed_risk_asset_risk_adjust_period   = 5
    allocationdata.allocation_lookback                   = 26
    allocationdata.allocation_adjust_period              = 4

    # 根据调整间隔抽取调仓点
    label_period = allocationdata.fund_measure_adjust_period
    if label_period > 1:
        label_index = index[::label_period]
        if index.max() not in label_index:
            label_index = label_index.insert(len(label_index), index.max())
    else:
        label_index = index
    #
    # [XXX] 由于马克维茨需要之前的之前allock_lookback周的数据, 所
    # 以我们需要添加一些调仓点
    #
    lookback = allocationdata.fund_measure_lookback + allocationdata.fixed_risk_asset_risk_lookback  + allocationdata.allocation_lookback + 1
    #print lookback
    tmp_index = DBData.trade_date_lookback_index(allocationdata.start_date, lookback=lookback)
    if label_period > 1:
        lookback_index = tmp_index[::-label_period]
        if tmp_index.min() not in lookback_index:
            lookback_index = lookback_index.insert(0, tmp_index.min())
    else:
        lookback_index = tmp_index

    #
    # 合并调仓点
    #
    label_index = label_index.union(lookback_index)
    print "adjust point:"
    for date in label_index:
        print date.strftime("%Y-%m-%d")

    #
    # 净值数据的开始日期
    #
    nav_start_date = label_index.min().strftime("%Y-%m-%d")

    print "allocation calc start date", allocationdata.start_date
    print "allocation calc end date", allocationdata.end_date
    print "history data begins at", nav_start_date

    if label_asset:
        #LabelAsset.labelasset(allocationdata)

        # label_index = pd.DatetimeIndex(['2015-04-03', '2015-09-30', '2016-04-08', '2016-10-14']
        LabelAsset.label_asset_tag(label_index, lookback=52)
        LabelAsset.label_asset_nav(nav_start_date, allocationdata.end_date)

    if reshape:
        print "calc equal risk ratio ...."
        # WeekFund2DayNav.week2day(nav_start_date, allocationdata.end_date)
        FixRisk.fixrisk(interval=20, short_period=20, long_period=252)
        # EqualRiskAssetRatio.equalriskassetratio(allocationdata.fixed_risk_asset_lookback, allocationdata.fixed_risk_asset_risk_adjust_period)
        print "calc equal risk ratio finished"

        print "calc equal risk nav...."
        EqualRiskAsset.equalriskasset()
        print "calc equal risk nav finished"

    if markowitz:
        
        print "calc high low risk model ..."
        # RiskHighLowRiskAsset.highlowriskasset(allocationdata.allocation_lookback, allocationdata.allocation_adjust_period)
        ModelHighLowRisk.asset_alloc_high_low(allocationdata.start_date, allocationdata.end_date, lookback=26, adjust_period=1, excluded=excluded)
        print "calc high low risk model finished"

    print "output category position ...."
    GeneralizationPosition.portfolio_category()
    print "output category portfolio ok"

    # print "output detail position ...."
    # GeneralizationPosition.portfolio_detail()
    # print "output detail position ok"

    print "perform risk management ..."
    ctx.invoke(CommandRiskManage.simple, datadir=datadir, optinst=optinst)
    print "perform risk management done"

    print "output stockavg position ..."
    GeneralizationPosition.portfolio_avg_simple(
        datapath('riskmgr_position.csv'), datapath('position-r.csv'))
    print "output stockavg positon done"

    if riskmgr is False:
        print "output stockavg position without risk management ..."
        GeneralizationPosition.portfolio_avg_simple(
            datapath('portfolio_position.csv'), datapath('position-v.csv'))
        print "output stockavg position without risk management done"


