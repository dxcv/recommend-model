#coding=utf8


import MySQLdb
import pandas as pd


trade = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "passwd": "Mofang123",
    "db":"trade",
    "charset": "utf8"
}


passport = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "passwd": "Mofang123",
    "db":"passport",
    "charset": "utf8"
}

recommend = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "passwd": "Mofang123",
    "db":"recommend",
    "charset": "utf8"
}


portfolio_statistics = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "passwd": "Mofang123",
    "db":"portfolio_statistics",
    "charset": "utf8"
}

asset_allocation = {
    "host": "rdsf4ji381o0nt6n2954.mysql.rds.aliyuncs.com",
    "port": 3306,
    "user": "jiaoyang",
    "passwd": "wgOdGq9SWruwATrVWGwi",
    "db":"asset_allocation",
    "charset": "utf8"
}

if __name__ == '__main__':


    conn  = MySQLdb.connect(**trade)
    conn.autocommit(True)

    sql = 'select ya_uid, ya_name, ya_identity_no, created_at from yingmi_accounts'

    df = pd.read_sql(sql, conn, index_col = ['ya_uid'])

    df['ya_identity_no'] = df['ya_identity_no'].apply(lambda x: x[6 : 14])

    #print df
    df.to_csv('yingmi_account.csv', encoding = 'utf8')

    conn  = MySQLdb.connect(**passport)
    conn.autocommit(True)

    sql = 'select id, province, city, carrier, device_info, created_at from users'
    df = pd.read_sql(sql, conn, index_col = ['id'])

    df.to_csv('user.csv', encoding = 'utf8')
    #print df


    conn  = MySQLdb.connect(**trade)
    conn.autocommit(True)
    sql = 'select yp_uid, yp_portfolio_id, yp_trade_type, yp_placed_amount, yp_placed_percentage ,yp_placed_date from yingmi_portfolio_trade_statuses'
    df = pd.read_sql(sql, conn, index_col = ['yp_uid'])
    #print df
    df.to_csv('yingmi_portfolio_trade_status.csv', encoding = 'utf8')

    conn  = MySQLdb.connect(**recommend)
    conn.autocommit(True)
    sql = 'select uq_uid, uq_question_id, uq_question_selection, uq_answer, uq_start_time from user_questionnaire_answers where uq_answer_status'
    df = pd.read_sql(sql, conn, index_col = ['uq_uid'])

    df.to_csv('user_question_answer.csv', encoding = 'utf8')
    #print df


    conn  = MySQLdb.connect(**recommend)
    conn.autocommit(True)
    sql = 'select id, uq_question, uq_question_type from user_questionnaire_questions'
    df = pd.read_sql(sql, conn, index_col = ['id'])
    df.to_csv('user_questionnaire_questions.csv', encoding = 'gbk')
    #print df

    conn  = MySQLdb.connect(**recommend)
    conn.autocommit(True)
    sql = 'select uq_question_id, uq_option_key, uq_option_val from user_questionnaire_options'
    df = pd.read_sql(sql, conn, index_col = ['uq_question_id'])
    df.to_csv('user_questionnaire_options.csv', encoding = 'gbk')
    #print df

    conn  = MySQLdb.connect(**asset_allocation)
    conn.autocommit(True)

    sql = 'select ua_uid, ua_service_id from user_account_infos'

    df = pd.read_sql(sql, conn, index_col = ['ua_uid'])
    df.to_csv('user_account_infos.csv')

    sql = 'select ip_uid, ip_portfolio_id, ip_date, ip_nav, ip_principal from investor_portfolio_holding_actuals'

    df = pd.read_sql(sql, conn, index_col = ['ip_uid'])
    #print df
    df.to_csv('investor_portfolio_holding_actuals.csv')



    conn  = MySQLdb.connect(**portfolio_statistics)
    conn.autocommit(True)

    sql = 'select * from st_trade_statistics'
    df = pd.read_sql(sql, conn, index_col = ['st_uid'])
    df.to_csv('st_trade_statistics.csv', encoding='gbk')