from finlab import data
from finlab.backtest import sim
from finlab.dataframe import FinlabDataFrame
import pandas as pd


# ADL 均線指標
def get_adl(benchmark=1, ma_range=[5, 60]):
    df = data.get('etl:adj_close')
    fluctuation = df / df.shift()
    fluctuation = fluctuation.dropna(how='all')
    fluctuation = fluctuation.T

    dataset = []
    for i in range(len(fluctuation.columns)):
        daily_stat = fluctuation.iloc[:, i].dropna()
        stats = {'ups': (daily_stat > benchmark).sum(), 'downs': (daily_stat < benchmark).sum()}
        dataset.append(stats)
    from finlab.dataframe import FinlabDataFrame
    ad_line_df = FinlabDataFrame(dataset, index=fluctuation.columns)
    ad_line_df['net'] = ad_line_df['ups'] - ad_line_df['downs']
    ad_line_df['ADL'] = ad_line_df['net'].cumsum()
    for i in ma_range:
        s = f'ADL_MA{i}'
        ad_line_df[s] = ad_line_df['ADL'].rolling(i).sum() / i
    ad_line_df = ad_line_df.dropna()
    ad_line_df = ad_line_df[[c for c in ad_line_df.columns if 'ADL' in c]]
    ad_line_df['ind'] = ad_line_df['ADL_MA5'] - ad_line_df['ADL_MA60']
    return ad_line_df.astype(float)

# 大盤融資維持率
def margin_position(short_par=5, long_par=30):
    融資券總餘額 = data.get("margin_balance:融資券總餘額").fillna(method="ffill")
    融資今日餘額 = data.get("margin_transactions:融資今日餘額")
    close = data.get("price:收盤價")
    融資總餘額 = 融資券總餘額[["上市融資交易金額", "上櫃融資交易金額"]].sum(axis=1)
    融資餘額市值 = (融資今日餘額 * close * 1000).sum(axis=1)[融資今日餘額.index]
    mt_rate = (融資餘額市值 / 融資總餘額)
    mt_rate = mt_rate.dropna()
    short_ma = mt_rate.rolling(short_par).mean()
    long_ma = mt_rate.rolling(long_par).mean()
    entry = short_ma >= long_ma
    return mt_rate, entry.astype(float)

# 大盤多空排列家數均線指標
def ls_order_position(short=5, mid=10, long=30):
    close = data.get("price:收盤價")
    short_ma = close.average(short)
    mid_ma = close.average(mid)
    long_ma = close.average(long)
    long_order = (short_ma >= mid_ma) & (mid_ma >= long_ma)
    long_order = long_order.sum(axis=1)
    short_order = (short_ma < mid_ma) & (mid_ma < long_ma)
    short_order = short_order.sum(axis=1)
    entry = long_order - short_order
    return entry.astype(float)

# 台灣50 MACD週線
def get_macd_0050():
    macd, macdsignal, macdhist = data.indicator('MACD', resample='W')
    return macdhist['0050']

# 大盤股價淨值比
def get_market_pb():
    capital = data.get('financial_statement:股本')
    close = data.get('price:收盤價')
    market_value = (capital * close)[capital.columns.intersection(close.columns)].sum(axis=1) / 10
    market_value = market_value.reindex(close.index)
    權益總計 = data.get('financial_statement:股東權益總額').index_str_to_date()
    market_pb = 權益總計[權益總計.columns.intersection(close.columns)].sum(axis=1).reindex(close.index).ffill()
    result = market_value / market_pb
    return result


# 大盤指數與月線交叉情況
benchmark_return_all = data.get('benchmark_return:發行量加權股價報酬指數')
ma20_long_all = benchmark_return_all > benchmark_return_all.average(20)

# ls_order_sig
ls_order_sig_all = ls_order_position()

# adl
adls_all = get_adl()

# macd_0050
macd_0050_all = get_macd_0050()

# mt_rate
mt_rate_all, mt_rate_sig_all = margin_position()

# market_pb
market_pb_all = get_market_pb()

# tw_total_pmi
tw_total_pmi_all = data.get('tw_total_pmi:製造業PMI')

# tw_total_nmi
tw_total_nmi_all = data.get('tw_total_nmi:臺灣非製造業NMI')

# tw_total_pmi_future
tw_total_pmi_future_all = data.get('tw_total_pmi:未來六個月展望')

# tw_business_policy_ind
tw_business_policy_ind_all = data.get('tw_business_indicators:景氣對策信號(分)')

# 計分細項
close = data.get('price:收盤價')

inds = pd.DataFrame({
  'ind1': ma20_long_all['發行量加權股價報酬指數'],
  'ind2': (ls_order_sig_all > 0).astype(float) * 1.5,
  'ind3': (adls_all['ind'] > 0).astype(float) * 1.5,
  'ind4': (macd_0050_all > 0).astype(float),
  'ind5': (mt_rate_all >= 1.8) * -1 + (mt_rate_all <= 1.4) * 2,
  'ind6': (market_pb_all >= 2) * -1 + (market_pb_all <= 1.4) * 1,
  'ind7': (tw_total_pmi_all['tw_total_pmi'] > 50) * 1.5,
  'ind8': (tw_total_nmi_all['tw_total_nmi'] > 50) * 1,
  'ind9': (tw_total_pmi_future_all['tw_total_pmi'] > 50) * 1.5,
  'ind10': (tw_business_policy_ind_all['tw_business_indicators'].rolling(3).mean() > tw_business_policy_ind_all[
    'tw_business_indicators'].rolling(12).mean()) * 2
})

score = inds.astype(float).ffill().sum(axis=1)

position = pd.DataFrame({
  '0050': score >= 4,
  '0051': score >= 4,
  '00632R': score < 4
}).astype(float) * 0.5

#report = sim(position.loc['2015':], live_performance_start='2022-09-01')
report = sim(position.loc['2015':], tax_ratio=1 / 1000 , fee_ratio=1.425 / 1000 / 3, live_performance_start='2022-09-01')
