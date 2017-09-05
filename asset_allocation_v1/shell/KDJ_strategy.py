#coding=utf8


import pandas as pd
import numpy as np

class KDJ_strategy:

	def timing(self, df_nav, date):
		periodHigh = pd.Series(0.0, index = df_nav.index)
		periodHigh = pd.rolling_max(df_nav.tc_high,window = date)
		periodLow = pd.Series(0.0, index = df_nav.index)
		periodLow = pd.rolling_min(df_nav.tc_low,window = date)
		rsv = pd.Series(0.0, index = df_nav.index)
		k_value = pd.Series(0.0, index = df_nav.index)
		d_value = pd.Series(0.0, index = df_nav.index)
		for i in range(8, len(df_nav)):
			rsv[i] = ((df_nav.tc_close[i] - periodLow[i])/(periodHigh[i] - periodLow[i]))*100
		for i in range(8, len(df_nav)):
			k_value[i] = (2.0/3)*k_value[i-1]+(1.0/3)*rsv[i]
			d_value[i] = (2.0/3)*d_value[i-1]+(1.0/3)*k_value[i]
		print df_nav.tc_close.tail()
		print k_value.tail()
		print d_value.tail()
		singnal = pd.Series(0.0, index = df_nav.index)
		for j in range(8, len(df_nav)):
			if k_value[j-1]<d_value[j-1] and k_value[j]>d_value[j]:
				singnal[j] = 1
			elif k_value[j-1]>d_value[j-1] and k_value[j]<d_value[j]:
				singnal[j] = -1
		return singnal	

