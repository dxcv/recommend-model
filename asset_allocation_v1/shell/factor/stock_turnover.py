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


#所有股票的换手率
def all_stock_turnover():

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
        sql = "select TRADEDATE, TURNRATE from TQ_QT_SKDAILYPRICE where SECODE = '%s' order by TRADEDATE asc" % secode
        df = pd.read_sql(sql, conn, index_col = 'TRADEDATE', parse_dates = ['TRADEDATE'])
        df.index.name = 'date'
        df.columns    = [secode_symbol_dict[secode]]
        df = df.replace(0.00, np.nan)
        dfs.append(df)
        print secode_symbol_dict[secode], 'done'
    stock_df = pd.concat(dfs, axis = 1)

    stock_df = stock_df / 100.0
    stock_df.to_csv('stock_turnover.csv')

    return 0


if __name__ == '__main__':
    all_stock_turnover()