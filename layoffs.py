#!/usr/bin/env python3

import requests
import json
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime
from datetime import date
from datetime import timedelta

# load credentials from .env file
load_dotenv()
airtableUrl = os.environ.get('airtableUrl')
airtableAppId = os.environ.get('airtableAppId')
airtableCookie = os.environ.get('airtableCookie')
slackChannel = os.environ.get('slackChannel')
slackApiKey = os.environ.get('slackApiKey')

# GET request for layoffs.fyi airtable data
headers = {
  'x-airtable-application-id': airtableAppId,
  'x-requested-with': 'XMLHttpRequest',
  'x-time-zone': 'America/Chicago',
  'Cookie': airtableCookie
}

response = requests.request("GET", airtableUrl, headers=headers)
data = json.loads(response.text)

# open sqlite
connection = sqlite3.connect("layoffs.db")
cursor = connection.cursor()

# clean up returned data
print("\n----------------------------------------------------------------")
for i in data['data']['rows']:
    try:
        company = i['cellValuesByColumnId']['fldWyUNuYW5ObN8Fw']
    except KeyError:
        company = 'Error'
    try:
        num_laid_off = i['cellValuesByColumnId']['flduZSpdFqkB4eeEh']
    except KeyError:
        num_laid_off = 'n/a'
    try:
        # convert percentage
        raw_percentage = i['cellValuesByColumnId']['fldMPQjXwImpjkDqb']
        x = raw_percentage * 100
        percent = str(int(x))+'%'
    except KeyError:
        percent = 'n/a'
    try:
        layoff_date = i['cellValuesByColumnId']['fldXPv4gHmcbxvQRi'].replace('T00:00:00.000Z', '')
        # convert to date object for use later
        layoff_date_obj = datetime.strptime(layoff_date, '%Y-%m-%d').date()
    except KeyError:
        layoff_date = 'Error'
    try:
        source = i['cellValuesByColumnId']['fldcrmTO88VxOYeSX']
    except KeyError:
        source = 'n/a'
    
    companyData = {
        "company": company,
        "num_laid_off": num_laid_off,
        "percent": percent,
        "date": layoff_date,
        "source": source
    }

    # only include layoff data that occurred today and yesterday
    today = date.today()
    yesterday = today - timedelta(days = 1)

    # only include layoff data that occurred today and yesterday
    if (today == layoff_date_obj or yesterday == layoff_date_obj):
        # make sure we haven't added it before
        entry = cursor.execute("SELECT company FROM layoffs WHERE company = ? AND date = ?", (company, str(layoff_date))).fetchall()
        if not entry:


            # post slack message
            slack_message = f":on_fire: :on_fire: :on_fire:\nLayoffs announced at *{company}*.\n<{source}|Click here for more details.>"

            url = "https://slack.com/api/chat.postMessage"

            payload = json.dumps({
                "channel": slackChannel,
                "text": slack_message
            })
            headers = {
                'Authorization': 'Bearer '+slackApiKey,
                'Content-type': 'application/json'
            }

            response = requests.request("POST", url, headers=headers, data=payload)

            # update database
            cursor.execute("INSERT INTO layoffs (company, num_laid_off, percent, date, source) VALUES (?, ?, ?, ?, ?)", (company, str(num_laid_off), str(percent), str(layoff_date), source))

            confirmation =  f"Posted Slack Message for {company}\n----------------------------------------------------------------"
            print(confirmation)

print("\n")
connection.commit()