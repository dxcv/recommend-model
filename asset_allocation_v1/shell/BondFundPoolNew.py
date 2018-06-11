#coding=utf-8
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
import click
from asset import *
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from db import *
from trade_date import *
from sklearn.linear_model import Lasso
from scipy.stats import ttest_rel
import DBData
import matplotlib
myfont = matplotlib.font_manager.FontProperties(fname='/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', size=10)

warnings.filterwarnings("ignore")

class BondIndex(Asset):
    cache = {}

    @classmethod
    def __getCache(cls, secode):
        if secode in cls.cache:
            return cls.cache[secode]
        return None

    def __new__(cls, secode, *args, **kwargs):
        secode = str(secode)
        existing = cls.__getCache(secode)
        if existing:
            return existing
        return super(BondIndex, cls).__new__(cls)

    def __init__(self, secode):
        secode = str(secode)
        if secode in self.cache:
            return
        name = load_bond_index_info(secode).loc[secode, "INDEXNAME"]
        nav_sr = load_cbdindex_nav(secode)
        if nav_sr.empty:
            #  nav_sr = load_index_nav(secode)
            print "? %s" % secode
        super(BondIndex, self).__init__(secode, name=name, nav_sr=nav_sr)
        self.cache[secode]=self

    def nav(self, begin_date = None, end_date = None, reindex = None, lookback=0):
        if begin_date is None:
            begin_date = '2013-01-01'
        if end_date is None:
            end_date = '2018-05-01'
        if reindex is None:
            reindex = ATradeDate.week_trade_date()
        nav = super(BondIndex, self).nav(begin_date, end_date, reindex).dropna()
        nav.name = self.name
        nav = nav.loc[begin_date:end_date]
        if lookback != 0:
            nav = nav.iloc[-lookback:]
        if nav.empty:
            return pd.Series()
        return nav/nav[0]

    def inc(self, begin_date = None, end_date = None, reindex = None, lookback=0):
        return self.nav(begin_date, end_date, reindex, lookback).pct_change().fillna(0)


#读取数据库
def load_bond_index_info(secode = None):
    db = database.connection('caihui')
    t1 = Table('tq_ix_basicinfo', MetaData(bind=db), autoload=True)
    columns = [t1.c.SECODE, t1.c.INDEXNAME, t1.c.ESTCLASS]
    if secode == None:
        s = select(columns).where((t1.c.INDEXTYPE == 4) and t1.c.ISVALID)
    else:
        s = select(columns).where(t1.c.SECODE == secode)
    df = pd.read_sql(s, db, index_col="SECODE")
    return df

def load_cbdindex_nav(secode):
    db = database.connection('caihui')
    t1 = Table('tq_qt_cbdindex', MetaData(bind=db), autoload=True)
    columns = [t1.c.TRADEDATE, t1.c.DIRTYCLOSE]
    s = select(columns).where(t1.c.SECODE == secode)
    df = pd.read_sql(s, db, index_col='TRADEDATE', parse_dates=['TRADEDATE'])
    return df.squeeze()

#  def load_index_nav(secode):
    #  db = database.connection('caihui')
    #  t1 = Table('tq_qt_index', MetaData(bind=db), autoload=True)
    #  columns = [t1.c.TRADEDATE, t1.c.TCLOSE]
    #  s = select(columns).where(t1.c.SECODE == secode)
    #  df = pd.read_sql(s, db, index_col='TRADEDATE', parse_dates=['TRADEDATE'])
    #  return df.squeeze()

def get_fund_nav(gid, begin_date = '2013-01-01', end_date='2018-05-01'):
    if os.path.exists("tmpfund/%s.csv" % gid):
        nav = pd.read_csv("tmpfund/%s.csv" % gid, index_col=0, parse_dates=True, header=None).squeeze()
        nav.index.name = "date"
        nav.name = "nav"
    else:
        nav = base_ra_fund_nav.load_series(gid)
        if not nav.empty:
            nav.to_csv("tmpfund/%s.csv" % gid)
        else:
            print gid
    return nav.reindex(tdate).loc[begin_date:end_date]

def get_fund_inc(gid, begin_date = '2013-01-01', end_date='2018-05-01'):
    return get_fund_nav(gid, begin_date, end_date).pct_change().fillna(0)



bond_fund = base_ra_fund.find_type_fund(2).set_index("ra_code")
bond_fund_ids = bond_fund.globalid.ravel()

#准备因子
lasso = Lasso(alpha=0, fit_intercept=True, positive=True)
tdate = ATradeDate.week_trade_date()
benchmark = BondIndex("2070006886")



#因子相关指数
#  indexes = pd.read_excel('Book1.xlsx', index_col=0)
#  index_ids = indexes.index[1:-2]
#  used_factor = [2070000278, 2070006893]
indexes = pd.read_excel('factor_cover_credit.xlsx', index_col=0).iloc[1:]
#  indexes = pd.read_excel('factor_cover_time.xlsx', index_col=0)
index_ids = indexes.index


#选取因子
#pair t test
def run_ttest_rel(begin_date = None, end_date = None):
    blacklist = [2070007385, 2070000071, 2070007387]
    pv = {}
    mean = {}
    stat = {}
    for id_ in index_ids:
        if id_ not in blacklist:
            targetIndex = BondIndex(id_)
            targetInc = targetIndex.inc(begin_date, end_date)
            benchmarkInc = benchmark.inc(begin_date, end_date)
            if len(targetInc) == len(benchmarkInc):
                stat_, pvalue =  ttest_rel(targetInc, benchmarkInc)
                stat[id_] = stat_
                pv[id_] = pvalue
                mean[id_] = targetIndex.inc().mean()
    res = pd.DataFrame({'stat':stat, 'pvalue':pv, 'mean':mean})
    res["name"] = indexes.loc[res.index].squeeze()
    res.index.name = "secode"
    return res[(res.pvalue<0.05) & (res.stat>0)]


def run_ttest_rel_by_adjpt(begin_date='2010-01-01', end_date="2018-05-01"):
    lookback = 52
    #  lookback = 13
    result = []
    if end_date is None:
        yesterday = datetime.now() - timedelta(days=1)
        end_date = yesterday.strftime("%Y-%m-%d")
    adjusted_point = ATradeDate.month_trade_date(begin_date=begin_date, end_date=end_date)
    with click.progressbar(length = len(adjusted_point), label="ttest_rel") as bar:
        for day in adjusted_point:
            index = ATradeDate.week_trade_date(end_date=day)[-lookback:]
            begin_date, end_date = index[0], day
            tmp_df = run_ttest_rel(begin_date, end_date).reset_index()
            tmp_df['date'] = day
            result.append(tmp_df)
            bar.update(1)
    return pd.concat(result).set_index("date", "secode")


def matrix_constructor(x, begin_date=None, end_date=None):
    return np.vstack(map(lambda t: BondIndex(t).inc(begin_date, end_date), x)).T

def factor_regression(factors, begin_date, end_date):
    all_fund_nav = DBData.bond_fund_value(begin_date, end_date)
    all_fund_inc = all_fund_nav.pct_change().fillna(0)
    factor_matrix = matrix_constructor(factors, begin_date, end_date)
    result = []
    for i in range(len(all_fund_inc)):
        fund_inc = all_fund_inc.T.iloc[i]
        fund_id = fund_inc.name
        res = lasso.fit(factor_matrix, fund_inc)
        score = res.score(factor_matrix, fund_inc)
        param_dict = {"fund_id":fund_id, "score":score}
        param_dict.update(dict(zip(factors, tuple((res.coef_/res.coef_.sum())))))
        result.append(pd.DataFrame([param_dict]))
    return pd.concat(result).set_index("fund_id")

def lookupday(day, lookback=0, lookforward=0):
    if lookback == 0 and lookforward == 0:
        return
    if lookback != 0:
        res = ATradeDate.week_trade_date(end_date = day)[-lookback]
    if lookforward != 0:
        res = ATradeDate.week_trade_date(begin_date = day)[lookback]
    return res.strftime("%Y-%m-%d")

def mean_of_all_fund(codes, begin_date, end_date):
    fund_values = DBData.bond_fund_value(start_date=begin_date, end_date=end_date).apply(lambda x: x[-1]/x[0]-1)
    ret_sr = fund_values.loc[codes]
    names = bond_fund.loc[ret_sr.index].ra_name
    return (fund_values.mean(), pd.DataFrame({"return":ret_sr, "name":names}))

def show_selected_factor(factors, day):
    factors = factors.secode
    for code in factors:
        BondIndex(code).nav(begin_date=lookupday(day, lookback=52), end_date=day).plot()
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0., prop=myfont)
    plt.show()

if __name__ == "__main__":
    from ipdb import set_trace
    #  df_selected_factors = run_ttest_rel_by_adjpt()
    #  end_date = '2018-04-27'
    #  begin_date = ATradeDate.week_trade_date(end_date=end_date)[-52]
    #  factors_0427 = df_selected_factors.loc[end_date]
    #  reg = factor_regression(factors_0427.secode, begin_date, end_date)
    set_trace()
