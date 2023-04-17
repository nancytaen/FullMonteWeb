# FullMonteWeb
A web-application for runnig and visualizing the results of the FullMonte simulator and PDT-SPACE optimizer. \
Details about this project can be found in the [Project Final Report](final_report_2020181.pdf).

Details about this project of FullMonteWeb 2.0

## Setting Up FullMonteWeb on IBM Cloud (Ubuntu) - Running it locally!

Step 1: Prerequisite
sudo apt update && sudo apt upgrade
sudo apt-get update && 
sudo apt-get install -y wget build-essential checkinstall libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev libpq-dev liblzma-dev libgl1-mesa-glx libsm6

sudo apt-get install -y wget build-essential checkinstall libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev libpq-dev liblzma-dev libgl1-mesa-glx libsm6

#broken - todo, can’t get this on ubuntu version for wsl?
libreadline-gplv2-dev 



Step 2: Install Python3.7.4
cd /usr/src
sudo wget https://www.python.org/ftp/python/3.7.4/Python-3.7.4.tgz
sudo tar xzf Python-3.7.4.tgz


Build:
cd Python-3.7.4
sudo ./configure --enable-optimizations
sudo make altinstall


Check (this should yield Python-3.7.4 as a result)
python3.7 -V


Step 3: Install Postgres
sudo apt-get install postgresql


Then change the password of the user postgres to sql (Default set on FullMonteWeb settings.py)

sudo -u postgres psql
alter user postgres password 'sql';

Step 4: Setup FullMonteWeb Codebase
git clone https://github.com/nancytaen/FullMonteWeb
cd FullMonteWeb


Virtual env:
python3.7 -m venv venv --prompt Capstone
source venv/bin/activate

Install required packages:
pip install -r requirements.txt

Create .env file with following lines in it
```
SECRET_KEY='#hn!b@)0r(dl49hko$2+7m%#lalw86)eluve-900m2wo=$0=!5'
AWS_SECRET_ACCESS_KEY=<your AWS_SECRET_ACCESS_KEY>
fullmonteuser='fullmontesuite@gmail.com'
fullmontepassword='capstone2020'
IBM_COS_SERVICE_INSTANCE_CRN = <your IBM_COS_SERVICE_INSTANCE_CRN/secret accress key>
COS_HMAC_ACCESS_KEY_ID = <find this on the service credentials of your bucket>
COS_HMAC_SECRET_ACCESS_KEY = <find this on the service credentials of your bucket> 
SERVERLESS_PASSWORD = <YOUR PASSWORD to disallow external users from running sims on your ibmcodeengine> 
```

Setup database migrations
python3.7 manage.py makemigrations
python3.7 manage.py migrate

Run project
python3.7 manage.py runserver 0.0.0.0:8000


