"""
Turns the scraper's per-property records into House Price Guesser game data.

Reads every record in `data/`, keeps the ones that make a playable round, maps
them onto the schema the game expects, downloads a capped set of photos per
house, and writes `data.json` sorted newest sale first so the daily challenge
can walk backwards through the list.

Usage:
    uv run python export.py [--max-images N] [--workers N] [--dry-run]
"""

import argparse
import hashlib
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_FILE = Path(__file__).resolve().parent / "image_cache.json"
LISTING_BASE_URL = "https://www.domain.com.au"
GAME_DIR = Path(__file__).resolve().parents[2] / "frontend" / "games" / "house-price-guesser"
DATA_FILE = GAME_DIR / "data.json"
IMAGES_DIR = GAME_DIR / "images"

# domain.com.au only serves its CDN images from signed URLs, so asking it for a
# smaller crop or a different format is rejected with a 400. The only lever is to
# re-encode what we download. They hand out 720x540 WebP at roughly 60 KB, so the
# dimension is left alone and AVIF at a high quality is used instead: it is
# visually indistinguishable from the source at a third less data. 0 means keep
# every photo a listing has.
DEFAULT_MAX_IMAGES = 0
IMAGE_FORMAT = "AVIF"
IMAGE_QUALITY = 80
IMAGE_MAX_DIMENSION = 720
IMAGE_EXTENSION = f".{IMAGE_FORMAT.lower()}"
ALLOWED_IMAGE_HOST_SUFFIX = "domainstatic.com.au"

# Listings that are not dwellings, or that omit the fields the game displays.
EXCLUDED_TYPES = {"land", "commercial", "industrial", "rural", "vacantland"}
MIN_BEDS = 1
DATE_DIGITS = 8


def slugify(value: str) -> str:
    """Lowercase hyphenated slug, safe for use as a directory name."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def to_int(value: object) -> int:
    """Parse domain's loosely typed numbers, returning 0 for blanks and junk."""
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int | float):
        return int(value)
    digits = re.sub(r"[^0-9]", "", str(value))
    return int(digits) if digits else 0


def parse_sold_date(value: object) -> str | None:
    """Convert the scraper's YYYYMMDD date into the game's ISO YYYY-MM-DD."""
    raw = str(value or "").strip()
    if len(raw) != DATE_DIGITS or not raw.isdigit():
        return None
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def load_records() -> list[dict[str, Any]]:
    """Read every scraper record, skipping files that are not valid JSON."""
    records = []
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as handle:
                records.append(json.load(handle))
        except json.JSONDecodeError, UnicodeDecodeError:
            print(f"  skipping unreadable record {path.name}")
    return records


def sale_method(tag_text: object) -> str:
    """Derive how a property sold from domain's status line.

    The scraper keeps the raw text, which reads "Sold by private treaty 02 Oct
    2026", "Sold at auction ..." or "Sold prior to auction ...". Auction sales
    and private treaties tend to price very differently, so the game shows this.
    """
    text = str(tag_text or "").lower()
    if "private treaty" in text:
        return "Private treaty"
    if "prior to auction" in text:
        return "Sold prior to auction"
    if "auction" in text:
        return "Auction"
    return "Sold"


def listing_url(relative: object) -> str:
    """Turn the scraper's site-relative listing path into an absolute link."""
    path = str(relative or "").strip()
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return f"{LISTING_BASE_URL}{path if path.startswith('/') else '/' + path}"


def is_playable(record: dict[str, Any]) -> bool:
    """Report whether a record has everything a guessing round needs.

    Requires a real price (the scraper blanks price-withheld sales), a sale date,
    at least one bedroom, a residential property type, land size and a photo.
    """
    checks = (
        to_int(record.get("price")) > 0,
        parse_sold_date(record.get("date")) is not None,
        to_int(record.get("beds")) >= MIN_BEDS,
        str(record.get("isRural", "")).lower() != "true",
        slugify(str(record.get("propertyType", ""))) not in EXCLUDED_TYPES,
        to_int(record.get("landSize")) > 0,
        bool(record.get("images")),
    )
    return all(checks)


def to_game_record(record: dict[str, Any], max_images: int) -> dict[str, Any] | None:
    """Map a scraper record onto the game schema, or None if it is not playable.

    The id doubles as the image folder name, so it is derived from the listing
    rather than the bare domain id to stay readable on disk.
    """
    if not is_playable(record):
        return None

    prop_id = str(record["id"])
    property_type = str(record.get("propertyTypeFormatted") or record.get("propertyType") or "Property")
    state = str(record.get("state", "")).lower()
    suburb = slugify(str(record.get("suburb", "")))
    game_id = f"property-{slugify(property_type)}-{state}-{suburb}-{prop_id}"

    state_postcode = " ".join(
        part for part in (str(record.get("state", "")).strip(), str(record.get("postcode", "")).strip()) if part
    )
    address_parts = [
        str(record.get("street", "")).strip(),
        str(record.get("suburb", "")).strip(),
        state_postcode,
    ]
    address = ", ".join(part for part in address_parts if part)

    urls = [str(url) for url in (record.get("images") or [])]
    if max_images > 0:
        urls = urls[:max_images]

    return {
        "id": game_id,
        "address": address,
        "bedrooms": to_int(record.get("beds")),
        "bathrooms": to_int(record.get("baths")),
        "carSpaces": to_int(record.get("parking")),
        "buildingSize": 0,
        "landSize": to_int(record.get("landSize")),
        "type": property_type,
        "soldDate": parse_sold_date(record.get("date")),
        "saleMethod": sale_method(record.get("tagText")),
        "description": str(record.get("description", "")),
        "price": to_int(record.get("price")),
        "listingUrl": listing_url(record.get("url")),
        # Filled in by download_images once the photos resolve to the shared pool.
        "images": [],
        "_urls": urls,
    }


def transcode(payload: bytes, max_dimension: int, quality: int) -> bytes:
    """Re-encode a downloaded photo as AVIF, scaled down to fit `max_dimension`.

    The longest edge is capped while preserving aspect ratio, and images already
    smaller than the cap are left at their original size rather than upscaled.
    """
    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGB")
        longest = max(image.size)
        if longest > max_dimension:
            scale = max_dimension / longest
            image = image.resize(
                (max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS
            )
        buffer = BytesIO()
        image.save(buffer, format=IMAGE_FORMAT, quality=quality)
        return buffer.getvalue()


def load_image_cache() -> dict[str, str]:
    """Load the URL to pool-filename map from a previous export, if there is one."""
    if not CACHE_FILE.is_file():
        return {}
    try:
        with CACHE_FILE.open(encoding="utf-8") as handle:
            cached = json.load(handle)
    except json.JSONDecodeError, UnicodeDecodeError:
        return {}
    return cached if isinstance(cached, dict) else {}


def save_image_cache(cache: dict[str, str]) -> None:
    """Persist the URL to pool-filename map so the next export can skip the CDN."""
    with CACHE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=1, sort_keys=True)
        handle.write("\n")


def pool_path(digest: str) -> Path:
    """Location of a photo in the shared pool, sharded to keep directories small."""
    return IMAGES_DIR / digest[:2] / f"{digest}{IMAGE_EXTENSION}"


def store_encoded(payload: bytes) -> str:
    """Store re-encoded bytes in the shared pool and return the file's name.

    Photos are content addressed by the SHA-256 of what we actually store, so two
    listings showing the same picture resolve to one file. Hashing the stored
    bytes rather than comparing images perceptually keeps this exact: an
    identical photo always matches and a different one never does.
    """
    digest = hashlib.sha256(payload).hexdigest()
    target = pool_path(digest)
    if not (target.is_file() and target.stat().st_size > 0):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return target.name


def encode_image(url: str, max_dimension: int, quality: int) -> bytes | None:
    """Download one CDN photo and re-encode it, or None if that is not possible."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not host.endswith(ALLOWED_IMAGE_HOST_SUFFIX):
        print(f"  refusing unexpected image host: {host}")
        return None
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        print(f"  failed to fetch image: {error}")
        return None
    if not payload:
        return None
    try:
        return transcode(payload, max_dimension, quality)
    except (OSError, ValueError) as error:
        print(f"  failed to re-encode image: {error}")
        return None


@dataclass
class ImagePool:
    """Resolves CDN photo URLs into paths in the shared content-addressed pool.

    A photo already held is returned without touching the network, so repeat
    exports cost nothing even though the listings are scraped fresh each time.
    """

    max_dimension: int
    quality: int
    cache: dict[str, str] = field(default_factory=dict)
    referenced: set[str] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def load(cls, max_dimension: int, quality: int) -> ImagePool:
        """Build a pool seeded from the cache a previous export left behind."""
        return cls(max_dimension=max_dimension, quality=quality, cache=load_image_cache())

    def resolve(self, url: str) -> str | None:
        """Return the pool path for a photo, downloading and encoding if needed."""
        cached = self.cache.get(url)
        if cached and (IMAGES_DIR / cached).is_file():
            self.referenced.add(cached.partition("/")[0])
            return cached

        encoded = encode_image(url, self.max_dimension, self.quality)
        if encoded is None:
            return None

        name = store_encoded(encoded)
        path = f"{name[:2]}/{name}"
        with self.lock:
            self.cache[url] = path
        self.referenced.add(path.partition("/")[0])
        return path

    def save(self) -> None:
        """Persist the URL to path map for the next export."""
        save_image_cache(self.cache)


def download_images(house: dict[str, Any], pool: ImagePool) -> None:
    """Attach a house's photos, as pool paths, dropping any that cannot be had."""
    paths: list[str] = []
    for url in house.pop("_urls"):
        path = pool.resolve(url)
        if path is not None:
            paths.append(path)
    house["images"] = paths


def prune_unreferenced(pool: ImagePool, *, prune_shards: bool) -> None:
    """Delete pooled shards the current export does not point at."""
    if not IMAGES_DIR.is_dir():
        return
    for shard in sorted(IMAGES_DIR.iterdir()):
        if not shard.is_dir() or shard.name in pool.referenced:
            continue
        if not prune_shards:
            print(f"  left unreferenced shard {shard.name} (pass --prune to remove)")
            continue
        for child in shard.iterdir():
            child.unlink()
        shard.rmdir()
        print(f"  removed shard {shard.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-images",
        type=int,
        default=DEFAULT_MAX_IMAGES,
        help="photos to keep per house (0 for all of them)",
    )
    parser.add_argument("--workers", type=int, default=8, help="parallel image downloads")
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=IMAGE_MAX_DIMENSION,
        help=f"longest edge in pixels for stored {IMAGE_FORMAT} photos",
    )
    parser.add_argument("--quality", type=int, default=IMAGE_QUALITY, help=f"{IMAGE_FORMAT} quality")
    parser.add_argument("--dry-run", action="store_true", help="report what would be written without downloading")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="delete image folders that no longer belong to any exported house",
    )
    args = parser.parse_args()

    if not DATA_DIR.is_dir():
        print(f"No scraper output at {DATA_DIR}. Run daily.py or main.py first.")
        return 1

    records = load_records()
    print(f"Read {len(records)} scraper records")

    houses = [house for house in (to_game_record(r, args.max_images) for r in records) if house]
    houses.sort(key=lambda house: str(house["soldDate"]), reverse=True)
    print(f"{len(houses)} playable houses, newest {houses[0]['soldDate'] if houses else '-'}")

    if args.dry_run:
        for house in houses[:10]:
            print(f"  {house['soldDate']}  {house['price']:>9}  {house['bedrooms']}bd  {house['address'][:60]}")
        print(f"... {len(houses)} total. Dry run, nothing written.")
        return 0

    image_budget = "all photos" if args.max_images <= 0 else f"up to {args.max_images} photos per house"
    print(f"Resolving {image_budget}, {IMAGE_FORMAT} q{args.quality} capped at {args.max_dimension}px")

    cache = ImagePool.load(args.max_dimension, args.quality)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(lambda house: download_images(house, cache), houses))
    cache.save()

    empty = [house for house in houses if not house["images"]]
    if empty:
        print(f"Dropping {len(empty)} houses with no usable images")
        houses = [house for house in houses if house["images"]]

    prune_unreferenced(cache, prune_shards=args.prune)

    for house in houses:
        house.pop("_urls", None)

    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(houses, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    stored = [p for p in IMAGES_DIR.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in stored)
    referenced_count = sum(len(house["images"]) for house in houses)
    print(f"Wrote {len(houses)} houses to {DATA_FILE}")
    print(
        f"Photos: {referenced_count} referenced, {len(stored)} stored ({len(stored) - referenced_count} deduplicated)"
    )
    print(f"Images on disk: {total / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
