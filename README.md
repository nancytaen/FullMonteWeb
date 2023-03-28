# FullMonteWeb
A web-application for runnig and visualizing the results of the FullMonte simulator and PDT-SPACE optimizer. \
Details about this project can be found in the [Project Final Report](final_report_2020181.pdf).

Changelist

0.0.1 Added 3 new views: tutorial, simulation and visualization


## Mymy
- your `.env` file should contain the following
```
SECRET_KEY='#hn!b@)0r(dl49hko$2+7m%#lalw86)eluve-900m2wo=$0=!5'
AWS_SECRET_ACCESS_KEY=<your AWS_SECRET_ACCESS_KEY>
fullmonteuser='fullmontesuite@gmail.com'
fullmontepassword='capstone2020'
IBM_COS_SERVICE_INSTANCE_CRN = <your IBM_COS_SERVICE_INSTANCE_CRN/secret accress key>
COS_HMAC_ACCESS_KEY_ID = <>
COS_HMAC_SECRET_ACCESS_KEY = <>
```
- remember to run python manage.py makemgiration + migrate
