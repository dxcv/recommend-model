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
from sklearn.cluster import AgglomerativeClustering, KMeans, SpectralClustering, AffinityPropagation
from sklearn.metrics import silhouette_score, silhouette_samples
from scipy.spatial import distance_matrix
import statsmodels.api as sm
import datetime
from collections import defaultdict
from ipdb import set_trace
import warnings
warnings.filterwarnings('ignore')

from db import asset_ra_pool_nav, asset_ra_pool_fund, asset_ra_pool, base_ra_fund_nav, base_ra_fund, base_ra_index, asset_ra_composite_asset_nav, database, asset_stock_factor, asset_fund_factor, asset_fund, asset_index, asset_index_factor
# from CommandMarkowitz import load_nav_series
from trade_date import ATradeDate
from asset import Asset

@click.group(invoke_without_command=True)
@click.option('--id', 'optid', help='specify markowitz id')
@click.pass_context
def fuc(ctx, optid):
    '''
    factor layering
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
    df_concentration.to_csv('data/factor/concentration/fund_ind_concentration.csv', index_label='date')


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_cluster_corr(ctx, optid):

    start_date = '2011-12-01'
    # start_date = '2013-09-30'
    # start_date = '2017-12-01'
    # end_date = '2010-01-05'
    end_date = '2018-09-01'
    lookback = 360
    layer_num = 10
    preference = 0.80
    method = 'euclid'
    # valid_funds = asset_fund.load_type_fund(l2codes=['200209']).index
    # valid_funds = asset_fund.load_type_fund(l2codes=['200202']).index
    # valid_funds = asset_fund.load_type_fund(l2codes=['200101']).index
    # 股票型基金加混合型基金
    # valid_funds = asset_fund.load_type_fund(l1codes=['2001', '2002']).index
    # 普通股票型基金加混合偏股型基金
    valid_funds = asset_fund.load_type_fund(l2codes=['200101', '200201']).index
    df_nav_fund = base_ra_fund_nav.load_daily(start_date, end_date, codes=valid_funds)

    fn = base_ra_fund.load(codes=valid_funds)
    fn = fn.set_index('ra_code')
    fn = fn.loc[:, ['ra_name']]
    # fn.to_csv('fund_name_strategy.csv', encoding='gbk')

    dates = pd.date_range(start_date, end_date)
    df_cluster_ret = pd.DataFrame(columns=['cluster%02d' % i for i in range(layer_num)])
    df_cluster = pd.DataFrame(columns=['trade_date', 'cluster_id', 'fund_id'])
    pre_asset_cluster = None
    pre_clusters = None
    pre_funds_output = None
    for ldate, date in zip(dates[:-lookback], dates[lookback:]):

        print(date)
        tnav = df_nav_fund.loc[ldate:date]
        tnav = tnav.dropna(1)
        tret = tnav.pct_change().dropna()
        # tnav = tnav.sub(tnav.mean(1), 0).div(tnav.std(1), 0)
        if method == 'corr':
            df_dist = tret.corr()
            df_dist = df_dist.fillna(0.0)
        elif method == 'euclid':
            tnav = tnav / tnav.iloc[0]
            dist = distance_matrix(tnav.T, tnav.T)
            df_dist = -pd.DataFrame(data=dist, columns=tnav.columns, index=tnav.columns)

        asset_cluster, silh, model = cluster_ap(df_dist, preference=preference)
        fund_codes = df_dist.index
        # asset_cluster = cluster_km(df_dist, 30)

        if pre_asset_cluster is not None:

            pre_silh = np.nan

            # if date.month != 12 or date.day != 31:
                # df_dist = df_dist.loc[pre_fund_codes]
                # pre_silh = silhouette_score(-df_dist, pre_model.labels_)

            df_dist = df_dist.loc[pre_fund_codes]
            pre_silh = silhouette_score(-df_dist, pre_model.labels_)
            if not pre_silh > silh - 0.3:
                tmp_clusters = sorted(asset_cluster, key=lambda x: len(asset_cluster[x]), reverse=True)[:layer_num+5]
                cluster_fund_num = np.array([len(asset_cluster[x]) for x in tmp_clusters])
                cluster_fund_num = max(len(cluster_fund_num[cluster_fund_num >= 5]), layer_num)
                tmp_clusters = tmp_clusters[:cluster_fund_num]
                clusters = []
                cluster_nav = {}
                for k in tmp_clusters:
                    funds = asset_cluster[k]
                    new_nav = tret.loc[:, funds].sum().mean()
                    cluster_nav[k] = new_nav

                for layer in pre_clusters:
                    pre_funds = pre_asset_cluster[layer]
                    pre_nav = tret.loc[:, pre_funds].sum().mean()
                    min_dist = 100.0
                    for k in tmp_clusters:
                        if k not in clusters:
                            new_nav = cluster_nav[k]
                            new_funds = asset_cluster[k]
                            tmp_overlap = len(np.intersect1d(pre_funds, new_funds)) / len(pre_funds)
                            tmp_dist = abs(new_nav - pre_nav) / (tmp_overlap + 0.01)
                            # tmp_dist = 1 - tmp_overlap
                            if tmp_dist < min_dist:
                                min_dist = tmp_dist
                                max_layer = k
                    clusters.append(max_layer)

                pre_clusters = clusters
                pre_asset_cluster = asset_cluster
                pre_fund_codes = fund_codes
                pre_model = model
            else:
                clusters = pre_clusters
                asset_cluster = pre_asset_cluster
                fund_codes = pre_fund_codes
                model = pre_model

        else:
            clusters = sorted(asset_cluster, key=lambda x: len(asset_cluster[x]), reverse=True)[:layer_num]
            pre_clusters = clusters
            pre_asset_cluster = asset_cluster
            pre_fund_codes = fund_codes
            pre_model = model
            # for k in clusters:
            #   print(asset_cluster[k])
        # for layer in clusters[:5]:
            # print(layer)
            # funds = asset_cluster[layer]
            # fund_names = fn.loc[funds]
            # print(fund_names)
            # print('#############################################################################')
        cluster_rets = []
        cluster_funds_day = pd.DataFrame(columns=['trade_date', 'cluster_id', 'fund_id'])
        for layer in clusters:
            cluster_funds_layer_day = pd.DataFrame(columns=['trade_date', 'cluster_id', 'fund_id'])
            funds = asset_cluster[layer]
            cluster_id = clusters.index(layer)
            cluster_funds_layer_day['fund_id'] = funds
            cluster_funds_layer_day['trade_date'] = date
            cluster_funds_layer_day['cluster_id'] = cluster_id
            cluster_funds_day = pd.concat([cluster_funds_day, cluster_funds_layer_day])
            cluster_ret = tret.loc[:, funds].iloc[-1].mean()
            cluster_rets.append(cluster_ret)
            # if cluster_id == layer_num - 1:
            if cluster_id == 3:
                print(fn.loc[funds])
                if pre_funds_output is not None:
                    tr = 1 - len(np.intersect1d(pre_funds_output, funds)) / len(pre_funds_output)
                    print("turnover ratio: %.2f" % tr)
                pre_funds_output = funds
        trade_date = tret.index[-1]
        df_cluster_ret.loc[trade_date] = cluster_rets
        df_cluster = pd.concat([df_cluster, cluster_funds_day])
        if date.day == 30:
            df_cluster_ret.to_csv('data/fund_cluster/fund_cluster_ret.csv', index_label='date')

    df_cluster_ret.to_csv('data/fund_cluster/fund_cluster_ret.csv', index_label='date')
    df_cluster = df_cluster.set_index(['trade_date', 'cluster_id', 'fund_id'])
    asset_fund_factor.update_fc_fund_cluster(df_cluster)


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_cluster_fs(ctx, optid):

    start_date = '2011-12-01'
    # start_date = '2013-09-30'
    # start_date = '2017-12-01'
    # end_date = '2010-01-05'
    end_date = '2018-09-01'
    lookback = 360
    layer_num = 10
    preference = 0.80
    # valid_funds = asset_fund.load_type_fund(l2codes=['200209']).index
    # valid_funds = asset_fund.load_type_fund(l2codes=['200202']).index
    # valid_funds = asset_fund.load_type_fund(l2codes=['200101']).index
    # 股票型基金加混合型基金
    # valid_funds = asset_fund.load_type_fund(l1codes=['2001', '2002']).index
    # 普通股票型基金加混合偏股型基金
    valid_funds = asset_fund.load_type_fund(l2codes=['200101', '200201']).index
    df_nav_fund = base_ra_fund_nav.load_daily(start_date, end_date, codes=valid_funds)

    fn = base_ra_fund.load(codes=valid_funds)
    fn = fn.set_index('ra_code')
    fn = fn.loc[:, ['ra_name']]
    # fn.to_csv('fund_name_strategy.csv', encoding='gbk')

    dates = pd.date_range(start_date, end_date)
    df_cluster_ret = pd.DataFrame(columns=['cluster%02d' % i for i in range(layer_num)])
    df_cluster = pd.DataFrame(columns=['trade_date', 'cluster_id', 'fund_id'])
    pre_asset_cluster = None
    pre_clusters = None
    pre_funds_output = None
    for ldate, date in zip(dates[:-lookback], dates[lookback:]):

        print(date)
        tnav = df_nav_fund.loc[ldate:date]
        tnav = tnav.dropna(1)
        tnav = tnav.pct_change().dropna()
        # tnav = tnav.sub(tnav.mean(1), 0).div(tnav.std(1), 0)
        df_dist = tnav.corr()
        df_dist = df_dist.fillna(0.0)
        asset_cluster = cluster_ap(df_dist, preference)
        # asset_cluster = cluster_km(df_dist, 30)

        if pre_asset_cluster is not None:

            tmp_clusters = sorted(asset_cluster, key=lambda x: len(asset_cluster[x]), reverse=True)[:layer_num+5]
            cluster_fund_num = np.array([len(asset_cluster[x]) for x in tmp_clusters])
            cluster_fund_num = max(len(cluster_fund_num[cluster_fund_num >= 5]), layer_num)
            tmp_clusters = tmp_clusters[:cluster_fund_num]
            clusters = []
            cluster_nav = {}
            for k in tmp_clusters:
                funds = asset_cluster[k]
                new_nav = tnav.loc[:, funds].sum().mean()
                cluster_nav[k] = new_nav

            for layer in pre_clusters:
                pre_funds = pre_asset_cluster[layer]
                pre_nav = tnav.loc[:, pre_funds].sum().mean()
                min_dist = 100.0
                for k in tmp_clusters:
                    if k not in clusters:
                        new_nav = cluster_nav[k]
                        new_funds = asset_cluster[k]
                        tmp_overlap = len(np.intersect1d(pre_funds, new_funds)) / len(pre_funds)
                        tmp_dist = abs(new_nav - pre_nav) / (tmp_overlap + 0.01)
                        # tmp_dist = 1 - tmp_overlap
                        if tmp_dist < min_dist:
                            min_dist = tmp_dist
                            max_layer = k
                clusters.append(max_layer)

            pre_clusters = clusters
            pre_asset_cluster = asset_cluster
        else:
            clusters = sorted(asset_cluster, key=lambda x: len(asset_cluster[x]), reverse=True)[:layer_num]
            pre_clusters = clusters
            pre_asset_cluster = asset_cluster
            # for k in clusters:
            #   print(asset_cluster[k])
        # for layer in clusters[:5]:
            # print(layer)
            # funds = asset_cluster[layer]
            # fund_names = fn.loc[funds]
            # print(fund_names)
            # print('#############################################################################')
        cluster_rets = []
        cluster_funds_day = pd.DataFrame(columns=['trade_date', 'cluster_id', 'fund_id'])
        for layer in clusters:
            cluster_funds_layer_day = pd.DataFrame(columns=['trade_date', 'cluster_id', 'fund_id'])
            funds = asset_cluster[layer]
            cluster_id = clusters.index(layer)
            cluster_funds_layer_day['fund_id'] = funds
            cluster_funds_layer_day['trade_date'] = date
            cluster_funds_layer_day['cluster_id'] = cluster_id
            cluster_funds_day = pd.concat([cluster_funds_day, cluster_funds_layer_day])
            cluster_ret = tnav.loc[:, funds].iloc[-1].mean()
            cluster_rets.append(cluster_ret)
            if cluster_id == layer_num - 1:
            # if cluster_id == 0:
                print(fn.loc[funds])
                if pre_funds_output is not None:
                    tr = 1 - len(np.intersect1d(pre_funds_output, funds)) / len(pre_funds_output)
                    print("turnover ratio: %.2f" % tr)
                pre_funds_output = funds
        trade_date = tnav.index[-1]
        df_cluster_ret.loc[trade_date] = cluster_rets
        df_cluster = pd.concat([df_cluster, cluster_funds_day])
        if date.day == 30:
            df_cluster_ret.to_csv('data/fund_cluster/fund_cluster_ret.csv', index_label='date')

    df_cluster_ret.to_csv('data/fund_cluster/fund_cluster_ret.csv', index_label='date')
    df_cluster = df_cluster.set_index(['trade_date', 'cluster_id', 'fund_id'])
    asset_fund_factor.update_fc_fund_cluster(df_cluster)


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_cluster_analysis(ctx, optid):

    # alloc_ids = ['MZ.FC0%02d0' % i for i in range(1, 11)]
    # alloc_ids = ['MZ.FC2%02d0' % i for i in range(1, 11)]
    alloc_ids = ['MZ.FC2060']
    df_nav_cluster = {}
    for alloc_id in alloc_ids:
        alloc_nav = Asset.load_nav_series(alloc_id)
        df_nav_cluster[alloc_id] = alloc_nav
    df_nav_cluster = pd.DataFrame(df_nav_cluster)
    df_nav_cluster = df_nav_cluster.dropna()
    df_nav_cluster = df_nav_cluster / df_nav_cluster.iloc[0]
    # df_ret_cluster = df_nav_cluster.pct_change().dropna()
    # df_corr = df_ret_cluster.corr()
    df_thresh = Asset.load_nav_series('120000084')
    df_thresh = df_thresh.reindex(df_nav_cluster.index)
    df_thresh = df_thresh / df_thresh.iloc[0]
    df_nav_cluster_rela = df_nav_cluster.div(df_thresh, 0)
    df_nav_cluster_rela.plot()
    plt.show()

    # cluster_ids = range(5)
    # for cluster_id in cluster_ids:
        # fund_cluster = asset_fund_factor.load_fc_fund_cluster(cluster_ids=[cluster_id])
        # fund_cluster['valid'] = 1.0
        # fund_count = fund_cluster.groupby(fund_cluster.fund_id).sum()

@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_cluster_pos_analysis(ctx, optid):

    cluster_ids = range(10)
    cluster_ids = [7]
    for cluster_id in cluster_ids:
        fund_cluster = asset_fund_factor.load_fc_fund_cluster(cluster_ids=[cluster_id])
        fund_cluster['valid'] = 1.0
        fund_count = fund_cluster.groupby(fund_cluster.fund_id).sum()
        set_trace()


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def fuc_pool_analysis(ctx, optid):

    pool_ids = ['11130100', '11130500', '11130700', '11140100', '11150900', '11151200', '11151800', '11151900']
    df = {}
    for pool_id in pool_ids:
        pool_fund = asset_ra_pool_fund.load(pool_id)
        df[pool_id] = pool_fund.loc['2018-08-31'].ra_fund_code.values
    df = pd.DataFrame(df)
    for i in range(len(pool_ids) - 1):
        for j in range(i+1, len(pool_ids)):
            pool_1 = df[pool_ids[i]]
            pool_2 = df[pool_ids[j]]
            print(i, j, len(np.intersect1d(pool_1, pool_2)))
    set_trace()


@fuc.command()
@click.option('--id', 'optid', help='specify cluster id')
@click.pass_context
def index_cluster_corr(ctx, optid):

    df = asset_index_factor.load_index_factor_exposure(index_id=130000007)
    df = df.loc['130000007']
    df = df.unstack()
    df.columns = df.columns.get_level_values(1)
    df = df.T
    start_date = '2010-01-01'
    end_date = '2018-08-01'
    estclass = ['中证策略指数', '上证策略指数', '国证策略指数', '深证策略指数', '申万量化策略指数']
    valid_index_info = asset_index.load_type_index(estclass)
    valid_index = valid_index_info.index
    df_nav_index = asset_index.load_caihui_index(valid_index)
    df_nav_index = df_nav_index.fillna(method='pad', limit=5)
    df_nav_fund = base_ra_fund_nav.load_daily(start_date, end_date, codes=['020001'])
    df_nav_index = pd.merge(df_nav_index, df_nav_fund, left_index=True, right_index=True, how='inner')

    dates = pd.date_range(start_date, end_date, freq='365D')
    dates = dates[-3:]
    for ldate, date in zip(dates[:-1], dates[1:]):
        ldate = '2012-01-01'
        date = '2018-01-01'

        tnav = df_nav_index.loc[ldate:date]
        tnav = tnav.fillna(method='pad')
        tnav = tnav.dropna(1)
        tnav = tnav / tnav.iloc[0]
        df_dist = tnav.corr()
        asset_cluster = clusterSimple(df_dist, 0.95)
        clusters = sorted(asset_cluster, key=lambda x: len(asset_cluster[x]), reverse=True)
        for layer in clusters:
            print(layer)
            indexes = asset_cluster[layer]
            index_names = valid_index_info.loc[indexes]
            print(index_names)
            print('#############################################################################')
        set_trace()


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

    fn = base_ra_fund.load(codes= valid_funds)
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


def cluster_ap(df_dist, preference=None):

    if preference is not None:
        ap_model = AffinityPropagation(affinity='precomputed', preference=preference)
    else:
        ap_model = AffinityPropagation(affinity='precomputed')

    try:
        ap_res = ap_model.fit(df_dist)
    except Exception as e:
        print(e)
        set_trace()

    silh = silhouette_score(-df_dist, ap_model.labels_)
    asset_cluster = defaultdict(list)
    for label, fund_id in zip(ap_res.labels_, df_dist.index):
        asset_cluster[label].append(fund_id)

    return asset_cluster, silh, ap_model


def cluster_km(df_dist, n_clusters=10):

    df_dist = ((1 - df_dist.fillna(0.0)) / 2)**0.5
    km_model = KMeans(n_clusters=n_clusters)
    km_model = km_model.fit(df_dist)

    try:
        km_res = km_model.fit(df_dist)
    except Exception as e:
        print(e)
        set_trace()
    asset_cluster = defaultdict(list)
    for label, fund_id in zip(km_res.labels_, df_dist.index):
        asset_cluster[label].append(fund_id)

    return asset_cluster



def clusterSimple(dist, threshold):

    asset_cluster = {}
    factor_ids = dist.keys()
    asset_cluster[0] = [factor_ids[0]]
    for factor_id in factor_ids[1:]:
        # print(factor_id)
        flag = False
        new_layer = len(asset_cluster)
        tmp_corrs = {}
        for layer in asset_cluster.keys():
            tmp_corrs[layer] = dist.loc[factor_id, asset_cluster[layer]].values.mean()
            tmp_corrs_ser = pd.Series(tmp_corrs)
            max_corr_index = tmp_corrs_ser.argmax()
        if (tmp_corrs_ser.loc[max_corr_index] > threshold) and (not flag):
            flag = True
            asset_cluster[max_corr_index].append(factor_id)
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
            tmp_corrs_ser = tmp_corrs_ser.sort_values(ascending=True)
        if (tmp_corrs_ser.iloc[0] < threshold) and (not flag):
            flag = True
            asset_cluster[tmp_corrs_ser.index[0]].append(factor_id)
        if not flag:
            asset_cluster[new_layer] = [factor_id]

    return asset_cluster


if __name__ == '__main__':

    # fund_stability_filter()
    fund_concentration_filter()




