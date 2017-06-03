#coding=utf8


import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys
sys.path.append('shell')
import indicator_delay


def factor_delay_index_ahead_process(factor, index_price, factor_delay):

    factor = factor.shift(factor_delay)
    factor = factor.dropna()
    index_price = index_price.shift(-1)
    index_price = index_price.dropna()
    index = index_price.index & factor.index
    factor = factor.loc[index]
    index_price = index_price.loc[index]

    return factor, index_price


if __name__ == '__main__':

    df = pd.read_csv('./data/macro_factor_index.csv', index_col = ['date'], parse_dates = ['date'])
    #print df.columns
    #cols = ['town_unemployment_rate']
    delay = indicator_delay.delay
    #print
    cols = df.columns[0: -9]
    #cols = df.columns[2: 3]
    #cols = df.columns[4: 5]
    #cols = ['rpi_yoy']
    index_col = '000852.SH'
    zz1000 = df[index_col].fillna(method = 'pad').dropna()

    data = []
    for col in cols:
        tmp_factor = df[col].copy()
        tmp_zz1000 = zz1000.copy()
        factor_delay = delay[col]
        tmp_factor, tmp_zz1000 = factor_delay_index_ahead_process(tmp_factor, tmp_zz1000, factor_delay)
        factor_r = tmp_factor.pct_change().fillna(0.0)
        zz1000_r = tmp_zz1000.pct_change().fillna(0.0)
        #print tmp_factor
        #print tmp_factor
        #print tmp_zz1000
        print col, np.corrcoef(tmp_factor.values, tmp_zz1000.values)[0][1], np.corrcoef(tmp_factor.values, zz1000_r.values)[0][1], np.corrcoef(factor_r.values, tmp_zz1000.values)[0][1], np.corrcoef(factor_r.values, zz1000_r.values)[0][1]
        data.append([np.corrcoef(tmp_factor.values, tmp_zz1000.values)[0][1], np.corrcoef(tmp_factor.values, zz1000_r.values)[0][1], np.corrcoef(factor_r.values, tmp_zz1000.values)[0][1], np.corrcoef(factor_r.values, zz1000_r.values)[0][1]])
        #X = tmp_factor.values
        #y = zz1000_r.values
        #X = sm.add_constant(X)
        #model = sm.OLS(y, X)
        #result = model.fit()
        #print result.summary()

    df = pd.DataFrame(data, index = cols, columns = ['factor_index', 'factor_index_r', 'factor_r_index','factor_r_index_r'])
    print df
    df.to_csv('macro_corr.csv')
