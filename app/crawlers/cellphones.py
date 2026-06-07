import os
import re
import time
from datetime import datetime

import pandas as pd
import requests

from app.crawlers.common import normalize_price_pair


BASE_URL = "https://cellphones.com.vn"
GRAPHQL_URL = "https://api.cellphones.com.vn/v2/graphql/query"
SAVE_DIR = "D:/Data/raw"
PAGE_SIZE = 30
PROVINCE_ID = 30

BRAND_CATEGORY_URLS = {
    "acer": "https://cellphones.com.vn/laptop/acer.html",
    "asus": "https://cellphones.com.vn/laptop/asus.html",
    "msi": "https://cellphones.com.vn/laptop/msi.html",
}

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://cellphones.com.vn/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
}


def get_category_id(category_url):
    response = requests.get(category_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    match = re.search(
        r"catalog\\u002Fcategory\\u002Fview\\u002Fid\\u002F(\d+)",
        response.text,
    )
    if not match:
        raise ValueError(f"Không tìm thấy category_id trong trang: {category_url}")

    return match.group(1)


def build_products_query(category_id, page):
    return f"""
    query products {{
      products(
        filter: {{
          static: {{
            categories: ["{category_id}"],
            province_id: {PROVINCE_ID},
            stock: {{ from: 1 }}
          }}
        }},
        page: {page},
        size: {PAGE_SIZE}
      ) {{
        general {{
          product_id
          name
          sku
          url_path
        }}
        filterable {{
          price
          special_price
          stock
        }}
      }}
    }}
    """


def normalize_product(item, brand):
    general = item.get("general") or {}
    filterable = item.get("filterable") or {}
    url_path = general.get("url_path")
    current_price, original_price = normalize_price_pair(
        filterable.get("special_price") or filterable.get("price"),
        filterable.get("price"),
    )

    return {
        "product_id": general.get("product_id"),
        "sku": general.get("sku"),
        "name": general.get("name"),
        "brand": brand,
        "current_price": current_price,
        "original_price": original_price,
        "stock": filterable.get("stock"),
        "url": f"{BASE_URL}/{url_path}" if url_path else None,
        "source": "cellphones",
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def fetch_products(category_id, brand):
    products = []
    page = 1

    while True:
        payload = {"query": build_products_query(category_id, page), "variables": {}}

        try:
            response = requests.post(
                GRAPHQL_URL,
                headers=HEADERS,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Lỗi khi gọi API CellphoneS hãng {brand} ở trang {page}: {e}")
            break

        if data.get("errors"):
            print(f"API CellphoneS trả lỗi ở trang {page}: {data['errors']}")
            break

        items = (data.get("data") or {}).get("products") or []
        print(f"{brand.upper()} - trang {page}: nhận được {len(items)} sản phẩm")

        if not items:
            break

        products.extend(normalize_product(item, brand) for item in items)

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
    return os.path.join(SAVE_DIR, f"cellphones_{brand}_laptop_{date_str}.{extension}")


def save_products(products, brand):
    os.makedirs(SAVE_DIR, exist_ok=True)
    df = pd.DataFrame(products)
    filename = build_output_filename(brand)

    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    except PermissionError:
        fallback_filename = os.path.join(
            SAVE_DIR,
            f"cellphones_{brand}_laptop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        df.to_csv(fallback_filename, index=False, encoding="utf-8-sig")
        print(
            f"Không ghi được vào {filename} (có thể file đang mở). "
            f"Đã lưu sang file khác: {fallback_filename}"
        )
        filename = fallback_filename

    return filename


def crawl_cellphones_laptops(brand):
    brand = brand.lower()
    if brand not in BRAND_CATEGORY_URLS:
        supported = ", ".join(BRAND_CATEGORY_URLS)
        raise ValueError(f"Hãng không hỗ trợ: {brand}. Chọn một trong: {supported}")

    category_id = get_category_id(BRAND_CATEGORY_URLS[brand])
    products = deduplicate_products(fetch_products(category_id, brand))
    filename = save_products(products, brand)
    print(f"Đã lưu {len(products)} sản phẩm {brand.upper()} → {filename}")
    return filename


def crawl_all_supported_brands():
    output_files = []
    for brand in BRAND_CATEGORY_URLS:
        output_files.append(crawl_cellphones_laptops(brand))
    return output_files


if __name__ == "__main__":
    crawl_all_supported_brands()
