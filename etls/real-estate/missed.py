"""
Scraper script for handling 'too many results' suburbs.
Breaks down searches by price range to ensure all properties are captured.
"""

import atexit
import json
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from utils import html_to_dict, value_to_dict, wait_until_ready

PAGE_SIZE_LIMIT = 20
MAX_PROPERTIES_LIMIT = 1_000

# Get information from the data folder
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
ids_file = Path("ids.txt")

ids = set()

if ids_file.exists():
    with ids_file.open(encoding="utf-8") as f:
        ids = {line.strip() for line in f if line.strip()}

# Load in done webpages
loaded_file = Path("loaded.txt")
if loaded_file.exists():
    with loaded_file.open(encoding="utf-8") as f:
        loaded = {line.strip() for line in f}
else:
    loaded = set()

# Create webpages
toomany_file = Path("toomany.txt")
if toomany_file.exists():
    with toomany_file.open(encoding="utf-8") as f:
        webpages = {line.strip() for line in f}
else:
    webpages = set()

price_ranges = [f"{10_000 * i}-{10_000 * i + 9_999}" for i in range(100)]
price_ranges.append("1000000-1500000")
price_ranges.append("1500000-any")

# Create selenium driver
options = Options()
options.add_argument("-headless")
driver = webdriver.Firefox(options=options)
atexit.register(driver.quit)

# Scrape them
for webpage in webpages:
    for price_range in price_ranges:
        for i in range(1, 51):
            url = webpage + "&price=" + price_range + "&page=" + str(i)
            if url in loaded:
                continue
            print(url)
            last_page = False
            driver.get(url)
            if not wait_until_ready(driver):
                print("Timed out waiting for page: " + url)
                continue
            if "The requested URL was not found on the server." in driver.page_source:
                print("URL not found: " + url)
                msg = f"URL not found: {url}"
                raise RuntimeError(msg)
            if "No exact matches" in driver.page_source:
                loaded.add(url)
                with loaded_file.open("a", encoding="utf-8") as f:
                    f.write(url + "\n")
                break
            if i == 1:
                search_string = '"searchResultCount":'
                start = driver.page_source.find(search_string) + len(search_string)
                end = driver.page_source[start:].find(",")
                number_of_properties = int(driver.page_source[start : start + end])
                print("Number of Properties:", number_of_properties)
                if number_of_properties <= PAGE_SIZE_LIMIT:
                    last_page = True
                elif number_of_properties > MAX_PROPERTIES_LIMIT:
                    print("Over 1000 properties at URL: " + url)
                    msg = f"Over 1000 properties at URL: {url}"
                    raise RuntimeError(msg)
            property_dictionary = html_to_dict(driver.page_source)
            for value in property_dictionary.values():
                prop_id = str(value["id"])
                if prop_id in ids:
                    continue
                ids.add(prop_id)
                data = value_to_dict(value)

                # Save JSON file
                with (data_dir / f"{prop_id}.json").open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

                # Update ids.txt
                with ids_file.open("a", encoding="utf-8") as f:
                    f.write(prop_id + "\n")

            loaded.add(url)
            with loaded_file.open("a", encoding="utf-8") as f:
                f.write(url + "\n")
            if last_page:
                break
