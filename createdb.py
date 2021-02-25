import psycopg2
import postgres
from configparser import ConfigParser
import time

config_file  = 'config.ini'
config = ConfigParser()
config.read(config_file)

# db_URI= config.get('config','DATABASE_URL2') #Local
db_URI= config.get('config','DATABASE_URL_Hero') # HerokuDB

connection = psycopg2.connect(db_URI)

cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_user (
        user_id bigserial PRIMARY KEY,
        full_name 	VARCHAR ( 100 ),
        email 		VARCHAR ( 255 ) UNIQUE NOT NULL,
        mobile_num 	VARCHAR ( 15 ),
        password 	VARCHAR ( 50 ) NOT NULL
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS client_table (
        client_id bigserial PRIMARY KEY,
        broker_id VARCHAR ( 15 ) UNIQUE NOT NULL ,
        broker_name VARCHAR ( 15 ),
        broker_password VARCHAR ( 20 ),
        broker_2fa VARCHAR ( 10 ),
        broker_API VARCHAR ( 20 ),
        broker_API_secret VARCHAR ( 100 ),
        group_name VARCHAR ( 20 ),
        mobile_num 	VARCHAR ( 10 ),
        client_email 	VARCHAR ( 255 ),
        access_token VARCHAR ( 150 ),
        token_date TEXT,
        client_name 	VARCHAR ( 100 ),
        acnt_balance 	VARCHAR ( 20 ),
        trade_status 	VARCHAR ( 50 ),
        place_order TEXT,
        cap_per_trade INTEGER,
        mx_total_prf INTEGER,
        mx_total_ls INTEGER,
        mx_prf_smbl REAL,
        mx_ls_smbl REAL
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_table (
        group_id serial PRIMARY KEY,
        group_name VARCHAR ( 20 ) UNIQUE NOT NULL,
        grp_total_cap INTEGER,
        grp_cap_per_trade INTEGER,
        grp_mx_total_prf INTEGER,
        grp_mx_total_ls INTEGER,
        grp_mx_prf_smbl REAL,
        grp_mx_ls_smbl REAL,
        group_desc 	VARCHAR ( 200 ),
        place_order TEXT
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS place_order_setting (
        row_id serial PRIMARY KEY,
        place_order TEXT UNIQUE,
        tv_trade TEXT,
        cl_trade TEXT,
        cl_timeframe INTEGER,
        pnl_monitor TEXT,
        cl_buffer REAL,
        cl_start_time TEXT,
        cl_end_time TEXT
    );
""")

try:
    place_order = 'custom'
    tv_trade = 'yes'
    cl_trade = 'yes'
    cl_timeframe = '5'
    pnl_monitor = 'False'
    cl_buffer = '0.1'
    cl_start_time = ''
    cl_end_time =  ''
    cursor.execute("""INSERT INTO place_order_setting (place_order, tv_trade, cl_trade, cl_timeframe, pnl_monitor, cl_buffer) VALUES (%s, %s, %s, %s, %s, %s);""", (place_order, tv_trade, cl_trade, cl_timeframe, pnl_monitor, cl_buffer,))
except:
    pass
# cursor.execute("""CREATE TABLE IF NOT EXISTS client_group (
#     group_id    int REFERENCES group_table (group_id) ON UPDATE CASCADE ON DELETE CASCADE,
#     client_id int REFERENCES client_table (client_id) ON UPDATE CASCADE,
#     CONSTRAINT client_group_pkey PRIMARY KEY (group_id, client_id)  -- explicit pk
# );""")

connection.commit()