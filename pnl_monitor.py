from alice_blue import *
import time
import dbquery
import broker_alice
from datetime import date, datetime, timedelta

def monitor_all_positions():
    client_list = dbquery.get_client_list()
    for _ in range(len(client_list)):
        client = client_list[_]['broker_id']
        access_token = client_list[_]['access_token']
        trade_status = client_list[_]['trade_status']
        max_prf = client_list[_]['mx_total_prf']
        max_lss = client_list[_]['mx_total_ls']
        alice = broker_alice.get_alice_obj(access_token)
        raw = alice.get_netwise_positions()
        positions = raw['data']['positions']
        total_profit = 0.0
        if len(positions)!=0 and trade_status !='off':
            order_details=[]
            for i in range(len(positions)):
                product = positions[i]['product']
                net_quantity = positions[i]['net_quantity']
                symbol = positions[i]['trading_symbol']
                exchange = positions[i]['exchange']
                buy_amount_mtm = positions[i]['buy_amount_mtm']
                sell_amount_mtm = positions[i]['sell_amount_mtm']
                symb_prf = client_list[_]['mx_prf_smbl']
                symd_loss = client_list[_]['mx_ls_smbl']
                pos_list = {'client':client, 'object':alice, 'product':product, 'quantity': net_quantity, 'symbol':symbol, 'exchange':exchange}
                order_details.append(pos_list)
                if product == 'MIS':
                    symbol_profit = float(positions[i]['unrealised_pnl'])+float(positions[i]['realised_pnl'])
                    total_profit += symbol_profit
                    # Check Open positions
                    if net_quantity > 0:
                        profit_trade = round((symbol_profit *100 ) / buy_amount_mtm, 2)
                        loss_trade = round((symbol_profit * -100 ) / buy_amount_mtm, 2)
                        if profit_trade >= symb_prf or loss_trade >= symd_loss:
                            print(f'Trigger Sell order to close for symbol : { symbol } { -1 * net_quantity }')
                            smbl = symbol.split("-")[0]
                            alice.place_order(transaction_type = TransactionType.Sell,
                                instrument = alice.get_instrument_by_symbol(exchange , smbl),
                                quantity = abs(net_quantity),
                                order_type = OrderType.Market,
                                product_type = ProductType.Intraday,
                                price = 0.0,
                                trigger_price = None, 
                                stop_loss = None,
                                square_off = None,
                                trailing_sl = None,
                                is_amo = False)
                        print(f'symbol : { symbol } prf: { profit_trade }, loss: { loss_trade }')
                    elif net_quantity < 0:
                        profit_trade = round((symbol_profit * 100 ) / sell_amount_mtm, 2)
                        loss_trade = round((symbol_profit * -100 ) / sell_amount_mtm, 2)
                        if profit_trade >= symb_prf or loss_trade >= symd_loss:
                            print(f'Trigger Buy order to close for symbol : { symbol } { -1 * net_quantity }')
                            smbl = symbol.split("-")[0]
                            alice.place_order(transaction_type = TransactionType.Buy,
                                instrument = alice.get_instrument_by_symbol(exchange , smbl),
                                quantity = abs(net_quantity),
                                order_type = OrderType.Market,
                                product_type = ProductType.Intraday,
                                price = 0.0,
                                trigger_price = None, 
                                stop_loss = None,
                                square_off = None,
                                trailing_sl = None,
                                is_amo = False)
                        print(f'symbol : { symbol }, prf: { profit_trade }, loss: { loss_trade }')
                    print(f'{ symbol } : { symbol_profit }')             
                    print(f'Total Profit : {round(total_profit, 2)}')
                else:
                    continue
            if total_profit >= max_prf or (-total_profit) >= max_lss:
                print(f"Trigger close all open positions for { client }")
                positio = order_details
                for i in range(len(positio)):
                    quanty = positio[i]['quantity']
                    smbl = positio[i]['symbol']
                    prd_typ = positio[i]['product']
                    symbol = smbl.split("-")[0]
                    exchange = positio[i]['exchange']
                    print(symbol, exchange, prd_typ, quanty)
                    if quanty == 0 and prd_typ=='MIS':
                        print(f"coming in since no open position for { client } ")
                        continue
                    elif quanty > 0 and prd_typ=='MIS':
                        alice.place_order(transaction_type = TransactionType.Sell,
                                    instrument = alice.get_instrument_by_symbol(exchange , symbol),
                                    quantity = abs(quanty),
                                    order_type = OrderType.Market,
                                    product_type = ProductType.Intraday,
                                    price = 0.0,
                                    trigger_price = None, 
                                    stop_loss = None,
                                    square_off = None,
                                    trailing_sl = None,
                                    is_amo = False)
                        continue
                    elif quanty < 0 and prd_typ=='MIS':
                        alice.place_order(transaction_type = TransactionType.Buy,
                                    instrument = alice.get_instrument_by_symbol(exchange , symbol),
                                    quantity = abs(quanty),
                                    order_type = OrderType.Market,
                                    product_type = ProductType.Intraday,
                                    price = 0.0,
                                    trigger_price = None, 
                                    stop_loss = None,
                                    square_off = None,
                                    trailing_sl = None,
                                    is_amo = False)
                        continue
                trade_status = 'off'
                dbquery.trade_status_update(client, trade_status)
                print(f"Turn off trade status for { client }")
            else:
                continue
        else:
            print(f"No trades for { client } or Trade status is off")

def start_monitoring():
    monitor_status = 'True'
    dbquery.update_pnl_monitor(monitor_status)
    while True:
        monitor = dbquery.pnl_monitor()
        if monitor!='True':
            print("Stopping Monitoring")
            break
        else:
            monitor_all_positions()
            time.sleep(15)
