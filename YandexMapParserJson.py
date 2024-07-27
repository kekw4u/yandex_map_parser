import json
from typing import List, Any
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
    CLICK_WAITING_TIME = 0.5
    DEFAULT_HEIGHT = 2000


    SEARCH_BAR_CONDITIONS = (By.CLASS_NAME, "input__control")
    SIDE_PANEL_CONDITIONS = (By.CLASS_NAME, "search-list-view__content")
    SEARCH_BUTTON_CONDITIONS = (
        By.XPATH, "//button[@type='submit' and @aria-haspopup='false']")


    def __init__(self, cities: list, districts: list, shops: list) -> None:
        self.cities = cities if isinstance(cities, list) else [cities]
        self.districts = districts if isinstance(districts, list) else [districts]
        self.shops = shops if isinstance(shops, list) else [shops]


    @staticmethod
    def __chrome_options() -> webdriver.ChromeOptions:
        # service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.add_argument('--window-size=1920,1080')
        options.set_capability('goog:loggingPrefs', 
                               {'performance': 'ALL', 'browser': 'ALL'})
        return options


    @staticmethod
    def __get_responses(querry: list[str]) -> list[Any | None]:

        options = YandexMapParser.__chrome_options()

        driver = webdriver.Chrome(options)
        driver.get(YandexMapParser.URL)

        wait = WebDriverWait(
            driver, YandexMapParser.RESPONSE_WAITING_TIME, poll_frequency=0.5)

        search_bar = wait.until(
            EC.visibility_of_element_located(
                YandexMapParser.SEARCH_BAR_CONDITIONS))

        YandexMapParser.__insert_querry(search_bar, querry, wait)

        side_panel = wait.until(
            EC.visibility_of_element_located(
                YandexMapParser.SIDE_PANEL_CONDITIONS))

        scroll_origin = ScrollOrigin.from_element(side_panel)
        total_height = YandexMapParser.DEFAULT_HEIGHT

        while True:
            ActionChains(driver).scroll_from_origin(
                scroll_origin, 0, total_height).perform()
            sleep(YandexMapParser.SCROLL_PAUSE_TIME)
            try:
                driver.find_element(By.CLASS_NAME, "add-business-view")
                total_height += YandexMapParser.DEFAULT_HEIGHT
                break
            except:
                continue

        logs = driver.get_log("performance")
        responses = [YandexMapParser.__process_log(log, driver) for log in logs
                     if YandexMapParser.__process_log(log, driver) != None]
        return responses


    @staticmethod
    def __insert_querry(search_bar: WebElement,
                        querry: list[str], wait: WebDriverWait) -> None:
        city, district, shop = querry
        for part in [f'{city} {district}', f' {shop}']:
            search_bar.send_keys(part, Keys.ENTER)

            sleep(YandexMapParser.CLICK_WAITING_TIME)

            wait.until(
                EC.visibility_of_element_located(
                    YandexMapParser.SEARCH_BUTTON_CONDITIONS))


    @staticmethod
    def __process_log(log: dict, driver: webdriver) -> dict:
        log_text = log["message"]
        log_json = json.loads(log["message"])["message"]
        try:
            if ("api/search" in log_text):
                try:
                    request_id = log_json['params']['requestId']
                    body = driver.execute_cdp_cmd('Network.getResponseBody',
                                                  {'requestId': request_id})
                    body_dict = json.loads(body['body'])
                    if "totalResultCount" in body_dict['data']:
                        return body_dict
                except:
                    return
        except:
            return


    @staticmethod
    def __parse_responses(querry: list[str]) -> list[dict]:
        data = []
        responses = YandexMapParser.__get_responses(querry)

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
                        metro_station_dict = {
                            'station_name': metro_station['name'], 
                            'station_distance': metro_station['distanceValue']}
                        shop['nearest_metro_stations'].append(
                            metro_station_dict)

                if 'stops' in item_keys:
                    shop['nearest_bus_stops'] = []
                    for bus_stop in item['stops']:
                        bus_stop_dict = {
                            'bus_stop_name': bus_stop['name'], 
                            'bus_stop_distance': bus_stop['distanceValue']}
                        shop['nearest_bus_stops'].append(bus_stop_dict)

                if item['type'] == 'business' and shop not in data:
                    data.append(shop)
        return data


    @staticmethod
    def upload_data(querry: list[str]) -> None:
        data = YandexMapParser.__parse_responses(querry)
        city, district, shop = querry
        filename = f'data/{city} {district} {shop}.json'
        with open(filename, mode='w', encoding='utf-8') as fp:
            fp.write(json.dumps(data))


    def upload_all_data(self) -> None:
        for city in self.cities:
            for district in self.districts:
                for shop in self.shops:
                    self.upload_data([city, district, shop])
