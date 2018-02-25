import hbClient as hbc
import time
from hbsdk import ApiError
import datetime

def timestamp():
    return int(time.time())

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
        return self.__direct == ORDER_BUY_LIMIT
    def isSell(self):
        return self.__direct == ORDER_SELL_LIMIT

class Order(OrderBase):
    def __init__(self, price, amount, direct):
        OrderBase.__init__(self, price, amount, direct)
        self.__id = None
        self.submit()
    def getId(self):
        return self.__id
    def submit(self):
        self.__id
        pass
    def cancel(self):
        pass
    def update(self):
        # orderInfo = orderQuery
        self.updateOrder(orderInfo.getFilledAmount(), orderInfo.getfilledCash(), orderInfo.getFilledFee())
        if orderInfo.filled():
            self.setStatus(Order.ORDER_FILLED)
        elif orderInfo.canceled():
            self.setStatus(Order.ORDER_CANCLED)

class OrderBook():
    ORDERBOOK_PRE_OPEN = 0
    ORDERBOOK_OPENED = 1
    ORDERBOOK_FINISHED = 2
    def __init__(self, symbol, pricePrecision, amountPrecision, minAmount):
        self.__symbol = symbol
        self.__pricePrecision = pricePrecision
        self.__amountPrecision = amountPrecision
        self.__buyOrder = None
        self.__sellOrders = []
        self.__minAmount = minAmount
        self.__status = OrderBook.ORDERBOOK_PRE_OPEN
    def isFinished(self):
        return self.__status == OrderBook.ORDERBOOK_FINISHED
    def getStatus(self):
        return self.__status
    def buyLimit(self, price, amount):
        self.__buyOrder = Order(price, amount, Order.ORDER_BUY_LIMIT)
        self.__status = OrderBook.ORDERBOOK_OPENED
    def sellLimit(self, price, amount):
        sellOrder = Order(price, amount, Order.ORDER_SELL_LIMIT)
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
        if diffAmount >= self.__minAmount:
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
            if self.__buyOrder.getAmountFilled() - self.__buyOrder.getFee() - sellAmountFilled < minAmount:
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

class Strategy():
    def __init__(self, symbol):
        self.__kline60 = KLine(60)
        self.__ma10 = self.__kline60.MA(10)
        self.__ma30 = self.__kline60.MA(30)
        self.__coin = hbc.hbSymbols().getCoin(symbol)
        self.__orderBook = OrderBook(symbol, self.__coin.getCashPrecision(), self.__coin.getCoinPrecision(), self.__coin.getMinAmount())
        self.__broker = hbc.hbTradeClient()
    def onTicks(self):
        pass
    def onBars(self):
        kclose = self.__kline60.getOHLC(OrderBook.OHLC_LOW)
        if self.__orderBook.getStatus() == OrderBook.ORDERBOOK_PRE_OPEN:
            if cross_above(self.__ma10, self.__ma30):
                self.__orderBook.buyLimit(self.__usdt/kclose, kclose)
        elif self.__orderBook.getStatus() == OrderBook.ORDERBOOK_OPENED and cross_below(self.__ma10, self.__ma30):
            self.__orderBook.exitOrderBook(kclose)
    def onTradeInfo(self):
        pass
    def run(self, period):
        klines = self.__broker.getKLine(self.__coin.getSymbol(), 60, 40)
        klines.pop(0)
        while len(klines):
            self.__kline60.updateOHLC(klines.pop(-1))
        while True:
            klines = self.__broker.getKLine(self.__coin.getSymbol(), 60, 2)
            time.sleep(period)

Strategy('ltcusdt').run(10)
