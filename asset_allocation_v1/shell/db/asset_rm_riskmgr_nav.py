#coding=utf8

from sqlalchemy import MetaData, Table, select, func, literal_column
# import string
# from datetime import datetime, timedelta
import pandas as pd
# import os
# import sys
import logging
import database

from dateutil.parser import parse

logger = logging.getLogger(__name__)

#
# mz_riskmgr
#
# def load(gids, xtypes=None):
#     db = database.connection('asset')
#     metadata = MetaData(bind=db)
#     t1 = Table('rm_riskmgr', metadata, autoload=True)

#     columns = [
#         t1.c.globalid,
#         t1.c.rm_type,
#         t1.c.rm_pool,
#         t1.c.rm_reshape,
#         t1.c.rm_name,
#     ]

#     s = select(columns)

#     if gids is not None:
#         s = s.where(t1.c.globalid.in_(gids))
#     if xtypes is not None:
#         s = s.where(t1.c.rm_type.in_(xtypes))
    
#     df = pd.read_sql(s, db)

#     return df

def save(gid, df):
    fmt_columns = ['rm_nav', 'rm_inc']
    fmt_precision = 6
    if not df.empty:
        df = database.number_format(df, fmt_columns, fmt_precision)
    #
    # 保存择时结果到数据库
    #
    db = database.connection('asset')
    t2 = Table('rm_riskmgr_nav', MetaData(bind=db), autoload=True)
    columns = [literal_column(c) for c in (df.index.names + list(df.columns))]
    s = select(columns, (t2.c.rm_riskmgr_id == gid))
    df_old = pd.read_sql(s, db, index_col=['rm_riskmgr_id', 'rm_date'], parse_dates=['rm_date'])
    if not df_old.empty:
        df_old = database.number_format(df_old, fmt_columns, fmt_precision)

    # 更新数据库
    # print df_new.head()
    database.batch(db, t2, df, df_old, timestamp=False)
