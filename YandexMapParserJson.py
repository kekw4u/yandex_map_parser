import json
from typing import Any
from time import sleep, time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class YandexMapParser:
    URL = 'https://yandex.ru/maps/'
    RESPONSE_WAITING_TIME = 15
    TIMEOUT_LOADING_COUNTER = 15
    SCROLL_PAUSE_TIME = 0.5
    CLICK_WAITING_TIME = 1
    DEFAULT_HEIGHT = 2000

    SEARCH_BAR_CLASS = "input__control"
    SIDE_PANEL_CLASS = "search-list-view__content"
    ONE_SHOP_CARD_CLASS = "business-card-view__main-wrapper"
    END_OF_LIST_CLASS = "add-business-view"
    SEARCH_BUTTON_XPATH = "//button[@type='submit' and @aria-haspopup='false']"

    def __init__(self, cities: list, districts: list, objects: list) -> None:
        self.cities = cities if isinstance(cities, list) else [cities]
        self.districts = districts if isinstance(districts, list) else [districts]
        self.objects = objects if isinstance(objects, list) else [objects]

    @staticmethod
    def __chrome_options() -> webdriver.ChromeOptions:

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.add_argument('--window-size=1920,1080')
        options.set_capability('goog:loggingPrefs',
                               {'performance': 'ALL', 'browser': 'ALL'})
        return options

    @staticmethod
    def __get_responses(query: list[str]) -> list[Any | None]:
        options = YandexMapParser.__chrome_options()

        driver = webdriver.Chrome(options)
        driver.get(YandexMapParser.URL)

        wait = WebDriverWait(
            driver, YandexMapParser.RESPONSE_WAITING_TIME, poll_frequency=0.5)

        search_bar = wait.until(
            EC.visibility_of_element_located(
                (By.CLASS_NAME, YandexMapParser.SEARCH_BAR_CLASS)))

        YandexMapParser.__insert_query(search_bar, query, wait)

        if not driver.find_elements(By.CLASS_NAME, YandexMapParser.ONE_SHOP_CARD_CLASS):
            YandexMapParser.__scroll(driver, wait)

        logs = driver.get_log("performance")
        responses = [response for response in
                     [YandexMapParser.__process_log(log, driver) for log in logs]
                     if response != None]

        return responses

    @staticmethod
    def __scroll(driver: webdriver, wait: WebDriverWait) -> None:
        side_panel = wait.until(EC.visibility_of_element_located(
            (By.CLASS_NAME, YandexMapParser.SIDE_PANEL_CLASS)))

        scroll_origin = ScrollOrigin.from_element(side_panel)
        total_height = YandexMapParser.DEFAULT_HEIGHT
        height_counter = 0
        last_height = side_panel.size['height']

        while True:
            if driver.find_elements(By.CLASS_NAME, YandexMapParser.END_OF_LIST_CLASS) \
                    or height_counter == YandexMapParser.TIMEOUT_LOADING_COUNTER:
                break
            ActionChains(driver).scroll_from_origin(
                scroll_origin, 0, total_height).perform()
            sleep(YandexMapParser.SCROLL_PAUSE_TIME)
            total_height += YandexMapParser.DEFAULT_HEIGHT
            current_height = side_panel.size['height']

            if last_height == current_height:
                height_counter += 1
            else:
                height_counter = 0
                last_height = current_height
            print(height_counter)

    @staticmethod
    def __insert_query(search_bar: WebElement,
                        query: list[str], wait: WebDriverWait) -> None:
        city, district, object = query
        for part in [f'{city} {district}', f' {object}']:
            search_bar.send_keys(part, Keys.ENTER)

            sleep(YandexMapParser.CLICK_WAITING_TIME)

            wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, YandexMapParser.SEARCH_BUTTON_XPATH)))

    @staticmethod
    def __process_log(log: dict, driver: webdriver) -> dict:
        log_text = log["message"]
        log_json = json.loads(log["message"])["message"]

        if "api/search" in log_text and 'params' in log_json \
                and 'requestId' in log_json['params']:

            request_id = log_json['params']['requestId']
            try:
                body = driver.execute_cdp_cmd('Network.getResponseBody',
                                          {'requestId': request_id})
            except:
                return None
            
            body_dict = json.loads(body['body'])
            if 'data' in body_dict and "totalResultCount" in body_dict['data']:
                return body_dict
              
    @staticmethod
    def __parse_responses(query: list[str]) -> list[dict]:
        data = []
        responses = YandexMapParser.__get_responses(query)

        print(f'[INFO] Got {len(responses)} responses')
        print(f'[INFO] Start parsing responses...')
        objects_count = 0

        for response in responses:
            for item in response['data']['items']:
                if item['type'] == 'business':
                    object = {}
                    item_keys = item.keys()
                    params = ['title', 'address', 'ratingData', 'phones',
                              'urls', 'workingTimeText', 'socialLinks']

                    for param in params:
                        if param in item_keys:
                            object[param] = item[param]

                    if 'metro' in item_keys:
                        object['nearest_metro_stations'] = []
                        for metro_station in item['metro']:
                            metro_station_dict = {
                                'station_name': metro_station['name'],
                                'station_distance': metro_station['distanceValue']}
                            object['nearest_metro_stations'].append(
                                metro_station_dict)

                    if 'stops' in item_keys:
                        object['nearest_bus_stops'] = []
                        for bus_stop in item['stops']:
                            bus_stop_dict = {
                                'bus_stop_name': bus_stop['name'],
                                'bus_stop_distance': bus_stop['distanceValue']}
                            object['nearest_bus_stops'].append(bus_stop_dict)

                    if object not in data:
                        data.append(object)
                        objects_count += 1
                        
        # Вывод слова зелёным цветом (возможно, стоит подключить библиотеку)
        print(f'\033[32m[SUCCESS]\033[0m')
        print(f'[INFO] {objects_count} objects were parsed')
        return data

    @staticmethod
    def upload_data(query: list[str]) -> None:
        start = time()
        
        data = YandexMapParser.__parse_responses(query)
        city, district, object = query
        filename = f'data/{city} {district} {object}.json'
        with open(filename, mode='w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        finish = time()
        print(f'[INFO] Executable time: {round(finish - start, 3)} sec')    

    def upload_all_data(self) -> None:
        for city in self.cities:
            for district in self.districts:
                for object in self.objects:
                    self.upload_data([city, district, object])
