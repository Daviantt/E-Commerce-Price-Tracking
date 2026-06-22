import os
import time
from datetime import datetime

import pandas as pd
import requests

from app.crawlers.common import (
    classify_price_segment,
    clean_url,
    compute_discount_percent,
    extract_specs_from_product,
    specs_to_display,
    normalize_price_pair,
)


BASE_URL = "https://gearvn.com"
SAVE_DIR = "D:/Data/raw"
PAGE_SIZE = 50

BRAND_COLLECTIONS = {
    "acer": {
        "office": "laptop-acer-hoc-tap-va-lam-viec",
        "gaming": "laptop-gaming-acer",
    },
    "asus": {
        "office": "laptop-asus-hoc-tap-va-lam-viec",
        "gaming": "laptop-gaming-asus",
    },
    "msi": {
        "office": "laptop-msi-hoc-tap-va-lam-viec",
        "gaming": "laptop-msi-gaming",
    },
}

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://gearvn.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
}


def build_collection_products_url(handle):
    return f"{BASE_URL}/collections/{handle}/products.json"

def extract_image_urls(item):
    urls = []
    for image in item.get("images") or []:
        src = image.get("src") if isinstance(image, dict) else None
        if src:
            urls.append(src)
    return urls

def normalize_product(item, brand, segment, collection_handle):
    variants = item.get("variants") or []
    first_variant = variants[0] if variants else {}
    handle = item.get("handle")
    image_urls = extract_image_urls(item)
    current_price, original_price = normalize_price_pair(
        first_variant.get("price"),
        first_variant.get("compare_at_price"),
    )
    specs = extract_specs_from_product(
        item,
        item.get("title"),
        item.get("body_html"),
        first_variant.get("sku"),
        " ".join(item.get("tags") or []),
    )

    return {
        "product_id": item.get("id"),
        "sku": first_variant.get("sku"),
        "name": item.get("title"),
        "brand": brand,
        "segment": segment,
        "current_price": current_price,
        "original_price": original_price,
        "available": first_variant.get("available", item.get("available")),
        "url": f"{BASE_URL}/products/{handle}" if handle else None,
        "collection_handle": collection_handle,
        "source": "gearvn",
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_url": clean_url(image_urls[0]) if image_urls else None,
        "image_urls": [url for url in (clean_url(url) for url in image_urls) if url],
        **specs,
        "technical_specs": specs_to_display(specs),
        "price_segment": classify_price_segment(current_price),
        "discount_percent": compute_discount_percent(current_price, original_price),
    }


def fetch_collection_products(handle, brand, segment):
    products = []
    page = 1

    while True:
        try:
            response = requests.get(
                build_collection_products_url(handle),
                headers=HEADERS,
                params={"page": page},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            print(f"Lỗi khi crawl collection {handle} ở trang {page}: {e}")
            break

        items = payload.get("products", [])
        print(
            f"{brand.upper()} - {segment} - trang {page}: "
            f"nhận được {len(items)} sản phẩm"
        )

        if not items:
            break

        products.extend(
            normalize_product(item, brand, segment, handle) for item in items
        )

        if len(items) < PAGE_SIZE:
            break

        page += 1
        time.sleep(0.5)

    return products


def deduplicate_products(products):
    unique_products = {}
    for product in products:
        key = product["product_id"] or product["sku"] or product["url"]
        if key not in unique_products:
            unique_products[key] = product
    return list(unique_products.values())


def build_output_filename(brand, extension="csv"):
    date_str = datetime.now().strftime("%Y%m%d")
    return os.path.join(SAVE_DIR, f"gearvn_{brand}_laptop_{date_str}.{extension}")


def save_products(products, brand):
    os.makedirs(SAVE_DIR, exist_ok=True)
    df = pd.DataFrame(products)
    filename = build_output_filename(brand)

    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    except PermissionError:
        fallback_filename = os.path.join(
            SAVE_DIR,
            f"gearvn_{brand}_laptop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        df.to_csv(fallback_filename, index=False, encoding="utf-8-sig")
        print(
            f"Không ghi được vào {filename} (có thể file đang mở). "
            f"Đã lưu sang file khác: {fallback_filename}"
        )
        filename = fallback_filename

    return filename


def crawl_gearvn_laptops(brand):
    brand = brand.lower()
    if brand not in BRAND_COLLECTIONS:
        supported = ", ".join(BRAND_COLLECTIONS)
        raise ValueError(f"Hãng không hỗ trợ: {brand}. Chọn một trong: {supported}")

    products = []
    for segment, handle in BRAND_COLLECTIONS[brand].items():
        products.extend(fetch_collection_products(handle, brand, segment))

    products = deduplicate_products(products)
    filename = save_products(products, brand)
    print(f"Đã lưu {len(products)} sản phẩm {brand.upper()} → {filename}")
    return filename


def crawl_all_supported_brands():
    output_files = []
    for brand in BRAND_COLLECTIONS:
        output_files.append(crawl_gearvn_laptops(brand))
    return output_files


if __name__ == "__main__":
    crawl_all_supported_brands()
