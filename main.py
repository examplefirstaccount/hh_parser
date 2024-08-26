import asyncio
import re
import time
from multiprocessing import Process, Manager

import pandas as pd
from playwright.async_api import async_playwright, BrowserContext, Page


LINK = 'https://stats.hh.ru/'
REGION_COLUMN_NAME = 'Субъект'

REGIONS_WRAP = '_regions_39f95_341'
REGION_EL = '_region_39f95_312'

SIDE_INFO_WRAP = '_regionInfo_1fsky_120'
SIDE_INFO_ITEM = '_infoItem_1fsky_181'
SIDE_INFO_TITLE = '_infoTitle_1fsky_192'
SIDE_INFO_VALUE = '_infoValue_1fsky_207'

BOTM_INFO_WRAP = '_badgesContainer_171fz_14'
BOTM_INFO_ITEM = '_shortInfo_1sluz_183'
BOTM_INFO_TITLE = '_text_1dgql_1'
BOTM_INFO_VALUE = '_value_1sluz_281'
BOTM_INFO_VALUE_NEG = '_negative_1sluz_299'


def chunked(iterable, *, chunk_size=None, num_chunks=None):
    if chunk_size is not None and num_chunks is not None:
        raise ValueError('Specify either chunk_size or num_chunks, not both.')

    if chunk_size is not None:
        if chunk_size <= 0:
            raise ValueError('chunk_size must be a positive integer.')
        return [iterable[i:i + chunk_size] for i in range(0, len(iterable), chunk_size)]

    if num_chunks is not None:
        if num_chunks <= 0:
            raise ValueError('num_chunks must be a positive integer.')
        sublists = [[] for _ in range(num_chunks)]
        for i, item in enumerate(iterable):
            sublists[i % num_chunks].append(item)
        return sublists

    raise ValueError('You must specify either chunk_size or num_chunks.')


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


async def get_elements_to_parse() -> list:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(LINK)
        container = await page.wait_for_selector(f'.{REGIONS_WRAP}')
        elements = await container.query_selector_all(f'.{REGION_EL}')
        element_ids = [await element.get_attribute('id') for element in elements if await element.get_attribute('id')]

        await browser.close()

    return element_ids


async def get_badges_data(page: Page, wrapper_cls: str, item_cls: str, title_cls: str, value_cls: str) -> dict:
    try:
        await page.wait_for_selector(f'.{value_cls}', state='attached')
        await page.wait_for_function(
            f"document.getElementsByClassName('{value_cls}')[0].innerText !== '-'"
        )
        badges_wrap = await page.query_selector(f'.{wrapper_cls}')
        badges = await badges_wrap.query_selector_all(f'.{item_cls}')

        data = dict()
        for badge in badges:
            key = await (await badge.query_selector(f'.{title_cls}')).inner_text()
            value = await (await badge.query_selector(f'.{value_cls}')).inner_text()
            data[key] = value
        return convert_dict_values(data)
    except Exception as e:
        print(f'Error parsing badge: {e}')


async def process_tab(ids_to_parse: list, context: BrowserContext) -> list[dict]:
    page = await context.new_page()
    try:
        await page.goto(LINK)
        await page.wait_for_selector(f'.{REGION_EL}')

        regions_data = list()
        for el_id in ids_to_parse:
            element = page.locator(f"[id='{el_id}']").first
            region = await element.inner_text()
            data = {REGION_COLUMN_NAME: region}
            try:
                await element.scroll_into_view_if_needed()
                await element.click()

                data.update(await get_badges_data(page, SIDE_INFO_WRAP, SIDE_INFO_ITEM,
                                                  SIDE_INFO_TITLE, SIDE_INFO_VALUE))

                data.update(await get_badges_data(page, BOTM_INFO_WRAP, BOTM_INFO_ITEM,
                                                  BOTM_INFO_TITLE, BOTM_INFO_VALUE))

                regions_data.append(data)
                print(f'Successfully parsed data for {region}')
            except Exception as e:
                print(f'Error processing region {region}: {e}')

        return regions_data

    except Exception as e:
        print(f'Error processing ids {ids_to_parse}: {e}')


async def run(ids_to_parse: list, max_tabs: int, headless: bool = False):
    lock = asyncio.Lock()
    regions_data = list()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()

        ids_chunked = chunked(ids_to_parse, num_chunks=max_tabs)
        tasks = [process_tab(chunk, context) for chunk in ids_chunked]
        for task_future in asyncio.as_completed(tasks):
            chunk_regions_data = await task_future
            async with lock:
                regions_data.extend(chunk_regions_data)

        await browser.close()

    return regions_data


def worker(chunk, max_tabs, headless, return_list):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(run(chunk, max_tabs, headless))
    return_list.extend(result)


def main(num_processes: int, num_tabs: int, headless: bool):
    # Get total number of elements to parse
    element_ids = asyncio.run(get_elements_to_parse())
    total_elements = len(element_ids)
    print(f'Total number of elements to parse: {total_elements}')

    # Set up processes
    start_time = time.time()
    ids_chunked = chunked(element_ids, num_chunks=num_processes)

    # Processes Variant 1.
    manager = Manager()
    return_list = manager.list()
    processes = []

    for chunk in ids_chunked:
        process = Process(target=worker, args=(chunk, num_tabs, headless, return_list))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    all_results = list(return_list)

    # Processes Variant 2.
    # with ProcessPoolExecutor() as executor:
    #     loop = asyncio.get_event_loop()
    #     futures = [
    #         loop.run_in_executor(
    #             executor,
    #             asyncio.run,
    #             run(chunk, num_tabs, headless)
    #         )
    #         for chunk in ids_chunked
    #     ]
    #     results = loop.run_until_complete(asyncio.gather(*futures))
    # all_results = [item for sublist in results for item in sublist]

    # End time for the entire program
    end_time = time.time()

    # Calculate total time, average time per thread, and average time per region
    total_time = end_time - start_time
    avg_thread_time = total_time / num_processes
    avg_region_time = total_time / total_elements

    # Print the time statistics
    print(f'Total time for the program: {total_time:.2f} seconds')
    print(f'Average time per thread: {avg_thread_time:.2f} seconds')
    print(f'Average time per region: {avg_region_time:.2f} seconds')

    # Convert the result list to a DataFrame and save it to an Excel file
    df = pd.DataFrame(all_results)
    df.sort_values(by=REGION_COLUMN_NAME).to_excel('data.xlsx', index=False)
    print('Data saved to data.xlsx')


if __name__ == '__main__':
    NUM_PROCESSES = 2
    NUM_TABS = 4
    HEADLESS = True
    main(NUM_PROCESSES, NUM_TABS, HEADLESS)

# p=1, t=3, urls=12;  28.51s
# p=2, t=3, urls=12;  25.83s
# p=2, t=4, urls=110; 75.56s
# p=2, t=4, urls=111; 70.54s - 0.64s/region
