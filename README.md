TradingView Strategy Alert Webhook for Aliceblue
============================================================
STAND ALONE MODE (running from local machine)
============================================================
## Flask set up

navigate to the BOT folder
...\mat_app

set FLASK_ENV=development # in the cmd to work on dev mode

run : flask run 

Copy paste http://127.0.0.1:80/ in the browser and see if the script is online on the local host.

Open another cmd prompt from the app folder to run the payload server

Run ngrok http 80  (**on the same port the Bot is listening to )

The Webhook payload server should be live now.

Copy Paste the https://random.ngrok.io/webhook in the tradingview alert webhook field.

Start the tradingview Alert. Bingo!!
===================================================================
WEB DEPLOYMENT to HEROKU cloud - PreProd
===================================================================!!!!!!!!!!
TAKE the APP down for MAINTENANCE!
Heroku login
COPY SETTINGS file before any deployment to not lose the settings.
heroku run bash
====================================================================!!!!!!!!!!! 
Make sure virtual env is deactivated during deployment.
Make Sure to change any file path used in dev app to /app/.. folder before deploying to heroku






