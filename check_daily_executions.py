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
from dateutil import tz
from local_settings import *


user = MD_USER
pwd = MD_PWD

ser = Service(executable_path=r"~/root/chromedriver/chromedriver")

op = webdriver.ChromeOptions()
op.add_argument('headless')
op.add_argument('--no-sandbox')
op.add_argument('--disable-dev-shm-usage')
op.add_argument("--remote-debugging-port=9222")

driver = webdriver.Chrome(service=ser, options=op)


def check_login_required():
    try:
        return WebDriverWait(driver, 1).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@id='id_username']"))
        )
    except TimeoutError as err:
        print(err.msg)
        return False


def get_last_middleware_execution():
    driver.get("https://patagonia.linets.cl/admin/azure_sql/erpstock/")
    driver.maximize_window()
    return driver.find_element("xpath", "(//td[contains(@class,'field-syncstartdatetime nowrap')])[1]").text


def check_execution_is_today(execution_date):
    # With setLocale, we can parse the name of the months in Spanish
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    date_today = dt.now().date()
    execution_date = execution_date.replace("de ", "").replace("a las ", "")
    execution_datetime = dt.strptime(execution_date, '%d %B %Y %H:%M')
    return execution_datetime.date() == date_today


def parse_date_to_correct_timezone(execution_date):
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz('America/Santiago')
    execution_date = execution_date.replace("de ", "").replace("a las ", "")
    execution_datetime = dt.strptime(execution_date, '%d %B %Y %H:%M')
    execution_datetime = execution_datetime.replace(tzinfo=from_zone)
    execution_datetime = execution_datetime.astimezone(to_zone)
    return execution_datetime.strftime('%d %B %Y %H:%M')


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


def check_correct_execution():
    driver.get("https://patagonia.linets.cl/admin/md_shopify/inventory/")

    login = check_login_required()
    if login:
        login.send_keys(user + Keys.TAB + pwd + Keys.TAB + Keys.ENTER)

    last_execution_date = get_last_middleware_execution()
    send_mail_results(
        check_execution_is_today(last_execution_date),
        parse_date_to_correct_timezone(last_execution_date)
    )
    if check_execution_is_today(last_execution_date):
        print("Ejecución correcta!")
    else:
        print("No hay ejecución hoy!!")
    driver.close()


def __main__():
    schedule.every().day.at("10:00").do(check_correct_execution)
    while True:
        schedule.run_pending()
        time.sleep(600)


__main__()


