#coding=utf-8
'''
Created on: May. 8, 2019
Modified on: May. 17, 2019
Author: Shixun Su
Contact: sushixun@licaimofang.com
'''

import logging
from sqlalchemy import MetaData, Table, select, func
import pandas as pd
from . import database
from . import util_db


logger = logging.getLogger(__name__)


def load_a_stock_free_float_share(stock_ids=None):

    stock_ids = util_db.to_list(stock_ids)

    engine = database.connection('wind')
    metadata = MetaData(bind=engine)
    t = Table('AShareFreeFloat', metadata, autoload=True)

    columns = [
        t.c.S_INFO_WINDCODE.label('stock_id'),
        t.c.CHANGE_DT.label('change_date'),
        # t.c.ANN_DT.label('ann_date'),
        t.c.S_SHARE_FREESHARES.label('free_float_share')
    ]

    s = select(columns)
    if stock_ids is not None:
        s = s.where(t.c.S_INFO_WINDCODE.in_(stock_ids))

    df = pd.read_sql(s, engine, parse_dates=['change_date'])
    df['begin_date'] = df['change_date']
    df.sort_values(
        by=['stock_id', 'begin_date', 'change_date'],
        ascending=[True, True, False],
        inplace=True
    )
    df.drop(
        df.loc[
            (df.stock_id==df.shift(1).stock_id) & \
            (df.change_date<=df.shift(1).change_date)
        ].index,
        inplace=True
    )
    df.set_index(['stock_id', 'begin_date'], inplace=True)
    df.drop(['change_date'], axis='columns', inplace=True)

    return df


if __name__ == '__main__':

    load_a_stock_free_float_share('601598.SH')

