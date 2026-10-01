"""
Utility functions for the Domain web scrapers.
Contains shared logic for HTML parsing and data transformation.
"""

import json
from datetime import UTC, datetime
from typing import Any


def add_column(group: dict[str, Any], header: str) -> str:
    """Returns '' if the key 'header' does not exist in dict 'group'."""
    val = group.get(header, "")
    return str(val) if val is not None else ""


def html_to_dict(s: str) -> dict[str, Any]:
    """Converts a domain.com.au search to a list of property information."""
    search = '"listingsMap":'
    start_index = s.find(search)
    if start_index == -1:
        return {}
    start_index += len(search)
    end_index = start_index
    count = 0
    while end_index < len(s):
        if s[end_index] == "{":
            count += 1
        elif s[end_index] == "}":
            count += -1
        if count == 0:
            break
        end_index += 1
    try:
        return json.loads(s[start_index : end_index + 1])
    except json.JSONDecodeError:
        return {}


def value_to_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Converts property dictionary to a structured dictionary."""
    data = {}
    data["id"] = str(value["id"])
    data["listingType"] = value["listingType"]
    data["url"] = value["listingModel"]["url"]
    price = value["listingModel"]["price"]
    if price == "Price Withheld":
        price = ""
    elif isinstance(price, str) and price.startswith("$"):
        price = price[1:].replace(",", "")
    data["price"] = price

    data["tagClassName"] = value["listingModel"]["tags"]["tagClassName"]
    tag_text = value["listingModel"]["tags"]["tagText"]
    data["tagText"] = tag_text
    try:
        date_str = " ".join(tag_text.split()[-3:])
        date = datetime.strptime(date_str, "%d %b %Y").replace(tzinfo=UTC)
        data["date"] = date.strftime("%Y%m%d")
    except ValueError, IndexError:
        data["date"] = ""

    address = value["listingModel"]["address"]
    data["street"] = add_column(address, "street").replace("\n", " ")
    data["suburb"] = add_column(address, "suburb")
    data["state"] = add_column(address, "state")
    data["postcode"] = add_column(address, "postcode")
    data["lat"] = add_column(address, "lat")
    data["lng"] = add_column(address, "lng")

    features = value["listingModel"]["features"]
    data["beds"] = add_column(features, "beds")
    data["baths"] = add_column(features, "baths")
    data["parking"] = add_column(features, "parking")
    data["propertyType"] = add_column(features, "propertyType")
    data["propertyTypeFormatted"] = add_column(features, "propertyTypeFormatted")
    data["isRural"] = add_column(features, "isRural")
    data["landSize"] = add_column(features, "landSize")
    land_unit = add_column(features, "landUnit")
    if land_unit == "m²":
        land_unit = "m2"
    data["landUnit"] = land_unit
    data["isRetirement"] = add_column(features, "isRetirement")
    return data


def value_to_row(value: dict[str, Any]) -> list[Any]:
    """Converts property dictionary to a list of values for CSV."""
    data = value_to_dict(value)
    return [
        data["id"],
        data["listingType"],
        data["url"],
        data["price"],
        data["tagClassName"],
        data["tagText"],
        data["date"],
        data["street"],
        data["suburb"],
        data["state"],
        data["postcode"],
        data["lat"],
        data["lng"],
        data["beds"],
        data["baths"],
        data["parking"],
        data["propertyType"],
        data["propertyTypeFormatted"],
        data["isRural"],
        data["landSize"],
        data["landUnit"],
        data["isRetirement"],
    ]
