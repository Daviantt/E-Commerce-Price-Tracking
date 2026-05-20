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

app = FastAPI(title="Laptop Price Analytics")
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


def format_vnd(value):
    value = clean_number(value)
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", ".") + "₫"


templates.env.filters["vnd"] = format_vnd


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


def product_from_record(record):
    prices = []
    price_options = []
    for source in SOURCE_LABELS:
        current_price = clean_number(record.get(f"gia_ban_{source}"))
        original_price = clean_number(record.get(f"gia_goc_{source}"))
        url = record.get(f"url_{source}")
        option = {
            "source": source,
            "label": SOURCE_LABELS[source],
            "current_price": current_price,
            "original_price": original_price,
            "url": url,
            "available": current_price is not None,
            "status": "Đang kinh doanh" if current_price is not None else "Không kinh doanh",
        }
        price_options.append(option)
        if current_price is not None:
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
        "so_website_co_hang": int(record.get("so_website_co_hang") or len(prices)),
        "prices": prices,
        "price_options": price_options,
        "lowest_price": lowest_price,
        "average_price": average_price,
        "best_source": prices[0]["label"] if prices else None,
    }


def fetch_products_from_database(limit=80):
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

    return [product_from_record(row) for row in rows]


def latest_csv(directory, pattern):
    files = sorted(Path(directory).glob(pattern))
    return files[-1] if files else None


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


def find_product(product_id):
    products, _ = fetch_dashboard_products(limit=1000)
    for product in products:
        if product["id"] == product_id:
            return product
    return None


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
        if price is not None and price < 999999999999:
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


def normalize_text(text):
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def build_assistant_answer(product, message):
    if not product:
        return "Mình chưa tìm thấy sản phẩm đang được chọn."

    message_lower = normalize_text(message)
    specs = extract_specs_from_name(product["display_name"])
    stock_rows = fetch_stock_rows(product)

    if any(keyword in message_lower for keyword in ["cau hinh", "cpu", "ram", "ssd", "man hinh", "thong so"]):
        if not specs:
            return (
                "Dữ liệu hiện tại chưa có bảng thông số kỹ thuật chi tiết. "
                "Mình chưa nên tự bịa cấu hình. Bước sau ta có thể thêm crawler chi tiết "
                "từ trang sản phẩm hoặc nối AI để trích xuất từ mô tả."
            )
        lines = ["Mình chỉ suy luận được từ tên sản phẩm, nên đây là thông tin tham khảo:"]
        lines.extend(f"- {key}: {value}" for key, value in specs.items())
        lines.append("Nếu cần chính xác 100%, ta nên crawl thêm trang chi tiết sản phẩm.")
        return "\n".join(lines)

    if any(keyword in message_lower for keyword in ["kho", "con hang", "het hang", "stock"]):
        if not stock_rows:
            return (
                "Dữ liệu so sánh hiện tại chưa có trạng thái kho đầy đủ cho model này. "
                "Một số raw data có `stock` hoặc `available`, nhưng chưa đủ tin cậy để kết luận toàn thị trường."
            )
        lines = ["Trạng thái kho mình thấy trong raw data mới nhất:"]
        for row in stock_rows:
            source = SOURCE_LABELS.get(row["source"], row["source"])
            stock = row.get("stock")
            available = row.get("available")
            if stock is not None:
                lines.append(f"- {source}: stock = {stock}")
            elif available is not None:
                lines.append(f"- {source}: {'có hàng' if available else 'chưa có hàng'}")
            else:
                lines.append(f"- {source}: chưa có trường kho rõ ràng")
        return "\n".join(lines)

    if any(keyword in message_lower for keyword in ["gia", "re", "mua", "website", "so sanh"]):
        if not product["prices"]:
            return "Mình chưa có giá bán cho model này."
        lines = [
            f"Giá thấp nhất hiện tại là {format_vnd(product['lowest_price'])} tại {product['best_source']}."
        ]
        for price in product["prices"]:
            lines.append(f"- {price['label']}: {format_vnd(price['current_price'])}")
        return "\n".join(lines)

    return (
        f"Model đang chọn: {product['display_name']}.\n"
        f"Giá thấp nhất: {format_vnd(product['lowest_price'])} tại {product['best_source'] or 'chưa rõ'}.\n"
        "Bạn có thể hỏi mình về giá, cấu hình suy luận từ tên máy, hoặc trạng thái kho hiện có trong raw data."
    )


class ChatRequest(BaseModel):
    product_id: int
    message: str


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

    return templates.TemplateResponse(
        request,
        "products.html",
        {
            "user": get_current_user(request),
            "products": products,
            "data_source": data_source,
            "query": query,
            "brand": brand,
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
    return {
        "product": product,
        "history": fetch_price_history(product),
        "stock": fetch_stock_rows(product),
        "specs": extract_specs_from_name(product["display_name"]),
    }


@app.post("/api/chat")
def chat(payload: ChatRequest):
    product = find_product(payload.product_id)
    return {"answer": build_assistant_answer(product, payload.message)}


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
