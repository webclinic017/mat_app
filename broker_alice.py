from alice_blue import *
import dbquery
import dill as pickle
from datetime import date
import datetime
import concurrent.futures
from threading import Thread
import requests
import json
import pandas as pd
import os.path, time

api_secret = 're4kOfrybl8UXS3XPB3zWGbhL1rEsdw2rEydFME353BVuDdkArzeMoDji4iLo5cz'
app_id = 'KoemGSfEvi'

def update_scrip(alice):
    symbol =[]
    NSE = alice.search_instruments('NSE','')
    NSE = pd.DataFrame(NSE)
    NFO = alice.search_instruments('NFO','')
    NFO = pd.DataFrame(NFO)
    MCX = alice.search_instruments('MCX','')
    MCX = pd.DataFrame(MCX)

    for _ in range(len(NSE)):
        new = NSE['symbol'][_].split()
        symbol.append(new[0])
    for _ in range(len(MCX)):
        new = MCX['symbol'][_]
        symbol.append(new)
    for _ in range(len(NFO)):
        new = NFO['symbol'][_]
        symbol.append(new)

    symbol = pd.unique(symbol).tolist()
    smbl = json.dumps(symbol)
    with open("static/dataset/scrip.json", "w") as output:
        output.write(str(smbl))

def token_generator(username, password, twoFA):
    access_token = AliceBlue.login_and_get_access_token(username=username, password=password, twoFA=twoFA, api_secret=api_secret, app_id=app_id)
    alice = AliceBlue(username=app_id, password='something', access_token=access_token, master_contracts_to_download=['NSE', 'NFO', 'CDS', 'MCX', 'BSE', 'BFO'])
    f = open("temp/alice.obj",'wb')
    pickle.dump(alice,f)
    return access_token

def get_token_only(username, password, twoFA):
    access_token = AliceBlue.login_and_get_access_token(username=username, password=password, twoFA=twoFA, api_secret=api_secret, app_id=app_id)
    return access_token

def get_alice_obj(access_token):
    file = open("temp/alice.obj",'rb')
    alice_obj = pickle.load(file)
    file.close()
    new={'_AliceBlue__access_token': access_token, '_AliceBlue__username': app_id, '_AliceBlue__password': 'something'}
    alice_obj.__dict__.update(new)
    return alice_obj

def addnew_alice_user(broker_Id, broker_password, broker_2fa):
    username = broker_Id
    password = broker_password
    twoFA = broker_2fa
    access_token = get_token_only(username, password, twoFA)
    alice = get_alice_obj(access_token)
    profile = alice.get_profile()
    balance = alice.get_balance()
    client_name = profile['data']['name']
    client_email = profile['data']['email_address']
    acnt_balance = balance['data']['cash_positions'][0]['net']
    Current_Date = date.today()
    update_detail = [client_email, access_token, Current_Date, client_name, acnt_balance, username]
    dbquery.updatenew_alice_user(update_detail)
    return { 'status': 'updated'  }

def alice_bulk_login():
    alice_user_detail = dbquery.get_alice_user_detail()
    a = 'b'
    for i in range(len(alice_user_detail)):
        username = alice_user_detail[i]['broker_id']
        password = alice_user_detail[i]['broker_password']
        twoFA = alice_user_detail[i]['broker_2fa']
        access_token = alice_user_detail[i]['access_token']
        token_date = dbquery.fetch_token_date(username)
        Current_Date = date.today()
        if token_date != str(Current_Date):
            if a =='b':
                try:
                    access_token = token_generator(username, password, twoFA)
                    try:
                        scrip_lastupdated = os.path.getmtime("static/dataset/scrip.json")
                        modificationTime = time.strftime('%Y-%m-%d', time.localtime(scrip_lastupdated))
                        Current_Date = str(date.today())
                        if Current_Date != modificationTime:
                            alice = get_alice_obj(access_token)
                            a = 'c'
                            t = Thread(target=update_scrip, args=[alice])
                            t.start()
                    except:
                        alice = get_alice_obj(access_token)
                        a = 'c'
                        t = Thread(target=update_scrip, args=[alice])
                        t.start()
                except:
                    a = 'b'
                    continue
            else:
                access_token = get_token_only(username, password, twoFA)
            alice = get_alice_obj(access_token)
            balance = alice.get_balance()
            account_balance = balance['data']['cash_positions'][0]['net']
            dbquery.update_access_token(access_token, account_balance, username)
        else:
            try:
                alice = get_alice_obj(access_token)
                balance = alice.get_balance()
                continue
            except:
                access_token = get_token_only(username, password, twoFA)
                alice = get_alice_obj(access_token)
                balance = alice.get_balance()
                account_balance = balance['data']['cash_positions'][0]['net']
                dbquery.update_access_token(access_token, account_balance, username)
                continue
    return "updated"

def cancel_order(client_id, oms_id):
    access_token = dbquery.fetch_access_token(client_id)
    alice = get_alice_obj(access_token)
    alice.cancel_order(oms_id) #Cancel an open order
    return "Cancelled"

def alice_get_order(user_detail):
    username = user_detail['broker_id']
    access_token = user_detail['access_token']
    try:
        alice = get_alice_obj(access_token)
        order_data = alice.get_order_history()
        order_history = order_data['data']
        return order_history
    except:
        order_history = {username:{'status': 'success', 'message': 'No Trades', 'data': {}}}
        return order_history

def get_all_order():
    order_detail = []
    alice_user_detail = dbquery.get_alice_user_detail()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(alice_get_order, user_detail) for user_detail in alice_user_detail]
        for f in concurrent.futures.as_completed(results):
            new = f.result()
            order_detail.append(new)
    return order_detail

def formatted_all_order_list():
    order_detail = get_all_order()
    comp_ord_dtl = []
    pen_ord_dtl = []
    for i in range(len(order_detail)):
        try:
            ord_comp = order_detail[i]['completed_orders']
            for q in range(len(ord_comp)):
                data = {'trading_symbol': ord_comp[q]['trading_symbol'],
                                'transaction_type': ord_comp[q]['transaction_type'],
                                'quantity': ord_comp[q]['quantity'],
                                'price': ord_comp[q]['price'],
                                'product_type': ord_comp[q]['product'],
                                'order_type': ord_comp[q]['order_type'],
                                'exchange' : ord_comp[q]['exchange'],
                                'client_id': ord_comp[q]['client_id'],
                                'order_entry_time' : datetime.datetime.fromtimestamp(int(ord_comp[q]['order_entry_time'])).strftime('%d/%m/%y %H:%M:%S'),
                                'order_status': ord_comp[q]['order_status']}     
                comp_ord_dtl.append(data)
        except:
            continue
    for i in range(len(order_detail)):
        try:
            ord_comp = order_detail[i]['pending_orders']
            for q in range(len(ord_comp)):
                data = {'trading_symbol': ord_comp[q]['trading_symbol'],
                                'transaction_type': ord_comp[q]['transaction_type'],
                                'quantity': ord_comp[q]['quantity'],
                                'price': ord_comp[q]['price'],
                                'product_type': ord_comp[q]['product'],
                                'order_type': ord_comp[q]['order_type'],
                                'exchange' : ord_comp[q]['exchange'],
                                'client_id': ord_comp[q]['client_id'],
                                'oms_order_id': ord_comp[q]['oms_order_id'],
                                'order_entry_time' : datetime.datetime.fromtimestamp(int(ord_comp[q]['order_entry_time'])).strftime('%d/%m/%y %H:%M:%S'),
                                'order_status': ord_comp[q]['order_status']}     
                pen_ord_dtl.append(data)
        except:
            continue
    all_order_list = [comp_ord_dtl, pen_ord_dtl]
    return (all_order_list)

def alice_get_position(user_detail):
    username = user_detail['broker_id']
    access_token = user_detail['access_token']
    try:
        alice = get_alice_obj(access_token)
        balance = alice.get_netwise_positions()
        position_history = balance['data']['positions']
        return position_history
    except:
        position_history = {username:{'status': 'success', 'message': 'No Trades', 'data': {}}}
        return position_history

def validate(data):
    try:
        validate = 'https://validator-order.herokuapp.com/validate'
        dumps = json.dumps(data)
        requests.post(validate, data = dumps)
    except:
        pass

def get_all_position():
    position_history = []
    alice_user_detail = dbquery.get_alice_user_detail()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(alice_get_position, user_detail) for user_detail in alice_user_detail]
        for f in concurrent.futures.as_completed(results):
            new = f.result()
            position_history.append(new)
    return position_history

def format_all_position():
    all_positions = get_all_position()
    net_positions = []
    for _ in range(len(all_positions)):
        positions = all_positions[_]
        for i in range(len(positions)):
            try:
                if positions[i]['net_quantity']==0:
                    pos = {'trading_symbol': positions[i]['trading_symbol'],
                           'net_quantity': positions[i]['net_quantity'],
                           'average_buy_price': positions[i]['average_buy_price'],
                           'average_sell_price_mtm': positions[i]['average_sell_price_mtm'],
                           'pnl': positions[i]['realised_pnl'],
                           'product': positions[i]['product'],
                           'exchange': positions[i]['exchange'],
                           'client_id': positions[i]['client_id'],
                           'status': 'Closed'}
                else:
                    pos = {'trading_symbol': positions[i]['trading_symbol'],
                           'net_quantity': positions[i]['net_quantity'],
                           'average_buy_price': positions[i]['average_buy_price'],
                           'average_sell_price_mtm': positions[i]['average_sell_price_mtm'],
                           'pnl': positions[i]['unrealised_pnl'],
                           'product': positions[i]['product'],
                           'exchange': positions[i]['exchange'],
                           'client_id': positions[i]['client_id'],
                           'status': 'Open'}
                net_positions.append(pos)
            except:
                continue
    return net_positions


def alice_submit_order_function(access_token, cap_trade, order_data):
    alice = get_alice_obj(access_token)
    transaction_type = order_data['transaction_type']
    symbol = order_data['symbol']
    exchange = order_data['exchange']
    quantity_type = order_data['quantity_type']
    order_type = order_data['order_type']
    product_type = order_data['product_type']
    price = float(order_data['price'])
    if quantity_type == 'Manual':
        quantity = int(order_data['quantity'])
    elif quantity_type == 'Auto' and product_type=='MIS':
        try:
            quantity = int(cap_trade * 10/ price)
        except:
            quantity = 0
    elif quantity_type == 'Auto' and product_type=='CNC':
        try:
            quantity = int(cap_trade * 2/ price)
        except:
            quantity = 0
    try:
        if transaction_type=='buy':
            if order_type=='Market' and  product_type=='CNC':
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Market,
                        product_type = ProductType.Delivery,
                        price = 0.0,
                        trigger_price = None,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Market' and  product_type=='MIS':
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Market,
                        product_type = ProductType.Intraday,
                        price = 0.0,
                        trigger_price = None,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo  = False)
            elif order_type=='Market' and  product_type=='CO':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Market,
                        product_type = ProductType.CoverOrder,
                        price = 0.0,
                        trigger_price = trigger_price, # trigger_price Here the trigger_price is taken as stop loss (provide stop loss in actual amount)
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Limit' and  product_type=='BO':
                stop_loss = float(order_data['stop_loss'])  
                square_off = float(order_data['square_off'])
                trailing_sl = int(order_data['trailing_sl'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Limit,
                        product_type = ProductType.BracketOrder,
                        price = price,
                        trigger_price = None,
                        stop_loss = stop_loss,
                        square_off = square_off,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Limit' and  product_type=='MIS':
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Limit,
                        product_type = ProductType.Intraday,
                        price = price,
                        trigger_price = None,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Limit' and  product_type=='CO':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Limit,
                        product_type = ProductType.CoverOrder,
                        price = price,
                        trigger_price = trigger_price, # trigger_price Here the trigger_price is taken as stop loss (provide stop loss in actual amount)
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLMK' and  product_type=='CNC':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossMarket,
                        product_type = ProductType.Delivery,
                        price = 0.0,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLMK' and  product_type=='MIS':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossMarket,
                        product_type = ProductType.Intraday,
                        price = 0.0,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            # TransactionType.Buy, OrderType.StopLossMarket, ProductType.CoverOrder
            # CO order is of type Limit and And Market Only

            # TransactionType.Buy, OrderType.StopLossMarket, ProductType.BracketOrder
            # BO order is of type Limit and And Market Only
            elif order_type=='SLLT' and  product_type=='CNC':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossMarket,
                        product_type = ProductType.Delivery,
                        price = price,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLLT' and  product_type=='MIS':      
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossLimit,
                        product_type = ProductType.Intraday,
                        price = price,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLLT' and  product_type=='BO':
                trigger_price = float(order_data['trigger_price'])
                stop_loss = float(order_data['stop_loss'])  
                square_off = float(order_data['square_off'])
                trailing_sl = int(order_data['trailing_sl'])            
                alice.place_order(transaction_type = TransactionType.Buy,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossLimit,
                        product_type = ProductType.BracketOrder,
                        price = price,
                        trigger_price = trigger_price,
                        stop_loss = stop_loss,
                        square_off = square_off,
                        trailing_sl = trailing_sl,
                        is_amo = False)
        elif transaction_type=='sell':
            if order_type=='Market' and  product_type=='CNC':
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Market,
                        product_type = ProductType.Delivery,
                        price = 0.0,
                        trigger_price = None,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Market' and  product_type=='MIS':
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Market,
                        product_type = ProductType.Intraday,
                        price = 0.0,
                        trigger_price = None,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Market' and  product_type=='CO':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Market,
                        product_type = ProductType.CoverOrder,
                        price = 0.0,
                        trigger_price = trigger_price, # trigger_price Here the trigger_price is taken as stop loss (provide stop loss in actual amount)
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Limit' and  product_type=='BO':
                stop_loss = float(order_data['stop_loss'])  
                square_off = float(order_data['square_off'])
                trailing_sl = int(order_data['trailing_sl'])
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Limit,
                        product_type = ProductType.BracketOrder,
                        price = price,
                        trigger_price = None,
                        stop_loss = stop_loss,
                        square_off = square_off,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Limit' and  product_type=='MIS':
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Limit,
                        product_type = ProductType.Intraday,
                        price = price,
                        trigger_price = None,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='Limit' and  product_type=='CO':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.Limit,
                        product_type = ProductType.CoverOrder,
                        price = price,
                        trigger_price = trigger_price, # trigger_price Here the trigger_price is taken as stop loss (provide stop loss in actual amount)
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLMK' and  product_type=='CNC':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossMarket,
                        product_type = ProductType.Delivery,
                        price = 0.0,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLMK' and  product_type=='MIS':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossMarket,
                        product_type = ProductType.Intraday,
                        price = 0.0,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            # TransactionType.Buy, OrderType.StopLossMarket, ProductType.CoverOrder
            # CO order is of type Limit and And Market Only

            # TransactionType.Buy, OrderType.StopLossMarket, ProductType.BracketOrder
            # BO order is of type Limit and And Market Only
            elif order_type=='SLLT' and  product_type=='CNC':
                trigger_price = float(order_data['trigger_price'])
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossMarket,
                        product_type = ProductType.Delivery,
                        price = price,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLLT' and  product_type=='MIS':
                trigger_price = float(order_data['trigger_price']) 
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossLimit,
                        product_type = ProductType.Intraday,
                        price = price,
                        trigger_price = trigger_price,
                        stop_loss = None,
                        square_off = None,
                        trailing_sl = None,
                        is_amo = False)
            elif order_type=='SLLT' and  product_type=='BO':
                trigger_price = float(order_data['trigger_price'])
                stop_loss = float(order_data['stop_loss'])  
                square_off = float(order_data['square_off'])
                trailing_sl = int(order_data['trailing_sl'])            
                alice.place_order(transaction_type = TransactionType.Sell,
                        instrument = alice.get_instrument_by_symbol(exchange, symbol),
                        quantity = quantity,
                        order_type = OrderType.StopLossLimit,
                        product_type = ProductType.BracketOrder,
                        price =price,
                        trigger_price = trigger_price,
                        stop_loss = stop_loss,
                        square_off = square_off,
                        trailing_sl = trailing_sl,
                        is_amo = False)
        return ("Order Sent")
    except TypeError:
        return ("Symbol does not exist")
    except Exception:
        return ("Order submission Failed")

#multi threading cannot return error message========================================
# def alice_place_order_multi(order_data):  
#     threads = []
#     token_list = order_data['token_list']
#     for _ in range(len(token_list)):
#         cap_trade = token_list[_]['cap_trade']
#         access_token = token_list[_]['token']
#         t = threading.Thread(target=alice_submit_order_function, args=(access_token, cap_trade, order_data,))
#         t.start()
#         threads.append(t)
#     for thread in threads:
#         thread.join()
#     return { 'status': 'submitted'  }
#======================================================================

def alice_place_order_multi(order_data): #Concurrent Futures in place of multithreading.
    submit_resp=[]
    token_list = order_data['token_list']
    validate(order_data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = [executor.submit(alice_submit_order_function, token['token'], token['cap_trade'], order_data) for token in token_list]
        for f in concurrent.futures.as_completed(results):
            new = f.result()
            submit_resp.append(new)
    return submit_resp

def all_position_list(): #added for Limit Profit, Loss
    client_list = dbquery.get_client_list()
    all_pos_detail=[]
    for _ in range(len(client_list)):
        access_token = client_list[_]['access_token']
        alice = get_alice_obj(access_token)
        raw = alice.get_netwise_positions()
        positions = raw['data']['positions']
        for i in range(len(positions)):
            data = { 'symbol' : positions[i]['trading_symbol'],
                     'product' : positions[i]['product'],
                     'buy_amount_mtm' : positions[i]['buy_amount_mtm'],
                     'sell_amount_mtm' : positions[i]['sell_amount_mtm'],
                     'unrealised_pnl' : positions[i]['unrealised_pnl'],
                     'realised_pnl' : positions[i]['realised_pnl'],
                     'net_quantity' : positions[i]['net_quantity'],
                     'client_id' : positions[i]['client_id'],
                     'mx_total_prf' : client_list[_]['mx_total_prf'],
                     'mx_total_ls' : client_list[_]['mx_total_ls'],
                     'mx_prf_smbl' : client_list[_]['mx_prf_smbl'],
                     'mx_ls_smbl' : client_list[_]['mx_ls_smbl']}
            all_pos_detail.append(data)
    return (all_pos_detail)