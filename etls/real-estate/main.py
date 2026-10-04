"""
Main scraper script for Domain.com.au.
Iterates through suburbs and scrapes sold property data into a CSV file.
"""

import atexit
import json
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from utils import html_to_dict, value_to_dict, wait_until_ready

PAGE_SIZE_LIMIT = 20

# Get information from the data folder
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
ids_file = Path("ids.txt")

ids = set()
suburbs: dict[str, float] = {}
look_up: dict[str, str] = {}

if ids_file.exists():
    with ids_file.open(encoding="utf-8") as f:
        ids = {line.strip() for line in f if line.strip()}

# We still need to populate 'suburbs' and 'look_up' for the scraper logic.
# Since we no longer have 'all.csv' for the min date, we'll scan the JSON files.
print(f"Loading {len(ids)} existing properties...")
for prop_id in ids:
    prop_file = data_dir / f"{prop_id}.json"
    if prop_file.exists():
        try:
            with prop_file.open(encoding="utf-8") as f:
                data = json.load(f)
                suburb = data.get("suburb")
                date_str = data.get("date")
                state = data.get("state")
                postcode = data.get("postcode")

                if suburb and date_str:
                    date_val = float(date_str)
                    if suburb not in suburbs or date_val < suburbs[suburb]:
                        suburbs[suburb] = date_val

                    if suburb not in look_up:
                        series = f"{suburb}-{state}-{postcode}".replace(" ", "-").replace("'", "-").lower()
                        look_up[suburb] = series
        except json.JSONDecodeError, ValueError:
            continue

if not ids:
    print("No existing data found. Starting fresh.")
# Load in done webpages
loaded_file = Path("loaded.txt")
if loaded_file.exists():
    with loaded_file.open(encoding="utf-8") as f:
        loaded = {line.strip() for line in f}
else:
    loaded = set()

# Load in finished suburbs
finished_suburbs_file = Path("finished_suburbs.txt")
if finished_suburbs_file.exists():
    with finished_suburbs_file.open(encoding="utf-8") as f:
        finished_suburbs = {line.strip() for line in f}
else:
    finished_suburbs = set()

for finished_suburb in finished_suburbs:
    suburbs.pop(finished_suburb, None)

# Create selenium driver
options = Options()
options.add_argument("-headless")
driver = webdriver.Firefox(options=options)
atexit.register(driver.quit)

# Scrape them
while True:
    if not suburbs:
        break
    suburb = max(suburbs, key=suburbs.__getitem__)
    main_webpage = (
        "https://www.domain.com.au/sold-listings/" + look_up[suburb] + "/?excludepricewithheld=1&ssubs=0&page="
    )
    url = None
    for i in range(1, 51):
        webpage = main_webpage + str(i)
        if webpage not in loaded:
            url = webpage
            break

    if not url:
        with Path("toomany.txt").open("a", encoding="utf-8") as f:
            f.write(main_webpage[:-6] + "\n")
        suburbs.pop(suburb)
        continue

    date_val = str(suburbs[suburb])
    year = date_val[0:4]
    month = date_val[4:6]
    day = date_val[6:8]
    print(f"{day}/{month}/{year} : {suburb: <30} - {url}")

    driver.get(url)
    if not wait_until_ready(driver):
        print("Timed out waiting for page: " + url)
        continue
    if "The requested URL was not found on the server." in driver.page_source:
        print("URL not found: " + url)
        msg = f"URL not found: {url}"
        raise RuntimeError(msg)
    if "No exact matches" in driver.page_source:
        if "page=1" in url:
            print("No properties in suburb: " + url)
            with finished_suburbs_file.open("a", encoding="utf-8") as f:
                f.write(suburb + "\n")
            suburbs.pop(suburb)
            continue
        with finished_suburbs_file.open("a", encoding="utf-8") as f:
            f.write(suburb + "\n")
        suburbs.pop(suburb)
    else:
        property_dictionary = html_to_dict(driver.page_source)
        for value in property_dictionary.values():
            prop_id = str(value["id"])
            if prop_id in ids:
                continue
            ids.add(prop_id)
            data = value_to_dict(value)
            if data["date"] != "":
                date = float(data["date"])
                suburb_name = data["suburb"]
                if suburb_name not in suburbs or date < suburbs[suburb_name]:
                    suburbs[suburb_name] = date

            # Save JSON file
            with (data_dir / f"{prop_id}.json").open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            # Update ids.txt
            with ids_file.open("a", encoding="utf-8") as f:
                f.write(prop_id + "\n")

        if len(property_dictionary.values()) < PAGE_SIZE_LIMIT:
            with finished_suburbs_file.open("a", encoding="utf-8") as f:
                f.write(suburb + "\n")
            suburbs.pop(suburb)

    loaded.add(url)
    with loaded_file.open("a", encoding="utf-8") as f:
        f.write(url + "\n")
