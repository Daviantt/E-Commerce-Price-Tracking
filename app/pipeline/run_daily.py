import html
import os

import requests

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


def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def build_run_daily_message(
    status,
    raw_files,
    merged_file=None,
    run_id=None,
    database_enabled=False,
    error=None,
):
    header = "RUN_DAILY HOAN TAT" if status == "success" else "RUN_DAILY THAT BAI"
    lines = [f"<b>{header}</b>"]
    if run_id is not None:
        lines.append(f"<b>Run ID:</b> {run_id}")
    lines.append(f"<b>Raw files:</b> {len(raw_files)}")
    if merged_file is not None:
        lines.append(f"<b>Merged file:</b> {html.escape(str(merged_file))}")
    lines.append(f"<b>Database:</b> {'enabled' if database_enabled else 'disabled'}")
    if error:
        lines.append(f"<b>Error:</b> {html.escape(str(error))}")
    return "\n".join(lines)


def notify_run_daily(
    status,
    raw_files,
    merged_file=None,
    run_id=None,
    database_enabled=False,
    error=None,
):
    token, chat_id = get_telegram_config()
    if not token or not chat_id:
        print("Telegram chua cau hinh nen bo qua thong bao run_daily.")
        return False

    message = build_run_daily_message(
        status=status,
        raw_files=raw_files,
        merged_file=merged_file,
        run_id=run_id,
        database_enabled=database_enabled,
        error=error,
    )
    send_telegram_message(token, chat_id, message)
    return True


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

        if database_enabled:
            sync_files_to_database(raw_files, merged_file, run_id=run_id)
            finish_crawl_run(run_id, status="success")

        notify_run_daily(
            status="success",
            raw_files=raw_files,
            merged_file=merged_file,
            run_id=run_id,
            database_enabled=database_enabled,
        )

    except Exception as exc:
        if database_enabled and run_id is not None:
            finish_crawl_run(run_id, status="failed", note=str(exc))
        try:
            notify_run_daily(
                status="failed",
                raw_files=raw_files,
                merged_file=merged_file,
                run_id=run_id,
                database_enabled=database_enabled,
                error=exc,
            )
        except Exception as notify_exc:
            print(f"Khong gui duoc thong bao Telegram: {notify_exc}")
        raise


if __name__ == "__main__":
    main()
