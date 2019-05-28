# Automated Trading

from oandapyV20.endpoints.pricing import PricingStream
import oandapyV20.endpoints.orders as orders
from oandapyV20.contrib.requests import MarketOrderRequest
from oandapyV20.exceptions import V20Error, StreamTerminated
import numpy as np
import pandas as pd
import datetime
import configparser
import json
from oandapyV20 import API
import oandapyV20.endpoints.trades as trades

config = configparser.ConfigParser()
config.read('oanda.cfg')

client = API(access_token=config['oanda']['access_token'])


class MomentumTrader(PricingStream): # Create Class that will inherit a class from the API in order to display live prices
    def __init__(self, mashort, malong,  *args, **kwargs):
        PricingStream.__init__(self, *args, **kwargs)
        self.ticks = 0
        self.position = 0
        self.df = pd.DataFrame()
        self.mashort = mashort
        self.malong = malong
        self.units = 1
        self.connected = False
        self.client = API(access_token=config['oanda']['access_token'])
    def create_order(self, units): # Creating the order for our account
        order = orders.OrderCreate(accountID=config['oanda']['account_id'], data=MarketOrderRequest(instrument="DE30_EUR", units=units).data)
        response = self.client.request(order)
        print('\t', response)
    def on_success(self, data): # Implementing the strategy that will trigger orders
        self.ticks += 1
        print("ticks=",self.ticks)
        self.df = self.df.append(pd.DataFrame([{'time': data['time'],'closeoutAsk':data['closeoutAsk']}],
                                 index=[data["time"]]))

        self.df.index = pd.DatetimeIndex(self.df["time"])

        self.df['closeoutAsk'] = pd.to_numeric(self.df["closeoutAsk"],errors='ignore')

        dfr = self.df.resample('5s').last().bfill()

        # Strategy

        signals = pd.DataFrame(index=dfr.index)
        signals['indication'] = 0.0

        signals['MovingA1'] = dfr['closeoutAsk'].rolling(window = self.mashort).mean()
        signals['MovingA2'] = dfr['closeoutAsk'].rolling(window = self.malong).mean()

        signals['indication'] = np.where(signals['MovingA1'] > signals['MovingA2'], 1.0, 0.0)
        MAd=self.malong-1

        signals['indication'] = signals['indication'][MAd:]
        signals['positions'] = signals['indication'].diff()
        signals['positions'] = signals['positions'].shift()

        # Orders given the signals

        print("position=",signals['positions'].iloc[-1])
        if signals['positions'].iloc[-1] == 1:
            print("go long")
            if self.position == 0:
                self.create_order(self.units)
            elif self.position == -1:
                self.create_order(self.units * 2)
            self.position = 1
        elif signals['positions'].iloc[-1] == -1:
            print("go short")
            if self.position == 0:
                self.create_order(-self.units)
            elif self.position == 1:
                self.create_order(-self.units * 2)
            self.position = -1
        if self.ticks == 300:
            print("close out the position")
            if self.position == 1:
                self.create_order(-self.units)
            elif self.position == -1:
                self.create_order(self.units)
            self.disconnect()
    def disconnect(self):
        self.connected=False
    def rates(self, account_id, instruments, **params):
        self.connected = True
        params = params or {}
        ignore_heartbeat = None
        if "ignore_heartbeat" in params:
            ignore_heartbeat = params['ignore_heartbeat']
        while self.connected:
            response = self.client.request(self)
            for tick in response:
                if not self.connected:
                    break
                if not (ignore_heartbeat and tick["type"]=="HEARTBEAT"):
                    print(tick)
                    self.on_success(tick)
#Executing the code


mt = MomentumTrader(mashort = 5, malong = 10, accountID=config['oanda']['account_id'],params={"instruments": "DE30_EUR"})
mt.rates(account_id=config['oanda']['account_id'], instruments="DE30_EUR", ignore_heartbeat=True)
