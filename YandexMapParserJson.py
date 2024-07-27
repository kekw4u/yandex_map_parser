import json
from typing import List, Any

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from time import sleep


class YandexMapParser:
    URL = 'https://yandex.ru/maps/'
    RESPONSE_WAITING_TIME = 15
    SCROLL_PAUSE_TIME = 1
    CLICK_WAITING_TIME = 1
    DEFAULT_HEIGHT = 2000

    SEARCH_BAR_CONDITIONS = (By.CLASS_NAME, "input__control")
    SIDE_PANEL_CONDITIONS = (By.CLASS_NAME, "search-list-view__content")
    SEARCH_BUTTON_CONDITIONS = (By.XPATH, "//button[@type='submit' and @aria-haspopup='false']")
    ONE_SHOP_CARD_CLASS = "business-card-view__main-wrapper"
    END_OF_LIST_CLASS = "add-business-view"

    def __init__(self, city: str, district: str, shop: str) -> None:
        self.city = city
        self.district = district
        self.shop = shop

    def __chrome_options(self) -> webdriver.ChromeOptions:
        # service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.add_argument('--window-size=1920,1080')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
        return options

    def __get_responses(self) -> list[Any | None]:

        options = self.__chrome_options()

        driver = webdriver.Chrome(options)
        driver.get(self.URL)

        wait = WebDriverWait(driver, self.RESPONSE_WAITING_TIME, poll_frequency=0.5)
        search_bar = wait.until(EC.visibility_of_element_located(self.SEARCH_BAR_CONDITIONS))

        self.__insert_querry(search_bar, wait)

        try:
            driver.find_element(By.CLASS_NAME, self.ONE_SHOP_CARD_CLASS)
            logs = driver.get_log("performance")
            responses = [YandexMapParser.__process_log(log, driver) for log in logs
                         if YandexMapParser.__process_log(log, driver) is not None]
            return responses
        except selenium.common.exceptions.NoSuchElementException:
            side_panel = wait.until(EC.visibility_of_element_located(self.SIDE_PANEL_CONDITIONS))

        scroll_origin = ScrollOrigin.from_element(side_panel)
        total_height = self.DEFAULT_HEIGHT

        while True:
            ActionChains(driver).scroll_from_origin(scroll_origin, 0, total_height).perform()
            sleep(self.SCROLL_PAUSE_TIME)
            try:
                driver.find_element(By.CLASS_NAME, self.END_OF_LIST_CLASS)
                total_height += self.DEFAULT_HEIGHT
                break
            except:
                continue

        logs = driver.get_log("performance")
        responses = [YandexMapParser.__process_log(log, driver) for log in logs
                     if YandexMapParser.__process_log(log, driver) is not None]
        return responses

    def __insert_querry(self, search_bar: WebElement, wait: WebDriverWait) -> None:
        for part in [f'{self.city} {self.district}', f' {self.shop}']:
            search_bar.send_keys(part, Keys.ENTER)
            sleep(self.CLICK_WAITING_TIME)
            wait.until(EC.visibility_of_element_located(self.SEARCH_BUTTON_CONDITIONS))

    @staticmethod
    def __process_log(log: dict, driver: webdriver) -> dict:
        log_text = log["message"]
        log_json = json.loads(log["message"])["message"]
        try:
            if ("api/search" in log_text):
                try:
                    request_id = log_json['params']['requestId']
                    body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                    body_dict = json.loads(body['body'])
                    if "totalResultCount" in body_dict['data']:
                        return body_dict
                except:
                    return
        except:
            return

    def __parse_responses(self) -> list[dict]:
        data = []
        responses = self.__get_responses()

        for response in responses:
            for item in response['data']['items']:
                shop = {}
                item_keys = item.keys()
                params = ['title', 'address', 'ratingData', 'phones',
                          'urls', 'workingTimeText', 'socialLinks']

                for param in params:
                    if param in item_keys:
                        shop[param] = item[param]

                if 'metro' in item_keys:
                    shop['nearest_metro_stations'] = []
                    for metro_station in item['metro']:
                        metro_station_dict = {'station_name': metro_station['name'],
                                              'station_distance': metro_station['distanceValue']}
                        shop['nearest_metro_stations'].append(metro_station_dict)

                if 'stops' in item_keys:
                    shop['nearest_bus_stops'] = []
                    for bus_stop in item['stops']:
                        bus_stop_dict = {'bus_stop_name': bus_stop['name'],
                                         'bus_stop_distance': bus_stop['distanceValue']}
                        shop['nearest_bus_stops'].append(bus_stop_dict)

                if item['type'] == 'business' and shop not in data:
                    data.append(shop)
        return data

    def upload_data(self) -> None:
        data = self.__parse_responses()
        filename = f'data/{self.city} {self.district} {self.shop}.json'
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False)
