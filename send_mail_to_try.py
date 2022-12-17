import time
import locale
import smtplib
import schedule
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime as dt
from local_settings import *


def send_mail_results(result, last_execution):
    result = "Successful" if result else "Failed"
    today_date_text = dt.now().strftime('%d/%m/%Y')
    sent_from = 'keko.up9@gmail.com'
    to = ['enrique.urrutia@patagonia.com']
    subject = 'Execution report ' + result + ' ' + today_date_text
    body = 'Execution result for ' + today_date_text + ' was ' + result + '\nLast Execution: ' + last_execution
    email_text = "\r\n".join([
      "From: " + sent_from,
      "To: enrique.urrutia@patagonia.com",
      "Subject: " + subject,
      "",
      body
    ])
    gmail_user = GMAIL_USER
    gmail_password = GMAIL_PWD
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, email_text)
        server.close()
        print('Email sent!')
    except:
        print("Something went wrong...")


def job():
    send_mail_results(True, "17 de Diciembre de 2022 a las 09:00")

schedule.every(5).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(60) # wait one minute
