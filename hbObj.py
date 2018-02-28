import hbClient as hbc
import time
from hbsdk import ApiError
from liveApi.liveUtils import *

hbBroker = hbc.hbTradeClient()

class OrderBase():
    ORDER_PRE_OPEN = 0
    ORDER_OPENED = 1
    ORDER_FILLED = 2
    ORDER_PRE_CANCLE = 3
    ORDER_CANCLED = 4
    ORDER_BUY_LIMIT = 0
    ORDER_SELL_LIMIT = 1
    def __init__(self, price, amount, direct):
        self.__price = price
        self.__amount = amount
        self.__filledAmount = 0
        self.__filledCash = 0
        self.__filledFee = 0
        self.__status = OrderBase.ORDER_PRE_OPEN
        self.__direct = direct
    def getPrice(self):
        return self.__price
    def getAmount(self):
        return self.__amount
    def getAmountFilled(self):
        return self.__filledAmount
    def getCashFilled(self):
        return self.__filledCash
    def getFee(self):
        return self.__filledFee
    def getStatus(self):
        return self.__status
    def setStatus(self, status):
        self.__status = status
    def updateOrder(self, filledAmount, filledCash, filledFee):
        self.__filledAmount = filledAmount
        self.__filledCash = filledCash
        self.__filledFee = filledFee
    def isBuy(self):
        return self.__direct == Order.ORDER_BUY_LIMIT
    def isSell(self):
        return self.__direct == Order.ORDER_SELL_LIMIT

class Order(OrderBase):
    def __init__(self, symbol, price, amount, direct):
        OrderBase.__init__(self, price, amount, direct)
        self.__broker = hbBroker
        self.__symbol = symbol
        self.__id = None
        self.submit()
    def getId(self):
        return self.__id
    def submit(self):
        if self.isBuy():
            orderInfo = self.__broker.buyLimit(self.__symbol, self.getPrice(), self.getAmount())
            print "buy: %f %f"%(self.getPrice(), self.getAmount())
        else:
            orderInfo = self.__broker.sellLimit(self.__symbol, self.getPrice(), self.getAmount())
            print "sell: %f %f"%(self.getPrice(), self.getAmount())
        self.__id = orderInfo.getId()
        self.setStatus(Order.ORDER_OPENED)
    def cancel(self):
        self.__broker.cancelOrder(self.getId())
        print "cancel order %d"%self.getId()
    def update(self):
        orderInfo = self.__broker.getUserTransactions([self.getId()])[0]
        print "upate %d : amount %f %f cash %f"%(self.getId(), self.getAmount(), orderInfo.getFilledAmount(), orderInfo.getFilledCash())
        self.updateOrder(orderInfo.getFilledAmount(), orderInfo.getFilledCash(), orderInfo.getFilledFee())
        if orderInfo.isFilled():
            self.setStatus(Order.ORDER_FILLED)
        elif orderInfo.isCanceled():
            self.setStatus(Order.ORDER_CANCLED)

class OrderBook():
    ORDERBOOK_PRE_OPEN = 0
    ORDERBOOK_OPENED = 1
    ORDERBOOK_FINISHED = 2
    def __init__(self, coin):
        self.__coin = coin
        self.__buyOrder = None
        self.__sellOrders = []
        self.__status = OrderBook.ORDERBOOK_PRE_OPEN
    def isFinished(self):
        return self.__status == OrderBook.ORDERBOOK_FINISHED
    def getStatus(self):
        return self.__status
    def buyLimit(self, price, amount):
        symbol = self.__coin.getSymbol()
        price = self.__coin.PriceRoundUp(price)
        amount = self.__coin.AmountRoundDown(amount)
        self.__buyOrder = Order(symbol, price, amount, Order.ORDER_BUY_LIMIT)
        self.__status = OrderBook.ORDERBOOK_OPENED
    def sellLimit(self, price, amount):
        symbol = self.__coin.getSymbol()
        price = self.__coin.PriceRoundDown(price)
        amount = self.__coin.AmountRoundDown(amount)
        sellOrder = Order(symbol, price, amount, Order.ORDER_SELL_LIMIT)
        self.__sellOrders.append(sellOrder)
        # self.__sellOrders.insert(0, sellOrder)
    def cancelOrder(self, order):
        # cancel order
        order.cancel()
        order.update()
    def exitOrderBook(self, price):
        for order in [self.__buyOrder] + self.__sellOrders:
            if order.getStatus() == Order.ORDER_OPENED:
                self.cancelOrder(order)
        sellAmount, sellAmountFilled = self.getSellAmount()
        diffAmount = self.__buyOrder.getAmountFilled() - self.__buyOrder.getFee() - sellAmount
        if diffAmount >= self.__coin.getMinAmount():
            self.sellLimit(price, diffAmount)
    def getBuyAmount(self):
        return self.__buyOrder.getAmount(), self.__buyOrder.getAmountFilled()
    def getSellAmount(self):
        sellAmount = 0
        sellAmountFilled = 0
        for sellOrder in self.__sellOrders:
            sellAmountFilled += sellOrder.getAmountFilled()
            if sellOrder.getStatus() == Order.ORDER_OPENED:
                sellAmount += sellOrder.getAmount()
            else:
                sellAmount += sellOrder.getAmountFilled()
        return sellAmount,sellAmountFilled
    def getBuyOrder(self):
        return self.__buyOrder
    def getSellOrders(self):
        return self.__sellOrders
    def updateOrders(self):
        for order in [self.__buyOrder] + self.__sellOrders:
            if order.getStatus() == Order.ORDER_OPENED:
                order.update()
        sellAmount, sellAmountFilled = self.getSellAmount()
        if self.__buyOrder.getStatus() in (Order.ORDER_FILLED, Order.ORDER_CANCLED):
            if self.__buyOrder.getAmountFilled() - self.__buyOrder.getFee() - sellAmountFilled < self.__coin.getMinAmount():
                self.__status = OrderBook.ORDERBOOK_FINISHED
    def getPNL(self):
        return self.getProfit()/self.__buyOrder.getCashFilled()
    def getProfit(self):
        selledCash = 0
        selledCashFee = 0
        for sellOrder in self.__sellOrders:
            selledCash += sellOrder.getCashFilled()
            selledCashFee += sellOrder.getFee()
        return selledCash - selledCashFee - self.__buyOrder.getCashFilled()

class DataSeries(list):
    def __init__(self, maxSize, *args, **kw):
        self.__maxSize = maxSize
        list.__init__(self, *args, **kw)
        self.resize()
    def resize(self):
        while len(self) > self.maxSize():
            self.pop(0)
    def extend(self, *args, **kw):
        list.extend(self, *args, **kw)
        self.resize()
    def insert(self, *args, **kw):
        list.insert(self, *args, **kw)
        self.resize()
    def append(self, *args, **kw):
        list.append(self, *args, **kw)
        self.resize()
    def maxSize(self):
        return self.__maxSize

class KLine():
    OHLC_TIME = 0
    OHLC_OPEN = 1
    OHLC_HIGH = 2
    OHLC_LOW = 3
    OHLC_CLOSE = 4
    OHLC_VOL = 5
    def __init__(self, maxSize=60):
        self.__maxSize = maxSize
        # time open high low close volume
        self.__ohlc = []
        self.__ma = {}
    def getOHLC(self, T=None):
        if T is None:
            return self.__ohlc
        if len(self.__ohlc) <= T:
            return []
        return self.__ohlc[T]
    def updateOHLC(self, k):
        if len(self.__ohlc) == 0:
            self.__ohlc = map(lambda x:DataSeries(self.__maxSize, [x]), k)
        else:
            for x in zip(self.__ohlc, k):
                ohlc_x,k_x = x
                ohlc_x.append(k_x)
        self.__updateMA()
    '''
    def updateOHLC(self, k):
        if len(self.__ohlc) == 0:
            self.__ohlc = map(lambda x:DataSeries(self.__maxSize, x), k)
            self.__updateMA()
            return
        ktime0,ktime1 = k[0]
        lastKtime = self.__ohlc[0][-1]
        if ktime0 == lastKtime:
            append = False
            for x in zip(self.__ohlc, k):
                ohlc_x,k_x = x
                ohlc_x[-1] = k_x[0]
        else:
            append = True
            for x in zip(self.__ohlc, k):
                ohlc_x,k_x = x
                ohlc_x[-1] = k_x[1]
                ohlc_x.append(k_x[0])
        self.__updateMA(append)
    '''
    def __updateMA(self, append=True):
        for period in self.__ma:
            low = self.__ohlc[self.OHLC_CLOSE] if len(self.__ohlc) else []
            if len(low) >= period:
                ma = sum(low[-period:])/float(period)
                if append or len(self.__ma) == 0:
                    self.__ma[period].append(ma)
                self.__ma[period][-1] = ma
    def MA(self, period):
        low = self.__ohlc[self.OHLC_CLOSE] if len(self.__ohlc) else []
        if self.__ma.get(period) is None:
            ma = []
            if len(low) >= period:
                ma = [sum(low[-period:])/float(period)]
            self.__ma[period] = DataSeries(self.__maxSize, ma)
        return self.__ma[period]

def cross_above(s1, s2):
    return False if len(s1) < 2 or len(s2) < 2 else s1[-2] <= s2[-2] and s1[-1] > s2[-1]
def cross_below(s1, s2):
    return False if len(s1) < 2 or len(s2) < 2 else s1[-2] >= s2[-2] and s1[-1] < s2[-1]

df=timestamp_to_DateTimeLocal

class Strategy():
    def __init__(self, symbol):
        self.__kline60 = KLine(60)
        self.__ma10 = self.__kline60.MA(10)
        self.__ma30 = self.__kline60.MA(30)
        self.__coin = hbc.hbSymbols().getCoin(symbol)
        self.__orderBook = None
        self.__orderBookHistory = []
        self.__broker = hbBroker
        self.__cash = 0
    def updateCash(self):
        self.__cash = self.__broker.getAccountBalance().getCoinTrade('usdt')
    def onTicks(self):
        pass
    def onBars(self):
        kclose = self.__kline60.getOHLC(KLine.OHLC_CLOSE)[-1]
        if self.__orderBook is None:
            self.updateCash()
            self.__orderBook = OrderBook(self.__coin)
            self.__orderBookHistory.append(self.__orderBook)
            self.__orderBook.buyLimit(kclose, self.__coin.getMinAmount()*2)
        elif self.__orderBook.getBuyOrder().getStatus() == Order.ORDER_FILLED:
            self.__orderBook.exitOrderBook(kclose)
    def _onBars(self):
        print '---onBars'
        print self.__ma10
        print self.__ma30
        print self.__kline60.getOHLC(KLine.OHLC_CLOSE)
        kclose = self.__kline60.getOHLC(KLine.OHLC_CLOSE)[-1]
        if self.__orderBook is None:
            if cross_above(self.__ma10, self.__ma30):
                self.__orderBook = OrderBook(self.__coin)
                self.__orderBookHistory.append(self.__orderBook)
                self.__orderBook.buyLimit(kclose, self.__usdt/kclose)
        elif self.__orderBook.getStatus() == OrderBook.ORDERBOOK_OPENED and cross_below(self.__ma10, self.__ma30):
            self.__orderBook.exitOrderBook(kclose)
    def onOrderBookExit(self):
        self.__orderBook = None
        exit()
        
    def onTradeInfo(self):
        if self.__orderBook.getStatus() == OrderBook.ORDERBOOK_FINISHED:
            self.onOrderBookExit()
            return
        buyPrice = self.__orderBook.getBuyOrder().getPrice()
        buyAmount,buyAmountFilled = self.__orderBook.getBuyAmount()
        sellAmount,selledAmountFilled = self.__orderBook.getSellAmount()
        newAmount = buyAmountFilled - sellAmount
        if newAmount > self.__coin.getMinAmount():
            self.__orderBook.sellLimit(buyPrice*1.1, newAmount)

    def getNextKTime(self, period):
        times = self.__kline60.getOHLC(KLine.OHLC_TIME)
        if len(times) == 0:
            return timestamp()/period*period-period
        return  times[-1] + period;

    def run(self, period):
        kPeriodMin = 1
        klines = self.__broker.getKLine(self.__coin.getSymbol(), kPeriodMin, 40)
        klines.pop(0)
        while len(klines):
            self.__kline60.updateOHLC(klines.pop(-1))
        while True:
            #if timestamp()%5 == 0 and self.__orderBook is not None:
            if self.__orderBook is not None:
                self.__orderBook.updateOrders()
                self.onTradeInfo()
                
            ksec = kPeriodMin*60
            ktime = self.getNextKTime(ksec)
            print df(ktime + ksec),' -- ',df(timestamp())
            if ktime + ksec <= timestamp():
                print '----'
                klines = self.__broker.getKLine(self.__coin.getSymbol(), kPeriodMin, 2)
                newK = klines[1]
                nk = klines[0]
                print (df(newK[KLine.OHLC_TIME]),newK[KLine.OHLC_CLOSE]),(df(nk[KLine.OHLC_TIME]),nk[KLine.OHLC_CLOSE])
                if newK[KLine.OHLC_TIME] == ktime or timestamp() > ktime + ksec + 30:
                    nk = klines[0]
                    newK[KLine.OHLC_TIME] = ktime
                    # newK[KLine.OHLC_CLOSE] = nk[KLine.OHLC_CLOSE]
                    self.__kline60.updateOHLC(newK)
                    self.onBars()
                time.sleep(0.2)
                continue
            time.sleep(min(period, ktime + ksec - timestamp()))

#Strategy('ltcusdt').run(60)
Strategy('ltcusdt').run(5)

