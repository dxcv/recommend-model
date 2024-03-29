#coding=utf8


import getopt
import string
import json
import os
import sys
import logging
sys.path.append('shell')
import click
import config
import pandas as pd
import numpy as np
import LabelAsset
import os
import DBData
import time
import Const
import DFUtil
import LabelAsset

from datetime import datetime, timedelta
from dateutil.parser import parse
from Const import datapath
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from tabulate import tabulate
from db import *
from util.xdebug import dd

import traceback, code

logger = logging.getLogger(__name__)

@click.group(name='import')  
@click.pass_context
def import_command(ctx):
    ''' generate portfolios
    '''
    pass;
    

@import_command.command()
@click.option('--list/--no-list', 'optlist', default=False, help='list pool to update')
@click.option('--id', 'optid', help='questionare to import')
@click.option('--question', '-q', type=click.Path(), help='excel file for question')
@click.option('--option', '-o', type=click.Path(), help='excel file for option')
@click.pass_context
def fp_da_question(ctx, optlist, optid, question, option):
    '''import mapi.fp_da_question from excel
    '''

    import sys
    # sys.setdefaultencoding() does not exist, here!
    reload(sys)  # Reload does the trick!
    sys.setdefaultencoding('UTF8')    

    if question is not None:
        columns = {
            '问题ID':'globalid',
            '问卷ID':'fp_nare_id',
            '问题标题':'fp_qst_text',
            '问题副标题':'fp_qst_subtext',
            '所属类别':'fp_qst_category',
            '问题类型(1:填空；2:选择)':'fp_qst_type',
            '是否必填':'fp_qst_required',
            '数字数据下限':'fp_lower_limit',
            '数字数据上限':'fp_upper_limit',
            '前端限制':'fp_limit_front',
            '后端限制2':'fp_limit_back',
            '排序':'fp_show_order',
            '显示层级':'fp_qst_level',
            # u'数据提示下限':'fp_',
            # u'数据提示文本（下限）':'fp_',
            # u'数据提示上限':'fp_',
            # u'数据提示文本（上限）':'fp_',
            '备注':'fp_qst_remark',
        }

        df = pd.read_excel(question)
        df = df.rename(columns=columns)
        df = df[list(columns.values())].copy()

        df.set_index(['globalid'], inplace=True)
        # 1print df.head(50)
        df['fp_limit_front'] = df['fp_limit_front'].str.strip('|')
        df['fp_limit_back'] = df['fp_limit_back'].str.strip('|')

        df['updated_at'] = df['created_at'] = datetime.now()
        
        db = database.connection('mapi')
        t2 = Table('fp_da_question', MetaData(bind=db), autoload=True)
        s = t2.delete(t2.c.fp_nare_id == optid)
        s.execute()

        df.to_sql(t2.name, db, index=True, if_exists='append', chunksize=500)

    if option is not None:
        columns = {
            '问题ID':'fp_qst_id',
            '选项':'fp_qst_option_key',
            '选项内容':'fp_qst_option_val',
            '是否启用':'fp_qst_option_enable',
        }

        df = pd.read_excel(option)
        df = df.rename(columns=columns)
        df = df[list(columns.values())].copy()

        df.set_index(['fp_qst_id', 'fp_qst_option_key'], inplace=True)
        # 1print df.head(50)
        df['updated_at'] = df['created_at'] = datetime.now()

        db = database.connection('mapi')
        t2 = Table('fp_da_options', MetaData(bind=db), autoload=True)
        s = t2.delete(t2.c.fp_qst_id.in_(df.index.get_level_values(0)))
        s.execute()

        df.to_sql(t2.name, db, index=True, if_exists='append', chunksize=500)


@import_command.command()
@click.pass_context
def import_riskmgr(ctx):

    riskmgr_id = {}
    riskmgr_id['000001.SH_tight'] = 61110106
    riskmgr_id['000001.SH_loose'] = 61110107
    riskmgr_id['399001.SZ_tight'] = 61110209
    riskmgr_id['399001.SZ_loose'] = 61110210
    riskmgr_id['HSI.HI_tight']    = 61110706
    riskmgr_id['HSI.HI_loose']    = 61110707
    riskmgr_id['SP500.SPI_tight'] = 61120206
    riskmgr_id['SP500.SPI_loose'] = 61120207
    riskmgr_id['NDX.GI_tight']    = 61120208
    riskmgr_id['NDX.GI_loose']    = 61120209
    riskmgr_id['000001.SH_ma'] = 61110108
    riskmgr_id['399001.SZ_ma'] = 61110211


    engine = database.connection('asset')
    Session = sessionmaker(bind=engine)
    session = Session()

    df = pd.read_csv('data/QRM_DATA.csv', index_col = ['date'])
    for col in df.columns:
        rm_id = riskmgr_id[col]
        if not (col in ['000001.SH_ma', '399001.SZ_ma']):
            continue
        pos = df[col]
        print(pos.tail())
        records = []
        for date in pos.index:
            p = pos.loc[date]
            signal = asset_allocate.rm_riskmgr_signal()
            signal.rm_riskmgr_id = rm_id
            signal.rm_date = date
            signal.rm_pos = p
            records.append(signal)

        session.add_all(records)
        session.commit()
    session.close()
