import os

from app.chatbot.app import (
    DEFAULT_LIMIT,
    DEFAULT_THRESHOLD,
    build_deals,
    load_comparison_frame,
    previous_processed_csv,
    send_deals,
)
from app.crawlers.cellphones import crawl_all_supported_brands as crawl_cellphones_brands
from app.crawlers.gearvn import crawl_all_supported_brands as crawl_gearvn_brands
from app.crawlers.phongvu import crawl_all_supported_brands as crawl_phongvu_brands
from app.db.database import (
    create_crawl_run,
    finish_crawl_run,
    get_database_url,
    init_database,
    sync_files_to_database,
)
from app.pipeline.merge_daily import merge_latest_daily_files


def get_telegram_config():
    return os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")


def get_env_float(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def build_price_drop_deals(current_csv_path):
    current_csv_path, current_df = load_comparison_frame(current_csv_path)
    previous_csv = previous_processed_csv(current_csv_path)
    _, previous_df = load_comparison_frame(previous_csv)

    return build_deals(
        current_df,
        previous_df,
        threshold=get_env_float("TELEGRAM_ALERT_THRESHOLD", DEFAULT_THRESHOLD),
        favorite_keys=None,
    )


def notify_price_drop_products(current_csv_path):
    token, chat_id = get_telegram_config()
    if not token or not chat_id:
        print("Telegram chua cau hinh nen bo qua thong bao san pham giam gia.")
        return 0

    deals = build_price_drop_deals(current_csv_path)
    limit = int(os.getenv("TELEGRAM_ALERT_LIMIT", DEFAULT_LIMIT))
    deals = deals[:limit]
    if not deals:
        print("Khong co san pham giam gia de gui Telegram.")
        return 0

    return send_deals(deals, token, chat_id, dry_run=False)


def main():
    database_enabled = bool(get_database_url())
    run_id = None
    raw_files = []
    merged_file = None

    if database_enabled:
        init_database()
        run_id = create_crawl_run(note="Daily crawl from run_daily.py")
    else:
        print(
            "Chua cau hinh DATABASE_URL nen chi luu CSV, "
            "chua ghi vao PostgreSQL."
        )

    try:
        raw_files.extend(crawl_phongvu_brands())
        raw_files.extend(crawl_gearvn_brands())
        raw_files.extend(crawl_cellphones_brands())

        merged_file = merge_latest_daily_files()

        try:
            sent_count = notify_price_drop_products(merged_file)
            print(f"Da gui {sent_count} thong bao san pham giam gia.")
        except Exception as exc:
            print(f"Khong gui duoc thong bao san pham giam gia: {exc}")

        if database_enabled:
            sync_files_to_database(raw_files, merged_file, run_id=run_id)
            finish_crawl_run(run_id, status="success")

    except Exception as exc:
        if database_enabled and run_id is not None:
            finish_crawl_run(run_id, status="failed", note=str(exc))
        raise


if __name__ == "__main__":
    main()
