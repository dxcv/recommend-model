#coding=utf8


import getopt
import string
import json
import os
import sys
import logging
sys.path.append('shell')
import click
import config
import pandas as pd
import numpy as np
import LabelAsset
import os
import DBData
import time
import Const
import DFUtil
import LabelAsset

from datetime import datetime, timedelta
from dateutil.parser import parse
from Const import datapath
from sqlalchemy import *
from tabulate import tabulate
from db import database, asset_mz_markowitz_nav, asset_ra_portfolio_nav
from ipdb import set_trace

import traceback, code

logger = logging.getLogger(__name__)

@click.group()
@click.pass_context
def composite(ctx):
    '''fund composite group
    '''
    click.echo("")

def load_asset_by_type(db, asset_type, assets):
    metadata = MetaData(bind=db)
    t = Table('ra_composite_asset', metadata, autoload=True)

    columns = [
        t.c.globalid,
        t.c.ra_calc_type,
        t.c.ra_begin_date,
        t.c.ra_name,
    ]

    s = select(columns)
    if assets is not None:
        s = s.where(t.c.globalid.in_(assets.split(',')))
    if asset_type is not None:
        s = s.where(t.c.ra_calc_type.in_(asset_type))

    df_asset = pd.read_sql(s, db)

    return df_asset


@composite.command()
@click.option('--asset', 'optasset', help='nav of which asset to update')
@click.option('--list/--no-list', 'optlist', default=False, help='list asset to update')
@click.pass_context
def nav(ctx, optasset, optlist):
    ''' calc asset nav and inc
    '''
    db_asset = create_engine(config.db_asset_uri)
    # db_asset.echo = True
    db_base = create_engine(config.db_base_uri)
    db = {'asset':db_asset, 'base':db_base}

    df_asset = load_asset_by_type(db['asset'], [2, 3, 4, 5], optasset)

    if optlist:
        #print df_asset
        #df_asset.reindex_axis(['ra_type','ra_date_type', 'ra_fund_type', 'ra_lookback', 'ra_name'], axis=1)
        df_asset['ra_name'] = df_asset['ra_name'].map(lambda e: e.decode('utf-8'))
        print(tabulate(df_asset, headers='keys', tablefmt='psql'))
        return 0

    with click.progressbar(length=len(df_asset.index), label='update nav for assets'.ljust(30)) as bar:
        for _, asset in df_asset.iterrows():
            if asset['ra_calc_type'] == 2:
                nav_update_index(db, asset)
            elif asset['ra_calc_type'] == 3:
                nav_update_fund(db, asset)
            elif asset['ra_calc_type'] == 4:
                nav_update_factor_index(db, asset)
            elif asset['ra_calc_type'] == 5:
                nav_update_cppi_benchmark(db, asset)
            else:
                pass
            bar.update(1)

def nav_update_index(db, asset):
    # 加载基金列表
    df = load_index_for_asset(db['asset'], asset['globalid'])

    # 构建均分仓位
    df_position = df.unstack().fillna(0.0)
    df_position.columns = df_position.columns.droplevel(0)


    # 加载基金收益率
    min_date = df_position.index.min()
    #max_date = df_position.index.max()
    max_date = (datetime.now() - timedelta(days=1)) # yesterday


    df_nav = DBData.db_index_value_daily(
        min_date, max_date, codes=df_position.columns)
    df_inc = df_nav.pct_change().fillna(0.0)

    dates = pd.date_range(df_position.index[0], datetime.now() - timedelta(1))
    df_position = df_position.reindex(dates).fillna(method = 'pad')
    # 计算复合资产净值
    df_nav_portfolio = DFUtil.portfolio_nav(df_inc, df_position, result_col='portfolio')
    # df_nav_portfolio.to_csv(datapath('category_nav_' + category + '.csv'))

    df_result = df_nav_portfolio[['portfolio']].rename(columns={'portfolio':'ra_nav'}).copy()
    df_result.index.name = 'ra_date'
    df_result['ra_inc'] = df_result['ra_nav'].pct_change().fillna(0.0)
    df_result['ra_asset_id'] = asset['globalid']
    df_result = df_result.reset_index().set_index(['ra_asset_id', 'ra_date'])

    df_new = df_result.apply(format_nav_and_inc)


    # 加载旧数据
    t2 = Table('ra_composite_asset_nav', MetaData(bind=db['asset']), autoload=True)
    columns2 = [
        t2.c.ra_asset_id,
        t2.c.ra_date,
        t2.c.ra_nav,
        t2.c.ra_inc,
    ]
    stmt_select = select(columns2, (t2.c.ra_asset_id == asset['globalid']))
    df_old = pd.read_sql(stmt_select, db['asset'], index_col=['ra_asset_id', 'ra_date'], parse_dates=['ra_date'])
    if not df_old.empty:
        df_old = df_old.apply(format_nav_and_inc)

    # 更新数据库
    database.batch(db['asset'], t2, df_new, df_old, timestamp=False)

def nav_update_fund(db, asset):
    # 加载基金列表
    df = database.asset_ra_composite_asset_position_load(asset['globalid'])

    # 构建仓位
    df_position = df.unstack().fillna(0.0)
    df_position.columns = df_position.columns.droplevel(0)


    # 加载基金收益率
    min_date = df_position.index.min()
    #max_date = df_position.index.max()
    max_date = (datetime.now() - timedelta(days=1)) # yesterday


    df_nav = DBData.db_fund_value_daily(
        min_date, max_date, codes=df_position.columns)
    df_inc = df_nav.pct_change().fillna(0.0)

    if df_inc.empty:
        click.echo(click.style("\nskipping due to fund/index nav for asset %s" % (asset['globalid']), fg='yellow'))
        return False

    # 计算复合资产净值
    df_nav_portfolio = DFUtil.portfolio_nav(df_inc, df_position, result_col='portfolio')
    # df_nav_portfolio.to_csv(datapath('category_nav_' + category + '.csv'))

    df_result = df_nav_portfolio[['portfolio']].rename(columns={'portfolio':'ra_nav'}).copy()
    df_result.index.name = 'ra_date'
    df_result['ra_inc'] = df_result['ra_nav'].pct_change().fillna(0.0)
    df_result['ra_asset_id'] = asset['globalid']
    df_result = df_result.reset_index().set_index(['ra_asset_id', 'ra_date'])

    df_new = df_result.apply(format_nav_and_inc)

    # 加载旧数据
    t2 = Table('ra_composite_asset_nav', MetaData(bind=db['asset']), autoload=True)
    columns2 = [
        t2.c.ra_asset_id,
        t2.c.ra_date,
        t2.c.ra_nav,
        t2.c.ra_inc,
    ]
    stmt_select = select(columns2, (t2.c.ra_asset_id == asset['globalid']))
    df_old = pd.read_sql(stmt_select, db['asset'], index_col=['ra_asset_id', 'ra_date'], parse_dates=['ra_date'])
    if not df_old.empty:
        df_old = df_old.apply(format_nav_and_inc)

    # 更新数据库
    database.batch(db['asset'], t2, df_new, df_old, timestamp=False)

def nav_update_factor_index(db, asset):

    df = asset_mz_markowitz_nav.load_series(asset.globalid)
    df = df.to_frame()
    df = df.reset_index()
    df['ra_asset_id'] = asset.globalid
    df['ra_inc'] = df['mz_nav'].pct_change().fillna(0.0)
    df.columns = ['ra_date', 'ra_nav', 'ra_asset_id', 'ra_inc']
    df = df.set_index(['ra_asset_id', 'ra_date'])
    df_new = df

    # 加载旧数据
    t2 = Table('ra_composite_asset_nav', MetaData(bind=db['asset']), autoload=True)
    columns2 = [
        t2.c.ra_asset_id,
        t2.c.ra_date,
        t2.c.ra_nav,
        t2.c.ra_inc,
    ]
    stmt_select = select(columns2, (t2.c.ra_asset_id == asset['globalid']))
    df_old = pd.read_sql(stmt_select, db['asset'], index_col=['ra_asset_id', 'ra_date'], parse_dates=['ra_date'])
    if not df_old.empty:
        df_old = df_old.apply(format_nav_and_inc)

    # 更新数据库
    database.batch(db['asset'], t2, df_new, df_old, timestamp=False)


def nav_update_cppi_benchmark(db, asset):

    df = load_index_for_asset(db['asset'], asset['globalid'])
    df = df.reset_index()
    globalid = df.loc[0, 'ra_fund_code']

    df = asset_ra_portfolio_nav.load_series(globalid, xtype=8)
    df = df.to_frame()
    df = df.reset_index()
    df['ra_asset_id'] = asset.globalid
    df['ra_inc'] = df['ra_nav'].pct_change().fillna(0.0)
    df.columns = ['ra_date', 'ra_nav', 'ra_asset_id', 'ra_inc']
    df = df.set_index(['ra_asset_id', 'ra_date'])
    df_new = df

    # 加载旧数据
    t2 = Table('ra_composite_asset_nav', MetaData(bind=db['asset']), autoload=True)
    columns2 = [
        t2.c.ra_asset_id,
        t2.c.ra_date,
        t2.c.ra_nav,
        t2.c.ra_inc,
    ]
    stmt_select = select(columns2, (t2.c.ra_asset_id == asset['globalid']))
    df_old = pd.read_sql(stmt_select, db['asset'], index_col=['ra_asset_id', 'ra_date'], parse_dates=['ra_date'])
    if not df_old.empty:
        df_old = df_old.apply(format_nav_and_inc)

    # 更新数据库
    database.batch(db['asset'], t2, df_new, df_old, timestamp=False)


def format_nav_and_inc(x):
    if x.name == "ra_nav":
        ret = x.map("{:.6f}".format)
    elif x.name == "ra_inc":
        ret = x.map("{:.6f}".format)
    else:
        ret = x

    return ret


def load_fund_category(db, pid, category):
    # 加载基金列表
    t = Table('ra_pool_fund', MetaData(bind=db), autoload=True)
    columns = [
        t.c.ra_date,
        t.c.ra_fund_code,
    ]
    s = select(columns, (t.c.ra_pool == pid))
    if category == 0:
        s = s.distinct()
    else:
        s = s.where(t.c.ra_category == category)

    df = pd.read_sql(s, db, index_col = ['ra_date'], parse_dates=['ra_date'])

    return df

def load_index_for_asset(db, asset_id):
    # 加载基金列表
    t = Table('ra_composite_asset_position', MetaData(bind=db), autoload=True)
    columns = [
        t.c.ra_date,
        t.c.ra_fund_code,
        t.c.ra_fund_ratio,
    ]
    s = select(columns, (t.c.ra_asset_id == asset_id))

    df = pd.read_sql(s, db, index_col = ['ra_date', 'ra_fund_code'], parse_dates=['ra_date'])

    return df


