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
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--disable-cache')
        options.add_argument("--disable-extensions")
        options.add_argument('--window-size=1920,1080')
        return options

    def __parse(self) -> str:
        options = self.__chrome_options()

        driver = webdriver.Chrome(options)
        driver.get(self.URL)

        search_bar = driver.find_element(By.CLASS_NAME, "input__control")
        search_bar.send_keys(f'{self.city} {self.district}', Keys.ENTER)
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

        cards = driver.find_elements(By.CLASS_NAME, 'search-business-snippet-view__content')
        data = ''
        for card in cards:
            try:
                rating = card.find_element(By.CLASS_NAME, 'business-rating-badge-view__rating-text').text
            except:
                rating = '-'
            title = card.find_element(By.CLASS_NAME, 'search-business-snippet-view__title').text
            address = card.find_element(By.CLASS_NAME, 'search-business-snippet-view__address').text

            data += f'{title} - [{rating}] - {address}\n'

        driver.close()
        return data

    def upload_data(self) -> None:
        data = self.__parse()
        filename = f'data/{self.city} {self.district} {self.shop}'
        with open(filename, mode='w', encoding='utf-8') as fp:
            fp.write(data)


if __name__ == '__main__':
    ymp = YandexMapParser('Витебск', '', 'Сантехника')
    ymp.upload_data()