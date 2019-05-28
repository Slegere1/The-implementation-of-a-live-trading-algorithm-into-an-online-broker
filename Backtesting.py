
# Importing the API, packages and configuring the access to the account

import configparser
import json
from oandapyV20 import API
import oandapyV20.endpoints.trades as trades
import json
from oandapyV20 import API
import oandapyV20.endpoints.accounts as accounts
import pandas as pd
import datetime
from dateutil import parser
import oandapyV20.endpoints.instruments as instruments
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


config = configparser.ConfigParser()
config.read('oanda.cfg')

client = API(access_token=config['oanda']['access_token'])

# Get a list of all instruments


client = API(access_token=config['oanda']['access_token'])
r = accounts.AccountInstruments(accountID=config['oanda']['account_id'])
rv = client.request(r)
print(json.dumps(rv, indent=2))

# Extract Data from the Trading Website


params={"from": parser.parse("2017-12-11 18:00:00 EDT").strftime('%s'), # Need to adapt the format of time
        "to": parser.parse("2017-12-13 00:00:00 EDT").strftime('%s'),
        "granularity":'M1',
        "price":'A'}
instruments1 = input("Enter an asset name based on the list above: ");
r = instruments.InstrumentsCandles(instrument=instruments1,params=params)
data = client.request(r) # Pulling the information from Oanda
results= [{"time":x['time'],"closeAsk":float(x['ask']['c'])} for x in data['candles']]
df = pd.DataFrame(results).set_index('time')

df.index = pd.DatetimeIndex(df.index)



# Define function that will create a signal to buy or sell based on our strategy


def create_signals(data, MA1, MA2): # The short MA should be MA1 and long MA should be MA2
    signals = pd.DataFrame(index=data.index)
    signals['indication'] = 0.0

    signals['MovingA1'] = data.rolling(window = MA1).mean()
    signals['MovingA2'] = data.rolling(window = MA2).mean()

    signals['indication'] = np.where(signals['MovingA1'] > signals['MovingA2'], 1.0, 0.0) # base of our strategy
    MAd=MA2-1
    signals['indication'] = signals['indication'][MAd:]
    signals['positions'] = signals['indication'].diff()

    return signals.shift(1)

print('')
print('The investing strategy is based on two moving averages crossing each other. Precisely, it is when the shorter term MA cross the longer-term MA')
print('')
print('The shorter for both periods, the shorter the signals and horizon of trading. Classical couples are 5/25, 20/50, 50/200')

inputMA1 = int(input("Type in the short-term MA length (5,15,20,50..etc): "))
inputMA2 = int(input("Type in the long-term MA length (50,100,150,200..etc): "))

Cross=create_signals(df, inputMA1, inputMA2)


# Separate the buy and sell signals

Indexnames = Cross[Cross['positions'] == 0.0 ].index
cross = Cross.drop(Indexnames)

SIndexnames = cross[cross['positions'] == -1.0 ].index
Sellcross = cross.drop(SIndexnames)

BIndexnames = cross[cross['positions'] == 1.0 ].index
Buycross = cross.drop(BIndexnames)

# Format data before Plotting

Buycross.index = pd.to_datetime(Buycross.index, dayfirst=True)
Sellcross.index = pd.to_datetime(Sellcross.index, dayfirst=True)
PositionsBuy = Buycross.dropna()
PositionsSell = Sellcross.dropna()

df.index=pd.to_datetime(df.index, dayfirst=True)

# Representation of the strategy

start_date = df.index[0]
end_date = df.index[-1]

fig, ax = plt.subplots(figsize=(16,9))

ax.plot(df.index, df.loc[start_date:end_date, 'closeAsk'], label='Price')
ax.plot(df.index, Cross.loc[start_date:end_date, 'MovingA1'], label = 'MA1')

ax.plot(df.index, Cross.loc[start_date:end_date, 'MovingA2'], label = 'MA2')
ax.plot(PositionsSell.index, PositionsSell['MovingA1'], '^', markersize=10, color='m', label = 'Buy Signal')
ax.plot(PositionsBuy.index, PositionsBuy['MovingA1'], 'v', markersize=10, color='k', label = 'Sell Signal')

ax.legend(loc='best')
ax.set_ylabel('Price')

# Calculating Portfolio value if following the strategy or not

Cross['closeAsk'] = df['closeAsk']
Cross['Return'] = np.log(Cross['closeAsk'] / Cross['closeAsk'].shift(1))
Cross['Return1'] = Cross['indication']*Cross['Return']

Cross['Return1'].fillna(0, inplace = True)
Cross['Return'].fillna(0, inplace = True)

Valuation = list(Cross['Return1'])
Valuation2 = list(Cross['Return'])

def Value(inital, returntype):
    sum1 =[]
    sum = inital
    for i in returntype:
        sum = sum + i*sum
        sum1.append(sum)

    return sum1

Cross['Valuation'] = Value(1000, Valuation)
Cross['Valuation2'] = Value(1000, Valuation2)


# Plotting Portfolio values

fig, ax = plt.subplots(figsize=(16,9))

ax.plot(df.index, Cross.loc[start_date:end_date, 'Valuation'], label='Portfolio value')
ax.plot(df.index, Cross.loc[start_date:end_date, 'Valuation2'], label='Market value')

ax.legend(loc='best')
ax.set_ylabel('Price')

print('Initial Value:',Cross['Valuation'].iloc[0] )
print('Final value for buy and hold strategy:',Cross['Valuation2'].iloc[-1] )
print('Final value for our strategy:',Cross['Valuation'].iloc[-1] )
