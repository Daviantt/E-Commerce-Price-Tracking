import math
import re
import hashlib
import hmac
import os
import secrets
import unicodedata
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.crawlers.common import (
    SPEC_DISPLAY_LABELS,
    TECHNICAL_COLUMNS,
    classify_price_segment,
    extract_specs_from_text,
    normalize_spec_value,
)
from app.db.database import (
    FALLBACK_PROCESSED_DIR,
    PROCESSED_DIR,
    get_connection,
    init_database,
    load_env_file,
)


PROJECT_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PROJECT_DIR / "templates"))

load_env_file()

app = FastAPI(title="LapWise")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-only-change-this-secret-key"),
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=str(PROJECT_DIR / "static")), name="static")

_schema_ready = False


SOURCE_LABELS = {
    "phongvu": "Phong Vũ",
    "gearvn": "GearVN",
    "cellphones": "CellphoneS",
}


def clean_number(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return int(number) if number.is_integer() else number


def clean_price_number(value):
    value = clean_number(value)
    if value is None or value <= 0:
        return None
    return value


def clean_float(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def format_vnd(value):
    value = clean_number(value)
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", ".") + "₫"


templates.env.filters["vnd"] = format_vnd


def clean_image_url(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    value = str(value).strip()
    if not value or value.lower() in {"nan", "none", "null"}:
        return None
    return value


def ensure_schema():
    global _schema_ready
    if _schema_ready:
        return
    init_database()
    _schema_ready = True


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def get_current_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        ensure_schema()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, display_name
                    FROM app_users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
    except Exception:
        return None
    if not row:
        request.session.clear()
        return None
    return {"id": row[0], "email": row[1], "display_name": row[2]}


def require_user(request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập trước.")
    return user

PRICE_SEGMENT_LABELS = {
    "budget": "Phổ thông",
    "mainstream": "Tầm trung",
    "upper_mid": "Cận cao cấp",
    "premium": "Cao cấp",
}

SPEC_LABELS_VI = {
    "CPU": "CPU",
    "GPU": "GPU",
    "RAM": "RAM",
    "Storage": "Ổ cứng",
    "Screen size": "Màn hình",
    "Resolution": "Độ phân giải",
    "Refresh rate": "Tần số quét",
    "Operating system": "Hệ điều hành",
    "Weight": "Trọng lượng",
    "Battery": "Pin",
}


def specs_from_record(record):
    inferred = extract_specs_from_text(
        record.get("display_name") or record.get("ten"),
        record.get("model_key"),
    )
    specs = {}
    for column in TECHNICAL_COLUMNS:
        value = normalize_spec_value(column, record.get(column)) or inferred.get(column)
        if value:
            label = SPEC_DISPLAY_LABELS[column]
            specs[SPEC_LABELS_VI.get(label, label)] = value
    return specs


def build_price_analysis(prices, record):
    lowest_price = prices[0]["current_price"] if prices else None
    highest_price = prices[-1]["current_price"] if prices else None
    spread = (
        highest_price - lowest_price
        if lowest_price is not None and highest_price is not None
        else None
    )
    spread_percent = (
        spread / lowest_price * 100
        if spread is not None and lowest_price and len(prices) > 1
        else None
    )
    discount_percent = clean_float(record.get("discount_percent"))
    if discount_percent is None:
        discount_percent = max(
            [
                (price["original_price"] - price["current_price"])
                / price["original_price"]
                * 100
                for price in prices
                if price.get("original_price") and price["original_price"] > price["current_price"]
            ]
            or [0]
        )
    price_segment = record.get("price_segment") or classify_price_segment(lowest_price)
    segment_label = PRICE_SEGMENT_LABELS.get(price_segment, "Chưa xếp hạng")

    if lowest_price is None:
        summary = "Chưa có giá bán hợp lệ để phân tích."
    elif spread_percent is not None and spread_percent >= 5:
        summary = f"Giá giữa các shop đang chênh khoảng {spread_percent:.1f}%, nên ưu tiên nơi có giá thấp nhất."
    elif discount_percent and discount_percent >= 5:
        summary = f"Mức giảm tốt nhất hiện khoảng {discount_percent:.1f}% so với giá gốc."
    else:
        summary = "Giá giữa các shop khá sát nhau, nên kiểm tra thêm bảo hành và tình trạng hàng."

    return {
        "price_segment": price_segment,
        "segment_label": segment_label,
        "spread": spread,
        "spread_percent": spread_percent,
        "discount_percent": discount_percent,
        "summary": summary,
    }


def product_from_record(record):
    prices = []
    price_options = []
    image_url = clean_image_url(record.get("image_url"))
    for source in SOURCE_LABELS:
        current_price = clean_price_number(record.get(f"gia_ban_{source}"))
        original_price = clean_price_number(record.get(f"gia_goc_{source}"))
        if original_price is not None and current_price is not None and original_price < current_price:
            original_price = current_price
        url = record.get(f"url_{source}")
        is_available = current_price is not None
        option = {
            "source": source,
            "label": SOURCE_LABELS[source],
            "current_price": current_price,
            "original_price": original_price,
            "url": url,
            "available": is_available,
            "status": "Đang kinh doanh" if current_price is not None else "Không kinh doanh",
            "image_url": image_url,
        }
        option["status"] = "Đang kinh doanh" if is_available else "Không kinh doanh"
        price_options.append(option)
        if is_available:
            prices.append(option)

    prices.sort(key=lambda item: item["current_price"])
    lowest_price = prices[0]["current_price"] if prices else None
    average_price = (
        sum(item["current_price"] for item in prices) / len(prices) if prices else None
    )

    return {
        "id": int(record["id"]) if record.get("id") is not None else None,
        "comparison_date": str(record.get("comparison_date") or record.get("ngay_crawl")),
        "model_key": record.get("model_key"),
        "display_name": record.get("display_name") or record.get("ten"),
        "brand": record.get("brand"),
        "so_website_co_hang": len(prices),
        "prices": prices,
        "price_options": price_options,
        "lowest_price": lowest_price,
        "average_price": average_price,
        "best_source": prices[0]["label"] if prices else None,
        "image_url": image_url,
        "specs": specs_from_record(record),
        "price_analysis": build_price_analysis(prices, record),
    }


def fetch_products_from_database(limit=80):
    ensure_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(comparison_date)
                FROM daily_price_comparisons
                """
            )
            latest_date = cur.fetchone()[0]

            if latest_date is None:
                return []

            cur.execute(
                """
                SELECT
                    id,
                    comparison_date,
                    model_key,
                    display_name,
                    brand,
                    gia_ban_phongvu,
                    gia_goc_phongvu,
                    url_phongvu,
                    gia_ban_gearvn,
                    gia_goc_gearvn,
                    url_gearvn,
                    gia_ban_cellphones,
                    gia_goc_cellphones,
                    url_cellphones,
                    image_url,
                    cpu,
                    gpu,
                    ram,
                    storage,
                    screen_size,
                    screen_resolution,
                    refresh_rate,
                    os,
                    weight,
                    battery,
                    price_segment,
                    discount_percent,
                    so_website_co_hang
                FROM daily_price_comparisons
                WHERE comparison_date = %s
                ORDER BY so_website_co_hang DESC, brand, display_name
                LIMIT %s
                """,
                (latest_date, limit),
            )
            columns = [desc.name for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    rows = enrich_records_with_images(rows)
    return [product_from_record(row) for row in rows]


def latest_csv(directory, pattern):
    files = sorted(Path(directory).glob(pattern))
    return files[-1] if files else None


def load_latest_image_lookup():
    path = latest_csv(PROCESSED_DIR, "laptop_price_compare_*.csv")
    if path is None:
        path = latest_csv(FALLBACK_PROCESSED_DIR, "laptop_price_compare_*.csv")
    if path is None:
        return {}

    try:
        df = pd.read_csv(path)
    except Exception:
        return {}

    required_columns = {"model_key", "brand", "image_url"}
    if not required_columns.issubset(df.columns):
        return {}

    lookup = {}
    for _, row in df.iterrows():
        image_url = clean_image_url(row.get("image_url"))
        model_key = row.get("model_key")
        brand = row.get("brand")
        if image_url and pd.notna(model_key) and pd.notna(brand):
            lookup[(str(model_key), str(brand).lower())] = image_url
    return lookup


def enrich_records_with_images(records):
    image_lookup = load_latest_image_lookup()
    if not image_lookup:
        return records

    for record in records:
        if clean_image_url(record.get("image_url")):
            continue
        key = (str(record.get("model_key")), str(record.get("brand")).lower())
        image_url = image_lookup.get(key)
        if image_url:
            record["image_url"] = image_url
    return records


def fetch_products_from_csv(limit=80):
    path = latest_csv(PROCESSED_DIR, "laptop_price_compare_*.csv")
    if path is None:
        path = latest_csv(FALLBACK_PROCESSED_DIR, "laptop_price_compare_*.csv")
    if path is None:
        return []

    df = pd.read_csv(path)
    products = []
    for index, row in df.head(limit).iterrows():
        record = row.to_dict()
        record["id"] = index + 1
        products.append(product_from_record(record))
    return products


def fetch_dashboard_products(limit=80):
    try:
        products = fetch_products_from_database(limit=limit)
        source = "PostgreSQL"
    except Exception:
        products = fetch_products_from_csv(limit=limit)
        source = "CSV fallback"
    return products, source


def featured_products_by_brand():
    products, _ = fetch_dashboard_products(limit=120)
    grouped = {"asus": [], "msi": [], "acer": []}
    for product in products:
        brand = (product.get("brand") or "").lower()
        if brand in grouped and len(grouped[brand]) < 4:
            grouped[brand].append(product)
    return grouped


def hero_price_movers(limit=8):
    try:
        ensure_schema()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH latest_date AS (
                        SELECT MAX(comparison_date) AS value
                        FROM daily_price_comparisons
                    ),
                    previous_date AS (
                        SELECT MAX(comparison_date) AS value
                        FROM daily_price_comparisons
                        WHERE comparison_date < (SELECT value FROM latest_date)
                    ),
                    scored AS (
                        SELECT
                            l.id,
                            l.comparison_date,
                            l.model_key,
                            l.display_name,
                            l.brand,
                            l.gia_ban_phongvu,
                            l.gia_goc_phongvu,
                            l.url_phongvu,
                            l.gia_ban_gearvn,
                            l.gia_goc_gearvn,
                            l.url_gearvn,
                            l.gia_ban_cellphones,
                            l.gia_goc_cellphones,
                            l.url_cellphones,
                            l.image_url,
                            l.so_website_co_hang,
                            LEAST(
                                COALESCE(l.gia_ban_phongvu, 999999999999),
                                COALESCE(l.gia_ban_gearvn, 999999999999),
                                COALESCE(l.gia_ban_cellphones, 999999999999)
                            ) AS latest_lowest,
                            LEAST(
                                COALESCE(p.gia_ban_phongvu, 999999999999),
                                COALESCE(p.gia_ban_gearvn, 999999999999),
                                COALESCE(p.gia_ban_cellphones, 999999999999)
                            ) AS previous_lowest,
                            (SELECT value FROM previous_date) AS previous_comparison_date
                        FROM daily_price_comparisons l
                        JOIN daily_price_comparisons p
                          ON p.model_key = l.model_key
                         AND p.brand = l.brand
                         AND p.comparison_date = (SELECT value FROM previous_date)
                        WHERE l.comparison_date = (SELECT value FROM latest_date)
                    )
                    SELECT *
                    FROM scored
                    WHERE latest_lowest < 999999999999
                      AND previous_lowest < 999999999999
                      AND latest_lowest <> previous_lowest
                    ORDER BY
                        CASE WHEN latest_lowest < previous_lowest THEN 0 ELSE 1 END,
                        ABS((latest_lowest - previous_lowest) / previous_lowest) DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                columns = [desc.name for desc in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    except Exception:
        rows = []

    rows = enrich_records_with_images(rows)
    movers = []
    for row in rows:
        product = product_from_record(row)
        latest_price = clean_number(row.get("latest_lowest"))
        previous_price = clean_number(row.get("previous_lowest"))
        if latest_price is None or previous_price is None or previous_price <= 0:
            continue

        change_amount = latest_price - previous_price
        change_percent = change_amount / previous_price * 100
        movers.append(
            {
                "id": product["id"],
                "brand": product["brand"],
                "display_name": product["display_name"],
                "model_key": product["model_key"],
                "image_url": product["image_url"],
                "lowest_price": product["lowest_price"],
                "best_source": product["best_source"],
                "comparison_date": str(row.get("comparison_date")),
                "previous_date": str(row.get("previous_comparison_date")),
                "change_amount": change_amount,
                "change_percent": change_percent,
                "change_label": f"{change_percent:+.1f}%",
                "is_drop": change_amount < 0,
            }
        )
    return movers


def find_product(product_id):
    products, _ = fetch_dashboard_products(limit=1000)
    for product in products:
        if product["id"] == product_id:
            return product
    return None


def attach_source_price_changes(product):
    if not product:
        return product

    comparison_date = product.get("comparison_date")
    if not comparison_date:
        return product

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        gia_ban_phongvu,
                        gia_ban_gearvn,
                        gia_ban_cellphones
                    FROM daily_price_comparisons
                    WHERE model_key = %s
                      AND brand = %s
                      AND comparison_date < %s
                    ORDER BY comparison_date DESC
                    LIMIT 1
                    """,
                    (product["model_key"], product["brand"], comparison_date),
                )
                row = cur.fetchone()
    except Exception:
        return product

    if not row:
        return product

    previous_prices = {
        "phongvu": clean_number(row[0]),
        "gearvn": clean_number(row[1]),
        "cellphones": clean_number(row[2]),
    }

    for option in product.get("price_options", []):
        current_price = clean_number(option.get("current_price"))
        previous_price = previous_prices.get(option.get("source"))
        option["previous_price"] = previous_price
        option["change_amount"] = None
        option["change_percent"] = None
        if current_price is None or previous_price is None or previous_price <= 0:
            continue
        option["change_amount"] = current_price - previous_price
        option["change_percent"] = (current_price - previous_price) / previous_price * 100

    change_by_source = {
        option["source"]: option
        for option in product.get("price_options", [])
    }
    for price in product.get("prices", []):
        change = change_by_source.get(price.get("source"))
        if change:
            price["previous_price"] = change.get("previous_price")
            price["change_amount"] = change.get("change_amount")
            price["change_percent"] = change.get("change_percent")

    return product


def fetch_price_history(product):
    if not product:
        return []

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        comparison_date,
                        LEAST(
                            COALESCE(gia_ban_phongvu, 999999999999),
                            COALESCE(gia_ban_gearvn, 999999999999),
                            COALESCE(gia_ban_cellphones, 999999999999)
                        ) AS lowest_price
                    FROM daily_price_comparisons
                    WHERE model_key = %s
                      AND brand = %s
                    ORDER BY comparison_date
                    """,
                    (product["model_key"], product["brand"]),
                )
                rows = cur.fetchall()
    except Exception:
        return []

    history = []
    for date, price in rows:
        price = clean_number(price)
        if price is not None and 0 < price < 999999999999:
            history.append({"date": str(date), "price": price})
    return history


def fetch_stock_rows(product):
    if not product:
        return []

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (source)
                        source,
                        stock,
                        available,
                        crawled_at,
                        url
                    FROM raw_products
                    WHERE model_key = %s
                      AND brand = %s
                    ORDER BY source, crawled_at DESC
                    """,
                    (product["model_key"], product["brand"]),
                )
                columns = [desc.name for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
    except Exception:
        return []


def extract_specs_from_name(name):
    text = name or ""
    specs = {}

    cpu_patterns = [
        r"(Ultra\s+\d[-\w]*)",
        r"(Core\s+i[3579][-\s]?\w*)",
        r"(Ryzen\s+[3579][-\s]?\w*)",
        r"(Snapdragon\s+X[\w\s-]*)",
        r"(Apple\s+M\d[\w\s-]*)",
        r"\b(M\d)\b",
    ]
    for pattern in cpu_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            specs["CPU"] = match.group(1).strip()
            break

    ram = re.search(r"(\d+)\s*GB\s*(?:RAM)?", text, flags=re.IGNORECASE)
    if ram:
        specs["RAM"] = f"{ram.group(1)} GB"

    storage = re.search(r"(\d+)\s*(GB|TB)\s*(?:SSD|PCIe)?", text, flags=re.IGNORECASE)
    if storage:
        specs["Ổ cứng"] = f"{storage.group(1)} {storage.group(2).upper()}"

    screen = re.search(r"(\d{2}(?:\.\d)?)\s*(?:inch|\"|-inch)", text, flags=re.IGNORECASE)
    if screen:
        specs["Màn hình"] = f'{screen.group(1)}"'

    return specs


def extract_specs_from_name(name):
    specs = extract_specs_from_text(name)
    return {
        SPEC_DISPLAY_LABELS[column]: value
        for column, value in specs.items()
        if column in SPEC_DISPLAY_LABELS
    }


def normalize_text(text):
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def price_change_summary(history):
    if len(history) < 2:
        return None

    previous = history[-2]
    current = history[-1]
    previous_price = clean_number(previous.get("price"))
    current_price = clean_number(current.get("price"))
    if previous_price is None or current_price is None:
        return None

    delta = current_price - previous_price
    percent = abs(delta) / previous_price * 100 if previous_price else 0
    return {
        "previous_date": previous.get("date"),
        "current_date": current.get("date"),
        "previous_price": previous_price,
        "current_price": current_price,
        "delta": delta,
        "percent": percent,
    }


def is_english(language):
    return str(language or "").lower().startswith("en")


def best_price_line(product, language="vi"):
    english = is_english(language)
    if not product["prices"]:
        return "I do not have a selling price for this model yet." if english else "Mình chưa có giá bán cho model này."
    if english:
        return (
            f"The current lowest price is {format_vnd(product['lowest_price'])} "
            f"at {product['best_source']}."
        )
    return (
        f"Giá thấp nhất hiện tại là {format_vnd(product['lowest_price'])} "
        f"tại {product['best_source']}."
    )


def build_price_answer(product, language="vi"):
    english = is_english(language)
    if not product["prices"]:
        return "I do not have a selling price for this model yet." if english else "Mình chưa có giá bán cho model này."

    lines = [best_price_line(product, language), "Available prices:" if english else "Bảng giá đang có:"]
    for price in product["prices"]:
        suffix = " - lowest" if english and price["label"] == product["best_source"] else ""
        if not english and price["label"] == product["best_source"]:
            suffix = " - rẻ nhất"
        lines.append(f"- {price['label']}: {format_vnd(price['current_price'])}{suffix}")
    return "\n".join(lines)


def build_trend_answer(product, language="vi"):
    english = is_english(language)
    history = fetch_price_history(product)
    if len(history) < 2:
        if english:
            return (
                "I do not have enough price history to conclude the trend yet. "
                "This model needs at least 2 valid crawls with price data."
            )
        return (
            "Mình chưa có đủ lịch sử giá để kết luận xu hướng. "
            "Cần ít nhất 2 lần crawl có giá hợp lệ cho model này."
        )

    change = price_change_summary(history)
    if not change:
        if english:
            return "I have price history, but the latest change is not readable yet."
        return "Mình có lịch sử giá nhưng chưa đọc được mức thay đổi hợp lệ."

    if english and change["delta"] < 0:
        direction = "is falling"
        detail = f"down {format_vnd(abs(change['delta']))} ({change['percent']:.1f}%)"
    elif english and change["delta"] > 0:
        direction = "is rising"
        detail = f"up {format_vnd(change['delta'])} ({change['percent']:.1f}%)"
    elif english:
        direction = "is flat"
        detail = "unchanged"
    elif change["delta"] < 0:
        direction = "đang giảm"
        detail = f"giảm {format_vnd(abs(change['delta']))} ({change['percent']:.1f}%)"
    elif change["delta"] > 0:
        direction = "đang tăng"
        detail = f"tăng {format_vnd(change['delta'])} ({change['percent']:.1f}%)"
    else:
        direction = "đang đi ngang"
        detail = "không đổi"

    lowest_seen = min(item["price"] for item in history)
    if english:
        lines = [
            f"Latest trend: the price {direction}.",
            (
                f"From {change['previous_date']} to {change['current_date']}, "
                f"the lowest price is {detail}."
            ),
            f"Lowest price seen in the data: {format_vnd(lowest_seen)}.",
            best_price_line(product, language),
        ]
        return "\n".join(lines)

    lines = [
        f"Xu hướng gần nhất: giá {direction}.",
        (
            f"Từ {change['previous_date']} đến {change['current_date']}, "
            f"giá thấp nhất {detail}."
        ),
        f"Giá thấp nhất từng thấy trong dữ liệu: {format_vnd(lowest_seen)}.",
        best_price_line(product),
    ]
    return "\n".join(lines)


def build_buy_recommendation(product, language="vi"):
    english = is_english(language)
    if not product["prices"]:
        return "I do not have a selling price yet, so I cannot recommend buying this model." if english else "Mình chưa có giá bán nên chưa thể khuyến nghị mua model này."

    history = fetch_price_history(product)
    change = price_change_summary(history)
    lines = [best_price_line(product, language)]

    if not change:
        lines.append(
            "I do not have enough history to know whether this is a better time than before."
            if english
            else "Mình chưa có đủ lịch sử giá để biết đây có phải thời điểm tốt hơn trước không."
        )
    elif change["delta"] < 0:
        if english:
            lines.append(
                f"Compared with the previous crawl, the price dropped {format_vnd(abs(change['delta']))} "
                f"({change['percent']:.1f}%). That is a good signal if the specs fit your needs."
            )
        else:
            lines.append(
                f"So với lần crawl trước, giá đã giảm {format_vnd(abs(change['delta']))} "
                f"({change['percent']:.1f}%). Đây là tín hiệu tốt nếu cấu hình đúng nhu cầu."
            )
    elif change["delta"] > 0:
        if english:
            lines.append(
                f"Compared with the previous crawl, the price increased {format_vnd(change['delta'])} "
                f"({change['percent']:.1f}%). If it is not urgent, keep watching."
            )
        else:
            lines.append(
                f"So với lần crawl trước, giá đã tăng {format_vnd(change['delta'])} "
                f"({change['percent']:.1f}%). Nếu không gấp, nên theo dõi thêm."
            )
    else:
        lines.append("The price is flat compared with the previous crawl." if english else "Giá đang đi ngang so với lần crawl trước.")

    best = product["prices"][0]
    if best.get("url"):
        lines.append(f"Link to check first: {best['url']}" if english else f"Link nên kiểm tra trước: {best['url']}")
    lines.append(
        "Bottom line: this is based on crawled prices, so you should still check specs and warranty at the retailer."
        if english
        else "Kết luận: mình dựa trên giá crawl được, bạn vẫn nên kiểm tra cấu hình và bảo hành tại cửa hàng."
    )
    return "\n".join(lines)


def build_stock_answer(product, language="vi"):
    english = is_english(language)
    stock_rows = fetch_stock_rows(product)
    if not stock_rows:
        if english:
            return (
                "Current data does not have a clear stock status for this model. "
                "Some raw rows contain `stock` or `available`, but not enough to conclude confidently."
            )
        return (
            "Dữ liệu hiện tại chưa có trạng thái kho đủ rõ cho model này. "
            "Một số raw data có `stock` hoặc `available`, nhưng chưa đủ để kết luận chắc."
        )

    lines = ["Latest stock status found in raw data:" if english else "Trạng thái kho mới nhất mình thấy trong raw data:"]
    for row in stock_rows:
        source = SOURCE_LABELS.get(row["source"], row["source"])
        stock = row.get("stock")
        available = row.get("available")
        if stock is not None:
            lines.append(f"- {source}: stock = {stock}")
        elif available is not None:
            if english:
                lines.append(f"- {source}: {'in stock' if available else 'not in stock'}")
            else:
                lines.append(f"- {source}: {'có hàng' if available else 'chưa có hàng'}")
        else:
            lines.append(f"- {source}: no clear stock field" if english else f"- {source}: chưa có trường kho rõ ràng")
    return "\n".join(lines)


def build_specs_answer(product, language="vi"):
    english = is_english(language)
    specs = product.get("specs") or extract_specs_from_name(product["display_name"])
    if not specs:
        if english:
            return (
                "Current data does not have a detailed specs table. "
                "I will not invent specs; crawl the product detail page for a safer answer."
            )
        return (
            "Dữ liệu hiện tại chưa có bảng thông số kỹ thuật chi tiết. "
            "Mình không tự bịa cấu hình; nên crawl thêm trang chi tiết sản phẩm để chắc hơn."
        )

    lines = ["I can only infer from the product name, so treat this as reference information:" if english else "Mình chỉ suy luận được từ tên sản phẩm, nên đây là thông tin tham khảo:"]
    if product.get("specs"):
        lines = ["Specs currently available from crawled data:" if english else "Thong so hien co tu du lieu crawl:"]
    lines.extend(f"- {key}: {value}" for key, value in specs.items())
    lines.append(
        "For 100% accuracy, compare it with the retailer's product detail page."
        if english
        else "Nếu cần chính xác 100%, nên đối chiếu trang chi tiết của cửa hàng."
    )
    return "\n".join(lines)


def build_assistant_answer(product, message, language="vi"):
    english = is_english(language)
    if not product:
        return "I could not find the selected product." if english else "Mình chưa tìm thấy sản phẩm đang được chọn."

    message_lower = normalize_text(message)

    if any(keyword in message_lower for keyword in ["nen mua", "mua hom nay", "co nen", "dang mua", "should i buy", "buy today", "worth buying", "purchase"]):
        return build_buy_recommendation(product, language)

    if any(keyword in message_lower for keyword in ["xu huong", "lich su", "giam gia", "tang gia", "bien dong", "trend", "history", "price moved", "price movement", "drop", "decrease", "increase", "recently"]):
        return build_trend_answer(product, language)

    if any(keyword in message_lower for keyword in ["cau hinh", "cpu", "ram", "ssd", "man hinh", "thong so", "spec", "configuration", "processor", "screen", "display", "memory", "storage"]):
        return build_specs_answer(product, language)

    if any(keyword in message_lower for keyword in ["kho", "con hang", "het hang", "stock", "available", "availability", "in stock", "out of stock"]):
        return build_stock_answer(product, language)

    if any(keyword in message_lower for keyword in ["gia", "re", "mua", "website", "so sanh", "cua hang", "price", "cheapest", "best price", "retailer", "shop", "compare"]):
        return build_price_answer(product, language)

    if english:
        return (
            f"Selected model: {product['display_name']}.\n"
            f"{best_price_line(product, language)}\n"
            "You can ask: best price, should I buy today, price trend, specs, or stock status."
        )
    return (
        f"Model đang chọn: {product['display_name']}.\n"
        f"{best_price_line(product, language)}\n"
        "Bạn có thể hỏi nhanh: giá rẻ nhất, có nên mua hôm nay, xu hướng giá, cấu hình, hoặc tình trạng kho."
    )


class ChatRequest(BaseModel):
    product_id: int
    message: str
    language: str | None = "vi"


class AuthRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class FavoriteRequest(BaseModel):
    product_id: int


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "user": get_current_user(request),
            "featured": featured_products_by_brand(),
            "hero_slides": hero_price_movers(),
        },
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "auth.html",
        {
            "mode": "login",
            "title": "Đăng nhập",
            "subtitle": "Đăng nhập để lưu và theo dõi sản phẩm yêu thích.",
            "button": "Đăng nhập",
        },
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "auth.html",
        {
            "mode": "register",
            "title": "Tạo tài khoản",
            "subtitle": "Tài khoản local dùng để lưu sản phẩm yêu thích.",
            "button": "Tạo tài khoản",
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    products, data_source = fetch_dashboard_products(limit=300)
    selected = products[0] if products else None
    product_id = request.query_params.get("product_id")
    if product_id:
        try:
            requested_id = int(product_id)
            selected = next(
                (product for product in products if product["id"] == requested_id),
                find_product(requested_id),
            )
        except ValueError:
            selected = products[0] if products else None
    selected = attach_source_price_changes(selected)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "products": products,
            "selected": selected,
            "data_source": data_source,
            "history": fetch_price_history(selected),
            "user": get_current_user(request),
        },
    )


@app.get("/dashboard/product/{product_id}")
def dashboard_product(product_id: int):
    return RedirectResponse(f"/dashboard?product_id={product_id}", status_code=303)


@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request):
    products, data_source = fetch_dashboard_products(limit=500)
    query = (request.query_params.get("q") or "").strip().lower()
    brand = (request.query_params.get("brand") or "").strip().lower()
    min_price = clean_number(request.query_params.get("min_price"))
    max_price = clean_number(request.query_params.get("max_price"))

    if query:
        products = [
            product
            for product in products
            if query in (product["display_name"] or "").lower()
            or query in (product["model_key"] or "").lower()
            or query in (product["brand"] or "").lower()
        ]

    if brand:
        products = [
            product
            for product in products
            if (product["brand"] or "").lower() == brand
        ]

    if min_price is not None:
        products = [
            product
            for product in products
            if product["lowest_price"] is not None and product["lowest_price"] >= min_price
        ]

    if max_price is not None:
        products = [
            product
            for product in products
            if product["lowest_price"] is not None and product["lowest_price"] <= max_price
        ]

    return templates.TemplateResponse(
        request,
        "products.html",
        {
            "user": get_current_user(request),
            "products": products,
            "data_source": data_source,
            "query": query,
            "brand": brand,
            "min_price": int(min_price) if min_price is not None else "",
            "max_price": int(max_price) if max_price is not None else "",
        },
    )


@app.get("/favorites", response_class=HTMLResponse)
def favorites_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    ensure_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, model_key, brand, display_name, created_at
                FROM favorite_products
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user["id"],),
            )
            columns = [desc.name for desc in cur.description]
            favorites = [dict(zip(columns, row)) for row in cur.fetchall()]

    products, _ = fetch_dashboard_products(limit=1000)
    products_by_key = {
        (product["model_key"], (product["brand"] or "").lower()): product
        for product in products
    }
    for favorite in favorites:
        product = products_by_key.get(
            (favorite["model_key"], (favorite["brand"] or "").lower())
        )
        favorite["product_id"] = product["id"] if product else None
        favorite["image_url"] = product["image_url"] if product else None
        favorite["lowest_price"] = product["lowest_price"] if product else None
        favorite["best_source"] = product["best_source"] if product else None

    return templates.TemplateResponse(
        request,
        "favorites.html",
        {"user": user, "favorites": favorites},
    )


@app.get("/api/products/{product_id}")
def product_detail(product_id: int):
    product = find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product = attach_source_price_changes(product)
    return {
        "product": product,
        "history": fetch_price_history(product),
        "stock": fetch_stock_rows(product),
        "specs": product.get("specs") or extract_specs_from_name(product["display_name"]),
    }


@app.post("/api/chat")
def chat(payload: ChatRequest):
    product = find_product(payload.product_id)
    return {"answer": build_assistant_answer(product, payload.message, payload.language)}


@app.post("/api/register")
def register(request: Request, payload: AuthRequest):
    email = payload.email.strip().lower()
    password = payload.password
    display_name = (payload.display_name or "").strip() or email.split("@")[0]

    if "@" not in email:
        raise HTTPException(status_code=400, detail="Email không hợp lệ.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu nên có ít nhất 6 ký tự.")

    ensure_schema()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_users (email, display_name, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (email, display_name, hash_password(password)),
                )
                user_id = cur.fetchone()[0]
    except Exception as exc:
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            raise HTTPException(status_code=400, detail="Email này đã được đăng ký.") from exc
        raise

    request.session["user_id"] = user_id
    return {"ok": True}


@app.post("/api/login")
def login(request: Request, payload: AuthRequest):
    email = payload.email.strip().lower()
    ensure_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, password_hash
                FROM app_users
                WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()

    if not row or not verify_password(payload.password, row[1]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")

    request.session["user_id"] = row[0]
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.post("/api/favorites")
def add_favorite(request: Request, payload: FavoriteRequest):
    user = require_user(request)
    product = find_product(payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")

    ensure_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO favorite_products (user_id, model_key, brand, display_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, model_key, brand)
                DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    created_at = NOW()
                RETURNING id
                """,
                (
                    user["id"],
                    product["model_key"],
                    product["brand"],
                    product["display_name"],
                ),
            )
            favorite_id = cur.fetchone()[0]

    return {"ok": True, "favorite_id": favorite_id}


@app.delete("/api/favorites/{favorite_id}")
def remove_favorite(request: Request, favorite_id: int):
    user = require_user(request)
    ensure_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM favorite_products
                WHERE id = %s AND user_id = %s
                """,
                (favorite_id, user["id"]),
            )
    return {"ok": True}
