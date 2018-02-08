
def timestamp():
    return int(time.time())

class Order():
    ORDER_PRE_OPEN = 0
    ORDER_OPENED = 1
    ORDER_FILLED = 2
    ORDER_PRE_CANCLE = 3
    ORDER_CANCLED = 3
    ORDER_BUY_LIMIT = 0
    ORDER_SELL_LIMIT = 1
    def __init__(self, price, amount, direct):
        self.__price = price
        self.__amount = amount
        self.__filledAmount = 0
        self.__filledCash = 0
        self.__filledFee = 0
        self.__status = ORDER_PRE_OPEN
        self.__direct = direct
    def getPrice(self):
        return self.__price
    def getAmount(self):
        return self.__amount
    def getAmountFilled(self):
        return self.__filledAmount
    def getCashFilled(self):
        return self.__filledCash
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

class OrderBook():
    ORDERBOOK_PRE_OPEN = 0
    ORDERBOOK_OPENED = 1
    ORDERBOOK_PRE_CANCLE = 2
    ORDERBOOK_CANCLED = 3
    ORDERBOOK_FINISHED = 4
    def __init__(self, symbol, pricePrecision, amountPrecision):
        self.__buyOrder = None
        self.__sellOrders = []
        self.__status = ORDERBOOK_PRE_OPEN
    def getBuyAmount(self):
        return self.__buyOrder.getAmount(), self.__buyOrder.getAmountFilled()
    def getSellAmount(self):
        sellAmount = 0
        sellAmountFilled = 0
        for sellOrder in self.__sellOrders:
            sellAmountFilled += sellOrder.getAmountFilled()
            if sellOrder.getStatus() == Order.ORDER_OPENED:
                sellAmount += sellOrder.getAmount()
            else
                sellAmount += sellOrder.getAmountFilled()
        return sellAmount,sellAmountFilled
    def getBuyOrder(self):
        return self.__buyOrder
    def getSellOrders(self):
        return self.__sellOrders
    def updateOrders(orderInfo):
        if orderInfo.isBuy():
            


