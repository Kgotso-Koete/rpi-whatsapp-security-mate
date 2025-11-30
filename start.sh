cd /home/kgotso-koete/Documents/Projects/rpi-whatsapp-security-mate
source venv/bin/activate
./stop.sh
nohup gunicorn -c gunicorn.conf run_flask &
#nohup python3 app/who_is_home.py >> app/logs/who_is_home.log 2>&1 &
nohup python3 app/security_system.py >> app/logs/security_system.log &
nohup python3 app/s3_upload.py >> app/logs/s3_upload.log &

#nohup glances -w -p 52962 --disable-plugin docker --password &
ngrok http --url=https://subsynovial-prelatic-maris.ngrok-free.app 52961