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


def main():
    database_enabled = bool(get_database_url())
    run_id = None

    if database_enabled:
        init_database()
        run_id = create_crawl_run(note="Daily crawl from run_daily.py")
    else:
        print(
            "Chua cau hinh DATABASE_URL nen chi luu CSV, "
            "chua ghi vao PostgreSQL."
        )

    try:
        raw_files = []
        raw_files.extend(crawl_phongvu_brands())
        raw_files.extend(crawl_gearvn_brands())
        raw_files.extend(crawl_cellphones_brands())

        merged_file = merge_latest_daily_files()

        if database_enabled:
            sync_files_to_database(raw_files, merged_file, run_id=run_id)
            finish_crawl_run(run_id, status="success")

    except Exception as exc:
        if database_enabled and run_id is not None:
            finish_crawl_run(run_id, status="failed", note=str(exc))
        raise


if __name__ == "__main__":
    main()
