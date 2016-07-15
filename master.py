#!/usr/bin/env python3
__author__ = "ABerger"

from multiprocessing import Process, Queue
from time import sleep

from log import ModelLog
from compute import Signals, Compute
from positions import Positions, ExitPosition, PnL
from order import OrderHandler

import logging
logging.basicConfig(filename="/home/andrew/Projects/Logs/master.py.log")

class Initialize:
	def __init__(self, path_to_config):
		self.path_to_config = path_to_config

	def init_model(self):
		try:
			name, setting = self.get_config()
		except Exception as e:
			print("Failed to initialize:\n%s" % e)	
			return False
		return name, setting

	def get_config(self):
		params = open(self.path_to_config)
		params = params.read().replace("\n", ",").split(",")

		name = [x for x in params if params.index(x)%2==0]
		setting = [x for x in params if params.index(x)%2!=0]

		return name, setting
			
class Model:
	def __init__(self, path_to_config):

		self.initialize = Initialize(path_to_config)
		param = self.get_parameters()
	
		self.COUNT = param[0]
		self.LONGWIN = param[1]
		self.SHORTWIN = param[2]
		
		self.SYMBOL = param[3]
		
		self.QUANTITY = param[4]
		self.MAXPOS = param[5]
		
		self.MAXLOSS = param[6]
		self.MAXGAIN = param[7] 
		
		self.LIMIT = param[8]
		
		self.KUP = param[9]
		self.KDOWN = param[10]
		
		self.TREND_THRESH = param[11] 
		
		self.signal_queue = Queue()
		self.position_queue = Queue()
		
		#self.model_log().start()

	def __repr__(self):
		return "SYMBOL:%s\nCOUNT:%s\nMAXPOS:%s\n" % (
			self.SYMBOL, self.COUNT, self.MAXPOS)

	def get_parameters(self):
		if self.initialize:
	    		return self.initialize.init_model()[1]
		else:
	    		print("Warning: model not initialized")
		return False

	def model_log(self):
	    return ModelLog(self.SYMBOL,
	                    self.COUNT,
	                    self.LONGWIN,
	                    self.SHORTWIN)
	
	def signals(self):
	    return Signals(self.COUNT,
	                   self.SYMBOL,
	                   self.LONGWIN,
	                   self.SHORTWIN,
	                   "S5")
	
	def positions(self):
	    return Positions().checkPosition(self.SYMBOL)
	
	def kthresh_up_cross(self, chan, param):
	    """ Upper threshold signal (self.KUP) """
	    if (chan == 0) and (param > self.KUP):
	        return True
	    else:
	        return False
	
	def kthresh_down_cross(self, chan, param):
	    """ Lower threshold signal (self.KDOWN) """
	    if (chan == 0) and (param < self.KDOWN):
	        return True
	    else:
	        return False
	
	def stoch_upcross(self, K_to_D, params):
	    K, D = params
	    if (K_to_D  == -1) and  (K > D):
	        if (K < self.KDOWN):
	            return True
	    else:
	        return False
	
	def stoch_downcross(self, K_to_D, params):
	    K, D = params
	    if (K_to_D  == 1) and  (K < D):
	        if (K > self.KUP):
	            return True
	    else:
	        return False
	
	def close_out(self, tick, position, profit_loss):
	    close = ExitPosition().closePosition(position, profit_loss, tick)
	    self.model_log().exit(close._time, close.price, close.id, profit_loss)
	
	def risk_control(self):
	    while True:
	        tick = self.signal_queue.get()[2]
	        
	        position = self.positions()
	        self.position_queue.put(position.units)
	
	        if position.units != 0:
	            lower_limit = self.MAXLOSS*(position.units/10000)
	            upper_limit = self.MAXGAIN*(position.units/10000)
	
	            profit_loss = PnL(tick, position).get_pnl()
	
	            # close position max loss
	            if profit_loss < lower_limit:
	                self.close_out(tick, position, profit_loss)
	
	            # close position max gain
	            if profit_loss > upper_limit:
	                self.close_out(tick, position, profit_loss)
	
	def order_handler(self, tick, side):
	    trade = OrderHandler(self.SYMBOL, tick, side, self.QUANTITY).send_order()
	
	    if trade.reject:
	            self.model_log().reject(trade._time, trade.code, trade.message, tick)
	    else:
	            self.model_log().order(trade.time, trade.price, trade.id, "market", side)
	
	def signal_listen(self):
	    while True:
	        channel, K_to_D, tick = self.signal_queue.get()
	        K = tick.K
	        D = tick.D
	
	        print(str(tick))
	        position = self.position_queue.get()
	
	        if self.stoch_upcross(K_to_D, [K, D]):
	            self.order_handler(tick, "buy")
	
	        if self.stoch_downcross(K_to_D, [K, D]):
	            self.order_handler(tick, "sell")
	
	        writer = tick.write_tick()
	
	         # market is not trending
	        if tick.trend < self.TREND_THRESH:
	
	            if self.kthresh_up_cross(channel, K):
	                self.order_handler(tick, "sell")
	
	            elif self.kthresh_down_cross(channel, K):
	                self.order_handler(tick, "buy")
	
	         # market is trending
	        if tick.trend > self.TREND_THRESH:
	
	            if self.kthresh_up_cross(channel, K):
	                self.order_handler(tick, "buy")
	
	            elif self.kthresh_down_cross(channel, K):
	                self.order_handler(tick, "sell")
	
	def trade_model(self):
	    model = self.signals()
	
	    tick = model.tick
	    channel = model.channel
	    K_to_D = model.stoch
	
	    while True:
	        self.signal_queue.put([channel, K_to_D, tick])
	
	        sleep(5)
	
	        channel = model.channel
	        K_to_D = model.stoch
	
	        model = self.signals()
	        tick = model.tick
	
	def main(self):
	    model = Process(target=self.trade_model)
	    risk = Process(target=self.risk_control)
	    signal = Process(target=self.signal_listen)
	
	    model.start(); risk.start(); signal.start()
	    model.join(); risk.join(); signal.join()

if __name__ == "__main__":
	path_to_config = "/home/andrew/src/Oanda/.config/model.conf"
	Model(path_to_config).main()
