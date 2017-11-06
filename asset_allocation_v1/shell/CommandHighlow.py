#coding=utf8


import string
import os
import sys
sys.path.append('shell')
import click
import pandas as pd
import numpy as np
import os
import time
import re
import logging
import Const
import DFUtil
import DBData
import util_numpy as npu
import Portfolio as PF

from datetime import datetime, timedelta
from dateutil.parser import parse
from Const import datapath
from sqlalchemy import MetaData, Table, select, func
from tabulate import tabulate
from db import *
from util import xdict
from util.xdebug import dd

import traceback, code

logger = logging.getLogger(__name__)

@click.group(invoke_without_command=True)  
@click.option('--full/--no-full', 'optfull', default=False, help=u'include all instance')
@click.option('--new/--no-new', 'optnew', default=False, help=u'use new framework')
@click.option('--id', 'optid', help=u'specify markowitz id')
@click.option('--name', 'optname', default=None, help=u'specify highlow name')
@click.option('--type', 'opttype', type=click.Choice(['1', '9']), default='1', help=u'online type(1:expriment; 9:online)')
@click.option('--replace/--no-replace', 'optreplace', default=False, help=u'replace pool if exists')
@click.option('--high', 'opthigh', type=int, default=0, help=u'high asset id')
@click.option('--low', 'optlow', type=int, default=0, help=u'low asset id')
@click.option('--riskmgr', 'optriskmgr', default='*', help=u'with riskmgr')
@click.option('--riskmgr/--no-riskmgr', 'optriskmgr', default=True, help=u'with riskmgr or not')
@click.option('--risk', 'optrisk', default='10,1,2,3,4,5,6,7,8,9', help=u'which risk to calc, [1-10]')
@click.option('--end-date', 'optenddate', default=None, help=u'calc end date for nav')
@click.pass_context
def highlow(ctx, optfull, optnew, optid, optname, opttype, optreplace, opthigh, optlow, optriskmgr, optrisk, optenddate):

    '''markowitz group
    '''
    if ctx.invoked_subcommand is None:
        # click.echo('I was invoked without subcommand')
        if optnew:
            ctx.invoke(pos, optid=optid, optrisk=optrisk)
            ctx.invoke(nav, optid=optid, optenddate=optenddate)
            ctx.invoke(turnover, optid=optid)
        else:
            if optfull is False:
                # ctx.obj['highlow'] = 70032880
                if optid is not None:
                    tmpid = int(optid)
                else:
                    tmpid = optid
                ctx.invoke(allocate, optid=tmpid, optname=optname, opttype=opttype, optreplace=optreplace, opthigh=opthigh, optlow=optlow, optriskmgr=optriskmgr, optrisk=optrisk)
                ctx.invoke(nav, optid=optid, optenddate=optenddate)
                ctx.invoke(turnover, optid=optid)
            else:
                ctx.invoke(nav, optid=optid, optenddate=optenddate)
                ctx.invoke(turnover, optid=optid)
    else:
        # click.echo('I am about to invoke %s' % ctx.invoked_subcommand)
        pass

@highlow.command()
@click.option('--id', 'optid', type=int, help=u'specify markowitz id')
@click.option('--name', 'optname', default=None, help=u'specify highlow name')
@click.option('--type', 'opttype', type=click.Choice(['1', '9']), default='1', help=u'online type(1:expriment; 9:online)')
@click.option('--replace/--no-replace', 'optreplace', default=False, help=u'replace pool if exists')
@click.option('--high', 'opthigh', type=int, default=0, help=u'high asset id')
@click.option('--low', 'optlow', type=int, default=0, help=u'low asset id')
@click.option('--riskmgr', 'optriskmgr', default='*', help=u'with riskmgr')
@click.option('--risk', 'optrisk', default='10,1,2,3,4,5,6,7,8,9', help=u'which risk to calc, [1-10]')
@click.pass_context
def allocate(ctx, optid, optname, opttype, optreplace, opthigh, optlow, optriskmgr, optrisk):
    '''calc high low allocate
    '''
    if opthigh == 0 and 'markowitz.high' in ctx.obj:
        opthigh = ctx.obj['markowitz.high']
    if optlow == 0 and 'markowitz.low' in ctx.obj:
        optlow = ctx.obj['markowitz.low']

    if opthigh == 0 and optlow == 0:
        click.echo(click.style("ether --high or --low shoud be given, aborted!", fg="red"))
        return 0

    #
    # 处理id参数
    #
    today = datetime.now()
    if optid is not None:
        #
        # 检查id是否存在
        #
        df_existed = asset_mz_highlow.load([str(optid * 10 + x) for x in range(0, 10)])
        if not df_existed.empty:
            s = 'highlow instance [%s] existed' % str(optid)
            if optreplace:
                click.echo(click.style("%s, will replace!" % s, fg="yellow"))
            else:
                click.echo(click.style("%s, import aborted!" % s, fg="red"))
                return -1;
    else:
        #
        # 自动生成id
        #
        prefix = '70' + today.strftime("%m%d");
        between_min, between_max = ('%s00' % (prefix), '%s99' % (prefix))

        max_id = asset_mz_highlow.max_id_between(between_min, between_max)
        if max_id is None:
            max_id = between_min

        if not (isinstance(max_id, int) or isinstance(max_id, long)):
            max_id = string.atoi(max_id)

        if max_id is None:
            optid = int(between_min)
        else:
            if max_id >= int(between_max):
                if optreplace:
                    s = "run out of instance id [%d]" % max_id
                    click.echo(click.style("%s, will replace!" % s, fg="yellow"))
                else:
                    s = "run out of instance id [%d]" % max_id
                    click.echo(click.style("%s, import aborted!" % s, fg="red"))
                    return -1

            if optreplace:
                optid = str(max_id)
            else:
                optid = str(max_id + 10)

    if optname is None:
        optname = u'高低风险%s' % today.strftime("%m%d")
    #
    # 加载用到的资产
    #
    df_asset = asset_mz_markowitz_asset.load([opthigh, optlow])
    df_asset = df_asset[['mz_markowitz_id', 'mz_asset_id', 'mz_asset_name', 'mz_asset_type']]
    df_asset = df_asset.rename(columns={'mz_markowitz_id': 'mz_origin_id'})
    df_asset = df_asset.set_index(['mz_asset_id'])
    #
    # 加载用到的风控
    #
    dt_riskmgr = {}
    for k, v in df_asset.iterrows():
        if optriskmgr == False:
            dt_riskmgr[k] = 0
        else:
            df_tmp = asset_rm_riskmgr.where_asset_id(k)
            if df_tmp.empty:
                dt_riskmgr[k] = 0
            else:
                dt_riskmgr[k] = df_tmp.ix[0, 'globalid']
    df_asset['mz_riskmgr_id'] = pd.Series(dt_riskmgr)
    #
    # 加载资产池
    #
    dt_pool = {}
    for k, v in df_asset.iterrows():
        dt_pool[k] = asset_ra_pool.match_asset_pool(k)
    df_asset['mz_pool_id'] = pd.Series(dt_pool)

    if '120000039' not in df_asset.index:
        df_asset.loc['120000039'] = (0, u'货币(低)', 31, 0, '120000039')
    if '120000039' not in df_asset.index:
        df_asset.loc['120000039'] = (0, u'货币(高)', 31, 0, '120000039')
    
    db = database.connection('asset')
    metadata = MetaData(bind=db)
    mz_highlow        = Table('mz_highlow', metadata, autoload=True)
    mz_highlow_alloc  = Table('mz_highlow_alloc', metadata, autoload=True)
    mz_highlow_asset  = Table('mz_highlow_asset', metadata, autoload=True)
    mz_highlow_pos    = Table('mz_highlow_pos', metadata, autoload=True)
    mz_highlow_nav    = Table('mz_highlow_nav', metadata, autoload=True)

    #
    # 处理替换
    #
    if optreplace:
        mz_highlow_nav.delete(mz_highlow_nav.c.mz_highlow_id.between(optid, optid + 9)).execute()
        mz_highlow_pos.delete(mz_highlow_pos.c.mz_highlow_id.between(optid, optid + 9)).execute()
        mz_highlow_asset.delete(mz_highlow_asset.c.mz_highlow_id == optid).execute()
        mz_highlow_alloc.delete(mz_highlow_alloc.c.mz_highlow_id == optid).execute()
        mz_highlow.delete(mz_highlow.c.globalid == optid).execute()

    now = datetime.now()
    # 导入数据: highlow
    row = {
        'globalid': optid, 'mz_type':opttype, 'mz_name': optname,
        'mz_algo': 1, 'mz_high_id': opthigh, 'mz_low_id': optlow,
        'mz_persistent': 0, 'created_at': func.now(), 'updated_at': func.now()
    }
    mz_highlow.insert(row).execute()

    #
    # 导入数据: highlow_asset
    #
    df_asset_tosave = df_asset.copy()
    df_asset_tosave['mz_highlow_id'] = optid
    df_asset_tosave = df_asset_tosave.reset_index().set_index(['mz_highlow_id', 'mz_asset_id'])
    asset_mz_highlow_asset.save([optid], df_asset_tosave)

    #
    # 加载高风险资产仓位
    #
    index = None
    if opthigh == 0:
        optrisk = '1'
    else:
        df_high = asset_mz_markowitz_pos.load_raw(opthigh)
        df_high_riskmgr = load_riskmgr(df_high.columns, df_high.index, optriskmgr)
        index = df_high.index.union(df_high_riskmgr.index)
    #
    # 加载低风险资产仓位
    #
    if optlow == 0:
        optrisk = '10'
    else:
        df_low  = asset_mz_markowitz_pos.load_raw(optlow)
        df_low_riskmgr = load_riskmgr(df_low.columns, df_low.index, optriskmgr)
        if index is None:
            index = df_low.index.union(df_low_riskmgr.index)
        else:
            index = index.union(df_low.index).union(df_low_riskmgr.index)

    #
    # 生成资产列表
    #

    for risk in [int(x) for x in optrisk.split(',')]:
        highlow_id = str(string.atoi(optid) + (risk % 10))
        name = optname + u"-等级%d" % (risk)
        # 配置比例
        ratio_h  = (risk - 1) * 1.0 / 9
        ratio_l  = 1 - ratio_h

        data_h = {}
        if not df_high.empty:
            df_high = df_high.reindex(index, method='pad')
            df_high_riskmgr = df_high_riskmgr.reindex(index, method='pad')
            for column in df_high.columns:
                data_h[column] = df_high[column] * df_high_riskmgr[column] * ratio_h
        df_h = pd.DataFrame(data_h)

        data_l = {}
        if not df_low.empty:
            df_low = df_low.reindex(index, method='pad')
            df_low_riskmgr = df_low_riskmgr.reindex(index, method='pad')
            for column in df_low.columns:
                data_l[column] = df_low[column] * df_low_riskmgr[column] * ratio_l
        df_l = pd.DataFrame(data_l)
        #
        # 用货币补足空仓部分， 因为我们的数据库结构无法表示所有资产空
        # 仓的情况（我们不存储仓位为0的资产）；所以我们需要保证任何一
        # 天的持仓100%， 如果因为风控空仓，需要用货币补足。
        #
        if ratio_h > 0:
            sr = ratio_h - df_h.sum(axis=1)
            if (sr > 0.000099).any():
                df_h['120000039'] = sr

        if ratio_l > 0:
            sr = ratio_l - df_l.sum(axis=1)
            if (sr > 0.000099).any():
                df_h['120000039'] = sr
        #
        # 合并持仓
        #
        df = pd.concat([df_h, df_l], axis=1)

        #
        # 导入数据: highlow_alloc
        #
        row = {
            'globalid': highlow_id, 'mz_type':opttype, 'mz_name': name,
            'mz_highlow_id': optid, 'mz_risk': risk / 10.0, 'created_at': func.now(), 'updated_at': func.now()
        }
        mz_highlow_alloc.insert(row).execute()

        #
        # 导入数据: highlow_pos
        #
        df = df.round(4)             # 四舍五入到万分位
        df[df.abs() < 0.0009999] = 0 # 过滤掉过小的份额
        # print df.head()
        df = df.apply(npu.np_pad_to, raw=True, axis=1) # 补足缺失
        # df = DFUtil.filter_same_with_last(df)          # 过滤掉相同
        # if turnover >= 0.01:
        #     df = DFUtil.filter_by_turnover(df, turnover)   # 基于换手率进行规律 

        df.index.name = 'mz_date'
        df.columns.name='mz_asset_id'


        # index
        df['mz_highlow_id'] = highlow_id
        df = df.reset_index().set_index(['mz_highlow_id', 'mz_date'])

        # unstack
        df_tosave = df.stack().to_frame('mz_ratio')
        df_tosave = df_tosave.loc[(df_tosave['mz_ratio'] > 0)]

        # save
        # print df_tosave
        asset_mz_highlow_pos.save(highlow_id, df_tosave)

        # click.echo(click.style("highlow allocation complement! instance id [%s]" % (optid), fg='green'))

    #
    # 在context的记录id, 以便命令两中使用
    #
    ctx.obj['highlow'] = optid

    click.echo(click.style("highlow allocation complement! instance id [%s]" % (optid), fg='green'))


def load_riskmgr(assets, reindex=None, enable=True):
    data = {}
    index = reindex.copy()
    for asset_id in assets:
        #
        # 这里打个小补丁，为了兼容先容0424的历史
        #
        if asset_id == 19220121:
            riskmgr_asset_id = 120000010
        elif asset_id == 19220122:
            riskmgr_asset_id = 120000011
        else:
            riskmgr_asset_id = asset_id

        if enable == False:
            sr = pd.Series(1.0, index=reindex)
            sr.index.name = 'mz_date'
        else:
            df_riskmgr = asset_rm_riskmgr.where_asset_id(riskmgr_asset_id)
            if df_riskmgr.empty:
                sr = pd.Series(1.0, index=reindex)
                sr.index.name = 'mz_date'
            else:
                gid = df_riskmgr.ix[0, 'globalid']
                sr = asset_rm_riskmgr_signal.load_series(gid)
                index = index.union(sr.index)
        data[asset_id] = sr

    df = pd.DataFrame(data, index=index).fillna(method='pad')
    df.columns.name = 'mz_asset_id'

    if reindex is not None:
        df = df[reindex.min():]

    return df

def load_riskmgr2(assets, sr_riskmgr, reindex=None, enable=True):
    data = {}
    index = reindex.copy()
    for asset_id in assets:
        sr = None
        if enable and asset_id in sr_riskmgr:
            gid = sr_riskmgr.at[asset_id]
            if gid != '' and gid != '0':
                sr = asset_rm_riskmgr_signal.load_series(gid)
                index = index.union(sr.index)

        if sr is None:
            sr = pd.Series(1.0, index=reindex)
            sr.index.name = 'mz_date'

        data[asset_id] = sr

    df = pd.DataFrame(data, index=index).fillna(method='pad')
    df.columns.name = 'mz_asset_id'

    if reindex is not None:
        df = df[reindex.min():]

    return df

def load_nav_series(asset_id, reindex=None, begin_date=None, end_date=None):

    if asset_id.isdigit():
        xtype = int(asset_id) / 10000000
    else:
        xtype = re.sub(r'([\d]+)','',asset_id).strip()


    if xtype == 1:
        #
        # 基金池资产
        #
        asset_id = string.atoi(asset_id) / 10000000
        (pool_id, category) = (asset_id / 100, asset_id % 100)
        ttype = pool_id / 10000
        sr = asset_ra_pool_nav.load_series(
            pool_id, category, ttype, reindex=reindex, begin_date=begin_date, end_date=end_date)
    elif xtype == 3:
        #
        # 基金池资产
        #
        sr = base_ra_fund_nav.load_series(
            asset_id, reindex=reindex, begin_date=begin_date, end_date=end_date)
    elif xtype == 4:
        #
        # 修型资产
        #
        sr = asset_rs_reshape_nav.load_series(
            asset_id, reindex=reindex, begin_date=begin_date, end_date=end_date)
    elif xtype == 12:
        #
        # 指数资产
        #
        sr = base_ra_index_nav.load_series(
            asset_id, reindex=reindex, begin_date=begin_date, end_date=end_date)
    elif xtype == 'ERI':

        sr = base_exchange_rate_index_nav.load_series(
            asset_id, reindex=reindex, begin_date=begin_date, end_date=end_date)

    else:
        sr = pd.Series()

    return sr

@highlow.command()
@click.option('--id', 'optid', help=u'ids of highlow to update')
@click.option('--list/--no-list', 'optlist', default=False, help=u'list instance to update')
@click.option('--type', 'opttype', default='8,9', help=u'which type to run')
@click.option('--risk', 'optrisk', default='10,1,2,3,4,5,6,7,8,9', help=u'which risk to calc, [1-10]')
@click.pass_context
def pos(ctx, optid, opttype, optlist, optrisk):
    ''' calc pool nav and inc
    '''
    if optid is not None:
        highlows = [s.strip() for s in optid.split(',')]
    else:
        if 'highlow' in ctx.obj:
            highlows = [str(ctx.obj['highlow'])]
        else:
            highlows = None

    xtypes = [s.strip() for s in opttype.split(',')]

    df_highlow = asset_mz_highlow.load(highlows, xtypes)

    if optlist:
        df_highlow['mz_name'] = df_highlow['mz_name'].map(lambda e: e.decode('utf-8'))
        print tabulate(df_highlow, headers='keys', tablefmt='psql')
        return 0

    for _, highlow in df_highlow.iterrows():
        pos_update_alloc(highlow, optrisk)

def pos_update_alloc(highlow, optrisk):
    risks =  [("%.2f" % (float(x)/ 10.0)) for x in optrisk.split(',')];
    df_alloc = asset_mz_highlow_alloc.where_highlow_id(highlow['globalid'], risks)

    for _, alloc in df_alloc.iterrows():
        pos_update(highlow, alloc)

    click.echo(click.style("highlow allocation complement! instance id [%s]" % (highlow['globalid']), fg='green'))


def pos_update(highlow, alloc):
    highlow_id = alloc['globalid']

    db = database.connection('asset')
    metadata = MetaData(bind=db)
    mz_highlow_pos    = Table('mz_highlow_pos', metadata, autoload=True)
    mz_highlow_nav    = Table('mz_highlow_nav', metadata, autoload=True)

    #
    # 处理替换
    #
    mz_highlow_nav.delete(mz_highlow_nav.c.mz_highlow_id == highlow_id).execute()
    mz_highlow_pos.delete(mz_highlow_pos.c.mz_highlow_id == highlow_id).execute()

    # #
    # # 加载参数
    # #
    # df_argv = asset_mz_markowitz_argv.load([markowitz_id])
    # df_argv.reset_index(level=0, inplace=True)
    # argv = df_argv['mz_value'].to_dict()

    # lookback = int(argv.get('lookback', '26'))
    # adjust_period = int(argv.get('adjust_period', 1))
    # wavelet_filter_num = int(argv.get('optwaveletfilternum', 2))
    # turnover = float(argv.get('turnover', 0))

    # algo = alloc['mz_algo'] if alloc['mz_algo'] != 0 else markowitz['mz_algo']
    algo = highlow['mz_algo']

    if algo == 1:
        #
        # 焦氏策略
        #
        if highlow['mz_high_id'] == '' or highlow['mz_low_id'] == '':
            markowitz_id = highlow['mz_markowitz_id']
            if  markowitz_id == '' or markowitz_id == '0':
                click.echo(click.style("\n both mz_high_id and mz_low_id must be set for jiao_method %d:%s\n" % (algo, highlow_id), fg='red'))
                return
            df_markowitz_alloc = asset_mz_markowitz_alloc.where_markowitz_id(markowitz_id)
            if df_markowitz_alloc.empty:
                click.echo(click.style("\n both mz_high_id and mz_low_id must be set for jiao_method %d:%s\n" % (algo, highlow_id), fg='red'))
                return
            max_ix = df_markowitz_alloc['mz_risk'].argmax()
            min_ix = df_markowitz_alloc['mz_risk'].argmin()

            highlow['mz_high_id'] = df_markowitz_alloc.at[max_ix, 'globalid']
            highlow['mz_low_id'] = df_markowitz_alloc.at[min_ix, 'globalid']

        df = jiao(highlow, alloc)
    elif algo == 2:
        #
        # 姚氏策略
        #
        df = yao(highlow, alloc)
    else:
        click.echo(click.style("\n unknow algo %d for %s\n" % (algo, highlow_id), fg='red'))
        return



    #
    # 导入数据: highlow_pos
    #
    df = df.round(4)             # 四舍五入到万分位
    df[df.abs() < 0.0009999] = 0 # 过滤掉过小的份额
    # print df.head()
    df = df.apply(npu.np_pad_to, raw=True, axis=1) # 补足缺失
    # df = DFUtil.filter_same_with_last(df)          # 过滤掉相同
    # if turnover >= 0.01:
    #     df = DFUtil.filter_by_turnover(df, turnover)   # 基于换手率进行规律 

    if alloc['mz_risk'] == 0.9:
        dd(df)
    df.index.name = 'mz_date'
    df.columns.name='mz_asset_id'


    # index
    df['mz_highlow_id'] = highlow_id
    df = df.reset_index().set_index(['mz_highlow_id', 'mz_date'])

    # unstack
    df_tosave = df.stack().to_frame('mz_ratio')
    df_tosave = df_tosave.loc[(df_tosave['mz_ratio'] > 0)]

    if alloc['mz_risk'] == 0.9:
        df_tosave = df_tosave.unstack(2)
        dd(df_tosave)
    # save
    # print df_tosave
    asset_mz_highlow_pos.save(highlow_id, df_tosave)

def jiao(highlow, alloc):

    high = highlow['mz_high_id']
    low  = highlow['mz_low_id']
    risk = int(alloc['mz_risk'] * 10)

    df_asset = asset_mz_highlow_asset.load([highlow['globalid']])
    df_asset.set_index(['mz_asset_id'], inplace=True)

    #
    # 加载高风险资产仓位
    #
    index = None

    df_high = asset_mz_markowitz_pos.load_raw(high)
    df_high_riskmgr = load_riskmgr2(df_high.columns, df_asset['mz_riskmgr_id'], df_high.index, True)
    index = df_high.index.union(df_high_riskmgr.index)

    #
    # 加载低风险资产仓位
    #
    df_low  = asset_mz_markowitz_pos.load_raw(low)
    df_low_riskmgr = load_riskmgr2(df_low.columns, df_asset['mz_riskmgr_id'], df_low.index, True)
    if index is None:
        index = df_low.index.union(df_low_riskmgr.index)
    else:
        index = index.union(df_low.index).union(df_low_riskmgr.index)

    # 配置比例
    ratio_h  = (risk - 1) * 1.0 / 9
    ratio_l  = 1 - ratio_h

    data_h = {}
    if not df_high.empty:
        df_high = df_high.reindex(index, method='pad')
        df_high_riskmgr = df_high_riskmgr.reindex(index, method='pad')
        for column in df_high.columns:
            data_h[column] = df_high[column] * df_high_riskmgr[column] * ratio_h
    df_h = pd.DataFrame(data_h)

    #dd(df_h)

    data_l = {}
    if not df_low.empty:
        df_low = df_low.reindex(index, method='pad')
        df_low_riskmgr = df_low_riskmgr.reindex(index, method='pad')
        for column in df_low.columns:
            data_l[column] = df_low[column] * df_low_riskmgr[column] * ratio_l
    df_l = pd.DataFrame(data_l)
    #
    # 用货币补足空仓部分， 因为我们的数据库结构无法表示所有资产空
    # 仓的情况（我们不存储仓位为0的资产）；所以我们需要保证任何一
    # 天的持仓100%， 如果因为风控空仓，需要用货币补足。
    #
    if ratio_h > 0:
        sr = ratio_h - df_h.sum(axis=1)
        if (sr > 0.000099).any():
            df_h['120000039'] = sr

    if ratio_l > 0:
        sr = ratio_l - df_l.sum(axis=1)
        if (sr > 0.000099).any():
            df_l['120000039'] = sr

    #
    # 合并持仓
    #
    df = pd.concat([df_h, df_l], axis=1)

    return df

def yao(highlow, alloc):

    high = alloc['mz_markowitz_id']
    risk = int(alloc['mz_risk'] * 10)

    df_asset = asset_mz_highlow_asset.load([alloc['globalid']])
    df_asset.set_index(['mz_asset_id'], inplace=True)

    #
    # 加载高风险资产仓位
    #
    index = None

    df_high = asset_mz_markowitz_pos.load_raw(high)
    df_high_riskmgr = load_riskmgr2(df_high.columns, df_asset['mz_riskmgr_id'], df_high.index, True)
    index = df_high.index.union(df_high_riskmgr.index)

    data_h = {}
    if not df_high.empty:
        df_high = df_high.reindex(index, method='pad')
        df_high_riskmgr = df_high_riskmgr.reindex(index, method='pad')
        for column in df_high.columns:
            data_h[column] = df_high[column] * df_high_riskmgr[column]

    df_h = pd.DataFrame(data_h)

    #
    # 用货币补足空仓部分， 因为我们的数据库结构无法表示所有资产空
    # 仓的情况（我们不存储仓位为0的资产）；所以我们需要保证任何一
    # 天的持仓100%， 如果因为风控空仓，需要用货币补足。
    #
    sr = 1.0 - df_h.sum(axis=1)
    if (sr > 0.000099).any():
        df_h['120000039'] = sr

    return df_h


@highlow.command()
@click.option('--id', 'optid', help=u'ids of highlow to update')
@click.option('--list/--no-list', 'optlist', default=False, help=u'list instance to update')
@click.option('--type', 'opttype', default='8,9', help=u'which type to run')
@click.option('--end-date', 'optenddate', default=None, help=u'calc end date for nav')
@click.pass_context
def nav(ctx, optid, opttype, optlist, optenddate):
    ''' calc pool nav and inc
    '''
    if optid is not None:
        highlows = [s.strip() for s in optid.split(',')]
    else:
        if 'highlow' in ctx.obj:
            highlows = [str(ctx.obj['highlow'])]
        else:
            highlows = None

    if optenddate is not None:
        enddate = pd.to_datetime(optenddate)
    else:
        enddate = None
        
    xtypes = [s.strip() for s in opttype.split(',')]

    df_highlow = asset_mz_highlow.load(highlows, xtypes)

    if optlist:
        df_highlow['mz_name'] = df_highlow['mz_name'].map(lambda e: e.decode('utf-8'))
        print tabulate(df_highlow, headers='keys', tablefmt='psql')
        return 0
    
    for _, highlow in df_highlow.iterrows():
        nav_update_alloc(highlow, enddate)

def nav_update_alloc(highlow, enddate):
    df_alloc = asset_mz_highlow_alloc.where_highlow_id(highlow['globalid'])
    
    with click.progressbar(length=len(df_alloc), label=('update nav %s' % (highlow['globalid'])).ljust(30)) as bar:
        for _, alloc in df_alloc.iterrows():
            bar.update(1)
            nav_update(alloc, enddate)
    
def nav_update(alloc, enddate):
    alloc_id = alloc['globalid']
    # 加载仓位信息
    df_pos = asset_mz_highlow_pos.load(alloc_id)
    
    # 加载资产收益率
    min_date = df_pos.index.min()
    #max_date = df_pos.index.max()
    if enddate is not None:
        max_date = enddate
    else:
        max_date = (datetime.now() - timedelta(days=1)) # yesterday


    data = {}
    for asset_id in df_pos.columns:
        data[asset_id] = load_nav_series(asset_id, begin_date=min_date, end_date=max_date)
    df_nav = pd.DataFrame(data).fillna(method='pad')
    df_inc  = df_nav.pct_change().fillna(0.0)

    # 计算复合资产净值
    df_nav_portfolio = DFUtil.portfolio_nav(df_inc, df_pos, result_col='portfolio')

    df_result = df_nav_portfolio[['portfolio']].rename(columns={'portfolio':'mz_nav'}).copy()
    df_result.index.name = 'mz_date'
    df_result['mz_inc'] = df_result['mz_nav'].pct_change().fillna(0.0)
    df_result['mz_highlow_id'] = alloc['globalid']
    df_result = df_result.reset_index().set_index(['mz_highlow_id', 'mz_date'])

    asset_mz_highlow_nav.save(alloc_id, df_result)

@highlow.command()
@click.option('--id', 'optid', help=u'ids of highlow to update')
@click.option('--type', 'opttype', default='8,9', help=u'which type to run')
@click.option('--list/--no-list', 'optlist', default=False, help=u'list instance to update')
@click.pass_context
def turnover(ctx, optid, opttype, optlist):
    ''' calc pool turnover and inc
    '''
    if optid is not None:
        highlows = [s.strip() for s in optid.split(',')]
    else:
        if 'highlow' in ctx.obj:
            highlows = [str(ctx.obj['highlow'])]
        else:
            highlows = None

    xtypes = [s.strip() for s in opttype.split(',')]

    df_highlow = asset_mz_highlow.load(highlows, xtypes)

    if optlist:

        df_highlow['mz_name'] = df_highlow['mz_name'].map(lambda e: e.decode('utf-8'))
        print tabulate(df_highlow, headers='keys', tablefmt='psql')
        return 0
    
    data = []
    with click.progressbar(length=len(df_highlow), label='update turnover'.ljust(30)) as bar:
        for _, highlow in df_highlow.iterrows():
            bar.update(1)
            turnover_update_alloc(highlow)

def turnover_update_alloc(highlow):
    df_alloc = asset_mz_highlow_alloc.where_highlow_id(highlow['globalid'])
    
    with click.progressbar(length=len(df_alloc), label=('update turnover %s' % (highlow['globalid'])).ljust(30)) as bar:
        for _, alloc in df_alloc.iterrows():
            bar.update(1)
            turnover_update(alloc)

            
def turnover_update(highlow):
    highlow_id = highlow['globalid']
    # 加载仓位信息
    df = asset_mz_highlow_pos.load(highlow_id)

    # 计算宽口换手率
    sr_turnover = DFUtil.calc_turnover(df)

    criteria_id = 6
    df_result = sr_turnover.to_frame('mz_value')
    df_result['mz_highlow_id'] = highlow_id
    df_result['mz_criteria_id'] = criteria_id
    df_result = df_result.reset_index().set_index(['mz_highlow_id', 'mz_criteria_id', 'mz_date'])
    asset_mz_highlow_criteria.save(highlow_id, criteria_id,  df_result)

    total_turnover = sr_turnover.sum()

    return total_turnover

    # df_result.reset_index(inplace=True)
    # df_result['turnover'] = df_result['turnover'].map(lambda x: "%6.2f%%" % (x * 100))
    # print tabulate(df_result, headers='keys', tablefmt='psql', stralign=u'right')
@highlow.command()
@click.option('--id', 'optid', help=u'ids of highlow to update')
@click.option('--list/--no-list', 'optlist', default=False, help=u'list instance to update')
@click.option('--exec/--no-exec', 'optexec', default=False, help=u'list instance to update')
@click.pass_context
def delete(ctx, optid, optlist, optexec):
    ''' delete highlow instance
    '''
    if optid is not None:
        highlows = [s.strip() for s in optid.split(',')]
    else:
        highlows = None

    df_highlow = asset_mz_highlow.load(highlows)

    if optlist:

        df_highlow['mz_name'] = df_highlow['mz_name'].map(lambda e: e.decode('utf-8'))
        print tabulate(df_highlow, headers='keys', tablefmt='psql')
        return 0

    if optid is None or not optexec:
         click.echo(click.style("\nboth --id and --exec is required to perform delete\n", fg='red'))
         return 0
    
    data = []
    with click.progressbar(length=len(df_highlow), label='highlow delete'.ljust(30)) as bar:
        for _, highlow in df_highlow.iterrows():
            bar.update(1)
            perform_delete(highlow)
            
def perform_delete(highlow):
    highlow_id = highlow['globalid']

    db = database.connection('asset')
    metadata = MetaData(bind=db)
    mz_highlow        = Table('mz_highlow', metadata, autoload=True)
    mz_highlow_asset  = Table('mz_highlow_asset', metadata, autoload=True)
    mz_highlow_pos    = Table('mz_highlow_pos', metadata, autoload=True)
    mz_highlow_nav    = Table('mz_highlow_nav', metadata, autoload=True)

    #
    # 处理删除
    #
    mz_highlow_nav.delete(mz_highlow_nav.c.mz_highlow_id == highlow_id).execute()
    mz_highlow_pos.delete(mz_highlow_pos.c.mz_highlow_id == highlow_id).execute()
    mz_highlow_asset.delete(mz_highlow_asset.c.mz_highlow_id == highlow_id).execute()
    mz_highlow.delete(mz_highlow.c.globalid == highlow_id).execute()

@highlow.command()
@click.option('--src', 'optsrc', help=u'src id of highlow to copy from')
@click.option('--dst', 'optdst', help=u'dst id of highlow to copy to')
@click.option('--list/--no-list', 'optlist', default=False, help=u'list instance to update')
@click.pass_context
def copy(ctx, optsrc, optdst, optlist):
    ''' create new highlow by copying  existed one
    '''
    if optsrc is not None:
        highlows = [optsrc]
    else:
        highlows = None

    df_highlow = asset_mz_highlow.load(highlows)

    if optlist:

        df_highlow['mz_name'] = df_highlow['mz_name'].map(lambda e: e.decode('utf-8'))
        print tabulate(df_highlow, headers='keys', tablefmt='psql')
        return 0

    if optsrc  is None or optdst is None:
        click.echo(click.style("\n both --src-id  and --dst-id is required to perform copy\n", fg='red'))
        return 0

    #
    # copy mz_highlow
    #
    df_highlow['globalid'] = optdst
    df_highlow.set_index(['globalid'], inplace=True)
    asset_mz_highlow.save(optdst, df_highlow)

    #
    # copy mz_highlow_alloc
    #
    df_highlow_alloc = asset_mz_highlow_alloc.where_highlow_id(optsrc)
    # df_highlow_alloc.reset_index(inplace=True)

    df_highlow_alloc['mz_highlow_id'] = optdst
    df_highlow_alloc['old'] = df_highlow_alloc['globalid']
    sr_tmp = df_highlow_alloc['mz_highlow_id'].str[:len(optdst) - 1]
    df_highlow_alloc['globalid'] = sr_tmp.str.cat((df_highlow_alloc['mz_risk'] * 10 % 10).astype(int).astype(str))

    df_xtab = df_highlow_alloc[['globalid', 'old']].copy()

    df_highlow_alloc.drop(['old'], axis=1, inplace=True)
    
    df_highlow_alloc.set_index(['globalid'], inplace=True)
    asset_mz_highlow_alloc.save(optdst, df_highlow_alloc)

    #
    # copy mz_highlow_argv
    #
    df_highlow_argv = asset_mz_highlow_argv.load(df_xtab['old'])
    df_highlow_argv.reset_index(inplace=True)

    df_highlow_argv = df_highlow_argv.merge(df_xtab, left_on='mz_highlow_id', right_on = 'old')
    df_highlow_argv['mz_highlow_id'] = df_highlow_argv['globalid']
    df_highlow_argv.drop(['globalid', 'old'], inplace=True, axis=1)
    df_highlow_argv = df_highlow_argv.set_index(['mz_highlow_id', 'mz_key'])

    asset_mz_highlow_argv.save(df_xtab['globalid'], df_highlow_argv)

    #
    # copy mz_highlow_asset
    #
    df_highlow_asset = asset_mz_highlow_asset.load(df_xtab['old'])
    # df_highlow_asset.reset_index(inplace=True)

    df_highlow_asset = df_highlow_asset.merge(df_xtab, left_on='mz_highlow_id', right_on = 'old')

    df_highlow_asset['mz_highlow_id'] = df_highlow_asset['globalid']
    df_highlow_asset.drop(['globalid', 'old'], inplace=True, axis=1)
    df_highlow_asset = df_highlow_asset.set_index(['mz_highlow_id', 'mz_asset_id'])

    asset_mz_highlow_asset.save(df_xtab['globalid'], df_highlow_asset)
    
