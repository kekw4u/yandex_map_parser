import json
from typing import List, Any
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By
from time import sleep


class YandexMapParser:

    URL = 'https://yandex.ru/maps/'
    RESPONSE_WAITING_TIME = 5
    SCROLL_PAUSE_TIME = 1
    DEFAULT_HEIGHT = 2000

    def __init__(self, city: str, district: str, shop: str) -> None:
        self.city = city
        self.district = district
        self.shop = shop

    def __chrome_options(self) -> webdriver.ChromeOptions:
        service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.add_argument('--window-size=1920,1080')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
        return options

    def get_responses(self) -> list[Any | None]:
        options = self.__chrome_options()

        driver = webdriver.Chrome(options)
        driver.get(self.URL)

        search_bar = driver.find_element(By.CLASS_NAME, "input__control")
        search_bar.send_keys(self.city+self.district, Keys.ENTER)
        sleep(self.RESPONSE_WAITING_TIME)
        search_bar.send_keys(self.shop, Keys.ENTER)
        sleep(self.RESPONSE_WAITING_TIME)

        side_panel = driver.find_element(By.CLASS_NAME, 'search-list-view__content')
        scroll_origin = ScrollOrigin.from_element(side_panel)
        total_height = self.DEFAULT_HEIGHT

        while True:
            ActionChains(driver).scroll_from_origin(scroll_origin, 0, total_height).perform()
            sleep(self.SCROLL_PAUSE_TIME)
            try:
                driver.find_element(By.CLASS_NAME, "add-business-view")
                total_height += self.DEFAULT_HEIGHT
                break
            except:
                continue
        def processLog(log):
            logtext = log["message"]
            logjson = json.loads(log["message"])["message"]
            try:
                # TODO: Фильтровать ответы, наверное, можно лучше
                if ("api/search" in logtext):
                    try:
                        body = driver.execute_cdp_cmd('Network.getResponseBody',
                                                      {'requestId': logjson["params"]["requestId"]})
                        body = json.loads(body['body'])
                        if "totalResultCount" in body['data']:
                            return body
                    except:
                        return
            except:
                return

        logs = driver.get_log("performance")
        responses = [processLog(log) for log in logs if processLog(log) != None]
        return responses

    def parse_responses(self):
        data = ''
        responses = self.get_responses()
        for response in responses:
            for item in response['data']['items']:
                title = item['title']
                address = item['address']
                try:
                    rating = item['ratingData']['ratingValue']
                except:
                    rating = ''
                try:
                    phone = item['phones'][0]['number']
                except:
                    phone = ''
                try:
                    url = item['urls'][0]
                except:
                    url = ''
                res_str = title + ' ' + address + ' ' +str(rating) +' '+phone +' '+ url + '\n'
                if item['type'] == 'business' and res_str not in data:
                    data += res_str
        return data

    def upload_data(self) -> None:
        data = self.parse_responses()
        filename = f'data/{self.city+" "+self.district+" "+self.shop}'
        with open(filename, mode='w', encoding='utf-8') as fp:
            fp.write(data)


if __name__ == '__main__':
    ymp = YandexMapParser('Витебск ', '', ' Сантехника')
    ymp.upload_data()
