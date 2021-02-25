import broker_alice
import datetime
from datetime import date, datetime, timedelta
# from nsetools import Nse
import time
import threading
# nse = Nse()
import yfinance as yf

def wait_to_place_order(order_data, cl_timeframe, cl_buffer):
    i=0
    a='b'
    side = order_data['transaction_type']
    Current_Date = date.today()
    Next_Date = date.today() + timedelta(days=1)
    while True:
        current_time = datetime.now()
        target_time = current_time + (datetime.min - current_time) % timedelta(minutes=cl_timeframe)
        deltame = target_time - current_time
        del_secs = int(deltame.total_seconds())
        i+=1
        if del_secs <10 and a=='b' and side=='buy':
            a='c'
            symbol = order_data['symbol']
            ysymbol ="{0}{1}".format(symbol,".NS")
            data = yf.download(ysymbol, start=Current_Date, end=Next_Date)
            # quote = nse.get_quote(symbol)
            High = float(data['High'])
            buybuffer = ( 100 + cl_buffer )/100
            high = High * buybuffer
            dayhigh = round(0.05*round( high / 0.05 ), 2)
            new_price = {'price': dayhigh}
            new_trigger = {'trigger_price': dayhigh}
            order_data.update(new_price)
            order_data.update(new_trigger)
        elif del_secs <10 and a=='b' and side=='sell':
            a='c'
            symbol = order_data['symbol']
            ysymbol ="{0}{1}".format(symbol,".NS")
            data = yf.download(ysymbol, start=Current_Date, end=Next_Date)
            # quote = nse.get_quote(symbol)
            Low = float(data['Low'])
            sellbuffer = ( 100 - cl_buffer )/100
            low = Low * sellbuffer
            daylow = round(0.05*round( low / 0.05 ), 2)
            new_price = {'price': daylow}
            new_trigger = {'trigger_price': daylow}
            order_data.update(new_price)
            order_data.update(new_trigger)
        if del_secs <= 0:
            print(order_data)
            print(f"Order Place Time: { target_time }")
            broker_alice.alice_place_order_multi(order_data)
            break
        time.sleep(1)

def start_to_wait_to_place_order(order_data, cl_timeframe, cl_buffer):
    t = threading.Thread(target=wait_to_place_order, args=(order_data, cl_timeframe, cl_buffer))
    t.start()
    return "Order Processing"