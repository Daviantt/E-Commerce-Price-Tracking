import argparse
import html
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests


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
    original_price: float
    current_price: float
    discount_percent: float
    link: str | None


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


def format_vnd(value):
    return f"{int(round(value)):,}".replace(",", ".") + " VND"


def latest_processed_csv():
    for directory in (PROCESSED_DIR, FALLBACK_PROCESSED_DIR):
        files = sorted(Path(directory).glob("laptop_price_compare_*.csv"))
        if files:
            return files[-1]
    raise FileNotFoundError(
        "Khong tim thay file laptop_price_compare_*.csv trong D:/Data/processed "
        "hoac data/output. Hay chay: python run_daily.py"
    )


def load_comparison_frame(csv_path=None):
    path = Path(csv_path) if csv_path else latest_processed_csv()
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file CSV: {path}")
    return path, pd.read_csv(path)


def discount_percent(original_price, current_price):
    if original_price is None or current_price is None:
        return None
    if current_price >= original_price:
        return None
    return (1 - current_price / original_price) * 100


def build_deals(df, threshold=DEFAULT_THRESHOLD):
    deals = []
    for _, row in df.iterrows():
        product_name = clean_text(row.get("ten")) or clean_text(row.get("display_name"))
        brand = clean_text(row.get("brand")) or ""
        model_key = clean_text(row.get("model_key")) or ""
        if not product_name:
            continue

        for source, store_name in SOURCES.items():
            current_price = clean_number(row.get(f"gia_ban_{source}"))
            original_price = clean_number(row.get(f"gia_goc_{source}"))
            discount = discount_percent(original_price, current_price)
            if discount is None or discount < threshold:
                continue

            deals.append(
                Deal(
                    product_name=product_name,
                    brand=brand,
                    model_key=model_key,
                    source=source,
                    store_name=store_name,
                    original_price=original_price,
                    current_price=current_price,
                    discount_percent=discount,
                    link=clean_text(row.get(f"url_{source}")),
                )
            )

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
        f"<b>CANH BAO DEAL LAPTOP - GIAM {deal.discount_percent:.1f}%</b>\n\n"
        f"<b>San pham:</b> {product_name}\n"
        f"<b>Brand:</b> {brand}\n"
        f"<b>Model:</b> {model_key}\n"
        f"<b>Cua hang:</b> {store_name}\n"
        f"<b>Gia goc:</b> {format_vnd(deal.original_price)}\n"
        f"<b>Gia hien tai:</b> {format_vnd(deal.current_price)}"
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

    csv_path, df = load_comparison_frame(args.csv)
    deals = build_deals(df, threshold=args.threshold)[: args.limit]
    print(f"CSV: {csv_path}")
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
