import ccxt
import time
from flask import Flask, request
import pandas as pd
pd.set_option('display.max_rows', None)
import pandas_ta as ta
import numpy as np
from line_notify import LineNotify 
from datetime import datetime as dt
import schedule
import warnings
warnings.filterwarnings('ignore')
import os
import math 
from tabulate import tabulate

app = Flask(__name__)

@app.route("/")
def hello_world():
    return 'VXMA bot (Form Tradingview)By Vaz. \nDonate XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm'

#key setting str(os.environ['API_KEY'])
API_KEY = str(os.environ['API_KEY'])
API_SECRET = str(os.environ['API_SECRET']) 
LINE_TOKEN = str(os.environ['LINE_TOKEN']) 
notify = LineNotify(LINE_TOKEN)
#Bot setting
BOT_NAME = 'VXMA'
MIN_BALANCE = str(os.environ['MIN_BALANCE'])
SYMBOL_NAME = str(os.environ['SYMBOL_NAME']).split(",") 
LEVERAGE = str(os.environ['LEVERAGE']).split(",") 
TF = str(os.environ['TF']) 
#STAT setting
RISK = str(os.environ['LOST_PER_TARDE']) 
TPRR1 = str(os.environ['RiskReward']) 
TPPer = str(os.environ['TP_Percent']) 
Pivot = str(os.environ['Pivot_lookback']) 
#TA setting
ATR_Period = str(os.environ['ATR_Period']) 
ATR_Mutiply = str(os.environ['ATR_Mutiply']) 
RSI_Period = str(os.environ['RSI_Period']) 
EMA_FAST = str(os.environ['EMA_Fast']) 
LINEAR = str(os.environ['SUBHAG_LINEAR']) 
SMOOTH = str(os.environ['SMOOTH']) 
LengthAO = str(os.environ['Andean_Oscillator'])

# API CONNECT
exchange = ccxt.binance({
"apiKey": API_KEY,
"secret": API_SECRET,
'options': {
'defaultType': 'future'
},
'enableRateLimit': True
})

Sside = 'BOTH'
Lside = 'BOTH'
messmode = ''
min_balance = 20

currentMODE = exchange.fapiPrivate_get_positionside_dual()
if currentMODE['dualSidePosition']:
    print('You are in Hedge Mode')
    Sside = 'SHORT'
    Lside = 'LONG'
    messmode = 'You are in Hedge Mode'
else:
    print('You are in One-way Mode')
    messmode = 'You are in One-way Mode'

if MIN_BALANCE[0]=='$':
    min_balance=float(MIN_BALANCE[1:len(MIN_BALANCE)])
    print("MIN_BALANCE=",min_balance)

#Alphatrend
def alphatrend(df,atr_p,atr_m,rsi):
    df['atr'] = ta.sma(ta.true_range(df['High'],df['Low'],df['Close']),atr_p)
    df['rsi'] = ta.rsi(df['Close'],rsi)
    df['downT'] = 0.0
    df['upT'] = 0.0
    df['alphatrend'] = 0.0
#AlphaTrend rsibb >= 50 ? upT < nz(AlphaTrend[1]) ? nz(AlphaTrend[1]) : upT : downT > nz(AlphaTrend[1]) ? nz(AlphaTrend[1]) : downT
    for current in range(1, len(df.index)):
        previous = current - 1
        df['downT'][current] = df['High'][current] + df['atr'][current] * atr_m
        df['upT'][current] = df['Low'][current] - df['atr'][current] * atr_m
        if df['rsi'][current] >= 50 :
            if df['upT'][current] < (df['alphatrend'][previous] if df['alphatrend'][previous] != None else 0):
                df['alphatrend'][current] = (df['alphatrend'][previous] if df['alphatrend'][previous] != None else 0)
            else : df['alphatrend'][current] = df['upT'][current]
        else:
            if df['downT'][current] > (df['alphatrend'][previous] if df['alphatrend'][previous] != None else 0):
                df['alphatrend'][current] = (df['alphatrend'][previous] if df['alphatrend'][previous] != None else 0)
            else : df['alphatrend'][current] = df['downT'][current]
    return df
    
#Andean_Oscillator
def andean(df,AOL):
    df['up1'] = 0.0
    df['up2'] = 0.0
    df['dn1'] = 0.0
    df['dn2'] = 0.0
    df['cmpbull'] = 0.0
    df['cmpbear'] = 0.0
    alpha = 2/(AOL + 1)
    for current in range(1, len(df.index)):
        previous = current - 1
        CloseP = df['Close'][current]
        OpenP = df['Open'][current]
        up1 = df['up1'][previous]
        up2 = df['up2'][previous]
        dn1 = df['dn1'][previous]
        dn2 = df['dn2'][previous]
        # up1 := nz(math.max(C, O, up1[1] - (up1[1] - C) * alpha), C)
        df['up1'][current] = (max(CloseP,OpenP,up1 - (up1 - CloseP)*alpha) if max(CloseP,OpenP,up1 - (up1 - CloseP)*alpha) != None else df['Close'][current])
        # up2 := nz(math.max(C * C, O * O, up2[1] - (up2[1] - C * C) * alpha), C * C)
        df['up2'][current] = (max(CloseP*CloseP,OpenP*OpenP,up2 - (up2 - CloseP*CloseP)*alpha) if max(CloseP*CloseP,OpenP*OpenP,up2 - (up2 - CloseP*CloseP)*alpha) != None else df['Close'][current]*df['Close'][current])
        # dn1 := nz(math.min(C, O, dn1[1] + (C - dn1[1]) * alpha), C)
        df['dn1'][current] = (min(CloseP,OpenP,dn1 + (CloseP - dn1)*alpha) if min(CloseP,OpenP,dn1 + (CloseP - dn1)*alpha) != None else df['Close'][current])
        # dn2 := nz(math.min(C * C, O * O, dn2[1] + (C * C - dn2[1]) * alpha), C * C)
        df['dn2'][current] = (min(CloseP*CloseP,OpenP*OpenP,dn2 + (CloseP*CloseP - dn2)*alpha) if min(CloseP*CloseP,OpenP*OpenP,dn2 + (CloseP*CloseP - dn2)*alpha) != None else df['Close'][current]*df['Close'][current])
        up1n = df['up1'][current] 
        up2n = df['up2'][current]
        dn1n = df['dn1'][current]
        dn2n = df['dn2'][current]
        df['cmpbull'][current] = math.sqrt(dn2n - (dn1n * dn1n))
        df['cmpbear'][current] = math.sqrt(up2n - (up1n * up1n))
    return df
    
#VXMA Indicator
def vxma(df):
    df['vxma'] = 0.0
    df['trend'] = False
    df['buy'] = False
    df['sell'] = False
    for current in range(2, len(df.index)):
        previous = current - 1
        before  = current - 2
        EMAFAST = df['ema'][current]
        LINREG = df['subhag'][current]
        ALPHATREND = df['alphatrend'][before]
        clohi = max(EMAFAST,LINREG,ALPHATREND)
        clolo = min(EMAFAST,LINREG,ALPHATREND)
#CloudMA := (bull > bear) ? clolo < nz(CloudMA[1]) ? nz(CloudMA[1]) : clolo :
        if df['cmpbull'][current] > df['cmpbear'][current] :
            if clolo < (df['vxma'][previous] if df['vxma'][previous] != None else 0):
                df['vxma'][current] = (df['vxma'][previous] if df['vxma'][previous] != None else 0)
            else : df['vxma'][current] = clolo
#  (bear > bull) ? clohi > nz(CloudMA[1]) ? nz(CloudMA[1]) : clohi : nz(CloudMA[1])
        elif df['cmpbull'][current] < df['cmpbear'][current]:
            if clohi > (df['vxma'][previous] if df['vxma'][previous] != None else 0):
                df['vxma'][current] = (df['vxma'][previous] if df['vxma'][previous] != None else 0)
            else : df['vxma'][current] = clohi
        else:
            df['vxma'][current] = (df['vxma'][previous] if df['vxma'][previous] != None else 0)
        #Get trend True = Bull False = Bear
        if df['vxma'][current] > df['vxma'][previous] and df['vxma'][previous] > df['vxma'][before] :
            df['trend'][current] = True
        elif df['vxma'][current] < df['vxma'][previous] and df['vxma'][previous] < df['vxma'][before] :
            df['trend'][current] = False
        else:
            df['trend'][current] = df['trend'][previous] 
        #get zone
        if df['trend'][current] and not df['trend'][previous] :
            df['buy'][current] = True
            df['sell'][current] = False
        elif not df['trend'][current] and df['trend'][previous] :
            df['buy'][current] = False
            df['sell'][current] = True
        else:
            df['buy'][current] = False
            df['sell'][current] = False
    return df

#Pivot High-Low
def pivot(df):
    df['Highest'] = df['High']
    df['Lowest'] = df['Low']
    for current in range(len(df.index) - int(Pivot), len(df.index)):
        previous = current - 1
        if df['Low'][current] < df['Lowest'][previous]:
            df['Lowest'][current] = df['Low'][current]
        else : df['Lowest'][current] = df['Lowest'][previous]
        if df['High'][current] > df['Highest'][previous]:
            df['Highest'][current] = df['High'][current]
        else : df['Highest'][current] = df['Highest'][previous]
    return df

#Position Sizing
def buysize(df,balance,symbol):
    last = len(df.index) - 1
    exchange.load_markets()
    freeusd = balance['free']['USDT']
    if RISK[0]=='%':
        percent = float(RISK[1:len(RISK)])
        risk = (percent/100)*freeusd
    elif RISK[0]=='$':
        risk = float(RISK[1:len(RISK)])
    amount = abs(risk  / (df['Close'][last] - df['Lowest'][last]))
    qty_precision = exchange.markets[symbol]['precision']['amount']
    lot = round(amount,qty_precision)
    return lot

def sellsize(df,balance,symbol):
    last = len(df.index) - 1
    exchange.load_markets()
    freeusd = balance['free']['USDT']
    if RISK[0]=='%':
        percent = float(RISK[1:len(RISK)])
        risk = (percent/100)*freeusd
    elif RISK[0]=='$':
        risk = float(RISK[1:len(RISK)])
    amount = abs(risk  / (df['Highest'][last] - df['Close'][last]))
    qty_precision = exchange.markets[symbol]['precision']['amount']
    lot = round(amount,qty_precision)
    return lot

#RiskReward    
def RRTP(df,symbol,direction):
    #buyprice  * (1 + (((Openprice - Lowest)/Openprice))*rrPer) 
    #sellprice * (1 - (((Highest - Openprice)/ Openprice))*rrPer)
    # true = long, false = short
    if direction :
        ask = exchange.fetchBidsAsks([symbol])[symbol]['info']['askPrice']
        target = ask *(1+((ask-df['Lowest'][len(df.index)-1])/ask)*TPRR1)
    else :
        bid = exchange.fetchBidsAsks([symbol])[symbol]['info']['bidPrice']
        target = bid *(1-((df['Highest'][len(df.index)-1]-bid)/bid)*TPRR1)
    return target

#OpenLong Buy
def OpenLong(df,balance,symbol,lev):
    print('Entry Long')
    amount = float(buysize(df,balance,symbol))
    ask = exchange.fetchBidsAsks([symbol])[symbol]['info']['askPrice']
    params = {
    'stopLoss': {
        'type': 'market', # or 'limit'
        'stopLossPrice': str(df['Lowest'][len(df.index)-1]),
    },
    'takeProfit': {
        'type': 'market',
        'takeProfitPrice': str(RRTP(df,symbol,True)),
        'quantity': str(amount*int(TPPer)/100),
    },
    'positionSide': Lside 
    }
    exchange.setLeverage(int(lev),symbol)
    free = balance['free']['USDT']
    if free > min_balance :
        order = exchange.create_order(symbol,'market','buy',amount,params)
        margin=ask*amount/lev
        total = balance['total']['USDT']
        msg ="BINANCE:\n" + "BOT         : " + BOT_NAME + "\nCoin        : " + symbol + "\nStatus      : " + "OpenLong[BUY]" + "\nAmount    : " + str(amount) +"("+str(round((amount*ask),2))+" USDT)" + "\nPrice        :" + str(ask) + " USDT" + str(round(margin,2))+  " USDT"+ "\nBalance   :" + str(round(total,2)) + " USDT"
    else :
        msg = "MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้  : " + str(min_balance)
    notify.send(msg)
    return

#OpenShort SELL
def OpenShort(df,balance,symbol,lev):
    print('Entry Long')
    amount = float(buysize(df,balance,symbol))
    bid = exchange.fetchBidsAsks([symbol])[symbol]['info']['bidPrice']
    params = {
    'stopLoss': {
        'type': 'market', # or 'limit'
        'stopLossPrice': str(df['Highest'][len(df.index)-1]),
    },
    'takeProfit': {
        'type': 'market',
        'takeProfitPrice': str(RRTP(df,symbol,False)),
        'quantity': str(amount*int(TPPer)/100),
    },
    'positionSide': Sside 
    }
    exchange.setLeverage(int(lev),symbol)
    free = balance['free']['USDT']
    if free > min_balance :
        order = exchange.create_order(symbol,'market','sell',amount,params)
        margin=bid*amount/lev
        total = balance['total']['USDT']
        msg ="BINANCE:\n" + "BOT         : " + BOT_NAME + "\nCoin        : " + symbol + "\nStatus      : " + "OpenShort[SELL]" + "\nAmount    : " + str(amount) +"("+str(round((amount*bid),2))+" USDT)" + "\nPrice        :" + str(bid) + " USDT" + str(round(margin,2))+  " USDT"+ "\nBalance   :" + str(round(total,2)) + " USDT"
    else :
        msg = "MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้  : " + str(min_balance)
    notify.send(msg)
    return

#CloseLong Sell
def CloseLong(df,balance,symbol,status):
    print('Close Long')
    amount = float(status["positionAmt"][len(status.index) -1])
    upnl = status["unrealizedProfit"][len(status.index) -1]
    bid = exchange.fetchBidsAsks([symbol])[symbol]['info']['bidPrice']
    params = {
    'positionSide': Lside
    }
    order = exchange.create_order(symbol,'market','sell',amount,params)
    time.sleep(1)
    total = balance['total']['USDT']
    msg ="BINANCE:\n" + "BOT         : " + BOT_NAME + "\nCoin        : " + symbol + "\nStatus      : " + "CloseLong[SELL]" + "\nAmount    : " + str(amount) +"("+str(round((amount*bid),2))+" USDT)" + "\nPrice        :" + str(bid) + " USDT" + "\nRealized P/L: " + str(round(upnl,2)) + " USDT"  +"\nBalance   :" + str(round(total,2)) + " USDT"
    notify.send(msg)
    return
 
#CloseShort Buy 
def CloseShort(df,balance,symbol,status):
    print('Close Short')
    amount = abs(float(status["positionAmt"][len(status.index) -1]))
    upnl = status["unrealizedProfit"][len(status.index) -1]
    ask = exchange.fetchBidsAsks([symbol])[symbol]['info']['askPrice']
    params = {
    'positionSide': Sside
    }
    order = exchange.create_order(symbol,'market','buy',amount,params)
    time.sleep(1)
    total = balance['total']['USDT']
    msg ="BINANCE:\n" + "BOT         : " + BOT_NAME + "\nCoin        : " + symbol + "\nStatus      : " + "CloseShort[BUY]" + "\nAmount    : " + str(amount) +"("+str(round((amount*ask),2))+" USDT)" + "\nPrice        :" + str(ask) + " USDT" + "\nRealized P/L: " + str(round(upnl,2)) + " USDT"  +"\nBalance   :" + str(round(total,2)) + " USDT"
    notify.send(msg)

    return

#clearconsol
def clearconsol():
    time.sleep(10)
    # posix is os name for linux or mac
    if(os.name == 'posix'):
        os.system('clear')
    # else screen will be cleared for windows
    else:
        os.system('cls') 

#Check position after fetch DATA
def check_buy_sell_signals(df,symbol,status,balance,lev):
    longPozisyonda = False
    shortPozisyonda = False
    pozisyondami = False
    print(f"Fetching new bars for {dt.now().isoformat()}")
    print(df.tail(5))
    last = len(df.index) -1
    previous = last - 1
        # NO Position
    if not status.empty and status["positionAmt"][len(status.index) -1] != 0:
        pozisyondami = True
    else: 
        pozisyondami = False
        shortPozisyonda = False
        longPozisyonda = False
    # Long position
    if pozisyondami and float(status["positionAmt"][len(status.index) -1]) > 0:
        longPozisyonda = True
        shortPozisyonda = False
    # Short position
    if pozisyondami and float(status["positionAmt"][len(status.index) -1]) < 0:
        shortPozisyonda = True
        longPozisyonda = False
    print("checking for buy and sell signals")
    if df['buy'][last]:
        print("changed to Bullish, buy")
        if shortPozisyonda :
            CloseShort(df,balance,symbol,status)
        if not longPozisyonda :
            OpenLong(df,balance,symbol,lev)
            longPozisyonda = True
        else:
            print("already in position, nothing to do")
    if df['sell'][last]:
        print("changed to Bearish, Sell")
        if longPozisyonda :
            CloseLong(df,balance,symbol,status)
        if not shortPozisyonda:
            OpenShort(df,balance,symbol,lev)
            shortPozisyonda = True
        else:
            print("already in position, nothing to do")

def indicator(df,ema_period,linear,smooth,atr_p,atr_m,rsi,AOL):
    df['ema'] = ta.ema(df['Close'],ema_period)
    df['subhag'] = ta.ema(ta.linreg(df['Close'],linear,0),smooth)
    alphatrend(df,atr_p,atr_m,rsi)
    andean(df,AOL)
    pivot(df)
    vxma(df)
    df.drop(columns=['ema','subhag','atr','up2'], axis=1,inplace=True)
    df.drop(columns=['downT','upT','alphatrend','dn1'], axis=1,inplace=True)
    df.drop(columns=['cmpbull','cmpbear','up1','dn2'], axis=1,inplace=True)
    return df

#Run everthing here then sent data to checking 
def run_bot():
    balance = exchange.fetch_balance()
    free_balance = exchange.fetch_free_balance()      
    exchange.precisionMode = ccxt.DECIMAL_PLACES
    positions = balance['info']['positions']
    for i in range(len(SYMBOL_NAME)):
        symbolNamei = SYMBOL_NAME[i]
        newSymboli = SYMBOL_NAME[i] + "USDT"
        symboli = SYMBOL_NAME[i] + "/USDT"
        leveragei = LEVERAGE[i]
        ema = int(EMA_FAST[i])
        linear = int(LINEAR[i])
        smooth = int(SMOOTH[i])
        atr_p = int(ATR_Period[i])
        atr_m = float(ATR_Mutiply[i])
        rsi = int(RSI_Period[i])
        AOL = int(LengthAO[i])
        current_positions = [position for position in positions if float(position['positionAmt']) != 0 and position['symbol'] == newSymboli]
        position_bilgi = pd.DataFrame(current_positions, columns=["symbol", "entryPrice","positionSide", "unrealizedProfit", "positionAmt", "initialMargin" ,"isolatedWallet"])
        exchange.load_markets()
        market = exchange.markets[symboli]
        bars = exchange.fetch_ohlcv(symboli, timeframe=TF, since = None, limit = 500)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        indicator(df,ema,linear,smooth,atr_p,atr_m,rsi,AOL)
        check_buy_sell_signals(df,symboli,position_bilgi,balance,leveragei)
        print('checking current position on hold...')
        print(tabulate(position_bilgi, headers = 'keys', tablefmt = 'grid'))


    
schedule.every(10).seconds.do(run_bot)

while True:
    schedule.run_pending()
    time.sleep(10)
    
if __name__ == '__main__':
    app.run(debug=True)