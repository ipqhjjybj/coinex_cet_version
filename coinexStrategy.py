# encoding: utf-8

import sys
import hmac
import hashlib
import requests
import sys
import time
import base64
import json
from collections import OrderedDict

from concurrent import futures

from coinex_api import CoinexApi
from time import sleep

from datetime import datetime

# 18304011249 账号
accessKey = 'your apiKey'
secretyKey = 'your secretkey'



log_file = "log.log"

log_file = open(log_file , "w")


'''
手续费计算器
'''
class FeeStrategyQuery(object):
    '''
    coinex策略
    '''
    #----------------------------------------------------------------------
    def __init__(self, coinex_obj , symbol):
        self.use_obj = coinex_obj
        self.symbol = symbol

        self.cache_key_orders = set([])
        self.cache_time_orders = {}

    #----------------------------------------------------------------------
    def generateDateTime(self , s):
        """生成时间"""
        dt = datetime.fromtimestamp(float(s))
        time = dt.strftime("%H:%M:%S")
        date = dt.strftime("%Y-%m-%d")
        return dt , date, time

    #----------------------------------------------------------------------
    def getKeyStr(self , dic_info):
        arr = [dic_info["type"] , dic_info["market"] , dic_info["id"] , dic_info["create_time"]]
        arr = [str(x) for x in arr]

        key_str = ','.join(arr)

        return key_str

    #----------------------------------------------------------------------
    def internetQuery(self ):
        data = self.use_obj.listCloseOrders( self.symbol , page = 1 , limit = 100)
        if str(data["code"]) == "0":
            loop_data = data["data"]["data"]
            for dic in loop_data:
                if dic["status"] == "done" and dic["market"].lower() == self.symbol.lower():
                    key_u = self.getKeyStr( dic)
                    dt , date, time = self.generateDateTime( dic["create_time"])
                    date_str = date + "_" + time[:2]

                    if key_u not in self.cache_key_orders:
                        self.cache_key_orders.add(key_u)

                        if date_str in self.cache_time_orders.keys():
                            self.cache_time_orders[date_str].append( dic )
                        else:
                            self.cache_time_orders[date_str] = [dic]

    #----------------------------------------------------------------------
    def getNowDateWork(self):
        dt = datetime.now()
        date = dt.strftime("%Y-%m-%d")
        time = dt.strftime("%H:%M:%S")

        date_str = date + "_" + time[:2]

        return date_str

    #----------------------------------------------------------------------
    def clearNotInNowDate(self):
        all_keys = self.cache_time_orders.keys()
        now_date = self.getNowDateWork()
        for key in all_keys:
            if key != now_date and key in self.cache_time_orders.keys():
                #### debug!!
                time_dic_list = self.cache_time_orders[key]
                for dic in time_dic_list:
                    key_u = self.getKeyStr( dic)
                    self.cache_key_orders.remove( key_u) 
                #####
                del self.cache_time_orders[key]

    #----------------------------------------------------------------------
    def getNowFee(self):
        all_cet_fee = 0
        now_str = self.getNowDateWork()
        if now_str in self.cache_time_orders.keys():
            dic_arr = self.cache_time_orders[now_str]

            for dic in dic_arr:
                all_cet_fee += float(dic["asset_fee"]) 

        return all_cet_fee


    #----------------------------------------------------------------------
    def debug_queryTotalFee(self):

        n_date = self.getNowDateWork()

        print n_date
        print self.cache_time_orders.keys()

        if n_date in self.cache_time_orders.keys():
            ll = self.cache_time_orders[n_date]

            print ll

        return self.getNowFee()
        
'''
Coinex Strategy
'''
class coinexStrategy(object):
    '''
    coinex策略
    '''
    def __init__(self, _accessKey , _secretKey , _init_vol , _shualiang_symbol, _hard_flag = False , _uselog = "log.log"):
        self.accessKey = _accessKey
        self.secretyKey = _secretKey

        self.logger = open(_uselog , "w")

        self.shualiang_symbol = _shualiang_symbol
        self.init_vol = _init_vol

        self.bef_hour = -1

        self.hard_flag = _hard_flag

        self.use_coinex_api = CoinexApi()
        self.use_coinex_api.auth( self.accessKey , self.secretyKey)

        self.now_difficulty = None
        self.predict_value = 0

        self.now_difficulty = self.getDifficulty()

        self.class_fee_get = FeeStrategyQuery(  self.use_coinex_api , symbol = self.shualiang_symbol)


    '''
    输出log日志
    '''
    #----------------------------------------------------------------------
    def writeLog(self, msg):
        global log_file
        print msg
        s = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " : " + msg + "\n"
        self.logger.write(s)
        self.logger.flush()

    '''
    获得难度值
    '''
    #----------------------------------------------------------------------
    def getDifficulty(self):
        diff_data = self.use_coinex_api.getMiningDifficulty()
        if str(diff_data["code"]) == "0":
            difficulty = diff_data["data"]["difficulty"]

            self.now_difficulty = float(difficulty)
            self.predict_value = float(diff_data["data"]["prediction"])

            return self.now_difficulty , self.predict_value
        else:
            self.writeLog( "get getMiningDifficulty failed! data:{}".format(diff_data))
            return self.now_difficulty

    '''
    '''
    #----------------------------------------------------------------------
    def runBuy( self, symbol, price, volume):
        return self.use_coinex_api.spotTrade( symbol = symbol , u_type = "buy" , amount = volume , price = price)
        # return coinApi.buy('btcusdt', price, volume)

    '''
    '''
    #----------------------------------------------------------------------
    def runSell( self, symbol , price , volume):
        return self.use_coinex_api.spotTrade( symbol = symbol , u_type = "sell" , amount = volume , price = price )

    '''
    '''

    '''
    发单函数
    '''
    def deal( self, symbol , price , bidPrice1 , askPrice1 , volume = 1  ):
        print self.runBuy( symbol , bidPrice1 , volume)
        print self.runSell( symbol , askPrice1 , volume)

    '''
    获得仓位
    '''
    #----------------------------------------------------------------------
    def getBalance(self):
        data = self.use_coinex_api.get_balance()

        btc_num = None
        usdt_num = None
        cet_num = None
        bch_num = None

        if str(data["code"]) == "0":
            info = data["data"]
            for currency in info.keys():
                use_key_pair = info[currency]
                currency = currency.lower()
                if currency == "btc":
                    btc_num = float(use_key_pair["available"]) + float(use_key_pair["frozen"])

                if currency == "usdt":
                    usdt_num = float(use_key_pair["available"]) + float(use_key_pair["frozen"])

                if currency == "cet":
                    cet_num = float(use_key_pair["available"]) + float(use_key_pair["frozen"])

                if currency == "bch":
                    bch_num = float(use_key_pair["available"]) + float(use_key_pair["frozen"])

            return btc_num , usdt_num , cet_num , bch_num

        else:
            self.writeLog( "Error in getBalance balance data:{}".format(data))
            return btc_num , usdt_num , cet_num , bch_num

    #----------------------------------------------------------------------
    def loadNowTradeList(self):
        self.writeLog( "now go to loadNowTradeList")
        self.class_fee_get.internetQuery()

        self.writeLog( "now go to clear other trade list")
        self.class_fee_get.clearNotInNowDate()


    #----------------------------------------------------------------------
    def getTotalCetFeiNowHour( self ):
        return self.class_fee_get.getNowFee()
        

    '''
    取中间值
    '''
    #----------------------------------------------------------------------
    def getMidPrice(self, symbol ):
        limitLowPrice = None
        limitHighPrice = None

        data = self.use_coinex_api.getDepth( symbol , depth = 20)
        if str(data["code"]) == "0":
            info = data["data"]

            bids_data = info["bids"]
            asks_data = info["asks"]

            bids_data = [(float(x[0]) , float(x[1])) for x in bids_data]
            asks_data = [(float(x[0]) , float(x[1])) for x in asks_data]
        
            llen_bids = len(bids_data)
            llen_asks = len(asks_data)

            sort_bids_data = sorted(bids_data , key=lambda price_pair: price_pair[0] )
            sort_asks_data = sorted(asks_data, key=lambda price_pair: price_pair[0] )

            sort_bids_data.reverse()

            len_sort_bids = len(sort_bids_data)
            len_sort_asks = len(sort_asks_data)

            accu_buy_volume = 0
            limitLowPrice = sort_bids_data[len_sort_bids-1][0]
            for i in range( len_sort_bids):
                accu_buy_volume += sort_bids_data[i][1]
                if accu_buy_volume > 0.3:
                    limitLowPrice = sort_bids_data[i][0]
                    break

            accu_sell_volume = 0
            limitHighPrice = sort_asks_data[len_sort_bids-1][0]
            for i in range( len_sort_asks):
                accu_sell_volume += sort_asks_data[i][1]
                if accu_sell_volume > 0.3:
                    limitHighPrice = sort_asks_data[i][0]
                    break

            bidPrice1, bidVolume1 = sort_bids_data[0]
            askPrice1, askVolume1 = sort_asks_data[0]

            midPrice = (bidPrice1 + askPrice1) / 2.0

            if symbol == "btcusdt":
                midPrice = round(midPrice , 2)

            return (midPrice , bidPrice1 , askPrice1 , limitLowPrice , limitHighPrice)
        else:
            return None , None , None , None , None


    '''
    取消所有 订单
    '''
    #----------------------------------------------------------------------
    def cancelAll(self, symbol ):
        print "cancelAll"

        cancel_order_nums = 3
        public_order_deal = CoinexApi()
        public_order_deal.auth( self.accessKey , self.secretyKey)

        all_orders = []
        
        data = public_order_deal.listOpenOrders( symbol = symbol )

        '''
        {u'message': u'Ok', u'code': 0, u'data': {u'count': 2, u'has_next': False, u'cur
    r_page': 1, u'data': [{u'status': u'not_deal', u'order_type': u'limit', u'price'
    : u'0.00100000', u'deal_fee': u'0', u'maker_fee_rate': u'0', u'amount': u'100',
    u'create_time': 1523953882, u'market': u'CETBCH', u'avg_price': u'0.00', u'deal_
    money': u'0', u'taker_fee_rate': u'0.001', u'type': u'sell', u'id': 121895881, u
    'deal_amount': u'0', u'left': u'100'}, {u'status': u'not_deal', u'order_type': u
    'limit', u'price': u'0.00100000', u'deal_fee': u'0', u'maker_fee_rate': u'0', u'
    amount': u'100', u'create_time': 1523953864, u'market': u'CETBCH', u'avg_price':
     u'0.00', u'deal_money': u'0', u'taker_fee_rate': u'0.001', u'type': u'sell', u'
    id': 121895545, u'deal_amount': u'0', u'left': u'100'}]}}
        '''
        if str(data["code"]) == "0":
            orders = data["data"]["data"]

            for use_order in orders:
                all_orders.append(use_order)

        if len(all_orders) > 0:        
            buy_order_array = []
            sell_order_array = []

            for use_order in all_orders:
                systemID = str(use_order["id"])
                status = use_order["status"]
                tradedVolume = float(use_order["deal_money"])
                totalVolume = float(use_order["amount"])
                price = float(use_order["price"])
                side = use_order["type"]

                if status in ["part_deal" , "not_deal" ]:
                    if side == "buy":
                        buy_order_array.append( [price , systemID])
                    else:
                        sell_order_array.append( [price , systemID])

            all_need_cancel = []
            if len(buy_order_array) > cancel_order_nums:
                sort_buy_arr = sorted(buy_order_array , key=lambda price_pair: price_pair[0] )
                sort_buy_arr.reverse()

                print "sort_buy_arr", sort_buy_arr

                for i in range(cancel_order_nums , len(sort_buy_arr)):
                    all_need_cancel.append( str(sort_buy_arr[i][1]) )
                    break

            if len(sell_order_array) > cancel_order_nums:
                sort_sell_arr = sorted(sell_order_array , key=lambda price_pair: price_pair[0] )

                print "sort_sell_arr", sort_sell_arr
                
                for i in range(cancel_order_nums , len(sell_order_array)):
                    all_need_cancel.append( str(sort_sell_arr[i][1]) )

                    break

            for systemID in all_need_cancel:
                try:
                    print public_order_deal.cancel_order( symbol ,systemID )
                    self.writeLog( "cancel order:{}".format(systemID))
                except Exception,ex:
                    print ex

        else:
            print "order_all is not "

    #----------------------------------------------------------------------
    def real_CancelAll(self, symbol ):
        print "cancelAll"

        public_order_deal = CoinexApi()
        public_order_deal.auth( self.accessKey , self.secretyKey)

        all_orders = []
        
        data = public_order_deal.listOpenOrders( symbol = symbol )

        if str(data["code"]) == "0":
            orders = data["data"]["data"]

            for use_order in orders:
                all_orders.append(use_order)

        if len(all_orders) > 0:        
            for use_order in all_orders:
                systemID = str(use_order["id"])
                status = use_order["status"]
                tradedVolume = float(use_order["deal_money"])
                totalVolume = float(use_order["amount"])
                price = float(use_order["price"])
                side = use_order["type"]

                if status in ["part_deal" , "not_deal" ]:
                    if side == "buy":
                        print public_order_deal.cancel_order( symbol ,systemID )
                        self.writeLog( "cancel order:{}".format(systemID))
                    else:
                        print public_order_deal.cancel_order( symbol ,systemID )
                        self.writeLog( "cancel order:{}".format(systemID))

        else:
            print "order_all is not "


    '''
    刷量策略
    '''
    #----------------------------------------------------------------------
    def run(self):
        count_time = 0
        flag = False

        btc_val , usdt_val , cet_val , bch_val = self.getBalance()
        midPrice , bidPrice1 , askPrice1 , limitLowPrice , limitHighPrice = self.getMidPrice( self.shualiang_symbol  )

        if usdt_val > btc_val * midPrice:
            flag = True
        else:
            flag = False

        self.loadNowTradeList( )
        need_cover_pianyi_liang = self.getTotalCetFeiNowHour()
        already_cover_pianyi_liang = 0

        self.writeLog( "init need_cover_pianyi_liang:{}".format(need_cover_pianyi_liang))

        self.now_difficulty , self.predict_value = self.getDifficulty()
        self.writeLog( "get new difficulty:{}  self.predict_value:{}".format( self.now_difficulty , self.predict_value) )

        midPrice_cetusdt , bidPrice1_cetusdt , askPrice1_cetusdt , limitLowPrice_cetusdt , limitHighPrice_cetusdt = self.getMidPrice( "cetusdt"  )
        hour_limit_cover_pianyi_liang = self.now_difficulty * 0.975

        while True:
            try:
                now_datetime = datetime.now()

                i_minute = int(now_datetime.strftime("%M") )
                i_secods = int(now_datetime.strftime("%S") )

                count_time += 1

                if cet_val == None or cet_val < 600:
                    self.writeLog( "cet_val is all used! < 600 or cet_val is None")
                    if count_time % 6 == 0:
                        btc_val , usdt_val , cet_val , bch_val = self.getBalance()
                        midPrice , bidPrice1 , askPrice1 , limitLowPrice , limitHighPrice = self.getMidPrice( self.shualiang_symbol  )

                        now_usdt = usdt_val + midPrice * btc_val
                        if self.shualiang_symbol == "bchusdt":
                            now_usdt = usdt_val + midPrice * bch_val

                    self.writeLog( "continue to run it!")
                    sleep(10)
                    continue

                midPrice , bidPrice1 , askPrice1 , limitLowPrice , limitHighPrice = self.getMidPrice( self.shualiang_symbol  )

                if midPrice != None:
                    if need_cover_pianyi_liang < hour_limit_cover_pianyi_liang and self.predict_value < self.now_difficulty * 0.99:
                        if flag == True:
                            print "askPrice1" , limitHighPrice - 0.01 ,  askPrice1 + 0.01
                            # bidPrice1 = bidPrice1 + 0.01
                            # askPrice1 = max(limitHighPrice - 0.01 , askPrice1 + 0.01)

                            bidPrice1 = bidPrice1 + 0.01
                            askPrice1 = askPrice1 + 0.01

                            midPrice = midPrice + 0.01
                        else:
                            print "bidPrice1" , limitLowPrice + 0.01 , bidPrice1 - 0.01
                            # bidPrice1 = min(limitLowPrice + 0.01 , bidPrice1 - 0.01)
                            # askPrice1 = askPrice1 - 0.01

                            bidPrice1 = bidPrice1 - 0.01
                            askPrice1 = askPrice1 - 0.01

                            midPrice = midPrice - 0.01

                        # self.deal( self.shualiang_symbol  , midPrice ,  bidPrice1 , askPrice1 , self.init_vol )

                        if 3 <= i_minute and i_minute <= 57:
                            self.deal( self.shualiang_symbol  , midPrice ,  midPrice , midPrice , self.init_vol )
                        else:
                            self.writeLog( "not in the trade minute i_minute:{}".format(i_minute))
                            self.real_CancelAll( self.shualiang_symbol)

                    else:
                        self.writeLog( "need_cover_pianyi_liang:{} < hour_limit_cover_pianyi_liang:{}".format(need_cover_pianyi_liang , hour_limit_cover_pianyi_liang))

                        self.writeLog( "now go to cancel all function")
                        self.real_CancelAll( self.shualiang_symbol )


                if count_time % 6 == 0:
                    self.cancelAll( self.shualiang_symbol )

                    self.now_difficulty , self.predict_value = self.getDifficulty()
                    self.writeLog( "get new difficulty:{}  self.predict_value:{}".format( self.now_difficulty , self.predict_value) )

                    btc_val , usdt_val , cet_val , bch_val = self.getBalance()
                    
                    midPrice_cetusdt , bidPrice1_cetusdt , askPrice1_cetusdt , limitLowPrice_cetusdt , limitHighPrice_cetusdt = self.getMidPrice( "cetusdt"  )

                    hour_limit_cover_pianyi_liang = self.now_difficulty * 0.975

                    now_usdt = usdt_val + midPrice * btc_val

                    now_msg = "now usdt_val:{} , cet_val:{} , btc_val:{} , bch_val:{}, now_usdt:{}".format(usdt_val ,cet_val ,  btc_val , bch_val, now_usdt )
                    self.writeLog(now_msg)

                    if self.hard_flag == False:
                        self.init_vol = round( now_usdt / midPrice / 10.0 , 3)

                    now_msg = "now self.init_vol is {}".format(self.init_vol)
                    self.writeLog(now_msg)

                    if usdt_val > btc_val * midPrice:
                        flag = True
                    else:
                        flag = False

                    self.writeLog( "now i_minute:{} , i_secods:{}".format( i_minute , i_secods))


                    # if count_time % 18 == 0:
                    self.loadNowTradeList( )
                    need_cover_pianyi_liang = self.getTotalCetFeiNowHour()

                    self.writeLog( "need_cover_pianyi_liang:{} ,already_cover_pianyi_liang:{} ,hour_limit_cover_pianyi_liang:{}".format(need_cover_pianyi_liang , already_cover_pianyi_liang ,hour_limit_cover_pianyi_liang))

                sleep(1)

            except Exception,ex:
                self.writeLog( "Error in running, ex:{}".format(ex))




if __name__ == '__main__':
    s = coinexStrategy( _accessKey = accessKey, _secretKey = secretyKey, _init_vol = 0.06 , _shualiang_symbol = "btcusdt" , _hard_flag = True , _uselog = "log.log")
    s.run()
