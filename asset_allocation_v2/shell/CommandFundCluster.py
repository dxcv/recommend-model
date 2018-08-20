# coding=utf-8


import pandas as pd
import numpy as np
from sqlalchemy import MetaData, Table, select, func, literal_column
import matplotlib
import matplotlib.pyplot as plt
import click
import sys
sys.path.append('shell/')
from sklearn.linear_model import LinearRegression
from scipy.stats import rankdata, spearmanr, pearsonr
from scipy.spatial import distance_matrix
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.cluster import SpectralClustering
from scipy.spatial import distance_matrix
import statsmodels.api as sm
import datetime
from ipdb import set_trace
import warnings
warnings.filterwarnings('ignore')

from db import asset_ra_pool_nav, asset_ra_pool_fund, asset_ra_pool, base_ra_fund_nav, base_ra_fund, base_ra_index, asset_ra_composite_asset_nav, database, asset_stock_factor, asset_fund_factor
# from CommandMarkowitz import load_nav_series
from trade_date import ATradeDate
from asset import Asset

@click.group(invoke_without_command=True)
@click.option('--id', 'optid', help='specify markowitz id')
@click.pass_context
def fuc(ctx, optid):
    '''
    factor layereing
    '''
    if ctx.invoked_subcommand is None:
        # ctx.invoke(fuc_stability, optid = optid)
        # ctx.invoke(fuc_style_concentration, optid = optid)
        ctx.invoke(fuc_ind_concentration, optid = optid)
    else:
        pass


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_stability(ctx, optid):

    ffe = asset_fund_factor.load_fund_factor_exposure()

    all_funds = ffe.index.levels[0]
    dict_stability = {}
    for fund in all_funds:
        dict_stability[fund] = {}

    dates = pd.date_range('2010-08-01', '2018-08-10', freq='183D')
    for ldate, date, ndate in zip(dates[:-2], dates[1:-1], dates[2:]):

        lffe = cal_feature(ffe, ldate, date)
        tffe = cal_feature(ffe, date, ndate)
        joint_funds = lffe.index.intersection(tffe.index)
        for fund in joint_funds:
            # print(fund, np.corrcoef(lffe.loc[fund], tffe.loc[fund])[1,0])
            dict_stability[fund][ndate] = np.corrcoef(lffe.loc[fund], tffe.loc[fund])[1,0]

    df_stability = pd.DataFrame(dict_stability)
    df_stability.to_csv('data/factor/stability/fund_stability.csv', index_label = 'date')


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_style_concentration(ctx, optid):

    ff_ids = ['FF.0000%02d'%i for i in range(1,10)]
    ffe = asset_fund_factor.load_fund_factor_exposure(ff_ids = ff_ids)

    all_funds = ffe.index.levels[0]
    dict_concentration = {}
    for fund in all_funds:
        dict_concentration[fund] = {}

    dates = pd.date_range('2010-08-01', '2018-08-10', freq='183D')
    for ldate, date in zip(dates[:-1], dates[1:]):

        tffe = cal_feature(ffe, ldate, date)
        tffe = tffe.apply(rankdata) / len(tffe)
        funds = tffe.index
        for fund in funds:
            dict_concentration[fund][date] = tffe.loc[fund].abs().max()

    df_concentration = pd.DataFrame(dict_concentration)
    df_concentration.to_csv('data/factor/concentration/fund_style_concentration.csv', index_label = 'date')


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_ind_concentration(ctx, optid):

    ff_ids = ['FF.1000%02d'%i for i in range(1,28)]
    ffe = asset_fund_factor.load_fund_factor_exposure(ff_ids = ff_ids)

    all_funds = ffe.index.levels[0]
    dict_concentration = {}
    for fund in all_funds:
        dict_concentration[fund] = {}

    dates = pd.date_range('2010-08-01', '2018-08-10', freq='183D')
    for ldate, date in zip(dates[:-1], dates[1:]):

        tffe = cal_feature(ffe, ldate, date)
        funds = tffe.index
        for fund in funds:
            dict_concentration[fund][date] = tffe.loc[fund].abs().max()

    df_concentration = pd.DataFrame(dict_concentration)
    df_concentration.to_csv('data/factor/concentration/fund_ind_concentration.csv', index_label = 'date')


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_cluster(ctx, optid):

    df_stability = pd.read_csv('data/factor/stability/fund_stability_mean.csv', index_col = ['date'], parse_dates = ['date'], encoding = 'gb2312')
    df_style_concentration = pd.read_csv('data/factor/concentration/fund_style_concentration_mean.csv', index_col = ['date'], parse_dates = ['date'], encoding = 'gb2312')
    df_ind_concentration = pd.read_csv('data/factor/concentration/fund_ind_concentration_mean.csv', index_col = ['date'], parse_dates = ['date'], encoding = 'gb2312')

    df_stability.index = ['%06d'%i for i in df_stability.index]
    df_style_concentration.index = ['%06d'%i for i in df_style_concentration.index]
    df_ind_concentration.index = ['%06d'%i for i in df_ind_concentration.index]

    valid_funds = df_stability[df_stability.stability > 0.9].index.values
    ffe = asset_fund_factor.load_fund_factor_exposure(fund_ids = valid_funds)

    fn = base_ra_fund.load(codes = valid_funds)
    fn = fn.set_index('ra_code')
    fn = fn.loc[:, ['ra_name']]

    dates = pd.date_range('2010-08-01', '2018-08-10', freq='183D')
    dates = dates[-2:]
    for ldate, date in zip(dates[:-1], dates[1:]):

        tffe = cal_feature(ffe, ldate, date)
        df_dist = tffe.T.corr()
        asset_cluster = clusterSimple(df_dist, 0.9)
        clusters = sorted(asset_cluster, key = lambda x: len(asset_cluster[x]), reverse = True)
        for layer in clusters:
            print(layer)
            funds = asset_cluster[layer]
            fund_names = fn.loc[funds]
            fund_names['style_concentration'] = df_style_concentration.loc[fund_names.index].concentration
            fund_names['ind_concentration'] = df_ind_concentration.loc[fund_names.index].concentration
            tffe.iloc[:, :9] = tffe.iloc[:,:9].apply(rankdata) / len(tffe)
            print(fund_names)
            print(tffe.loc[fund_names.index].mean().sort_values(ascending = False))
            print('#############################################################################')


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_cluster2(ctx, optid):

    df_stability = pd.read_csv('data/factor/stability/fund_stability_mean.csv', index_col = ['date'], parse_dates = ['date'], encoding = 'gb2312')
    df_style_concentration = pd.read_csv('data/factor/concentration/fund_style_concentration_mean.csv', index_col = ['date'], parse_dates = ['date'], encoding = 'gb2312')
    df_ind_concentration = pd.read_csv('data/factor/concentration/fund_ind_concentration_mean.csv', index_col = ['date'], parse_dates = ['date'], encoding = 'gb2312')

    df_stability.index = ['%06d'%i for i in df_stability.index]
    df_style_concentration.index = ['%06d'%i for i in df_style_concentration.index]
    df_ind_concentration.index = ['%06d'%i for i in df_ind_concentration.index]

    valid_funds = df_stability[df_stability.stability > 0.0].index.values
    ffe = asset_fund_factor.load_fund_factor_exposure(fund_ids = valid_funds)

    fn = base_ra_fund.load(codes = valid_funds)
    fn = fn.set_index('ra_code')
    fn = fn.loc[:, ['ra_name']]

    dates = pd.date_range('2010-08-01', '2018-08-10', freq='183D')
    dates = dates[-2:]
    for ldate, date in zip(dates[:-1], dates[1:]):

        tffe = cal_feature(ffe, ldate, date)
        dist = distance_matrix(tffe, tffe)
        df_dist = pd.DataFrame(data = dist, index = tffe.index, columns = tffe.index)
        asset_cluster = clusterSimple2(df_dist, 1.0)
        clusters = sorted(asset_cluster, key = lambda x: len(asset_cluster[x]), reverse = True)
        for layer in clusters:
            print(layer)
            funds = asset_cluster[layer]
            fund_names = fn.loc[funds]
            fund_names['style_concentration'] = df_style_concentration.loc[fund_names.index].concentration
            fund_names['ind_concentration'] = df_ind_concentration.loc[fund_names.index].concentration
            tffe.iloc[:, :9] = tffe.iloc[:,:9].apply(rankdata) / len(tffe)
            print(fund_names)
            print(tffe.loc[fund_names.index].mean().sort_values(ascending = False))
            print('#############################################################################')


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_factor_cluster(ctx, optid):


    ff_ids = ['FF.0000%02d'%i for i in range(1,10)] + ['FF.1000%02d'%i for i in range(1,28)]
    ffe = asset_fund_factor.load_fund_factor_exposure(ff_ids = ff_ids)

    dates = pd.date_range('2010-08-01', '2018-08-10', freq='183D')
    dates = dates[-2:]
    for ldate, date in zip(dates[:-1], dates[1:]):

        tffe = cal_feature(ffe, ldate, date)
        tffe.iloc[:, :9] = tffe.iloc[:,:9].apply(rankdata) / len(tffe)
        for i in range(len(tffe)):
            print(tffe[tffe.iloc[:,i] > 0.9].mean().sort_values(ascending = False))


def cal_feature(ffe, sdate, edate):

    ffe = ffe.reset_index()
    ffe = ffe[(ffe.trade_date >= sdate) & (ffe.trade_date <= edate)]
    ffe = ffe[['fund_id', 'ff_id', 'exposure']].groupby(['fund_id', 'ff_id']).last().unstack()
    ffe.columns = ffe.columns.levels[1]
    ffe = ffe.dropna()

    return ffe


def fund_stability_filter():

    fs = pd.read_csv('data/factor/stability/fund_stability.csv', index_col = ['date'], parse_dates = ['date'])
    valid_funds = fs.tail(4).dropna(1).columns
    fs = fs.loc[:, valid_funds]
    fsm = fs.mean().dropna()
    fsm = fsm.to_frame(name = 'stability')

    fn = base_ra_fund.load(codes = fsm.index)
    fn = fn.set_index('ra_code')
    fn = fn.loc[:, ['ra_name']]

    df = pd.merge(fn, fsm, left_index = True, right_index = True)
    df = df.sort_values(by = 'stability', ascending = False)
    df.to_csv('data/factor/stability/fund_stability_mean.csv', index_label = 'date', encoding = 'gb2312')


def fund_concentration_filter():

    fc = pd.read_csv('data/factor/concentration/fund_style_concentration.csv', index_col = ['date'], parse_dates = ['date'])
    # fc = pd.read_csv('data/factor/concentration/fund_ind_concentration.csv', index_col = ['date'], parse_dates = ['date'])
    valid_funds = fc.tail(4).dropna(1).columns
    fc = fc.loc[:, valid_funds]
    fcm = fc.mean().dropna()
    fcm = fcm.to_frame(name = 'concentration')

    fn = base_ra_fund.load(codes = fcm.index)
    fn = fn.set_index('ra_code')
    fn = fn.loc[:, ['ra_name']]

    df = pd.merge(fn, fcm, left_index = True, right_index = True)
    df = df.sort_values(by = 'concentration', ascending = False)
    df.to_csv('data/factor/concentration/fund_style_concentration_mean.csv', index_label = 'date', encoding = 'gb2312')
    # df.to_csv('data/factor/concentration/fund_ind_concentration_mean.csv', index_label = 'date', encoding = 'gb2312')


def clusterSimple(dist, threshold):

    asset_cluster = {}
    factor_ids = dist.keys()
    asset_cluster[0] = [factor_ids[0]]
    for factor_id in factor_ids[1:]:
        print(factor_id)
        flag = False
        new_layer = len(asset_cluster)
        tmp_corrs = {}
        for layer in asset_cluster.keys():
            tmp_corrs[layer] = dist.loc[factor_id, asset_cluster[layer]].values.mean()
            tmp_corrs_ser = pd.Series(tmp_corrs)
            tmp_corrs_ser = tmp_corrs_ser.sort_values(ascending = False)
        if (tmp_corrs_ser.iloc[0] > threshold) and (not flag):
            flag = True
            asset_cluster[tmp_corrs_ser.index[0]].append(factor_id)
        if not flag:
            asset_cluster[new_layer] = [factor_id]

    return asset_cluster


def clusterSimple2(dist, threshold):

    asset_cluster = {}
    factor_ids = dist.keys()
    asset_cluster[0] = [factor_ids[0]]
    for factor_id in factor_ids[1:]:
        print(factor_id)
        flag = False
        new_layer = len(asset_cluster)
        tmp_corrs = {}
        for layer in asset_cluster.keys():
            tmp_corrs[layer] = dist.loc[factor_id, asset_cluster[layer]].values.max()
            tmp_corrs_ser = pd.Series(tmp_corrs)
            tmp_corrs_ser = tmp_corrs_ser.sort_values(ascending = True)
        if (tmp_corrs_ser.iloc[0] < threshold) and (not flag):
            flag = True
            asset_cluster[tmp_corrs_ser.index[0]].append(factor_id)
        if not flag:
            asset_cluster[new_layer] = [factor_id]

    return asset_cluster







if __name__ == '__main__':

    # fund_stability_filter()
    fund_concentration_filter()





