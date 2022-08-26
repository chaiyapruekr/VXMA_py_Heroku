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
    return BOT_NAME + 'By Vaz. \nDonate XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm'

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

wellcome = 'VXMA Bot Started :\n' + messmode + '\nTrading pair : ' + str(SYMBOL_NAME) + '\nTimeframe : ' + str(TF) + '\nBasic Setting\n----------\nRisk : ' + str(RISK) + '\nRisk:Reward : ' + str(TPRR1) + '\nATR Period : ' + str(ATR_Period) + '\nATR Multiply : ' + str(ATR_Mutiply) + '\nRSI  : ' + str(RSI_Period) + '\nEMA  : '+ str(EMA_FAST) + '\nLinear : ' + str(LINEAR) + '\nSmooth : ' + str(SMOOTH) + '\nAndean_Oscillator : ' + str(LengthAO) + '\nBot Will Stop Entry when balance < ' + str(min_balance) + '\nGOODLUCK'
notify.send(wellcome)

#Alphatrend
def alphatrend(df, period=int(ATR_Period), atr_multiplier=float(ATR_Mutiply)):
    df['atr'] = ta.atr(df['high'],df['low'],df['close'], period)
    df['rsi'] = ta.rsi(df['close'],int(RSI_Period))
    df['downT'] = df['high'] + (atr_multiplier * df['atr'])
    df['upT'] = df['low'] - (atr_multiplier * df['atr'])
    df['alphatrend'] = 0.0
    for current in range(1, len(df.index)):
        previous = current - 1
        if df['rsi'][current] >= 50 :
            if df['upT'][current] < df['alphatrend'][previous]:
                df['alphatrend'][current] = df['alphatrend'][previous]
            else : df['alphatrend'][current] = df['upT'][current]
        else:
            if df['downT'][current] > df['alphatrend'][previous]:
                df['alphatrend'][current] = df['alphatrend'][previous]
            else : df['alphatrend'][current] = df['downT'][current]
        
    return df
#Andean_Oscillator
def andean(df):
    df['cmpbull'] = 0.0
    df['cmpbear'] = 0.0
    df['up1'] = 0.0
    df['up2'] = 0.0
    df['dn1'] = 0.0
    df['dn2'] = 0.0
    alpha = 2/(int(LengthAO) + 1)
    for current in range(1, len(df.index)):
        previous = current - 1
        CloseP = df['close'][current]
        OpenP = df['open'][current]
        up1 = df['up1'][previous]
        up2 = df['up2'][previous]
        dn1 = df['dn1'][previous]
        dn2 = df['dn2'][previous]
        # up1 := nz(math.max(C, O, up1[1] - (up1[1] - C) * alpha), C)
        if max(CloseP,OpenP,up1 - (up1 - CloseP)*alpha) == 0:
            df['up1'][current] = df['close'][current]
        else : 
            df['up1'][current] = max(CloseP,OpenP,up1 - (up1 - CloseP)*alpha)
        # up2 := nz(math.max(C * C, O * O, up2[1] - (up2[1] - C * C) * alpha), C * C)
        if max(CloseP*CloseP,OpenP*OpenP,up2 - (up2 - CloseP*CloseP)*alpha) == 0:
            df['up2'][current] = df['close'][current]*df['close'][current]
        else :
            df['up2'][current] = max(CloseP*CloseP,OpenP*OpenP,up2 - (up2 - CloseP*CloseP)*alpha)
        # dn1 := nz(math.min(C, O, dn1[1] + (C - dn1[1]) * alpha), C)
        if min(CloseP,OpenP,dn1 + (CloseP - dn1)*alpha) == 0:
            df['dn1'][current] = df['close'][current]
        else :
            df['dn1'][current] = min(CloseP,OpenP,dn1 + (CloseP - dn1)*alpha)
        # dn2 := nz(math.min(C * C, O * O, dn2[1] + (C * C - dn2[1]) * alpha), C * C)
        if min(CloseP*CloseP,OpenP*OpenP,dn2 + (CloseP*CloseP - dn2)*alpha) ==0:
            df['dn2'][current] = df['close'][current]*df['close'][current]
        else :
            df['dn2'][current] = min(CloseP*CloseP,OpenP*OpenP,dn2 + (CloseP*CloseP - dn2)*alpha)
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
    for current in range(2, len(df.index)):
        previous = current - 1
        before  = current - 2
        EMAFAST = df['ema'][current]
        LINREG = df['subhag'][current]
        ALPHATREND = df['alphatrend'][before]
        clohi = min(EMAFAST,LINREG,ALPHATREND)
        clolo = max(EMAFAST,LINREG,ALPHATREND)
#CloudMA := (bull > bear) ? clolo < nz(CloudMA[1]) ? nz(CloudMA[1]) : clolo : (bear > bull) ? clohi > nz(CloudMA[1]) ? nz(CloudMA[1]) : clohi : nz(CloudMA[1])
        if df['cmpbull'][current] > df['cmpbear'][current] :
            if clolo < df['vxma'][previous]:
                df['vxma'][current] = df['vxma'][previous]
            else : df['vxma'][current] = clolo
        elif df['cmpbull'][current] < df['cmpbear'][current]:
            if clohi > df['vxma'][previous]:
                df['vxma'][current] = df['vxma'][previous]
            else : df['vxma'][current] = clohi
        else:
            df['vxma'][current] = df['vxma'][previous]
        #Get trend True = Bull False = Bear
        if df['vxma'][current] > df['vxma'][previous] and df['vxma'][previous] > df['vxma'][before] :
            df['trend'][current] = True
        elif df['vxma'][current] < df['vxma'][previous] and df['vxma'][previous] < df['vxma'][before] :
            df['trend'][current] = False
        else:
            df['trend'][current] = df['trend'][previous] 
   
    return df
#Pivot High-Low
def pivot(df):
    df['highest'] = df['high']
    df['lowest'] = df['low']
    for current in range(len(df.index) - int(Pivot), len(df.index)):
        previous = current - 1
        if df['low'][current] < df['lowest'][previous]:
            df['lowest'][current] = df['low'][current]
        else : df['lowest'][current] = df['lowest'][previous]
        if df['high'][current] > df['highest'][previous]:
            df['highest'][current] = df['high'][current]
        else : df['highest'][current] = df['highest'][previous]
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
    amount = abs(risk  / (df['close'][last] - df['lowest'][last]))
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
    amount = abs(risk  / (df['highest'][last] - df['close'][last]))
    qty_precision = exchange.markets[symbol]['precision']['amount']
    lot = round(amount,qty_precision)
    return lot
    
def RRTP(df,symbol,direction):
    #buyprice  * (1 + (((openprice - lowest)/openprice))*rrPer) 
    #sellprice * (1 - (((highest - openprice)/ openprice))*rrPer)
    # true = long, false = short
    if direction :
        ask = exchange.fetchBidsAsks([symboli])[symboli]['info']['askPrice']
        target = ask *(1+((ask-df['lowest'][len(df.index)-1])/ask)*TPRR1)
    else :
        bid = exchange.fetchBidsAsks([symboli])[symboli]['info']['bidPrice']
        target = bid *(1-((df['highest'][len(df.index)-1]-bid)/bid)*TPRR1)
    return target

def OpenLong(df,balance,symbol,lev):
    print('Entry Long')
    amount = float(buysize(df,balance,symbol))
    ask = exchange.fetchBidsAsks([symbol])[symbol]['info']['askPrice']
    params = {
    'stopLoss': {
        'type': 'market', # or 'limit'
        'stopLossPrice': df['lowest'][len(df.index)-1],
    },
    'takeProfit': {
        'type': 'market',
        'takeProfitPrice': RRTP(df,symbol,True),
        'quantity': (amount*int(TPPer)/100),
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
    
def OpenShort(df,balance,symbol,lev):
    print('Entry Long')
    amount = float(buysize(df,balance,symbol))
    bid = exchange.fetchBidsAsks([symbol])[symbol]['info']['bidPrice']
    params = {
    'stopLoss': {
        'type': 'market', # or 'limit'
        'stopLossPrice': df['highest'][len(df.index)-1],
    },
    'takeProfit': {
        'type': 'market',
        'takeProfitPrice': RRTP(df,symbol,False),
        'quantity': (amount*int(TPPer)/100),
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

def CloseLong(df,balance,symbol,status):
    print('Close Long')
    amount = float(status["positionAmt"][len(status.index) -1])
    upnl = status["unrealizedProfit"][len(status.index) -1]
    bid = exchange.fetchBidsAsks([symboli])[symboli]['info']['bidPrice']
    params = {
    'positionSide': Lside
    }
    order = exchange.create_order(symbol,'market','sell',amount,params)
    time.sleep(1)
    total = balance['total']['USDT']
    msg ="BINANCE:\n" + "BOT         : " + BOT_NAME + "\nCoin        : " + symbol + "\nStatus      : " + "CloseLong[SELL]" + "\nAmount    : " + str(amount) +"("+str(round((amount*bid),2))+" USDT)" + "\nPrice        :" + str(bid) + " USDT" + "\nRealized P/L: " + str(round(upnl,2)) + " USDT"  +"\nBalance   :" + str(round(total,2)) + " USDT"
    notify.send(msg)
    return
    
def CloseShort(df,balance,symbol,status):
    print('Close Short')
    amount = abs(float(status["positionAmt"][len(status.index) -1]))
    upnl = status["unrealizedProfit"][len(status.index) -1]
    ask = exchange.fetchBidsAsks([symboli])[symboli]['info']['askPrice']
    params = {
    'positionSide': Sside
    }
    order = exchange.create_order(symbol,'market','buy',amount,params)
    time.sleep(1)
    total = balance['total']['USDT']
    msg ="BINANCE:\n" + "BOT         : " + BOT_NAME + "\nCoin        : " + symbol + "\nStatus      : " + "CloseShort[BUY]" + "\nAmount    : " + str(amount) +"("+str(round((qty_close*ask),2))+" USDT)" + "\nPrice        :" + str(ask) + " USDT" + "\nRealized P/L: " + str(round(upnl,2)) + " USDT"  +"\nBalance   :" + str(round(total,2)) + " USDT"
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

def check_buy_sell_signals(df,symbol,status,balance,lev):
    longPozisyonda = False
    shortPozisyonda = False
    pozisyondami = False
    print(df.tail(5))
    print("checking for buy and sell signals")
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
    
    if not df['trend'][previous] and df['trend'][last]:
        print("changed to Bullish, buy")
        if shortPozisyonda :
            CloseShort(df,balance,symbol,status)
        if not longPozisyonda :
            OpenLong(df,balance,symbol,lev)
            longPozisyonda = True
        else:
            print("already in position, nothing to do")
    if df['trend'][previous] and not df['trend'][last]:
        print("changed to Bearish, Sell")
        if longPozisyonda :
            CloseLong(df,balance,symbol,status)
        if not shortPozisyonda:
            OpenShort(df,balance,symbol,lev)
            shortPozisyonda = True
        else:
            print("already in position, nothing to do")
    

def run_bot():
    kesisim = False
    amount = 0
    ROE = 0
    balance = exchange.fetch_balance()
    free_balance = exchange.fetch_free_balance()      
    exchange.precisionMode = ccxt.DECIMAL_PLACES
    positions = balance['info']['positions']
    for i in range(len(SYMBOL_NAME)):
        symbolNamei = SYMBOL_NAME[i]
        newSymboli = SYMBOL_NAME[i] + "USDT"
        symboli = SYMBOL_NAME[i] + "/USDT"
        leveragei = LEVERAGE[i]
        current_positions = [position for position in positions if float(position['positionAmt']) != 0 and position['symbol'] == newSymboli]
        position_bilgi = pd.DataFrame(current_positions, columns=["symbol", "entryPrice","positionSide", "unrealizedProfit", "positionAmt", "initialMargin" ,"isolatedWallet"])
        exchange.load_markets()
        market = exchange.markets[symboli]
        print(f"Fetching new bars for {dt.now().isoformat()}")
        bars = exchange.fetch_ohlcv(symboli, timeframe=TF, since = None, limit = 500)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['ema'] = ta.ema(df['close'],int(EMA_FAST))
        df['subhag'] = ta.ema(ta.linreg(df['close'],int(LINEAR),0),int(SMOOTH))
        alphatrend(df)
        andean(df)
        pivot(df)
        vxma(df) 
        check_buy_sell_signals(df,symboli,position_bilgi,balance,leveragei)
        print('checking current position on hold...')
        print(tabulate(position_bilgi, headers = 'keys', tablefmt = 'grid'))


    
schedule.every(5).seconds.do(run_bot)

while True:
    schedule.run_pending()
    time.sleep(1)
    
if __name__ == '__main__':
    app.run(debug=True)