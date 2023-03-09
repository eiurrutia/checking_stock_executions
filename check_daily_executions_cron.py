import json
import locale
import smtplib
import shopify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions \
    import SessionNotCreatedException, WebDriverException, \
    NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from datetime import datetime as dt
from dateutil import tz
from local_settings import *


user = MD_USER
pwd = MD_PWD
url = MD_URL
shop_URL = SHOP_URL


def set_up_driver(local=False):
    try:
        op = webdriver.ChromeOptions()
        if local:
            ser = Service(
                ChromeDriverManager().install()
            )
            op.add_argument('headless')
            op.add_argument('--no-sandbox')
            op.add_argument('--disable-dev-shm-usage')
        else:
            ser = Service(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            )
            op.add_argument('headless')
            op.add_argument('--no-sandbox')
            op.add_argument('--disable-dev-shm-usage')
            op.add_argument("--remote-debugging-port=4444")
        return webdriver.Chrome(service=ser, options=op)
    except (SessionNotCreatedException, WebDriverException) as err:
        print(f"{dt.now()} - {err.msg}")
        send_error_mail(f"{dt.now()} - {err.msg}")
        return False


def check_login_required(driver):
    try:
        return WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//input[@id='id_username']")
            )
        )
    except (TimeoutError, WebDriverException) as err:
        print(err.msg)
        send_error_mail(f"{dt.now()} - {err.msg}")
        return False


def get_last_middleware_execution(driver):
    try:
        driver.get(f"{url}/azure_sql/erpstock/")
        driver.maximize_window()
        return driver.find_element(
            "xpath",
            "(//td[contains(@class,'field-syncstartdatetime nowrap')])[1]"
        ).text
    except NoSuchElementException as err:
        print(err.msg)
        send_error_mail(f"{dt.now()} - {err.msg}")
        return False


def get_wms_service_date(driver):
    try:
        driver.get(f"{url}/wms/wmsstock/")
        driver.maximize_window()
        return driver.find_element(
            "xpath",
            "(//td[contains(@class,'field-registered_dt nowrap')])[1]"
        ).text
    except NoSuchElementException as err:
        print(err.msg)
        send_error_mail(f"{dt.now()} - {err.msg}")
        return False


def check_execution_is_today(execution_date):
    # With setLocale, we can parse the name of the months in Spanish
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    date_today = dt.now().date()
    execution_date = execution_date.replace("de ", "").replace("a las ", "")
    execution_datetime = dt.strptime(execution_date, '%d %B %Y %H:%M')
    return execution_datetime.date() == date_today


def check_sku_example_with_difference(driver):
    example_sku = None
    example_inventory_id = None
    # Will check max 6 pages to the inventory table.
    try:
        for actual_page in range(0, 100):
            driver.get(
                f"{url}/md_shopify/inventory"
                "/?location_name=CD&o=-4&p={actual_page}&q="
            )
            # There are max 100 rows for each page in inventory table
            inventory_table_element = \
                WebDriverWait(driver, 4).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, f"(//*[@id='result_list'])/tbody"))
                )
            inventory_rows_list = [
                i.split() for i in inventory_table_element.text.split('\n')
            ]
            for i in inventory_rows_list:
                # Compare Stock I. (index 3) with Stock C. (index 4)
                if i[3] != i[4]:
                    # Save sku (index 1) and shopify_inventory_id (index 0)
                    example_sku = i[1]
                    example_inventory_id = i[0]
                    print(i)
                    break
            if example_sku:
                print(f"{example_inventory_id} - {example_sku}")
                break
        return example_inventory_id, example_sku
    except (NoSuchElementException, TimeoutException) as err:
        print(err)
        send_error_mail(f"{dt.now()} - {err.msg}")
        return False, False


def get_shopify_inventory_level_object(inventory_id):
    try:
        print('inventory_id: ', inventory_id)
        shopify.ShopifyResource.set_site(shop_URL)
        return json.loads(
            shopify.InventoryLevel.find_first(
                inventory_item_ids=inventory_id,
                location_ids=5611814967).to_json()
        )['inventory_level']
    except (ValueError, AttributeError) as err:
        print(err)
        send_error_mail(f"{dt.now()} - {err}")
        return False


def check_last_shopify_update_was_today(last_updated_datetime):
    print(f"last_updated_datetime: {last_updated_datetime}")
    return dt.fromisoformat(last_updated_datetime).date() == dt.now().date()


def parse_date_to_correct_timezone(execution_date):
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz('America/Santiago')
    execution_date = execution_date.replace("de ", "").replace("a las ", "")
    execution_datetime = dt.strptime(execution_date, '%d %B %Y %H:%M')
    execution_datetime = execution_datetime.replace(tzinfo=from_zone)
    execution_datetime = execution_datetime.astimezone(to_zone)
    return execution_datetime.strftime('%d %B %Y %H:%M')


def send_mail_results(last_md_execution_date, wms_service_date,
                      shopify_loaded_date, shopify_loaded_sku):
    if last_md_execution_date and wms_service_date and shopify_loaded_date\
        and check_execution_is_today(last_md_execution_date)\
            and check_last_shopify_update_was_today(shopify_loaded_date):
        result = "Successful"
        last_md_execution_date = \
            parse_date_to_correct_timezone(last_md_execution_date)
        print("Execution Successful!")
    else:
        result = "FAILED"
        print("Execution Failed!!")

    today_date_text = dt.now().strftime('%d/%m/%Y')
    sent_from = 'keko.up9@gmail.com'
    to = ['enrique.urrutia@patagonia.com']
    subject = result + ' | ' + 'Execution report ' + today_date_text
    body = """
    {}
    Online Stock execution result for today {} was {}.
    Last Execution: {}
    WMS Execution: {}
    Shopify Loaded data: {} | {}
    """.format(
        result,
        today_date_text,
        result,
        last_md_execution_date,
        wms_service_date,
        shopify_loaded_date,
        shopify_loaded_sku
    )
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


def send_error_mail(message):
    today_date_text = dt.now().strftime('%d/%m/%Y')
    sent_from = 'keko.up9@gmail.com'
    to = ['enrique.urrutia@patagonia.com']
    subject = 'ERROR | ' + 'Execution report ' + today_date_text
    body = """
    ERROR
    It was an error with the today's execution:
    {}
    """.format(message)
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
    if not driver: return
    driver.get(f"{url}/md_shopify/inventory/")

    login = check_login_required(driver)
    if login:
        login.send_keys(user + Keys.TAB + pwd + Keys.TAB + Keys.ENTER)

    inventory_id, sku = check_sku_example_with_difference(driver)
    inventory_level = get_shopify_inventory_level_object(inventory_id)
    last_shopify_update = \
        inventory_level['updated_at'] if inventory_level else False

    send_mail_results(
        get_last_middleware_execution(driver),
        get_wms_service_date(driver),
        last_shopify_update,
        sku
    )
    driver.close()


if __name__ == "__main__":
    check_correct_execution()
