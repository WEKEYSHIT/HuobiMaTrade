from liveApi.TradeClientBase import *
from liveApi.liveUtils import *
from pyalgotrade.utils import dt
from liveApi import liveLogger

from hbsdk import ApiClient, ApiError

from ApiKey import API_KEY
from ApiKey import API_SECRET
hbClient = ApiClient(API_KEY, API_SECRET)
logger = liveLogger.getLiveLogger("hbClient")

def Str2float(func):
    def waper(*args, **kwargs):
        return float(func(*args, **kwargs))
    return waper

class hbOrderType():
    BuyLimit   = 'buy-limit'
    BuyMarket  = 'buy-market'
    SellLimit  = 'sell-limit'
    SellMarket = 'sell-market'

class hbOrderState():
    OrderFilled = 'filled'
    OrderCanceled = 'canceled'
    OrderSubmited = 'submitted'

class hbTradeOrder(TradeOrderBase):
    def __init__(self, obj):
        self.__obj = obj
        super(hbTradeOrder, self).__init__()

    def getId(self):
        return self.__obj.id
    def isBuy(self):
        return self.__obj.type in (hbOrderType.BuyLimit, hbOrderType.BuyMarket)
    def isSell(self):
        return not self.isBuy()
    @Str2float
    def getPrice(self):
        return self.__obj.price
    @Str2float
    def getAmount(self):
        return self.__obj.amount
    def getDateTime(self):
        return dt.timestamp_to_datetime(int(self.__obj['created-at'])/1000)

# GET /v1/order/orders/{order-id}/matchresults
class hbTradeUserTransaction(TradeUserTransactionBase):
    def __init__(self, obj):
        self.__obj = obj
    @Str2float
    def getBTC(self):
        return self.__obj['field-amount']
    @Str2float
    def getBTCUSD(self):
        #return self.__obj['field-cash-amount']
        return self.__obj['price']
    @Str2float
    def getFee(self):
        return self.__obj['field-fees']
    def getOrderId(self):
        return self.__obj['id']
    def isFilled(self):
        return self.__obj['state'] == hbOrderState.OrderFilled
    def getDateTime(self):
        return dt.timestamp_to_datetime(int(self.__obj['finished-at'])/1000)

class hbTradeAccountBalance(TradeAccountBalanceBase):
    def __init__(self, obj):
        self.__obj = obj
        
    def getUSDAvailable(self):
        return self.__obj['usdt']
    def getBTCAvailable(self):
        return self.__obj['coin']

class Coin():
    def __init__(self, coinInfo):
        self.__cash = coinInfo['quote-currency']
        self.__coin = coinInfo['base-currency']
        self.__cashPrecision = coinInfo['price-precision']
        self.__coinPrecision = coinInfo['amount-precision']
        self.__minAmount = coinInfo['minAmount']
        f = lambda x:round((10**(3-x))/2.0, x)
        #self.__minLoseAmount = max(self.__minAmount, f(self.__coinPrecision))
        self.__minLoseAmount = f(self.__coinPrecision)
    def getCashName(self):
        return self.__cash
    def getCoinName(self):
        return self.__coin
    def getMinAmount(self):
        return self.__minAmount
    def getMinLoseAmount(self):
        return self.__minLoseAmount
    def getSymbol(self):
        return self.__coin + self.__cash
    def getCashPrecision(self):
        return self.__cashPrecision
    def getCoinPrecision(self):
        return self.__coinPrecision

class hbCoin(Coin):
    def __init__(self, coinInfo):
        self.__client = hbClient
        baseCurrency = coinInfo['base-currency']
        quoteCurrency = coinInfo['quote-currency']
        symbol = baseCurrency + quoteCurrency
        amountPrecision = coinInfo['amount-precision']
        coinInfo['minAmount'] = hbTradeClient().getMinAmount(symbol, 10**-amountPrecision)
        Coin.__init__(self, coinInfo)

class hbSymbols():
    def __init__(self):
        self.__client = hbClient
        coinInfos = self.__client.mget('/v1/common/symbols')
        coinInfos = filter(lambda x:x['quote-currency'] == 'usdt', coinInfos)
        def f(d, x):
            d[x['base-currency']+x['quote-currency']] = x
            return d
        self.__coinInfo = reduce(f, coinInfos, {})
        self.__coins = {}
    def getCoin(self, symbol):
        if self.__coins.get(symbol) is None:
            self.__coins[symbol] = hbCoin(self.__coinInfo[symbol])
        return self.__coins[symbol]
    def getAllSymbol(self):
        return self.__coinInfo.keys()
    
class hbAccountBalance():
    def __init__(self, obj):
        self.__balancesTrade = {}
        self.__balancesFrozen = {}
        balancesList = obj.get('list')
        if balancesList is None:
            return
        for x in balancesList:
            if x.type == 'trade':
                self.__balancesTrade[x.currency] = float(x.balance)
            else:
                self.__balancesFrozen[x.currency] = float(x.balance)
    def getCoinTrade(self, coin):
        return self.__balancesTrade.get(coin, 0)
    def getCoinFrozen(self, coin):
        return self.__balancesFrozen.get(coin, 0)
    def getCoin(self, coin):
        return self.getCoinTrade(coin), self.getCoinFrozen(coin)

class hbTradeClient(TradeClientBase):
    def __init__(self):
        self.__client = hbClient
        self.__accountid = self.getAccountId()

    @tryForever
    def getAccountId(self):
        accs = self.__client.get('/v1/account/accounts')
        for x in accs:
            if x.type == 'spot' and x.state == 'working':
                return x.id
        raise Exception('no active account ID!')
        
    @tryForever
    def getAccountBalance(self):
        balances = self.__client.get('/v1/account/accounts/%s/balance' % self.__accountid)
        return hbAccountBalance(balances)

    @tryForever
    def cancelOrder(self, orderId):
        logger.info('cancelOrder:%s'%orderId)
        try:
            self.__client.post('/v1/order/orders/%s/submitcancel' % orderId)
        except:
            self.__checkOrderState(orderId, [hbOrderState.OrderCanceled, hbOrderState.OrderFilled])

    def buyLimit(self, symbol, limitPrice, quantity):
        logger.info('buyLimit: %s %s %s'%(symbol, limitPrice, quantity))
        orderInfo = self.__postOrder(symbol, limitPrice, quantity, hbOrderType.BuyLimit)
        return hbTradeOrder(orderInfo)

    def sellLimit(self, symbol, limitPrice, quantity):
        logger.info('sellLimit: %s %s %s'%(symbol, limitPrice, quantity))
        orderInfo = self.__postOrder(symbol, limitPrice, quantity, hbOrderType.SellLimit)
        return hbTradeOrder(orderInfo)

    @tryForever
    def getUserTransactions(self, ordersId):
        if len(ordersId):
            logger.info('getUserTransactions:%s'%ordersId)
        ret = []
        for oid in ordersId:
            orderInfo = self.__client.get('/v1/order/orders/%s' % oid)
            ret.append(hbTradeUserTransaction(orderInfo))
        return ret

    @tryForever
    def __postOrder(self, symbol, limitPrice, quantity, orderType):
        order_id = self.__client.post('/v1/order/orders', {
            'account-id': self.__accountid,
            'amount': quantity,
            'price': limitPrice,
            'symbol': symbol,
            'type': orderType,
            'source': 'api'
        })
        self.__activeOrder(order_id)
        while True:
            try:
                orderInfo = self.__checkOrderState(order_id, [hbOrderState.OrderSubmited, hbOrderState.OrderFilled])
                break
            except:
                continue
        return orderInfo

    def __checkOrderState(self, orderid, states):
        orderInfo = self.__client.get('/v1/order/orders/%s' % orderid)
        if orderInfo.state in states:
            return orderInfo
        raise Exception('wait state:%s => %s'%(orderInfo.state, states))

    @tryForever
    def __activeOrder(self, orderid):
        return self.__client.post('/v1/order/orders/%s/place' % orderid)
    @tryForever
    def getMinAmount(self, symbol, minAmount):
        try:
           order_id = self.__client.post('/v1/order/orders', {
                'account-id': self.__accountid,
                'amount': minAmount,
                'price': 1,
                'symbol': symbol,
                'type': hbOrderType.BuyLimit,
                'source': 'api'
           })
        except ApiError, e:
            msgs = e.message.split(':')
            if msgs[0] == "order-limitorder-amount-min-error" and len(msgs) == 3:
                strAmount = msgs[-1].split('`')[1]
                minAmount = float(strAmount)
        return minAmount
    @tryForever
    def getKLine(self, symbol, period, length = 1):
        klines = self.__client.mget('/market/history/kline', symbol=symbol, period='%dmin'%period, size=length)
        return [(k.id, k.open, k.high, k.low, k.close, k.vol) for k in klines]

