import psycopg2
import postgres
from configparser import ConfigParser
import time
from datetime import date, datetime
import concurrent.futures
import broker_alice

config_file  = 'config.ini'
config = ConfigParser()
config.read(config_file)

# db_URI= config.get('config','DATABASE_URL2') #Local postgres
db_URI= config.get('config','DATABASE_URL_Hero') # HerokuDB

class Database:
    def __init__(self, name):
        self._conn = psycopg2.connect(db_URI)
        self._cursor = self._conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def connection(self):
        return self._conn

    @property
    def cursor(self):
        return self._cursor

    def commit(self):
        self.connection.commit()

    def close(self, commit=True):
        if commit:
            self.commit()
        self.connection.close()

    def execute(self, sql, params=None):
        self.cursor.execute(sql, params or ())

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def query(self, sql, params=None):
        self.cursor.execute(sql, params or ())
        return self.fetchall()

def update_userbase():
    with Database(db_URI) as db:
        userlist = db.query('SELECT email, password FROM app_user')
        userbase={row[0]:row[1] for row in userlist}
    return(userbase)
        
def register_appuser(fullname, mobile, email, password):
    with Database(db_URI) as db:
        db.execute("""INSERT INTO app_user (full_name, email, mobile_num, password)
                        VALUES (%s, %s, %s, %s);""", (fullname, email, mobile, password,))

def update_password(email, password):
    with Database(db_URI) as db:
        db.execute("""UPDATE app_user SET password=%s WHERE email=%s;""", (password, email))


def create_group(group_details):
    with Database(db_URI) as db:
        db.execute("""INSERT INTO group_table (group_name, grp_total_cap,
                        grp_cap_per_trade, grp_mx_total_prf, grp_mx_total_ls, grp_mx_prf_smbl, 
                        grp_mx_ls_smbl, group_desc) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""", (group_details))

def create_client(client_detail):
    with Database(db_URI) as db:
        db.execute("""INSERT INTO client_table (broker_id, broker_name,
                        broker_password, broker_2fa, broker_API, broker_api_secret, group_name,
                        mobile_num, trade_status, cap_per_trade, mx_prf_smbl, mx_ls_smbl, mx_total_prf, mx_total_ls)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""", (client_detail))
    return { 'status': 'updated'  }

def edit_client(client_edit_detail):
    with Database(db_URI) as db:
        db.execute("""UPDATE client_table SET broker_password= %s, broker_2fa= %s, broker_API= %s, group_name= %s,
                        mobile_num= %s, cap_per_trade= %s, mx_prf_smbl= %s, mx_ls_smbl= %s, mx_total_prf= %s, mx_total_ls= %s 
                        WHERE broker_id=%s;""", (client_edit_detail))
    return { 'status': 'updated'  }

def update_settings_client(broker_id, group_name):
    with Database(db_URI) as db:
        db.execute("""SELECT grp_cap_per_trade, grp_mx_total_prf, grp_mx_total_ls, grp_mx_prf_smbl,
                grp_mx_ls_smbl FROM group_table WHERE group_name=%s;""", (group_name,))
        ans =db.fetchone()
        params = [ans[0], ans[1], ans[2], ans[3], ans[4], broker_id]
        db.execute("""UPDATE client_table SET cap_per_trade= %s, mx_total_prf= %s, mx_total_ls= %s, mx_prf_smbl= %s,
                        mx_ls_smbl= %s WHERE broker_id=%s;""", (params))
        return { 'status': 'updated'  }

def update_group_users(group_name):
    with Database(db_URI) as db:
        db.execute("""SELECT broker_id FROM client_table WHERE group_name=%s;""", (group_name,))
        result = db.fetchall()
        group_users = [value[0] for value in result]
        for broker_id in group_users:
            update_settings_client(broker_id, group_name)
        return { 'status': 'updated'  }

def update_group(update_group):
    with Database(db_URI) as db:
        db.execute("""UPDATE group_table SET grp_total_cap= %s, grp_cap_per_trade= %s, grp_mx_total_prf= %s, grp_mx_total_ls= %s,
                        grp_mx_prf_smbl= %s, grp_mx_ls_smbl= %s, group_desc= %s WHERE group_id=%s;""", (update_group))
    return { 'status': 'updated'  }

def delete_client(broker_id):
    with Database(db_URI) as db:
        db.execute("""DELETE FROM client_table WHERE broker_id=%s;""", (broker_id,))
        return { 'status': 'deleted'  }

def delete_group(group_id):
    with Database(db_URI) as db:
        db.execute("""SELECT group_name FROM group_table WHERE group_id=%s;""", (group_id,))
        group_name = db.fetchone()[0]
        new_val = ['',group_name]
        db.execute("""UPDATE client_table SET group_name= %s WHERE group_name=%s;""", (new_val))
        db.execute("""DELETE FROM group_table WHERE group_id=%s;""", (group_id,))
        return { 'status': 'deleted'  }

def client_count():
    with Database(db_URI) as db:
        db.execute("""SELECT count (*) FROM client_table;""")
        client_count = db.fetchone()[0]
        return client_count

def client_dash():
    with Database(db_URI) as db:
        db.execute("SELECT * FROM client_table;")
        ans =db.fetchall()
        client_list = []
        for i in range(len(ans)):
            username = ans[i][1]
            token_date = fetch_token_date(username)
            Current_Date = date.today()
            if str(token_date[0]) == str(Current_Date):
                try:
                    access_token = token_date[1]
                    alice = broker_alice.get_alice_obj(access_token)
                    balance = alice.get_balance()
                    unrealised = float(balance['data']['cash_positions'][0]['utilized']['unrealised_m2m'])
                    realised = float(balance['data']['cash_positions'][0]['utilized']['realised_m2m'])
                    PnL = unrealised + realised
                    orders = alice.get_order_history()
                    ord_count = 0
                    if orders['data']:
                        try:
                            pen_ord = len(orders['data']['pending_orders'])
                            com_ord = len(orders['data']['completed_orders'])
                            ord_count = pen_ord + com_ord
                        except:
                            com_ord = len(orders['data']['completed_orders'])
                            ord_count = com_ord
                    else:
                        pass
                    posi = alice.get_netwise_positions()
                    trd_count = len(posi['data']['positions'])
                    login_status = 'Active'
                except:
                    PnL = 0
                    ord_count = 0
                    trd_count = 0
                    login_status = 'Expired'
            else:
                PnL = 0
                ord_count = 0
                trd_count = 0
                login_status = 'Expired'
            dict_1 = {'broker_id': ans[i][1],
                    'broker_name': ans[i][2],
                    'broker_password': ans[i][3],
                    'broker_2fa': ans[i][4],
                    'broker_api': ans[i][5],
                    'broker_api_secret': ans[i][6],
                    'client_name': ans[i][12],
                    'group_name': ans[i][7],
                    'mobile_num': ans[i][8],
                    'client_email': ans[i][9],
                    'login_status': login_status,
                    'client_balance': ans[i][13],
                    'client_pnl': PnL,
                    'trade_status': ans[i][14],
                    'cap_per_trade': ans[i][16],
                    'mx_total_prf': ans[i][17],
                    'mx_total_ls': ans[i][18],
                    'mx_prf_smbl': ans[i][19],
                    'mx_ls_smbl': ans[i][20],
                    'client_count': len(ans),
                    'trd_count': trd_count,
                    'ord_count': ord_count}
            client_list.append(dict_1)
        return client_list

def group_dash():
    with Database(db_URI) as db:
        db.execute("SELECT * FROM group_table;")
        ans =db.fetchall()
        group_list = []
        for i in range(len(ans)):
            db.execute("""SELECT COUNT(*) FROM client_table WHERE group_name=%s;""", (ans[i][1],))
            client_count = db.fetchone()[0]
            dict_1 = {'group_id':ans[i][0],
                        'group_name': ans[i][1],
                        'client_count':client_count,
                        'grp_total_cap': ans[i][2],
                        'grp_cap_per_trade': ans[i][3],
                        'grp_mx_total_prf': ans[i][4],
                        'grp_mx_total_ls': ans[i][5],
                        'grp_mx_prf_smbl': ans[i][6],
                        'grp_mx_ls_smbl': ans[i][7],
                        'group_desc': ans[i][8]}
            group_list.append(dict_1)
        return group_list

def trade_status_update(ts_client_id, trade_status):
    with Database(db_URI) as db:
        db.execute("""UPDATE client_table SET trade_status=%s WHERE broker_id in (%s);""", (trade_status, ts_client_id))
        return { 'status': 'updated'  }

def get_alice_user_detail():
    with Database(db_URI) as db:
        db.execute("""SELECT * FROM client_table WHERE broker_name='AliceBlue';""")
        result =db.fetchall()
        alice_user_detail = []
        for i in range(len(result)):
            dict_1 = {'broker_id': result[i][1],
                    'broker_password': result[i][3],
                    'broker_2fa': result[i][4],
                    'access_token':result[i][10]}
            alice_user_detail.append(dict_1)
        return alice_user_detail

def updatenew_alice_user(update_detail):
    with Database(db_URI) as db:
        db.execute("""UPDATE client_table SET client_email= %s, access_token=%s, token_date=%s, client_name= %s, acnt_balance= %s WHERE broker_id=%s;""", (update_detail))
        return { 'status': 'updated'  }

def fetch_token_date(username):
    with Database(db_URI) as db:
        db.execute("SELECT token_date, access_token FROM client_table WHERE broker_id=%s;", (username,))
        token_date = db.fetchone()
        return (token_date)

def fetch_access_token(username):
    with Database(db_URI) as db:
        db.execute("SELECT access_token FROM client_table WHERE broker_id=%s;", (username,))
        access_token = db.fetchone()[0]
        return (access_token)

def update_access_token(access_token, account_balance, username):
    Current_Date = date.today()
    token_date = str(Current_Date)
    with Database(db_URI) as db:
        db.execute("""UPDATE client_table SET access_token= %s, token_date = %s, acnt_balance = %s WHERE broker_id=%s;""", (access_token, token_date, account_balance, username,))
    return { 'status': 'updated' }

def update_place_order_set(placeorder_set, selected_values):
    with Database(db_URI) as db:
        db.execute("""UPDATE group_table SET place_order='no';""")
        db.execute("""UPDATE client_table SET place_order='no';""")
        for value in selected_values:
            if placeorder_set =='group':
                db.execute("""UPDATE group_table SET place_order='yes' WHERE group_name in(%s);""", (value,))
                db.execute("""UPDATE place_order_setting SET place_order='group';""")
            else:
                db.execute("""UPDATE client_table SET place_order='yes' WHERE broker_id in(%s);""", (value,))
                db.execute("""UPDATE place_order_setting SET place_order='custom';""")

def fetch_place_order_setting():
    with Database(db_URI) as db:
        db.execute("""SELECT * FROM place_order_setting WHERE row_id='1';""")
        place_order_setting = db.fetchone()[1]
        return place_order_setting

def selected_list():
    place_order_setting = fetch_place_order_setting()
    with Database(db_URI) as db:
        if place_order_setting == 'group':
            db.execute("""SELECT group_name FROM group_table WHERE place_order ='yes';""")
            result =db.fetchall()
            selected_list = [value[0] for value in result]
            return selected_list
        else:
            db.execute("""SELECT client_name FROM client_table WHERE place_order ='yes';""")
            result =db.fetchall()
            selected_list = [value[0] for value in result]
            return selected_list

def make_order_list():
    select_list = selected_list()
    placeorder_set = fetch_place_order_setting()
    with Database(db_URI) as db:
        if placeorder_set=='group':
            db.execute("""SELECT cap_per_trade, access_token FROM client_table WHERE group_name = ANY (%(parameters)s)
                        and trade_status='on';""" , {"parameters": select_list})
            result = db.fetchall()
            final_list_token = [{'cap_trade':value[0],'token':value[1]} for value in result]
            return final_list_token
        else:
            db.execute("""SELECT cap_per_trade, access_token FROM client_table WHERE place_order='yes' and trade_status='on';""")
            result = db.fetchall()
            final_list_token = [{'cap_trade':value[0],'token':value[1]} for value in result]
            return final_list_token

def auto_order_list(forme):
    with Database(db_URI) as db:
        if forme=='TV':
            db.execute("""SELECT * FROM place_order_setting WHERE row_id='1';""")
            tv_trade = db.fetchone()[2]
            if tv_trade == 'yes':
                db.execute("""SELECT cap_per_trade, access_token FROM client_table WHERE trade_status='on';""")
                result = db.fetchall()
                auto_list_token = [{'cap_trade':value[0],'token':value[1]} for value in result]
                return auto_list_token
            else:
                auto_list_token=[]
                return auto_list_token
        elif forme=='CL':
            db.execute("""SELECT * FROM place_order_setting WHERE row_id='1';""")
            cl_trade = db.fetchone()[3]
            if cl_trade == 'yes':
                db.execute("""SELECT cap_per_trade, access_token FROM client_table WHERE trade_status='on';""")
                result = db.fetchall()
                auto_list_token = [{'cap_trade':value[0],'token':value[1]} for value in result]
                return auto_list_token
            else:
                auto_list_token=[]
                return auto_list_token

def cl_setting():
    with Database(db_URI) as db:
        db.execute("""SELECT * FROM place_order_setting WHERE row_id='1';""")
        results = db.fetchall()
        cl_setting = [{'cl_tl':value[4],'cl_bf':value[6], 'cl_start_time':value[7],'cl_end_time':value[8]} for value in results]
        return cl_setting

def get_client_list(): #added for Limit Profit, Loss
    with Database(db_URI) as db:
        db.execute("SELECT * FROM client_table;")
        ans =db.fetchall()
        client_list = []
        for i in range(len(ans)):
            dict_1 = {'broker_id': ans[i][1],
                      'access_token': ans[i][10],
                      'trade_status': ans[i][14],
                      'cap_per_trade': ans[i][16],
                      'mx_total_prf': ans[i][17],
                      'mx_total_ls': ans[i][18],
                      'mx_prf_smbl': ans[i][19],
                      'mx_ls_smbl': ans[i][20]}
            client_list.append(dict_1)
        return client_list

def pnl_monitor():
    with Database(db_URI) as db:
        db.execute("SELECT pnl_monitor FROM place_order_setting WHERE row_id='1';")
        pnl_monitor = db.fetchone()[0]
        return pnl_monitor

def update_pnl_monitor(monitor_status):
    with Database(db_URI) as db:
        db.execute("""UPDATE place_order_setting SET pnl_monitor=%s WHERE row_id='1';""", (monitor_status,))
        return { 'status': 'updated' }

def algo_setting():
    with Database(db_URI) as db:
        db.execute("SELECT * FROM place_order_setting WHERE row_id='1';")
        algo_setting = db.fetchone()
        return algo_setting

def update_tv_algo(tv_trade):
    with Database(db_URI) as db:
        db.execute("""UPDATE place_order_setting SET tv_trade=%s WHERE row_id='1';""", (tv_trade,))
        return { 'status': 'updated' }

def update_cl_algo(cl_trade):
    with Database(db_URI) as db:
        db.execute("""UPDATE place_order_setting SET cl_trade=%s WHERE row_id='1';""", (cl_trade,))
        return { 'status': 'updated' }

def update_cl_tf(cl_tf, cl_bf, cl_start_time, cl_end_time):
    with Database(db_URI) as db:
        db.execute("""UPDATE place_order_setting SET cl_timeframe=%s, cl_buffer=%s, cl_start_time=%s, cl_end_time=%s  WHERE row_id='1';""", (cl_tf, cl_bf, cl_start_time, cl_end_time,))
        return { 'status': 'updated' }

def status_pnl_monitor():
    with Database(db_URI) as db:
        db.execute("SELECT * FROM place_order_setting WHERE row_id='1';")
        pnl_monitor = db.fetchone()[5]
        return pnl_monitor