
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
    def __init__(self, period, maxSize=60):
        self.__period = period
        self.__klines = DataSeries(maxSize)
        self.__ma = {}
    def update(self, k):
        if len(self.__klines) == 0:
            self.__klines.extern(k)
            return
        lastK = self.__klines[-1]
        k0, k1 = k[0], k[1]
        if k0.timestamp() == lastK.timestamp():
            self.__klines[-1] = k0
        else:
            self.__klines[-1] = k1
            self.__klines.append(k0)
        self.__updateMA()
    def __updateMA(self):
        for period in self.__klines:
            if len(self.__klines) >= period:
                self.__ma[period].append(sum(self.__klines[-period:])/float(period))
            
    def MA(self, period):
        if self.__ma.get(period) is None:
            ma = []
            if len(self.__klines) >= period:
                ma = [sum(self.__klines[-period:])/float(period)]
            self.__ma[period] = DataSeries(self.__klines.maxSize(), ma)
        return self.__ma[period]

class Strategy():
    def __init__(self):
        pass


book = OrderBook('ltcusdt', 2, 4, 0.001)
book.buyLimit(190.21, 0.8)
book.sellLimit(200, 0.8*0.998)
book.exitOrderBook(197.05)
book.updateOrders()
book.isFinished()

