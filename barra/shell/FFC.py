#coding=utf8

import numpy as np
import pandas as pd
import time


def ffc(sse_df, pb_df, size_df, close_df):

    start = time.time()
    print 'Programme Start', start
    print '----------------------------------------------------'
    #Data Clearn

    #导入相关数据
    #sse       = pd.read_excel('sse.xlsx', index_col='Date', parse_dates=True)         #Benchmark         0
    #Financial Ratios
    #pb        = pd.read_csv('pb.csv', index_col='Date', parse_dates=True)             #pb                1
    #Stocks Information
    #size      = pd.read_csv('size.csv', index_col='Date', parse_dates=True)           #size              2
    #close     = pd.read_csv('close.csv', index_col='Date', parse_dates=True)          #Prices            3

    sse          = sse_df
    pb           = pb_df
    size         = size_df
    close        = close_df

    pb_list      = set(list(pb.columns.values))
    size_list    = set(list(size.columns.values))
    close_list   = set(list(close.columns.values))

    col = pb_list & size_list & close_list

    pb       = pb[list(col)]
    size     = size[list(col)]
    close    = close[list(col)]

    '''sse = sse[3000:]
    pb = pb[3000:]
    size = size[3000:]
    close = close[3000:]'''

    #returns
    returns   = np.log(close/close.shift(1)).fillna(0)
    #book to market ratio
    bm        = 1/pb

    #size['median'] = size.mean(axis=1,skipna=True)
    big            = size.copy()
    stocks         = list(big.columns.values)

    size['sums']   = size.sum(axis=1, skipna=True)
    size['Q80']    = size.quantile(q=0.8, axis=1, numeric_only=False)

    #Growth&Value
    growth         = bm.copy()
    value          = bm.copy()
    bm['Q30']      = bm.quantile(q=0.3, axis=1, numeric_only=False)
    bm['Q70']      = bm.quantile(q=0.7, axis=1, numeric_only=False)

    #Momentum
    momentum        = pd.rolling_sum(returns,21)
    up              = momentum.copy()
    down            = momentum.copy()
    momentum['Q30'] = bm.quantile(q=0.3, axis=1, numeric_only=False)
    momentum['Q70'] = bm.quantile(q=0.7, axis=1, numeric_only=False)

    #SMB==================================================================
    size_Q80   = size['Q80'] 
    for j in stocks:
        big[j] = np.where(big[j]>size_Q80,1,0)

    small      = 1 - big

    #big.to_excel('big.xlsx')
    #small.to_excel('small.xlsx')

    print 'big, small', time.time()

    bm_Q30     = bm['Q30']
    bm_Q70     = bm['Q70']
    for j in stocks:
        growth[j] = np.where(growth[j]<bm_Q30,1,0)

    for j in stocks:
        value[j] = np.where(value[j]>bm_Q70,1,0)

    neutral    = 1 - (growth + value)

    #growth.to_excel('growth.xlsx')
    #neutral.to_excel('neutral.xlsx')
    #value.to_excel('value.xlsx')

    print 'growth, value', time.time()

    big     = big.shift(1)
    small   = small.shift(1)
    growth  = growth.shift(1)
    value   = value.shift(1)
    neutral = neutral.shift(1)  

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++

    size_sums   = size[['sums']]
    del size['sums'], size['Q80']

    big_growth  = ((big * growth) * returns * size)
    big_neutral = ((big * neutral) * returns * size)
    big_value   = ((big * value) * returns * size)

    big_growth['sums']  = big_growth.sum(axis=1, skipna=True)
    big_neutral['sums'] = big_neutral.sum(axis=1, skipna=True)
    big_value['sums']   = big_value.sum(axis=1, skipna=True)

    #big_growth.to_excel('big_growth.xlsx')
    #big_neutral.to_excel('big_neutral.xlsx')
    #big_value.to_excel('big_value.xlsx')

    big_growth    = big_growth[['sums']]
    big_neutral   = big_neutral[['sums']]
    big_value     = big_value[['sums']]

    big_growth  = big_growth/size_sums
    big_neutral = big_neutral/size_sums
    big_value   = big_value/size_sums

    small_growth  = ((small * growth) * returns * size)
    small_neutral = ((small * neutral) * returns * size)
    small_value   = ((small * value) * returns * size)

    small_growth['sums']  = small_growth.sum(axis=1, skipna=True)
    small_neutral['sums'] = small_neutral.sum(axis=1, skipna=True)
    small_value['sums']   = small_value.sum(axis=1, skipna=True)

    #small_growth.to_excel('small_growth.xlsx')
    #small_neutral.to_excel('small_neutral.xlsx')
    #small_value.to_excel('small_value.xlsx')

    small_growth    = small_growth[['sums']]
    small_neutral   = small_neutral[['sums']]
    small_value     = small_value[['sums']]

    small_growth  = small_growth/size_sums
    small_neutral = small_neutral/size_sums
    small_value   = small_value/size_sums

    SMB = ((small_growth['sums'] + small_neutral['sums'] + small_value['sums'])/3.0) - ((big_growth['sums'] + big_neutral['sums'] + big_value['sums'])/3.0)
    SMB = pd.DataFrame({'SMB' : SMB})
    SMB['uv'] = 1.0
    uv        = SMB['uv']
    smb       = SMB['SMB']
    for i in range(1,len(SMB.index)):
        uv[i] = uv[i-1] * (1+smb[i])
    SMB.to_csv('./tmp/smb.csv')

    print 'SMB', time.time()

    #HML====================================================================

    HML = ((big_value['sums'] + small_value['sums'])/2.0) - ((big_growth['sums'] + small_growth['sums'])/2.0)
    HML = pd.DataFrame({'HML' : HML})
    HML['uv'] = 1.0
    uv        = HML['uv']
    hml       = HML['HML']
    for i in range(1,len(HML.index)):
        uv[i] = uv[i-1] * (1+hml[i])
    HML.to_csv('./tmp/hml.csv')

    print 'HML', time.time()

    #Momentum===============================================================

    momentum_Q30     = momentum['Q30']
    momentum_Q70     = momentum['Q70']
    for j in stocks:
        down[j] = np.where(down[j]<momentum_Q30,1,0)

    for j in stocks:
        up[j] = np.where(up[j]>momentum_Q70,1,0)

    medium    = 1 - (down + up)

    #down.to_excel('down.xlsx')
    #medium.to_excel('medium.xlsx')
    #up.to_excel('up.xlsx')

    down   = down.shift(1)
    medium = medium.shift(1)
    up     = up.shift(1)

    print 'down, up', time.time()

    big_ups   = ((big * up) * returns * size)
    small_ups = ((small * up) * returns * size)

    big_downs   = ((big * down) * returns * size)
    small_downs = ((small * down) * returns * size)

    big_ups['sums']   = big_ups.sum(axis=1, skipna=True)
    small_ups['sums'] = small_ups.sum(axis=1, skipna=True)

    big_downs['sums']   = big_downs.sum(axis=1, skipna=True)
    small_downs['sums'] = small_downs.sum(axis=1, skipna=True)

    #big_ups.to_excel('big_ups.xlsx')
    #small_ups.to_excel('small_ups.xlsx')
    #big_downs.to_excel('big_downs.xlsx')
    #small_downs.to_excel('small_downs.xlsx')

    big_ups      = big_ups[['sums']] 
    small_ups    = small_ups[['sums']]
    big_downs    = big_downs[['sums']] 
    small_downs  = small_downs[['sums']]

    big_ups      = big_ups/size_sums
    small_ups    = small_ups/size_sums
    big_downs    = big_downs/size_sums
    small_downs  = small_downs/size_sums

    Momentum_Factor     = ((big_ups['sums'] + small_ups['sums'])/2.0) - ((big_downs['sums'] + small_downs['sums'])/2.0)
    Momentum_Factor     = pd.DataFrame({'Momentum' : Momentum_Factor})
    Momentum_Factor['uv'] = 1.0
    uv                    = Momentum_Factor['uv']
    momentum              = Momentum_Factor['Momentum']
    for i in range(1,len(Momentum_Factor.index)):
        uv[i] = uv[i-1] * (1+momentum[i])
    Momentum_Factor.to_csv('./tmp/momentum.csv')

    print 'Momentum_Factor', time.time()

    end = time.time()
    print 'Programme End', end
    print 'Costs (Mins)', (end-start)/60.0	
    print '----------------------------------------------------'

    return SMB, HML, Momentum_Factor
