from finlab import data, backtest
# talib
# real = RSI(close, timeperiod=14)

rsi20 = data.indicator("RSI", timeperiod=20)
rsi60 = data.indicator("RSI", timeperiod=60)
rsi120 = data.indicator("RSI", timeperiod=120)
ROE稅後 = data.get("fundamental_features:ROE稅後")

長週期上漲 = rsi120 > 55
中週期別過熱 = rsi60 < 75
短週期RSI上漲 = rsi20.pct_change(3) > 0.02
短週期RSI高檔頓化 = (rsi20 > 75).sustain(3)

ROE為正 = ROE稅後 > 0

買 = (長週期上漲 
     & 中週期別過熱 
     & 短週期RSI上漲 
     & 短週期RSI高檔頓化
     & ROE為正
    )

持有60天 = 買.shift(60)
收盤價 = data.get('price:收盤價')
跌破季線 = 收盤價 < 收盤價.average(60)

賣 = 持有60天 | 跌破季線

股票部位 = 買.hold_until(賣)

report = backtest.sim(股票部位, resample='W',name='三頻率RSI策略', live_performance_start='2019-01-01')