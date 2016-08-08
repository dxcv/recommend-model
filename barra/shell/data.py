#coding=utf8


import pandas as pd
import numpy  as np


if __name__ == '__main__':


    '''
    df = pd.read_csv('./data/stock_price.csv', index_col = 'date', parse_dates = ['date'])
    data = []
    for col in df.columns:
        print col
        vs = df[col]
        for i in range(2, len(vs)):
            if vs[i - 2] == vs[ i ] and vs[ i ] == vs[i - 1] and not np.isnan(vs[i]):
                j = i
                replace = vs[i - 3]
                while j < len(vs) and vs[j] == replace:
                    vs[j] = np.nan
                    j = j + 1
                i = j 
        data.append(vs)


    df = pd.DataFrame(np.matrix(data).T, index = df.index, columns = df.columns)
    df.to_csv('stock_price.csv')
    print df          
    '''


    ## 停牌一两天的数填补换手率为0
    df = pd.read_csv('./data/stock_price.csv', index_col = 'date', parse_dates = ['date'])
    data = []
    for col in df.columns:
        vs = df[col].values
        for i in range(0, len(vs) - 2):
            if np.isnan(vs[i]) and ( not np.isnan(vs[i + 1]) or not np.isnan(vs[ i + 2])):
                vs[i] = 0.0
        data.append(vs)

    df = pd.DataFrame(np.matrix(data).T, index = df.index, columns = df.columns)
    df.to_csv('stock_turnover.csv')
 
