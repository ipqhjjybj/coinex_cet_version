# encoding: utf-8
import hmac
import hashlib
import requests
import sys
import time
import base64
import json
import urllib
from collections import OrderedDict


COINEX_MARKET_URL = "api.coinex.com"
COINEX_SPOT_HOST = "wss://socket.coinex.com/"                   # coinex_api

FUNCTIONCODE_GET_SYMBOS_COINEX = "get_symbols"
FUNCTIONCODE_GET_BALANCE_COINEX = "get_balance"
FUNCTIONCODE_POST_SEND_ORDERS_COINEX = "send_order"
FUNCTIONCODE_POST_CANCEL_ORDERS_COINEX = "cancel_order"
FUNCTIONCODE_GET_ORDER_INFO_COINEX = "order_info"
FUNCTIONCODE_GET_OPEN_ORDER_LIST_COINEX = "order_list"
FUNCTIONCODE_GET_CLOSE_ORDER_LIST_COINEX = "close_order_list"

'''
    ethusdt --> eth_usdt
    etcbtc  --> etc_btc
    ethusdt.HUOBI --> eth_usdt
    etcbtc.HUOBI  --> etc_btc
'''
def systemSymbolToVnSymbol(symbol):
    symbol = symbol.replace('_','')
    symbol = ((symbol.split('.'))[0]).lower()
    if 'usdt' in symbol:
        return symbol[:-4] + "_usdt"
    else:
        return symbol[:-3] + "_" + symbol[-3:]
'''
    ethusdt --> ETH_USDT
    etcbtc  --> ETC_BTC
    ethusdt.HUOBI --> ETH_USDT
    etcbtc.HUOBI  --> ETC_BTC
'''
def systemSymbolToVnSymbolUpper(symbol):
    return systemSymbolToVnSymbol(symbol).upper()

'''
    etc_btc  --> etcbtc
    eth_usdt --> ethusdt
'''
def VnSymbolToSystemSymbol(symbol):
    symbol = (symbol.split('.'))[0]
    return (''.join(symbol.split('_'))).lower()


'''
    etc_btc  --> ETCBTC
    eth_usdt --> ETHUSDT
'''
def VnSymbolToSystemSymbolUpper(symbol):
    return VnSymbolToSystemSymbol(symbol).upper()

'''
'''
class CoinexApi():
    __headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36'
    }

    base_url = "api.coinex.com"

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.accessKey = ''
        self.secretKey = ''

        self.headers = self.__headers

    #----------------------------------------------------------------------
    def auth( self, _apiKey , _secretKey):
        self.accessKey = _apiKey
        self.secretKey = _secretKey

    #各种请求,获取数据方式
    #----------------------------------------------------------------------
    def http_get_request(self, url , resource, params, add_to_headers=None):
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
        }
        if add_to_headers:
            headers.update(add_to_headers)
        try:
            # print url , resource
            conn = httplib.HTTPSConnection(url, timeout=10)
            params = urllib.urlencode(params)
            conn.request("GET", resource + '?' + params)
            response = conn.getresponse()
            data = response.read().decode('utf-8')
            return json.loads(data) 
        except Exception,ex:
            print("httpGet failed, detail is:%s" %ex)
            return {"status":"fail","message":ex ,"code":"ch6"}

    #----------------------------------------------------------------------
    def request(self, method, url, params={}, data='', json_params={}):
        method = method.upper()
        try:
            if method == 'GET':
                self.set_authorization(params)
                result = requests.request('GET', url, params=params, headers=self.headers)
            elif method == "POST":
                if data:
                    json_params.update(complex_json.loads(data))
                self.set_authorization(json_params)

                result = requests.request(method, url, json=json_params, headers=self.headers)
            elif method == "DELETE":
                self.set_authorization(json_params)
                tempParams = urllib.urlencode(json_params) if json_params else '' 
                real_url = url + "?" + tempParams
                result = requests.request('DELETE', real_url,  headers=self.headers)
            else:
                print "Error in vncoinex.request , error method %s" % (str(method))

            if result.status_code == 200:
                return result.json()
            else:
                print "request failed , response is %s" % (str(result.status_code))
                return result.json()

        except Exception , ex:
            print("request failed, detail is:%s" %ex)
            return {"status":"fail","message":ex ,"code":"ch7"}

    #----------------------------------------------------------------------
    def get_sign(self, params):
        sort_params = sorted(params)
        data = []
        for item in sort_params:
            data.append(item + '=' + str(params[item]))
        str_params = "{0}&secret_key={1}".format('&'.join(data), self.secretKey)
        token = hashlib.md5(str_params).hexdigest().upper()
        return token

    #----------------------------------------------------------------------
    def set_authorization(self, params):
        params['access_id'] = self.accessKey
        params['tonce'] = int(time.time()*1000)
        self.headers['AUTHORIZATION'] = self.get_sign(params )

    #----------------------------------------------------------------------
    def processRequest(self, url , method , kwargs ):
        try:
            data = None
            if method in [FUNCTIONCODE_GET_SYMBOS_COINEX]:
                data = self.http_get_request( COINEX_MARKET_URL ,resource = url , params = kwargs )
            elif method in [FUNCTIONCODE_GET_BALANCE_COINEX  , FUNCTIONCODE_GET_ORDER_INFO_COINEX , FUNCTIONCODE_GET_OPEN_ORDER_LIST_COINEX , FUNCTIONCODE_GET_CLOSE_ORDER_LIST_COINEX]:
                real_url = "https://" + COINEX_MARKET_URL + url 
                data = self.request( "GET" , real_url , params = kwargs)
            elif method in [FUNCTIONCODE_POST_SEND_ORDERS_COINEX ]:
                real_url = "https://" + COINEX_MARKET_URL + url 
                data = self.request( "POST" , real_url , json_params = kwargs )
            elif method in [FUNCTIONCODE_POST_CANCEL_ORDERS_COINEX]:
                real_url = "https://" + COINEX_MARKET_URL + url 
                data = self.request( "DELETE" , real_url , json_params = kwargs )
            return data
        except Exception,ex:
            print "Error in processRequest" , ex
        return None

    '''
    获得所有交易对
    '''
    #----------------------------------------------------------------------
    def get_symbols(self):
        print(u'vncoinex.get_symbols')
        kwargs = {}
        return self.processRequest( '/v1/market/list' , FUNCTIONCODE_GET_SYMBOS_COINEX  , kwargs = kwargs )

    '''
    {u'message': u'Ok', u'code': 0, u'data': {u'NEO': {u'available': u'0', u'frozen'
: u'0'}, u'BCH': {u'available': u'0', u'frozen': u'0'}, u'DASH': {u'available':
u'0', u'frozen': u'0'}, u'EOS': {u'available': u'0', u'frozen': u'0'}, u'ETC': {
u'available': u'0', u'frozen': u'0'}, u'USCB': {u'available': u'0', u'frozen': u
'0'}, u'ETH': {u'available': u'0', u'frozen': u'0'}, u'QTUM': {u'available': u'0
', u'frozen': u'0'}, u'CET': {u'available': u'5236.00000065', u'frozen': u'0'},
u'ZEC': {u'available': u'0', u'frozen': u'0'}, u'USHA': {u'available': u'0', u'f
rozen': u'0'}, u'XMC': {u'available': u'0', u'frozen': u'0'}, u'LTC': {u'availab
le': u'0', u'frozen': u'0'}, u'BTM': {u'available': u'0', u'frozen': u'0'}, u'VE
N': {u'available': u'0', u'frozen': u'0'}, u'USDT': {u'available': u'0', u'froze
n': u'0'}, u'XMR': {u'available': u'0', u'frozen': u'0'}, u'USCA': {u'available'
: u'0', u'frozen': u'0'}, u'USHB': {u'available': u'0', u'frozen': u'0'}, u'BTV'
: {u'available': u'0', u'frozen': u'0'}, u'OMG': {u'available': u'0', u'frozen':
 u'0'}, u'DOGE': {u'available': u'0.00002131', u'frozen': u'0'}, u'BTC': {u'avai
lable': u'0', u'frozen': u'0'}, u'SC': {u'available': u'0', u'frozen': u'0'}, u'
CDY': {u'available': u'0', u'frozen': u'0'}}}
    '''
    #----------------------------------------------------------------------
    def get_balance(self):
        # print(u'vncoinex.get_balance')
        kwargs = {}
        return self.processRequest( "/v1/balance/" , FUNCTIONCODE_GET_BALANCE_COINEX  , kwargs = kwargs )

    #----------------------------------------------------------------------
    def spotTrade(self, symbol , u_type ,amount,  price ):
        print(u'vncoinex.spotTrade symbol:{},type:{},amount:{},price:{},'.format(symbol , u_type , amount , price))
        try:
            kwargs = {
                "amount": float(amount),
                "price": float(price),
                "type": u_type,
                "market": VnSymbolToSystemSymbolUpper(symbol)
            }
            return self.processRequest( "/v1/order/limit" , FUNCTIONCODE_POST_SEND_ORDERS_COINEX  , kwargs = kwargs )
        except Exception,ex:
            print ex
            return None

    #----------------------------------------------------------------------
    def getOrder(self, symbol , order_id):
        # print(u'vncoinex.getOrder %s' % (str(order_id)))
        kwargs = {
            "id": str(order_id),
            "market": VnSymbolToSystemSymbolUpper(symbol),
        }
        url = "/v1/order/"
        return self.processRequest(url , FUNCTIONCODE_GET_ORDER_INFO_COINEX  , kwargs = kwargs )

    #----------------------------------------------------------------------
    def listOpenOrders(self , symbol , page = 1 , limit = 100):
        # print(u'vncoinex.listOpenOrders symbol:{}, page:{}, limit:{}'.format(symbol ,page , limit))
        kwargs = {
            "market": VnSymbolToSystemSymbolUpper(symbol),
            "page": str(page),
            "limit": str(limit)
        }
        url = "/v1/order/pending"
        return self.processRequest( url , FUNCTIONCODE_GET_OPEN_ORDER_LIST_COINEX  , kwargs = kwargs )

    # 查询已经执行完的单子
    #----------------------------------------------------------------------
    def listCloseOrders(self, symbol , page = 1 , limit = 100):
        print(u'vncoinex.listCloseOrders symbol:{}, page:{}, limit:{}'.format(symbol ,page , limit))
        kwargs = {
            "market": VnSymbolToSystemSymbolUpper(symbol),
            "page": str(page),
            "limit": str(limit)
        }
        url = "/v1/order/finished"
        return self.processRequest( url , FUNCTIONCODE_GET_CLOSE_ORDER_LIST_COINEX , kwargs = kwargs )

    # 撤销订单
    #----------------------------------------------------------------------
    def cancel_order(self , symbol , order_id):
        print(u'vncoinex.cancel_order %s' % (str(order_id)))
        kwargs = {
            "market": VnSymbolToSystemSymbolUpper(symbol),
            "id": str(order_id)
        }
        url = "/v1/order/pending"
        return self.processRequest(url , FUNCTIONCODE_POST_CANCEL_ORDERS_COINEX  , kwargs = kwargs )

    # getTicker()
    # https://api.coinex.com/v1/market/kline?market=btcbch&type=1min
    '''
    {u'message': u'Ok', u'code': 0, u'data': [[1529827200, u'676.94', u'678.1', u'68
2.83', u'667.66', u'165.75424067'], [1529830800, u'678.87', u'683.92', u'688.58'
, u'676.98', u'196.45822647']]}
    '''
    #----------------------------------------------------------------------
    def getTicker(self , symbol):
        print(u'vncoinex.getTicker %s' % (str(symbol)))
        url = "https://"+ "api.coinex.com/v1/market/kline?market=%s&type=1hour&limit=2" % (symbol)

        data = self.request( "GET" , url , params = {})
        return data

    '''
    {u'message': u'Ok', u'code': 0, u'data': {u'bids': [[u'739.12', u'26.378'], [u'7
    37.09', u'2.6378'], [u'732.74', u'0.531'], [u'732.73', u'53.94941231'], [u'728.4
    1', u'26.378'], [u'700.01', u'0.76'], [u'700', u'5.1'], [u'697.99', u'13.32'], [
    u'670', u'0.300502'], [u'666', u'10'], [u'659.68', u'0.001811'], [u'659.3', u'0.
    00121'], [u'659.18', u'0.00167'], [u'656.48', u'0.00107'], [u'654.51', u'0.00581
    6'], [u'654', u'0.1'], [u'653.39', u'22.92322686'], [u'652.79', u'5'], [u'634',
    u'8'], [u'632.09', u'3']], u'asks': [[u'743', u'0.37368102'], [u'746.98', u'0.46
    783384'], [u'746.99', u'6.98589774'], [u'775.99', u'2.72'], [u'776', u'0.9826963
    7'], [u'781.02', u'0.279'], [u'781.03', u'0.23520778'], [u'781.04', u'1'], [u'78
    1.51', u'0.001'], [u'789', u'0.17813361'], [u'799.99', u'44.2882062'], [u'800',
    u'5.00361936'], [u'834', u'0.03638055'], [u'850', u'0.00928891'], [u'852', u'0.2
    6937944'], [u'853', u'1'], [u'882', u'5'], [u'885', u'5'], [u'889', u'5'], [u'89
    5', u'0.00523924']]}}
    '''
    #----------------------------------------------------------------------
    def getDepth(self, symbol , depth = 20):
        print(u'vncoinex.getDepth %s' % (str(symbol)))
        url = "https://api.coinex.com/v1/market/depth?market=%s&limit=%s&merge=0" % (symbol , str(depth))

        data = self.request( "GET" , url  , params = {})
        return data

    '''
    {u'message': u'Ok', u'code': 0, u'data': {u'difficulty': u'50000', u'prediction'
: u'0'}}
    '''
    #----------------------------------------------------------------------
    def getMiningDifficulty(self):
        print(u'vncoinex.getMiningDifficulty' )
        url = "https://api.coinex.com/v1/order/mining/difficulty"
        data = self.request( "GET" , url  , params = {})
        return data