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
Deploy to Heroku from cmd
git init
heroku git:remote -a mat-rajan-app
git status
git add .
git commit -am "initial commit"
git push heroku master
======
update the scheduled job
heroku ps:scale clock=1
==================
heroku logs --tail   /   heroku logs -a mat-rajan-app --tail
heroku run bash
==================================================================
cli restart command;
heroku ps:stop worker
heroku ps:restart
TV Webhook URL : https://mat-rajan-app.herokuapp.com/quickey_webhook
==================================================================
Update to github
git init
git status
git add -A
git commit -m "Initial Commit"
git push https://github.com/youngking1686/mat_app.git main

=============
pull from git
git init
git pull https://github.com/youngking1686/mat_app.git main
git reset --hard https://github.com/youngking1686/EQ-Quickey.git main (only when there is a conflict and you know it)





