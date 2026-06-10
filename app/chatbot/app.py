import argparse
import html
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

# duong dan toi file procsessed
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import FALLBACK_PROCESSED_DIR, PROCESSED_DIR, load_env_file


SOURCES = {
    "phongvu": "Phong Vu",
    "gearvn": "GearVN",
    "cellphones": "CellphoneS",
}

DEFAULT_THRESHOLD = 10.0
DEFAULT_LIMIT = 20


@dataclass
class Deal:
    product_name: str
    brand: str
    model_key: str
    source: str
    store_name: str
    previous_price: float
    current_price: float
    discount_percent: float
    link: str | None

# kiem tra tinh dung dan cua so
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
    if math.isnan(number) or number <= 0:
        return None
    return number

# lam sach du lieu chu
def clean_text(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text

#chuyen qua dang tien vnd
def format_vnd(value):
    return f"{int(round(value)):,}".replace(",", ".") + " VND"

def processed_csv_files():
    files = []
    for directory in (PROCESSED_DIR, FALLBACK_PROCESSED_DIR):
        files.extend(Path(directory).glob("laptop_price_compare_*.csv"))
    return sorted(set(files))


# lay file processed moi nhat
def latest_processed_csv():
    files = processed_csv_files()
    if files:
        return files[-1]
    raise FileNotFoundError(
        "Khong tim thay file laptop_price_compare_*.csv trong D:/Data/processed "
        "hoac data/output. Hay chay: python run_daily.py"
    )


def previous_processed_csv(current_csv_path=None):
    files = processed_csv_files()
    if not current_csv_path:
        if len(files) < 2:
            raise FileNotFoundError(
                "Khong tim thay file CSV ngay hom truoc de so sanh gia. "
                "Can it nhat 2 file laptop_price_compare_*.csv."
            )
        return files[-2]

    if current_csv_path:
        current_csv_path = Path(current_csv_path).resolve()
        for index, path in enumerate(files):
            if path.resolve() == current_csv_path:
                if index == 0:
                    break
                return files[index - 1]

        fallback_files = [path for path in files if path.resolve() != current_csv_path]
        if fallback_files:
            return fallback_files[-1]

    raise FileNotFoundError(
        "Khong tim thay file CSV ngay hom truoc de so sanh gia. "
        "Can it nhat 2 file laptop_price_compare_*.csv."
    )


def load_comparison_frame(csv_path=None):
    path = Path(csv_path) if csv_path else latest_processed_csv()
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file CSV: {path}")
    return path, pd.read_csv(path)


def price_drop_percent(previous_price, current_price):
    if previous_price is None or current_price is None:
        return None
    if current_price >= previous_price:
        return None
    return (1 - current_price / previous_price) * 100


def build_previous_row_map(df):
    rows = {}
    for _, row in df.iterrows():
        model_key = clean_text(row.get("model_key"))
        if model_key:
            rows[model_key] = row
    return rows


def build_deals(current_df, previous_df, threshold=DEFAULT_THRESHOLD):
    previous_rows = build_previous_row_map(previous_df)
    deals = []
    for _, row in current_df.iterrows():
        product_name = clean_text(row.get("ten")) or clean_text(row.get("display_name"))
        brand = clean_text(row.get("brand")) or ""
        model_key = clean_text(row.get("model_key")) or ""
        previous_row = previous_rows.get(model_key)
        if not product_name or previous_row is None:
            continue

        for source, store_name in SOURCES.items():
            current_price = clean_number(row.get(f"gia_ban_{source}"))
            previous_price = clean_number(previous_row.get(f"gia_ban_{source}"))
            discount = price_drop_percent(previous_price, current_price)
            if discount is None or discount < threshold:
                continue

            deals.append(
                Deal(
                    product_name=product_name,
                    brand=brand,
                    model_key=model_key,
                    source=source,
                    store_name=store_name,
                    previous_price=previous_price,
                    current_price=current_price,
                    discount_percent=discount,
                    link=clean_text(row.get(f"url_{source}")),
                )
            )
    #tra ve danh sach phan tram giam gia cua laptop tu cao den thap
    return sorted(deals, key=lambda deal: deal.discount_percent, reverse=True)

    
def build_telegram_message(deal):
    product_name = html.escape(deal.product_name)
    store_name = html.escape(deal.store_name)
    brand = html.escape(deal.brand.upper()) if deal.brand else "N/A"
    model_key = html.escape(deal.model_key) if deal.model_key else "N/A"
    link = html.escape(deal.link or "", quote=True)
    detail_line = (
        f"\n<a href='{link}'>Xem chi tiet san pham</a>"
        if deal.link
        else "\nKhong co link san pham."
    )

    return (
        f"<b>CANH BAO GIA LAPTOP GIAM {deal.discount_percent:.1f}% SO VOI HOM QUA</b>\n\n"
        f"<b>San pham:</b> {product_name}\n"
        f"<b>Brand:</b> {brand}\n"
        f"<b>Model:</b> {model_key}\n"
        f"<b>Cua hang:</b> {store_name}\n"
        f"<b>Gia hom qua:</b> {format_vnd(deal.previous_price)}\n"
        f"<b>Gia hom nay:</b> {format_vnd(deal.current_price)}\n"
        f"<b>Muc giam:</b> {format_vnd(deal.previous_price - deal.current_price)}"
        f"{detail_line}"
    )


def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def send_deals(deals, token, chat_id, dry_run=True):
    sent_count = 0
    for deal in deals:
        message = build_telegram_message(deal)
        if dry_run:
            print("-" * 80)
            print(message.replace("<b>", "").replace("</b>", ""))
            continue
        send_telegram_message(token, chat_id, message)
        sent_count += 1
    return sent_count


def get_env_float(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def main():
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Scan laptop comparison data and send Telegram deal alerts."
    )
    parser.add_argument(
        "--csv",
        help="Duong dan CSV processed. Mac dinh lay file laptop_price_compare_*.csv moi nhat.",
    )
    parser.add_argument(
        "--previous-csv",
        help="Duong dan CSV processed ngay hom truoc. Mac dinh lay file lien truoc file hien tai.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=get_env_float("TELEGRAM_ALERT_THRESHOLD", DEFAULT_THRESHOLD),
        help="Nguong giam gia toi thieu theo phan tram.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("TELEGRAM_ALERT_LIMIT", DEFAULT_LIMIT)),
        help="So deal toi da duoc in/gui.",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Gui Telegram that. Neu khong co flag nay thi chi dry-run.",
    )
    args = parser.parse_args()

    csv_path, current_df = load_comparison_frame(args.csv)
    previous_csv = Path(args.previous_csv) if args.previous_csv else previous_processed_csv(csv_path)
    previous_csv_path, previous_df = load_comparison_frame(previous_csv)
    deals = build_deals(current_df, previous_df, threshold=args.threshold)[: args.limit]
    print(f"CSV hom nay: {csv_path}")
    print(f"CSV hom qua: {previous_csv_path}")
    print(f"Threshold: {args.threshold:.1f}%")
    print(f"Deals found: {len(deals)}")

    if not deals:
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    dry_run = not args.send
    if not dry_run and (not token or not chat_id):
        raise RuntimeError(
            "Thieu TELEGRAM_BOT_TOKEN hoac TELEGRAM_CHAT_ID trong file .env."
        )

    sent_count = send_deals(deals, token, chat_id, dry_run=dry_run)
    if dry_run:
        print("\nDry-run xong. Them --send neu muon gui Telegram that.")
    else:
        print(f"Da gui {sent_count} tin nhan Telegram.")


if __name__ == "__main__":
    main()
