import json
from time import sleep
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By

RESPONSE_WAITING_TIME = 5
SCROLL_PAUSE_TIME = 1
DEFAULT_HEIGHT = 2000

def map_parser(url, city, district, corner):
    #Настройка webdriver'а
    service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument('--enable-logging')
    options.add_argument('--log-level=0')
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})

    driver = webdriver.Chrome(service = service, options=options)
    driver.set_window_size(1920, 1080)
    driver.get(url)
    #Поиск строки для адреса
    search_bar = driver.find_element(By.CLASS_NAME, "input__control")
    search_bar.send_keys(city+' ', Keys.ENTER)
    sleep(RESPONSE_WAITING_TIME)
    search_bar.send_keys(corner, Keys.ENTER)
    sleep(RESPONSE_WAITING_TIME)

    #Перемещаем мышку к списку магазинов и листаем вниз, пока не появится div с классом add-business-view
    element = driver.find_element(By.CLASS_NAME, 'search-list-view__content')
    scroll_origin = ScrollOrigin.from_element(element)
    d_y = 2000

    while True:
        ActionChains(driver).scroll_from_origin(scroll_origin, 0, d_y).perform()
        sleep(1)
        try:
            driver.find_element(By.CLASS_NAME, "add-business-view")
            d_y += 2000
            break
        except:
            continue

    #Дальше есть два варианта - вся информация уже получена. Выбор: обрабатывать сам скролл бар и все элементы в нём или получать json-response, который приходит при прогрузке страницы и парсить его
    #Я выбрал 2 вариант и решил парсить логи, т.к. в них больше информации
    def processLog(log):
        log = json.loads(log["message"])["message"]
        try:
            #TODO: Фильтровать ответы, наверное, можно лучше
            if ("Network.responseReceived" in log["method"] and "params" in log.keys()):
                try:
                    body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': log["params"]["requestId"]})
                    body = json.loads(body['body'])
                    if "totalResultCount" in body['data']:
                        return body
                except:
                    return
        except:
            return

    #Получаем логи
    logs = driver.get_log("performance")

    #Получаем все ответы
    responses = [processLog(log) for log in logs if processLog(log) != None]
    items = []
    for entry in responses:
        try:
            items.append(entry['data']['items'])
        except:
            continue
    #В принципе, в items лежит вся нужная нам информация
    print(items)
    # Закрытие драйвера
    sleep(10)
    driver.quit()

map_parser("https://yandex.ru/maps/",'Алейск ', '',' Аникс')