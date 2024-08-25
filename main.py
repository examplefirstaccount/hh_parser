import multiprocessing as mp
import re
import time

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


def convert_dict_values(input_dict):
    output_dict = {}

    for key, value in input_dict.items():
        # Remove all types of spaces
        cleaned_value = re.sub(r'\s+', '', value)

        # Handle percent values
        if cleaned_value.endswith('%'):
            cleaned_value = cleaned_value[:-1]  # Remove '%' from the value
            key += ' %'  # Add '%' to the key

        # Convert the value to a float or int
        if '.' in cleaned_value:
            converted_value = float(cleaned_value)
        else:
            converted_value = int(cleaned_value)

        output_dict[key] = converted_value

    return output_dict


class Worker(mp.Process):
    def __init__(self, ids_to_parse, name, result_list, stop_ev=mp.Event(), daemon=True):
        self.ids_to_parse = ids_to_parse
        self.result_list = result_list
        self.driver = None
        self.stop_ev = stop_ev
        super().__init__(name=name, daemon=daemon)

    def scroll_and_click(self, element):
        actions = ActionChains(self.driver)
        self.driver.execute_script("arguments[0].scrollIntoViewIfNeeded();", element)
        WebDriverWait(self.driver, 10).until(ec.element_to_be_clickable(element))
        actions.move_to_element(element).click().perform()

    def get_badges_data(self, wrapper_cls: str, item_cls: str, title_cls: str, value_cls: str) -> dict:
        try:
            WebDriverWait(self.driver, 30).until(lambda d: d.find_element(By.CLASS_NAME, value_cls).text != '-')
            badges_wrap = self.driver.find_element(By.CLASS_NAME, wrapper_cls)
            badges = badges_wrap.find_elements(By.CLASS_NAME, item_cls)

            data = dict()
            for badge in badges:
                key = badge.find_element(By.CLASS_NAME, title_cls).text
                value = badge.find_element(By.CLASS_NAME, value_cls).text
                data[key] = value
            return convert_dict_values(data)
        except Exception as e:
            print(f"Error parsing badge: {e}")

    def run(self):
        self.driver = uc.Chrome(user_multi_procs=True)
        self.driver.get(LINK)
        WebDriverWait(self.driver, 30).until(ec.presence_of_element_located((By.CLASS_NAME, ELEMENT_CLASS)))

        for el_id in self.ids_to_parse:
            element = self.driver.find_element(By.ID, el_id)
            region = element.text
            data = {REGION_COL: region}
            try:
                self.scroll_and_click(element)
                data.update(self.get_badges_data(REGION_INFO_WRAP, INFO_ITEM, INFO_TITLE, INFO_VALUE))
                data.update(self.get_badges_data(BADGES_WRAP, BADGE, BADGE_TITLE, BADGE_VALUE))
                self.result_list.append(data)
                print(f"Successfully parsed data for {region}")
            except Exception as e:
                print(f"Error parsing data for {region}: {e}")

            time.sleep(0.5)

    def start(self) -> None:
        super().start()


LINK = 'https://stats.hh.ru/'
REGION_COL = 'Субъект'

CONTAINER_CLASS = "_regions_39f95_341"
ELEMENT_CLASS = "_region_39f95_312"

REGION_INFO_WRAP = '_regionInfo_1fsky_120'
INFO_ITEM = '_infoItem_1fsky_181'
INFO_TITLE = '_infoTitle_1fsky_192'
INFO_VALUE = '_infoValue_1fsky_207'

BADGES_WRAP = '_badgesContainer_171fz_14'
BADGE = '_shortInfo_1sluz_183'
BADGE_TITLE = '_text_1dgql_1'
BADGE_VALUE = '_value_1sluz_281'
BADGE_VALUE_NEG = '_negative_1sluz_299'


def main(num_processes: int):
    # Get total number of elements to parse
    driver = uc.Chrome()
    driver.get(LINK)
    container = WebDriverWait(driver, 30).until(ec.presence_of_element_located((By.CLASS_NAME, CONTAINER_CLASS)))
    elements = container.find_elements(By.CLASS_NAME, ELEMENT_CLASS)
    element_ids = [element.get_attribute('id') for element in elements if element.get_attribute('id')]
    total_elements = len(elements)
    driver.quit()

    # Set up processes
    workers = []
    chunk_size = total_elements // num_processes
    result_list = mp.Manager().list()

    for i in range(num_processes):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i != num_processes - 1 else total_elements
        to_parse = element_ids[start_idx:end_idx]
        worker = Worker(name=f'worker-{i+1}', ids_to_parse=to_parse, result_list=result_list)
        workers.append(worker)

    start_time = time.time()
    for w in workers:
        w.start()

    for w in workers:
        w.join()

    # End time for the entire program
    end_time = time.time()

    # Calculate total time, average time per thread, and average time per region
    total_time = end_time - start_time
    avg_thread_time = total_time / num_processes
    avg_region_time = total_time / total_elements

    # Print the time statistics
    print(f"Total time for the program: {total_time:.2f} seconds")
    print(f"Average time per thread: {avg_thread_time:.2f} seconds")
    print(f"Average time per region: {avg_region_time:.2f} seconds")

    # Convert the result list to a DataFrame and save it to an Excel file
    df = pd.DataFrame(list(result_list))
    df.to_excel('parsed_data.xlsx', index=False)
    print("Data saved to parsed_data.xlsx")


if __name__ == '__main__':
    NUM_PROCESSES = 1
    main(NUM_PROCESSES)
