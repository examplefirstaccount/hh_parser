# hh.ru Stats Parser

## Overview

This project is a fun, educational exercise designed to demonstrate how to parse statistical data from the [hh.ru](https://stats.hh.ru/) website using Python. The script utilizes asynchronous programming with the Playwright library to interact with the website, scrape region-specific data, and then processes this data concurrently across multiple browser tabs and processes.

**Important Note:** There is a much simpler way to access the statistics from hh.ru — by using the API endpoint at `https://stats.hh.ru/api/v1/data/RU`. This API returns a JSON file containing all the data for 2023 and 2024, eliminating the need for web scraping.

## Project Structure

The script is divided into several key functions:

- **`get_elements_to_parse()`**: Retrieves the list of region element IDs from the hh.ru stats page.
- **`get_badges_data()`**: Extracts and processes specific data from a region's page.
- **`process_tab()`**: Manages the parsing of data within a single browser tab, iterating over a list of region IDs.
- **`run()`**: Coordinates the overall parsing process, managing multiple tabs in a browser context.
- **`worker()`**: Runs the parsing tasks within a new process.
- **`main()`**: Orchestrates the entire program, setting up multiprocessing, and saving the final parsed data to an Excel file.

## Usage

### Prerequisites

- Python 3.7 or later
- The required Python packages (`playwright`, `pandas`, etc.) can be installed via `pip`:
  ```bash
  pip install pandas playwright
  ```

### Running the Script

To run the script, simply execute the following command:

```bash
python main.py
```

### Configuration

You can modify the following parameters in the `main()` function:

- **`NUM_PROCESSES`**: Number of processes to run concurrently. Each process has its own browser window.
- **`NUM_TABS`**: Number of tabs per browser window to run concurrently per process.
- **`HEADLESS`**: Set to `True` for headless operation (no browser UI).

### Performance

The script's performance varies depending on the number of processes, tabs, and regions being processed. Below are some example benchmarks:

- **p=2, t=4, regions=111**(all regions): 
  - Total time: 70.54s 
  - Average time per region: ~0.64s

The script demonstrates relatively efficient parsing, with time per region decreasing as the number of concurrent processes and tabs increases.

The Playwright library is highly capable of handling asynchronous tasks, including running 50+ tabs concurrently with ease. By increasing the NUM_TABS parameter and scaling the NUM_PROCESSES to match the number of cores on your processor (typically 8-12 cores), you can significantly boost the performance of the script, potentially reducing the time required to scrape large amounts of data. 

However, while it is technically feasible to load a server with such intense requests, it is strongly discouraged. Doing so is almost certain to trigger rate limits and could potentially overwhelm the server, leading to IP bans or other restrictions. To mitigate this, you would need to use a separate proxy for each process, but even then, this approach is not recommended due to ethical considerations and presence of API.

## Ethics and Purpose

This project is intended purely for educational purposes. Web scraping, while a valuable skill, must be approached with caution. Many websites have terms of service that restrict or prohibit automated access. Always ensure that your activities comply with the site's terms of service and consider using official APIs when available.

This script, like many pet projects, is designed to enhance learning and experimentation in Python programming. It should not be used for any commercial purposes or in ways that could overload or harm web services.
