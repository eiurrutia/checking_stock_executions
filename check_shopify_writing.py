import datetime
import time
import locale
import smtplib
import requests
import shopify
import json
#import schedule
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions \
    import SessionNotCreatedException, WebDriverException, NoSuchElementException, TimeoutException
from datetime import datetime as dt
from dateutil import tz
from local_settings import *


user = MD_USER
pwd = MD_PWD
shop_URL = "https://705b02ca5eb86e9e80fe468fb6cd315b:9c26ce6b8d5065652d378408f28ff21d@patagoniachile.myshopify.com/admin"

# ser = Service(executable_path=r"~/root/chromedriver/chromedriver")
#ser = Service(executable_path=r"C:\Users\Enrique Urrutia\Desktop\driver\chromedriver.exe")

#op = webdriver.ChromeOptions()
#op.add_argument('headless')
#op.add_argument('--no-sandbox')
#op.add_argument('--disable-dev-shm-usage')
# op.add_argument("--remote-debugging-port=9222")

#driver = webdriver.Chrome(service=ser, options=op)


def set_up_driver():
    try:
        # ser = Service(executable_path=r"~/root/chromedriver/chromedriver")
        ser = Service(executable_path=r"C:\Users\Enrique Urrutia\Desktop\driver\chromedriver.exe")
        op = webdriver.ChromeOptions()
        op.add_argument('headless')
        op.add_argument('--no-sandbox')
        op.add_argument('--disable-dev-shm-usage')
        # op.add_argument("--remote-debugging-port=9222")
        return webdriver.Chrome(service=ser, options=op)
    except SessionNotCreatedException as err:
        print(f"{datetime.datetime.now()} - {err.msg}")


def check_login_required(driver):
    try:
        return WebDriverWait(driver, 1).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@id='id_username']"))
        )
    except TimeoutError as err:
        print(err.msg)
        return False


def get_last_middleware_execution(driver):
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
    driver = set_up_driver()
    driver.get("https://patagonia.linets.cl/admin/md_shopify/inventory/")

    login = check_login_required(driver)
    if login:
        login.send_keys(user + Keys.TAB + pwd + Keys.TAB + Keys.ENTER)

    last_execution_date = get_last_middleware_execution(driver)
    send_mail_results(
        check_execution_is_today(last_execution_date),
        parse_date_to_correct_timezone(last_execution_date)
    )
    if check_execution_is_today(last_execution_date):
        print("Ejecución correcta!")
    else:
        print("No hay ejecución hoy!!")
    driver.close()


def get_sku_to_write_example():
    driver = set_up_driver()
    driver.get("https://patagonia.linets.cl/admin/md_shopify/inventory/")

    login = check_login_required(driver)
    if login:
        login.send_keys(user + Keys.TAB + pwd + Keys.TAB + Keys.ENTER)
    #driver.find_element("xpath", "//span[@id='select2-c2bg-container']")

    element = WebDriverWait(driver, 4).until(
        EC.visibility_of_element_located((By.XPATH, "//*[@id='changelist-search']/div/span[2]/span"))
    )
    element.click()
    element = WebDriverWait(driver, 4).until(
        EC.visibility_of_element_located((By.XPATH, "/html/body/span/span/span[1]/input"))
    )
    element.send_keys("CD" + Keys.ENTER)
    element = WebDriverWait(driver, 4).until(
        EC.visibility_of_element_located((By.XPATH, "(//a[contains(., 'Stock I.')])[1]"))
    )
    element.click()
    element = WebDriverWait(driver, 4).until(
        EC.visibility_of_element_located((By.XPATH, "(//a[contains(., 'Stock I.')])[1]"))
    )
    element.click()

    ###################### buscar en tabla valores distintos
    example_sku = None
    example_inventory_id = None
    for actual_page in range(1, 6):
        for row in range(1, 100):
            a = WebDriverWait(driver, 4).until(
                EC.visibility_of_element_located((By.XPATH, f"(//td[contains(@class ,'field-quantity')])[{row}]"))
            )
            b = WebDriverWait(driver, 4).until(
                EC.visibility_of_element_located((By.XPATH, f"(//td[contains(@class ,'field-new_quantity')])[{row}]"))
            )
            if a.text != b.text:
                example_sku =\
                    WebDriverWait(driver, 4).until(
                        EC.visibility_of_element_located((By.XPATH, f"(//td[contains(@class ,'field-sku')])[{row}]"))
                    ).text
                example_inventory_id = \
                    WebDriverWait(driver, 4).until(
                        EC.visibility_of_element_located((By.XPATH, f"(//td[contains(@class ,'field-inventory_id')])[{row}]"))
                    ).text
                break
        if example_sku: break

        print(f"{example_inventory_id} - {example_sku}")

    time.sleep(1)


def totry():
    driver = set_up_driver()
    driver.get("https://patagonia.linets.cl/admin/md_shopify/inventory/?location_name=CD&o=-4&p=0&q=")

    login = check_login_required(driver)
    if login:
        login.send_keys(user + Keys.TAB + pwd + Keys.TAB + Keys.ENTER)

    inventory_id, sku = check_sku_example_with_difference(driver)
    inventory_level = get_shopify_inventory_level_object(inventory_id)
    if inventory_level:
        print(check_last_update_was_today(inventory_level['updated_at']))
    print(inventory_level)



def check_sku_example_with_difference(driver):
    example_sku = None
    example_inventory_id = None
    # Will check max 6 pages to the inventory table.
    try:
        for actual_page in range(1, 6):
            driver.get(f"https://patagonia.linets.cl/admin/md_shopify/inventory/?location_name=CD&o=-4&p={actual_page}&q=")
            # There are max 100 rows for each page in inventory table paginated.
            for row in range(1, 100):
                stock_i = WebDriverWait(driver, 4).until(
                    EC.visibility_of_element_located((By.XPATH, f"(//td[contains(@class ,'field-quantity')])[{row}]"))
                )
                stock_c = WebDriverWait(driver, 4).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, f"(//td[contains(@class ,'field-new_quantityXX')])[{row}]"))
                )
                if stock_i.text != stock_c.text:
                    example_sku = \
                        WebDriverWait(driver, 4).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, f"(//td[contains(@class ,'field-sku')])[{row}]"))
                        ).text
                    example_inventory_id = \
                        WebDriverWait(driver, 4).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, f"(//td[contains(@class ,'field-inventory_id')])[{row}]"))
                        ).text
                    break
            if example_sku:
                print(f"{example_inventory_id} - {example_sku}")
                break
        return example_inventory_id, example_sku
    except (NoSuchElementException, TimeoutException) as err:
        print(err)
        return False, False


def get_shopify_inventory_level_object(inventory_id):
    try:
        shopify.ShopifyResource.set_site(shop_URL)
        return json.loads(
            shopify.InventoryLevel.find_first(inventory_item_ids=inventory_id, location_ids=5611814967).to_json()
        )['inventory_level']
    except (ValueError, AttributeError) as err:
        print(err)
        print("Error")
        return False


def check_last_update_was_today(last_updated_datetime):
    print(f"last_updated_datetime: {last_updated_datetime}")
    return dt.fromisoformat(last_updated_datetime).date() == dt.now().date()



def __main__():
    totry()
    #get_sku_to_write_example()
    #check_shopify()
    #get_shopify_inventory_info(34303497535572)



__main__()


