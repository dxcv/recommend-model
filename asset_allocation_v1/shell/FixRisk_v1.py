#coding=utf8


import pandas as pd
import numpy  as np
import sys
sys.path.append('shell')
import portfolio
import datetime


def intervalreturn(df, interval):

    dates = df.index

    rs = []
    ds = []
    for i in range(interval, len(dates)):
        d = dates[i]
        r = 1.0 * df.iloc[i, 0] / df.iloc[i - interval, 0] - 1
        rs.append(r)
        ds.append(d)

    df = pd.DataFrame(rs, index=ds, columns=['nav'])
    return df


def periodstdmean(df, period):

    dates = df.index

    meanstd = []
    ds      = []
    for i in range(period, len(dates)):
        d  = dates[i]
        rs = df.iloc[i - period : i, 0]

        meanstd.append([np.std(rs), np.mean(rs)])
        ds.append(d)

    df = pd.DataFrame(meanstd, index=ds, columns=['std','mean'])

    return df


def rerisk(risks):

    risk_std  = np.std(risks)
    risk_mean = np.mean(risks)

    rerisks = []

    risk_max = risk_mean + 2 * risk_std

    for risk in risks:
        if risk >= risk_max:
            continue
        else:
            rerisks.append(risk)

    return rerisks


if __name__ == '__main__':


    #code         = '000011.OF'
    #code         = '000300.SH'
    interval     = 20
    short_period = 20
    long_period  = 250


    df = pd.read_csv('./data/000905.csv', index_col='date', parse_dates=['date'])
    timing_df = pd.read_csv('./data/000905_signals.csv', index_col = 'date', parse_dates=['date'])
    #df = pd.read_csv('./data/166002-160505-260110-000011.csv', index_col='date', parse_dates=['date'])
    #df = pd.read_csv('./data/index.csv', index_col='date', parse_dates=['date'])
    #df = pd.read_csv('./data/000905-000016-000300.csv', index_col='date', parse_dates=['date'])
    ##df = pd.read_csv('./data/166002-160505.csv', index_col='date', parse_dates=['date'])
    #df = pd.read_csv('./data/166002-160505-260110-000011.csv', index_col='date', parse_dates=['date'])
    #df = pd.read_csv('./data/spgoldhs.csv', index_col='date', parse_dates=['date'])
    #df = pd.read_csv('./data/guan_fund_value.csv', index_col='date', parse_dates=['date'])
    #df = pd.read_csv('./data/labelasset.csv', index_col='date', parse_dates=['date'])
    #cols = df.columns
    #code = cols[10]
    code = '000905.SH'
    #code = 'largecap'
    #code = 'smallcap'
    #code = 'growth'
    #code = 'value'
    #code = 'rise'
    #code = 'decline'
    #code = 'oscillation'

    df = df.fillna(method='pad')
    df = df[[code]]


    dfr = df.pct_change().fillna(0.0)


    interval_df = intervalreturn(df, interval)
    periodstdmean_df = periodstdmean(interval_df, short_period)
    #riskstdmean_df   = riskstdmean(periodstdmean_df[['std']], 252)
    #rstdmean_df      = rstdmean(periodstdmean_df[['mean']], 252)


    dates = periodstdmean_df.index

    vs    = [1]
    ovs   = [1]
    ds    = [dates[long_period]]
    ps    = [0]
    pds   = [dates[long_period]]
    risk_positions = [0]


    position     = 0
    change_index = -100

    for i in range(long_period, len(dates) - 2):

        d = dates[i]

        signal = timing_df.loc[d].values[0]
        #print d, signal

        risk    = periodstdmean_df.iloc[i, 0]
        r       = periodstdmean_df.iloc[i, 1]

        risks   = periodstdmean_df.iloc[i - long_period : i + 1 , 0]
        rs      = periodstdmean_df.iloc[i - long_period : i + 1 , 1]

        #rerisks = rerisk(risks)
        #rers    = rerisk(rs)
        rerisks  = risks
        rers     = rs


        riskstd     = np.std(rerisks)
        riskmean    = np.mean(rerisks)


        rstd        = np.std(rers)
        rmean       = np.mean(rers)


        #r_median    = periodstdmean_df.iloc[i - long_period : i, 1].median()
        #std_median  = periodstdmean_df.iloc[i - long_period : i, 0].median()

        #if signal == 1:
        #if ma5_dfr.loc[d, code] > 0 and ma10_dfr.loc[d, code] > 0 and ma20_dfr.loc[d, code] > 0:
        #    position = riskmean / risk
        #    if position >= 1.0:
        #        position = 1.0

        if risk <= riskmean:
            position = 1.0
        else:
            position = riskmean / risk

        '''
        if risk >= riskmean + 2 * riskstd and r < rmean - 1 * rstd:
            position = riskmean / risk
        elif risk >= riskmean + 2 * riskstd and r > rmean + 1 * rstd:
            position = 0.0
            #position = riskmean / risk
        elif risk <= riskmean:
            position = 1.0
        else:
            position = riskmean / risk
        '''

        '''
        risk_positions.append(position)

        if len(risk_positions) >= 3:
            if (position <= ps[-1] * 0.5 or position <= ps[-1] - 0.2) and signal == -1:
                position = min(position, ps[-1])
            elif risk_positions[-3] <= risk_positions[-2] and risk_positions[-2] <= risk_positions[-1]:
                position = min(position, ps[-1])
        #if  signal == -1:
        #position = riskmean / risk
        '''

        '''
        if position == 0:
            pass
        elif (position <= ps[-1] * 0.5 or position <= ps[-1] - 0.2) and signal == -1:
        #if  signal == -1:
            #position = min(position, ps[-1])
            pass
        elif (position >= ps[-1] * 2 or position >= ps[-1] + 0.2 or position == 1.0) and signal == 1:
            #positition = max(position, ps[-1])
            pass
        else:
            position = ps[-1]
        '''

        '''
        if signal == 1:
            position = 1.0
            #position = riskmean / risk
            #if position >= 1.0:
            #    position = 1.0
        else:
            position = 0
        '''

        '''
        if risk >= riskmean + 2 * riskstd and r < rmean - 1 * rstd:
            position = riskmean / risk
        elif risk >= riskmean + 2 * riskstd and r > rmean + 1 * rstd:
            position = 0.0
            #position = riskmean / risk
        elif risk <= riskmean:
            position = 1.0
        else:
            position = riskmean / risk
        '''


        #p = ps[-1]
        #if position == 0.0:
        #    position = 0
        #elif (not (position <= p * 0.5 or position >= p * 2.0)) and (not (position <= p - 0.2 or position >= p + 0.2)):
        #    position = p


        #if position < 0.1:$
        #    position = 0.0$

        r = dfr.loc[dates[i + 1], code]
        #r = dfr.loc[dates[i + 2], code]
        v = vs[-1] * (1 + r * position)
        ovs.append(ovs[-1] * (1 + r))
        #v = vs[-1] * (1 + r)

        vs.append(v)
        ds.append(dates[i + 1])
        ps.append(position)
        pds.append(dates[i + 1])


    vdf = pd.DataFrame(np.matrix([vs, ovs]).T, index=ds, columns=['nav', code])
    vdf.index.name = 'date'

    #print vdf
    pdf = pd.DataFrame(ps, index=pds, columns=['position'])
    pdf.index.name = 'date'

    #ma_df = pd.DataFrame(mas, index = mads, columns = ['ma'])
    #start_date = datetime.datetime.strptime('2010-01-01','%Y-%m-%d')
    #vdf  = vdf[vdf.index >= start_date]
    #vdf  = vdf / vdf.iloc[0, :]
    #vdf = vdf.resample('M')
    vdf.to_csv('./tmp/vdf.csv')
    pdf.to_csv('./tmp/pdf.csv')


    print 'fixed risk'
    print "sharpe : ", portfolio.portfolio_sharpe(vdf['nav'],'d')
    print "annual_return : ", portfolio.portfolio_return(vdf['nav'],'d')
    print "maxdrawdown : ", portfolio.portfolio_maxdrawdown(vdf['nav'])
    print "risk : ", np.std(vdf['nav'].pct_change().fillna(0).values) * (252 ** 0.5)

    print code
    print "sharpe : ", portfolio.portfolio_sharpe(vdf[code],'d')
    print "annual_return : ", portfolio.portfolio_return(vdf[code],'d')
    print "maxdrawdown : ", portfolio.portfolio_maxdrawdown(vdf[code])
    print "risk : ", np.std(vdf[code].pct_change().fillna(0).values) * (252 ** 0.5)


    #print vdf.corr()
