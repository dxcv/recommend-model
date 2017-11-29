#coding=utf8

import sys
import logging
import pandas as pd
import numpy as np
import datetime
import calendar
import heapq
import TradeNav
import readline
import pdb



from datetime import datetime, timedelta
from sqlalchemy import *
from util.xdebug import dd

from db import *

logger = logging.getLogger(__name__)
readline.parse_and_bind('tab: complete')

class Policy(object):    

    def __init__(self, df_ts_order_fund):

        self.df_ts_order_fund = df_ts_order_fund.set_index(['ts_portfolio_txn_id', 'ts_placed_date', 'ts_trade_type'], drop=False).sort_index()

        # # 赎回到账期限 记录了每个基金的到账日到底是T+n；
        # # 购买确认日期 记录了每个基金的到购买从份额确认到可以赎回需要T+n；
        # self.df_ack = base_fund_infos.load_ack(fund_ids)
        # # dd(self.df_ack.loc[(self.df_ack['buy'] > 10) | (self.df_ack['redeem'] > 10) ])

        # # 未来交易日 记录了每个交易日的t+n是哪个交易日
        # max_n = int(max(self.df_ack['buy'].max(), self.df_ack['redeem'].max()))
        # dates = base_trade_dates.load_index(sdate, edate)
        # self.df_t_plus_n = pd.DataFrame(dates, index=dates, columns=["td_date"])
        # for i in xrange(0, max_n + 1):
        #     self.df_t_plus_n["T+%d" % i] = self.df_t_plus_n['td_date'].shift(-i)
        # self.df_t_plus_n = self.df_t_plus_n.drop('td_date', axis=1)
        # self.df_t_plus_n.fillna(pd.to_datetime('2029-01-01'), inplace=True)
        # # dd(self.df_t_plus_n)


        # # 任何自然日所属交易日及其对应的净值序列
        # self.dt_nav = Nav.Nav().load_tdate_and_nav(fund_ids, sdate, edate)
        # # dd(self.dt_nav)
        
        # #
        # # 加载分红信息
        # #
        # self.df_bonus = base_ra_fund_bonus.load(fund_ids, sdate=sdate, edate=edate)
        # #
        # # 我们发现基础数据里面有部分基金缺少派息日信息(000930)，这里统
        # # 一用除息日填充。
        # #
        # if not self.df_bonus.loc[self.df_bonus['ra_payment_date'].isnull(), 'ra_payment_date'].empty:
        #     self.df_bonus.loc[self.df_bonus['ra_payment_date'].isnull(), 'ra_payment_date'] = self.df_bonus['ra_dividend_date']
        # # dd(self.df_bonus, self.df_bonus.loc[('2016-01-20', [523, 524]), :])
        
        # # 
        # # 加载分拆信息
        # # 
        # #
        # self.df_split = base_fund_split.load(fund_ids, sdate, edate)
        # self.df_split.sort_index(inplace=True)
        # # dd(self.df_split)

        # # 
        # # 加载基金净值
        # #
        # self.df_nav = Nav.Nav().load_nav_and_date(fund_ids, sdate, edate)
        # self.df_nav = self.df_nav.swaplevel(0, 1, axis=0)
        # self.df_nav.sort_index(inplace=True)
        # # dd(self.df_nav.head(20))

        # #
        # # 加载调仓信息
        # #
        # for day, v0 in df_pos.groupby(level=0):
        #     argv = {'pos': v0.loc[day]}
        #     ev = (day + timedelta(hours=17), 8, 0, 0, argv)
        #     heapq.heappush(self.events, ev)
        
        # pass
    
    def place_buy_order(self, dt, ts_order):
        date = pd.to_datetime(dt.date())

        df_ts_order_fund = self.df_ts_order_fund.loc[(ts_order['ts_txn_id'], date, (30, 31, 63)), ['ts_txn_id', 'ts_uid', 'ts_portfolio_txn_id', 'ts_pay_method', 'ts_fund_code', 'ts_trade_type', 'ts_trade_status', 'ts_placed_amount', 'ts_placed_share', 'ts_placed_fee', 'ts_scheduled_at']].copy()

        df_ts_order_fund = df_ts_order_fund.reset_index(drop=True).set_index('ts_txn_id', drop=False)
        df_ts_order_fund['ts_trade_status'] = 0
        df_ts_order_fund['ts_trade_date'] = None
        df_ts_order_fund['ts_trade_nav'] = 0.0000
        df_ts_order_fund['ts_placed_date'] = None
        df_ts_order_fund['ts_placed_time'] = None
        df_ts_order_fund['ts_acked_date'] = None
        df_ts_order_fund['ts_acked_amount'] = 0.00
        df_ts_order_fund['ts_acked_share'] = 0.0000
        df_ts_order_fund['ts_acked_fee'] = 0.00

        return df_ts_order_fund

    def is_need_adjust(self, dt):
        date = pd.to_datetime(dt.date())

        dd(date, self.df_ts_order_fund)
        
    def place_adjust_order(self, dt, ts_order):
        date = pd.to_datetime(dt.date())

        df_ts_order_fund = self.df_ts_order_fund.loc[(ts_order['ts_txn_id'], date, (30, 31, 40, 41, 50, 51, 63, 64)), ['ts_txn_id', 'ts_uid', 'ts_portfolio_txn_id', 'ts_pay_method', 'ts_fund_code', 'ts_trade_type', 'ts_trade_status', 'ts_placed_amount', 'ts_placed_share', 'ts_placed_fee', 'ts_scheduled_at']].copy()

        df_ts_order_fund = df_ts_order_fund.reset_index(drop=True).set_index('ts_txn_id', drop=False)
        df_ts_order_fund['ts_trade_status'] = 0
        df_ts_order_fund['ts_trade_date'] = None
        df_ts_order_fund['ts_trade_nav'] = 0.0000
        df_ts_order_fund['ts_placed_date'] = None
        df_ts_order_fund['ts_placed_time'] = None
        df_ts_order_fund['ts_acked_date'] = None
        df_ts_order_fund['ts_acked_amount'] = 0.00
        df_ts_order_fund['ts_acked_share'] = 0.0000
        df_ts_order_fund['ts_acked_fee'] = 0.00

        return df_ts_order_fund
