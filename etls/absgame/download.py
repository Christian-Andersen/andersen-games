import zipfile
from pathlib import Path

import httpx

URL = "https://www.abs.gov.au/methodologies/data-region-methodology/2011-25/All-data-by-region-data-items.zip"
OUT_DIR = Path("./data/")
ZIP_PATH = OUT_DIR / URL.rpartition("/")[-1]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / ".gitignore").write_text("*\n")
    print(f"Downloading {URL}...")
    with httpx.stream("GET", URL, follow_redirects=True) as r:
        r.raise_for_status()
        with ZIP_PATH.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    print(f"Extracting to {OUT_DIR}...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(OUT_DIR)
    print("Extraction success, removing zip file...")
    ZIP_PATH.unlink()
    print("Done!")


if __name__ == "__main__":
    main()
