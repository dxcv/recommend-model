#coding=utf8


import MySQLdb
import pandas as pd
import numpy  as np
import datetime


db_params = {
            "host": "rdsijnrreijnrre.mysql.rds.aliyuncs.com",
            "port": 3306,
            "user": "koudai",
            "passwd": "Mofang123",
            "db":"caihui",
            "charset": "utf8"
        }


#所有股票的收盘价
def all_stock_price():

    conn = MySQLdb.connect(**db_params)
    cur  = conn.cursor()

    sql = 'select SECODE, SYMBOL from TQ_SK_BASICINFO'
    cur.execute(sql)

    secode_symbol_dict = {}
    for record in cur.fetchall():
        secode = record[0]
        symbol = record[1]
        if symbol.find('00') == 0 or symbol.find('60') == 0 or symbol.find('30') == 0:
            #print symbol , secode
            secode_symbol_dict[secode] = symbol
    cur.close()

    #print secode_symbol_dict
    secodes = secode_symbol_dict.keys()

    dfs = []
    for secode in secodes:
        sql = "select TRADEDATE, TCLOSEAF from TQ_SK_DQUOTEINDIC where SECODE = '%s' order by TRADEDATE asc" % secode
        df = pd.read_sql(sql, conn, index_col = 'TRADEDATE', parse_dates = ['TRADEDATE'])
        df.index.name = 'date'
        df.columns    = [secode_symbol_dict[secode]]
        df.replace(0.00, np.nan, inplace = True)
        dfs.append(df)
        print secode_symbol_dict[secode], 'done'
    stock_df = pd.concat(dfs, axis = 1)

    stock_df.to_csv('./data/stock_price_adjust.csv')


#所有股票的收盘价
def all_stock_price_update():

    stock_df = pd.read_csv('./data/stock_price_adjust.csv', index_col = 'date', parse_dates = ['date'])

    conn = MySQLdb.connect(**db_params)
    cur  = conn.cursor()

    sql = 'select SECODE, SYMBOL from TQ_SK_BASICINFO'
    cur.execute(sql)

    secode_symbol_dict = {}
    for record in cur.fetchall():
        secode = record[0]
        symbol = record[1]
        if symbol.find('00') == 0 or symbol.find('60') == 0 or symbol.find('30') == 0:
            #print symbol , secode
            secode_symbol_dict[secode] = symbol
    cur.close()

    #print secode_symbol_dict
    secodes = secode_symbol_dict.keys()

    #sql = 'select TRADEDATE, TCLOSEAF from TQ_SK_DQUOTEINDIC where SECODE = %s order by TRADEDATE asc' % secode
    sql = 'select distinct TRADEDATE from TQ_SK_DQUOTEINDIC'
    cur = conn.cursor()
    cur.execute(sql)

    dates = []
    for record in cur.fetchall():
        dates.append(record[0])
    dates.sort()
    cur.close()

    end_date = dates[-1]

    sql = 'select SECODE, TCLOSEAF from TQ_SK_DQUOTEINDIC where TRADEDATE = %s' % end_date
    symbol_close_dict = {}
    cur = conn.cursor()
    cur.execute(sql)
    for record in cur.fetchall():
        secode = record[0]
        close  = record[1]
        if not secode_symbol_dict.has_key(secode):
            continue
        else:
            symbol = secode_symbol_dict[secode]
            symbol_close_dict[symbol] = close

    conn.close()

    end_date = datetime.datetime.strptime(end_date, '%Y%m%d')
    cols = stock_df.columns
    vs   = []
    for symbol in cols:
        if symbol in symbol_close_dict.keys():
            v = symbol_close_dict[symbol]
            if v == 0.00:
                v = np.nan
            vs.append(v)
        else:
            vs.append(np.nan)

    stock_df.loc[end_date] = vs
    stock_df.index.name = 'date'
    stock_df.to_csv('./data/stock_price_adjust.csv')


if __name__ == '__main__':
    #all_stock_price_update()
    all_stock_price()
    print 'update stock price done'
