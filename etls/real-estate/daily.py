"""
Daily update scraper for Domain.com.au.
Scrapes the most recent sold listings to keep the database up to date.
"""

import atexit
import json
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from utils import html_to_dict, value_to_dict, wait_until_ready

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

# Populate suburbs and look_up for the scraper logic
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

# Create webpages
mainpage = "https://www.domain.com.au/sold-listings/?excludepricewithheld=1&ssubs=0"
webpages = [mainpage]
states = ["nt", "nsw", "act", "vic", "qld", "sa", "wa", "tas"]
webpages.extend(mainpage + "&state=" + state for state in states)
print("Total Webpages:", len(webpages))

# Create selenium driver
options = Options()
options.add_argument("-headless")
driver = webdriver.Firefox(options=options)
atexit.register(driver.quit)

# Scrape them
for webpage in webpages:
    for i in range(1, 51):
        url = webpage + "&page=" + str(i)
        print(url, end="")
        driver.get(url)
        if not wait_until_ready(driver):
            print("timed out")
            continue
        property_dictionary = html_to_dict(driver.page_source)
        dupes = 0
        for value in property_dictionary.values():
            prop_id = str(value["id"])
            if prop_id in ids:
                dupes += 1
                continue
            ids.add(prop_id)
            data = value_to_dict(value)
            date_str = data.get("date")
            if date_str:
                date = float(date_str)
                suburb_name = data.get("suburb")
                if suburb_name and (suburb_name not in suburbs or date < suburbs[suburb_name]):
                    suburbs[suburb_name] = date

            # Save JSON file
            with (data_dir / f"{prop_id}.json").open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            # Update ids.txt
            with ids_file.open("a", encoding="utf-8") as f:
                f.write(prop_id + "\n")
        print(" \tDupes:", dupes)
        if not property_dictionary:
            # Paged past the last result, so every later page would be empty too.
            break
