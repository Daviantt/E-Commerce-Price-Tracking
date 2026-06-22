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


API_URL = "https://discovery.tekoapis.com/api/v2/search-skus-v2"
SAVE_DIR = "D:/Data/raw"

BRAND_SLUGS = {
    "acer": "/c/laptop-acer",
    "asus": "/c/laptop-asus",
    "msi": "/c/laptop-msi",
}

HEADERS = {
    "Accept": "*/*",
    "Origin": "https://phongvu.vn",
    "Referer": "https://phongvu.vn/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
    "accept-language": "vi",
    "content-type": "application/json",
}

# vòng lặp đào tìm dữ liệu nhiều lớp
def get_nested(data, *keys, default=None):
    """Lấy dữ liệu lồng nhau an toàn."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current

def extract_image_urls(item):
    candidates = [
        item.get("imageUrl"),
        item.get("image_url"),
        item.get("thumbnail"),
        item.get("thumbnailUrl"),
        get_nested(item, "product", "imageUrl"),
        get_nested(item, "product", "thumbnail"),
    ]

    urls = [url for url in candidates if isinstance(url, str) and url]

    for key in ("images", "imageUrls"):
        value = item.get(key)
        if isinstance(value, list):
            for image in value:
                if isinstance(image, str):
                    urls.append(image)
                elif isinstance(image, dict):
                    src = image.get("url") or image.get("src") or image.get("imageUrl")
                    if src:
                        urls.append(src)

    return list(dict.fromkeys(urls))

def normalize_product(item, brand):
    """Chuẩn hóa một sản phẩm từ JSON API thành một dòng dữ liệu."""
    name = (
        item.get("name")
        or item.get("skuName")
        or item.get("displayName")
        or get_nested(item, "product", "name")
    )

    sku = item.get("sku") or item.get("skuId") or item.get("id")

    slug = (
        item.get("canonical")
        or item.get("slug")
        or item.get("url")
        or get_nested(item, "product", "slug")
    )
    product_url = None
    if isinstance(slug, str):
        if slug.startswith("http"):
            product_url = slug
        else:
            product_url = f"https://phongvu.vn/{slug.lstrip('/')}"

    current_price = (
        item.get("latestPrice")
        or item.get("price")
        or item.get("salePrice")
        or item.get("finalPrice")
        or get_nested(item, "price", "salePrice")
        or get_nested(item, "price", "supplierSalePrice")
        or get_nested(item, "prices", "latestPrice")
    )

    original_price = (
        item.get("supplierRetailPrice")
        or item.get("originalPrice")
        or item.get("listedPrice")
        or item.get("basePrice")
        or get_nested(item, "price", "listedPrice")
        or get_nested(item, "price", "supplierRetailPrice")
        or get_nested(item, "prices", "supplierRetailPrice")
    )

    current_price, original_price = normalize_price_pair(current_price, original_price)
    image_urls = extract_image_urls(item)
    specs = extract_specs_from_product(item, name, sku)

    return {
        "sku": sku,
        "name": name,
        "brand": brand,
        "current_price": current_price,
        "original_price": original_price,
        "url": product_url,
        "source": "phongvu",
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_url": clean_url(image_urls[0]) if image_urls else None,
        "image_urls": [url for url in (clean_url(url) for url in image_urls) if url],
        **specs,
        "technical_specs": specs_to_display(specs),
        "price_segment": classify_price_segment(current_price),
        "discount_percent": compute_discount_percent(current_price, original_price),
    }


def extract_items(payload):
    """Tìm danh sách sản phẩm trong response JSON."""
    candidates = [
        get_nested(payload, "result", "products"),
        get_nested(payload, "result", "items"),
        get_nested(payload, "data", "products"),
        get_nested(payload, "data", "items"),
        payload.get("products") if isinstance(payload, dict) else None,
        payload.get("items") if isinstance(payload, dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate

    return []


def build_request_body(page, page_size, brand):
    return {
        "terminalId": 4,
        "page": page,
        "pageSize": page_size,
        "slug": BRAND_SLUGS[brand],
        "filter": {},
        "sorting": {
            "sort": "SORT_BY_CREATED_AT",
            "order": "ORDER_BY_DESCENDING",
        },
        "returnFilterable": [],
        "isNeedFeaturedProducts": True,
    }


def build_output_filename(brand, extension="csv"):
    date_str = datetime.now().strftime("%Y%m%d")
    return os.path.join(SAVE_DIR, f"phongvu_{brand}_laptop_{date_str}.{extension}")


def save_products(products, brand):
    os.makedirs(SAVE_DIR, exist_ok=True)
    df = pd.DataFrame(products)
    filename = build_output_filename(brand)

    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    except PermissionError:
        fallback_filename = os.path.join(
            SAVE_DIR,
            f"phongvu_{brand}_laptop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        df.to_csv(fallback_filename, index=False, encoding="utf-8-sig")
        print(
            f"Không ghi được vào {filename} (có thể file đang mở). "
            f"Đã lưu sang file khác: {fallback_filename}"
        )
        filename = fallback_filename

    return filename


def crawl_phongvu_laptops(brand):
    brand = brand.lower()
    if brand not in BRAND_SLUGS:
        supported = ", ".join(BRAND_SLUGS)
        raise ValueError(f"Hãng không hỗ trợ: {brand}. Chọn một trong: {supported}")

    products = []
    page = 1
    page_size = 40

    while True:
        body = build_request_body(page, page_size, brand)

        try:
            response = requests.post(API_URL, headers=HEADERS, json=body, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            print(f"Lỗi khi gọi API hãng {brand} ở trang {page}: {e}")
            break

        items = extract_items(payload)
        print(f"{brand.upper()} - trang {page}: nhận được {len(items)} sản phẩm")

        if not items:
            if page == 1:
                debug_filename = f"phongvu_{brand}_api_debug.json"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(
                    "Không đọc được danh sách sản phẩm từ response. "
                    f"Đã lưu {debug_filename} để kiểm tra cấu trúc JSON."
                )
            break

        products.extend(normalize_product(item, brand) for item in items)

        if len(items) < page_size:
            break

        page += 1
        time.sleep(0.5)

    filename = save_products(products, brand)
    print(f"Đã lưu {len(products)} sản phẩm {brand.upper()} → {filename}")
    return filename


def crawl_all_supported_brands():
    output_files = []
    for brand in BRAND_SLUGS:
        output_files.append(crawl_phongvu_laptops(brand))
    return output_files


if __name__ == "__main__":
    crawl_all_supported_brands()
