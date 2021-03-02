from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from configparser import ConfigParser
import dbquery
import app_data
import broker_alice
import json
import chartlink_signal
import pnl_monitor
from threading import Thread
import yfinance as yf
import datetime
from datetime import date, datetime, timedelta
import time

config_file  = 'config.ini'
config = ConfigParser()
config.read(config_file)

app = Flask(__name__)
app.secret_key = config.get('config','app.secret_key')

@app.route('/')
@app.route('/login',  methods=['POST', 'GET'])
def login():
    userbase = dbquery.update_userbase()
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        user = request.form['email']
        pwd = request.form['password']
        if user in userbase:
            if userbase[user]==pwd:
                session["user"] = user
                t = Thread(target=broker_alice.alice_bulk_login, args=[])
                t.start()
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid Password', "error")
                return render_template('login.html')
        else:
            flash('Invalid User', "error")
            return render_template('login.html')
    return render_template('login.html')

@app.route('/changepass',  methods=['POST', 'GET'])
def changepass():
    if request.method == 'POST' and 'user' in request.form and 'password' in request.form:
        email = request.form['user']
        password = request.form['password']
        dbquery.update_password(email, password)
        flash("Updated Password","success")
        return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('login'))

@app.route('/forgotpass')
def forgotpass():
    return render_template('forgot-password.html')

@app.route('/register',  methods=['POST', 'GET'])
def register():
    userbase = dbquery.update_userbase()
    if request.method == 'POST' and 'FullName' in request.form and 'Mobile' in request.form and 'InputEmail' in request.form and 'InputPassword' in request.form and 'RepeatPassword' in request.form:
        fullname = request.form['FullName']
        mobile = request.form['Mobile']
        email = request.form['InputEmail']
        password = request.form['InputPassword']
        if email in userbase:
            flash("User Email Already Exists", "warning")
            return render_template('register.html')
        else:
            dbquery.register_appuser(fullname, mobile, email, password)
            session["user"] = email
            flash("User Registred!", "success")
            return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/bulk_login')
def bulk_login():
    try:
        broker_alice.alice_bulk_login()
        return redirect(url_for('clients'))
    except:
        flash("Oops something went wrong Retry!", "error")
        return redirect(url_for('clients'))

@app.route('/dashboard')
def dashboard():
    email = session["user"]
    if "user" in session:
        client_list = dbquery.client_dash()
        total_orders = 0
        total_trades = 0
        total_pnl = 0
        client_count = 0
        for client in client_list:
            client_pnl = client['client_pnl']
            total_pnl += client_pnl
            client_trd = client['trd_count']
            total_trades += client_trd
            client_ord = client['ord_count']
            total_orders += client_ord
            client_count = client['client_count']
        pnl_monitor = dbquery.status_pnl_monitor()
        return render_template('dashboard.html', user_email=email, client_list=client_list, pnl_monitor=pnl_monitor,
                                 total_pnl=total_pnl, client_count=client_count, total_trades = total_trades, total_orders = total_orders)
    else:
        return render_template("login.html")

@app.route('/monitoring',  methods=['POST', 'GET'])
def monitoring():
    if request.method == 'POST' and 'monitoring' in request.form:
        monitor_status = request.form['monitoring']
        if monitor_status == 'True':
            t = Thread(target=pnl_monitor.start_monitoring, args=[])
            t.start()
            flash("Monitoring for Auto Cutoff started", "success")
            return redirect(url_for('dashboard'))
        elif monitor_status == 'False':
            dbquery.update_pnl_monitor('False')
            flash("Monitoring for Auto Cutoff stopped", "warning")
        return redirect(url_for('dashboard'))

def start_monitoring():
        pnl_monitor.start_monitoring()

@app.route('/deleteclient',  methods=['POST', 'GET'])
def deleteclient():
    if request.method == 'POST' and 'ts_client_id' in request.form and 'delete' in request.form:
        broker_id = request.form['ts_client_id']
        dbquery.delete_client(broker_id)
        return redirect(url_for('clients'))

@app.route('/editclient',  methods=['POST', 'GET'])
def editclient():
    if request.method == 'POST' and 'ts_client_id' in request.form and 'edit' in request.form:
        broker_password = request.form['broker_password']
        broker_2fa = request.form['broker_2fa']
        broker_API = request.form['broker_API']
        group_name = request.form['group_name']
        mobile_num = request.form['mobile_num']
        cap_per_trade = request.form['cap_per_trade']
        mx_prf_smbl = request.form['mx_prf_smbl']
        mx_ls_smbl = request.form['mx_ls_smbl']
        mx_total_prf = request.form['mx_total_prf']
        mx_total_ls = request.form['mx_total_ls']
        broker_id = request.form['ts_client_id']
        client_edit_detail = [broker_password, broker_2fa, broker_API, group_name, mobile_num,
                                cap_per_trade, mx_prf_smbl, mx_ls_smbl, mx_total_prf, mx_total_ls, broker_id]
        dbquery.edit_client(client_edit_detail)
        if group_name:
            dbquery.update_settings_client(broker_id, group_name)
        return redirect(url_for('clients'))

@app.route('/createclient',  methods=['POST', 'GET'])
def createclient():
    if request.method == 'POST' and 'ts_client_id' in request.form and 'trade_status' in request.form:
        ts_client_id = request.form['ts_client_id']
        trade_status = request.form['trade_status']
        dbquery.trade_status_update(ts_client_id, trade_status)
        return redirect(url_for('clients'))
    if request.method == 'POST' and 'client_new' in request.form:
        broker = request.form['broker']
        broker_Id = request.form['broker_Id']
        broker_password = request.form['broker_password']
        broker_2fa = request.form['broker_2fa']
        broker_API = request.form['broker_API']
        broker_API_secret = request.form['broker_API_secret']
        group_name = request.form['group_name']
        mobile_num = request.form['mobile_num']
        cap_per_trade = request.form['cap_per_trade']
        mx_prf_smbl = request.form['mx_prf_smbl']
        mx_ls_smbl = request.form['mx_ls_smbl']
        mx_total_prf = request.form['mx_total_prf']
        mx_total_ls = request.form['mx_total_ls']
        trade_status = 'on'
        client_detail = [broker_Id, broker, broker_password, broker_2fa, broker_API,
                         broker_API_secret, group_name, mobile_num, trade_status,
                         cap_per_trade, mx_prf_smbl, mx_ls_smbl, mx_total_prf, mx_total_ls]
        try:
            dbquery.create_client(client_detail)
            if broker=='AliceBlue':
                broker_alice.addnew_alice_user(broker_Id, broker_password, broker_2fa)
            elif broker=='Zerodha':  #Other Broker
                pass
            if group_name:
                dbquery.update_settings_client(broker_Id, group_name)
            return redirect(url_for('clients'))
        except:
            flash("Client already exist or creation Failed, Try Again!", "warning")
            return redirect(url_for('clients'))
    return redirect(url_for('clients'))

@app.route('/clients')
def clients():
    email = session["user"]
    if "user" in session:
        client_list = dbquery.client_dash()
        group_list = dbquery.group_dash()
        return render_template('clients.html', user_email=email, broker_list=app_data.broker_supported, client_list=client_list, group_list=group_list)
    else:
        return render_template("login.html")

@app.route('/creategroup',  methods=['POST', 'GET'])
def creategroup():
    if request.method == 'POST' and 'group_name' in request.form and 'group_desc' in request.form:
        group_name = request.form['group_name']
        grp_total_cap = request.form['grp_total_cap']
        grp_cap_per_trade = request.form['grp_cap_per_trade']
        grp_mx_total_prf = request.form['grp_mx_total_prf']
        grp_mx_total_ls = request.form['grp_mx_total_ls']
        grp_mx_prf_smbl = request.form['grp_mx_prf_smbl']
        grp_mx_ls_smbl = request.form['grp_mx_ls_smbl']
        group_desc = request.form['group_desc']
        try:
            group_details = [group_name, grp_total_cap, grp_cap_per_trade, grp_mx_total_prf, grp_mx_total_ls, grp_mx_prf_smbl, grp_mx_ls_smbl, group_desc]
            dbquery.create_group(group_details)
            return redirect(url_for('groups'))
        except:
            flash("Creation Failed or Group already exist, Try Again!", "warning")
            return redirect(url_for('groups'))
    flash("Oops something went wrong, Try Again!", "warning") #useless warning
    return redirect(url_for('groups'))
    
@app.route('/groups')
def groups():
    email = session["user"]
    if "user" in session:
        group_list = dbquery.group_dash()
        return render_template('groups.html', user_email=email, group_list=group_list)
    else:
        return render_template("login.html")

@app.route('/editgroup',  methods=['POST', 'GET']) #get edit details from edit modal
def editgroup():
    if request.method == 'POST' and 'edit_group_id' in request.form:
        group_name = request.form['edit_group_name']
        group_id = request.form['edit_group_id']
        grp_total_cap = request.form['grp_total_cap']
        grp_cap_per_trade = request.form['grp_cap_per_trade']
        grp_mx_total_prf = request.form['grp_mx_total_prf']
        grp_mx_total_ls = request.form['grp_mx_total_ls']
        grp_mx_prf_smbl = request.form['grp_mx_prf_smbl']
        grp_mx_ls_smbl = request.form['grp_mx_ls_smbl']
        group_desc = request.form['group_desc']
        update_group = [grp_total_cap, grp_cap_per_trade, grp_mx_total_prf, grp_mx_total_ls, grp_mx_prf_smbl, grp_mx_ls_smbl, group_desc, group_id]
        dbquery.update_group(update_group)
        dbquery.update_group_users(group_name)
        return redirect(url_for('groups'))
    flash("Oops something went wrong, Try Again!", "warning")
    return redirect(url_for('groups'))

@app.route('/deletegroup',  methods=['POST', 'GET'])
def deletegroup():
    if request.method == 'POST' and 'del_group_id' in request.form and 'delete' in request.form:
        group_id = request.form['del_group_id']
        dbquery.delete_group(group_id)
        return redirect(url_for('groups'))

@app.route('/syntax',  methods=['POST', 'GET'])
def syntax():
    email = session["user"]
    if "user" in session:
        if request.method=="POST":
            broker = request.form['broker']
            symbol = request.form['symbol']
            exchange_val = request.form['exchange']
            product_type_val = request.form['product_type']
            order_type_val = request.form['order_type']
            quantity_type = request.form['quantity_type']
            if product_type_val =='ProductType.BracketOrder' and order_type_val=='OrderType.Market':
                flash("BO cannot be of type Market","warning")
                return render_template('syntax.html',symbol=symbol,
                            exchange_val=exchange_val, order_type_val=order_type_val, broker=broker,
                            quantity_type=quantity_type, product_type_val=product_type_val)
            flash("Syntax Generated","success")
            return render_template('syntax.html', symbol=symbol, exchange_val=exchange_val,
                                     order_type_val=order_type_val, broker=broker, quantity_type=quantity_type,
                                      product_type_val=product_type_val)
        else:
            return render_template('syntax.html', user_email=email)
    else:
        return render_template("login.html")

@app.route('/comporders')
def comporders():
    email = session["user"]
    if "user" in session:
        all_order_list = broker_alice.formatted_all_order_list()
        order_completed_list = all_order_list[0]
        order_pending_list = all_order_list[1]
        return render_template('comporders.html', user_email=email, order_completed_list=order_completed_list,
                                order_pending_list=order_pending_list )
    else:
        return render_template("login.html")

@app.route('/cancelorder',  methods=['POST'])
def cancelorder():
    if request.method=="POST":
        oms_ids = request.form.getlist('oms_order_id')
        for i in range(len(oms_ids)):
            club = oms_ids[i].split(":")
            oms_id = club[0]
            client_id = club[1]
            broker_alice.cancel_order(client_id, oms_id)
    flash("Orders has been cancelled","success")
    return redirect(url_for('comporders'))

@app.route('/positions')
def positions():
    email = session["user"]
    if "user" in session:
        all_positions_list = broker_alice.format_all_position()
        return render_template('positions.html', user_email=email, all_positions_list=all_positions_list)
    else:
        return render_template("login.html")

@app.route('/placeorders',  methods=['GET', 'POST'])
def placeorders():
    email = session["user"]
    if "user" in session:
        client_list = dbquery.client_dash()
        group_list = dbquery.group_dash()
        selected_list = dbquery.selected_list()
        return render_template('placeorders.html', user_email=email, group_list=group_list,
                                 client_list=client_list, selected_list=selected_list)
    else:
        return render_template("login.html")

@app.route('/set_place_order_group',  methods=['POST'])
def set_place_order_group():
    if request.method == 'POST' and 'placeorder_set' in request.form:
        placeorder_set = request.form['placeorder_set']
        selected_values = request.form.getlist('selected_values')
        dbquery.update_place_order_set(placeorder_set, selected_values)
        return redirect(url_for('placeorders'))

@app.route('/set_auto_trade',  methods=['POST'])
def set_auto_trade():
    if request.method == 'POST' and 'tv_trade_val' in request.form:
        tv_trade = request.form['tv_trade_val']
        dbquery.update_tv_algo(tv_trade)
        return redirect(url_for('auto_trade'))
    elif request.method == 'POST' and 'cl_trade_val' in request.form:
        cl_trade = request.form['cl_trade_val']
        dbquery.update_cl_algo(cl_trade)
        return redirect(url_for('auto_trade'))
    elif request.method == 'POST' and  'cl_tf' in request.form and  'cl_bf' in request.form and  'cl_start_time' in request.form and  'cl_end_time' in request.form:
        cl_tf = request.form['cl_tf']
        cl_bf = request.form['cl_bf']
        cl_start_time = request.form['cl_start_time']
        cl_end_time = request.form['cl_end_time']
        dbquery.update_cl_tf(cl_tf, cl_bf, cl_start_time, cl_end_time)
        return redirect(url_for('auto_trade'))
    flash("Enter Valid input","warning")
    return

@app.route('/auto_trade')
def auto_trade():
    email = session["user"]
    if "user" in session:
        algo_setting = dbquery.algo_setting()
        tv_trade = algo_setting[2]
        cl_trade = algo_setting[3]
        cl_tf = algo_setting[4]
        cl_bf = algo_setting[6]
        cl_start_time = algo_setting[7]
        cl_end_time = algo_setting[8]
        return render_template('auto_trade.html', user_email=email, tv_trade=tv_trade, cl_trade=cl_trade,
                                 cl_tf=cl_tf, cl_bf=cl_bf, cl_start_time=cl_start_time, cl_end_time=cl_end_time)
    else:
        return render_template("login.html")

@app.route('/submit_order',  methods=['POST'])
def submit_order():
    if request.method == 'POST' and 'submitorder' in request.form:
        final_list_token = dbquery.make_order_list()
        quantity_type = request.form['quantityRadio']
        symbol = request.form['symbol']
        order_type = request.form['ordertypeRadio']
        price = float(request.form['price'])
        exchange = request.form['exchange']
        try:
            if price == 0.0 and (exchange == "NSE" or exchange == "BSE"):
                Current_Date = date.today()
                Next_Date = date.today() + timedelta(days=1)
                ysymbol ="{0}{1}".format(symbol,".NS")
                data = yf.download(ysymbol, start=Current_Date, end=Next_Date)
                price = float(data['Close'])
            else:
                price = request.form['price']
        except:
            flash("Market closed or Price not availble!", "warning")
            return redirect(url_for('placeorders'))
            
        if quantity_type == 'Auto':
            quantity = 0
        else:
            quantity = request.form['quantity']
        if order_type == 'Market' or order_type == 'Limit':
            trigger_price = ""
        else:
            trigger_price = request.form['triggerprice']
        order_data = {'transaction_type':request.form['tradetypeRadio'],
                    'symbol':symbol,
                    'exchange':exchange,
                    'quantity':quantity,
                    'quantity_type':request.form['quantityRadio'],
                    'price':price,
                    'order_type': request.form['ordertypeRadio'], #
                    'product_type':request.form['producttypeRadio'], #'MIS'
                    'trigger_price':trigger_price,
                    'stop_loss':request.form['bostoploss'],
                    'square_off':request.form['botarget'],
                    'trailing_sl':request.form['botrailsl'],
                    'token_list':final_list_token}
        response = broker_alice.alice_place_order_multi(order_data)
        flash(response,"info")
        return redirect(url_for('comporders'))

@app.route('/tv_webhook',  methods=['POST','GET'])
def tv_webhook():
    tv_webhook_message = json.loads(request.data)
    transaction_type = tv_webhook_message['strategy']['order_action']
    symbol = tv_webhook_message['symbol']
    exchange = tv_webhook_message['exchange']
    quantity_type = tv_webhook_message['quantity_type']
    price = tv_webhook_message['strategy']['order_price']
    product_type = tv_webhook_message['strategy']['product_type']
    order_type = tv_webhook_message['strategy']['order_type']
    trigger_price = tv_webhook_message['strategy']['order_price']
    if quantity_type == 'Manual':
        quantity = tv_webhook_message['order_contracts']
    else:
        quantity = 0
    forme = 'TV'
    auto_list_token = dbquery.auto_order_list(forme)
    order_data = {'transaction_type':transaction_type,
            'symbol':symbol,
            'exchange':exchange,
            'quantity':quantity,
            'quantity_type':quantity_type,
            'price':price,
            'order_type': order_type, #
            'product_type':product_type, #'MIS'
            'trigger_price':trigger_price,
            'stop_loss':None, #TV cannot support these now
            'square_off':None, #TV cannot support these now
            'trailing_sl':None, #TV cannot support these now
            'token_list':auto_list_token}
    try:
        broker_alice.alice_place_order_multi(order_data)
        return {'Order Submitted'}
    except TypeError:
         return {'Order Submitted but....'}

@app.route('/chartlink_webhook',  methods=['POST','GET'])
def chartlink_webhook():
    cl_webhook_message = json.loads(request.data)
    symbol_list = cl_webhook_message['stocks'].split(",")    
    price_list = cl_webhook_message['trigger_prices'].split(",")
    alert_name  = cl_webhook_message['alert_name'].split(",")
    exchange = alert_name[0] #Must have exchange mentioned in alert_name. eg: NSE,buy
    transaction_type = alert_name[1] # Must have transaction type set as scan name buy / sell eg: NSE,buy
    forme = 'CL'
    auto_list_token = dbquery.auto_order_list(forme)
    cl_setting = dbquery.cl_setting()
    cl_timeframe = cl_setting[0]['cl_tl']
    cl_buffer = cl_setting[0]['cl_bf']
    cl_start_time = cl_setting[0]['cl_start_time']
    cl_end_time = cl_setting[0]['cl_end_time']
    t = time.localtime()
    current_time = str(time.strftime("%H:%M", t))
    cur_t = current_time.split(':')
    str_t = cl_start_time.split(':')
    end_t = cl_end_time.split(':')
    curr = int(cur_t[0]) *60 + int(cur_t[1])
    start = int(str_t[0]) *60 + int(str_t[1])
    end = int(end_t[0]) *60 + int(end_t[1])
    if curr >= start and curr <= end:
        signal = []
        for i in range(len(symbol_list)):
            data = {'symbol':symbol_list[i], 'price' : price_list[i]}
            signal.append(data)
        for _ in range (len(signal)):
            order_data = {'transaction_type':transaction_type,
                    'symbol':signal[_]['symbol'],
                    'exchange':exchange,
                    'quantity':0,
                    'quantity_type':'Auto', #by default quantity type auto for chartlink system
                    'price':signal[_]['price'],
                    'order_type': 'SLMK', #by default will trigger stoploss market order,
                    'product_type':'MIS', #'MIS' only intraday supported
                    'trigger_price':signal[_]['price'],
                    'stop_loss':0.0,
                    'square_off':0.0,
                    'trailing_sl':0.0,
                    'token_list':auto_list_token}
            chartlink_signal.start_to_wait_to_place_order(order_data, cl_timeframe, cl_buffer)
        return "Order Submitted successfully"
    else:
        return "Out of Trade Time Range"


if __name__ == '__main__':
    app.run(debug=True)