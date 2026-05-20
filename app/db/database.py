import argparse
import os
from pathlib import Path

import pandas as pd

from app.pipeline.merge_daily import extract_model_key


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"
PROJECT_DIR = PROJECT_ROOT
SCHEMA_FILE = APP_DIR / "db" / "schema.sql"
RAW_DIR = Path("D:/Data/raw")
PROCESSED_DIR = Path("D:/Data/processed")
FALLBACK_PROCESSED_DIR = PROJECT_ROOT / "data" / "output"


def load_env_file(path=PROJECT_DIR / ".env"):
    """Load simple KEY=VALUE pairs from .env without requiring python-dotenv."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_database_url():
    load_env_file()
    return os.getenv("DATABASE_URL")


def get_connection():
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError(
            "Chua cau hinh DATABASE_URL. Hay tao file .env tu .env.example."
        )

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Chua cai thu vien psycopg. Hay chay: .\\.venv\\Scripts\\pip.exe install -r requirements.txt"
        ) from exc

    return psycopg.connect(database_url)


def init_database():
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
    print("Da khoi tao/cap nhat schema PostgreSQL.")


def create_crawl_run(note=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO crawl_runs (status, note)
                VALUES ('running', %s)
                RETURNING id
                """,
                (note,),
            )
            return cur.fetchone()[0]


def finish_crawl_run(run_id, status="success", note=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE crawl_runs
                SET status = %s,
                    note = COALESCE(%s, note),
                    finished_at = NOW()
                WHERE id = %s
                """,
                (status, note, run_id),
            )


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def clean_text(value):
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def clean_number(value):
    value = clean_value(value)
    if value in ("", None):
        return None
    return value


def clean_bool(value):
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def parse_datetime(value):
    value = clean_value(value)
    if value is None:
        return pd.Timestamp.now().to_pydatetime()
    return pd.to_datetime(value).to_pydatetime()


def row_extra_data(row, known_columns):
    extra = {}
    for key, value in row.items():
        if key in known_columns:
            continue
        cleaned = clean_value(value)
        if cleaned is not None:
            extra[key] = cleaned
    return extra


def import_raw_csv(path, run_id=None):
    from psycopg.types.json import Jsonb

    path = Path(path)
    df = pd.read_csv(path)
    if df.empty:
        print(f"Bo qua file rong: {path}")
        return 0

    known_columns = {
        "product_id",
        "sku",
        "name",
        "brand",
        "segment",
        "current_price",
        "original_price",
        "stock",
        "available",
        "url",
        "collection_handle",
        "source",
        "crawled_at",
    }

    inserted_or_skipped = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                name = clean_text(row.get("name"))
                brand = clean_text(row.get("brand"))
                source = clean_text(row.get("source"))
                if not name or not brand or not source:
                    continue

                crawled_at = parse_datetime(row.get("crawled_at"))
                model_key = extract_model_key(name)

                cur.execute(
                    """
                    INSERT INTO raw_products (
                        run_id, source, source_product_id, sku, name, brand, segment,
                        current_price, original_price, stock, available, url,
                        collection_handle, model_key, crawled_at, crawl_date,
                        raw_file, extra_data
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s
                    )
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        run_id,
                        source,
                        clean_text(row.get("product_id")),
                        clean_text(row.get("sku")),
                        name,
                        brand,
                        clean_text(row.get("segment")),
                        clean_number(row.get("current_price")),
                        clean_number(row.get("original_price")),
                        clean_number(row.get("stock")),
                        clean_bool(row.get("available")),
                        clean_text(row.get("url")),
                        clean_text(row.get("collection_handle")),
                        model_key,
                        crawled_at,
                        crawled_at.date(),
                        str(path),
                        Jsonb(row_extra_data(row, known_columns)),
                    ),
                )
                inserted_or_skipped += 1

    print(f"Da import raw CSV vao DB: {path.name} ({inserted_or_skipped} dong xu ly)")
    return inserted_or_skipped


def import_comparison_csv(path):
    path = Path(path)
    df = pd.read_csv(path)
    if df.empty:
        print(f"Bo qua file rong: {path}")
        return 0

    processed = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                comparison_date = pd.to_datetime(row["ngay_crawl"]).date()
                cur.execute(
                    """
                    INSERT INTO daily_price_comparisons (
                        comparison_date, model_key, display_name, brand,
                        gia_ban_phongvu, gia_goc_phongvu, url_phongvu,
                        gia_ban_gearvn, gia_goc_gearvn, url_gearvn,
                        gia_ban_cellphones, gia_goc_cellphones, url_cellphones,
                        so_website_co_hang, source_file
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                    ON CONFLICT (comparison_date, model_key, brand)
                    DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        gia_ban_phongvu = EXCLUDED.gia_ban_phongvu,
                        gia_goc_phongvu = EXCLUDED.gia_goc_phongvu,
                        url_phongvu = EXCLUDED.url_phongvu,
                        gia_ban_gearvn = EXCLUDED.gia_ban_gearvn,
                        gia_goc_gearvn = EXCLUDED.gia_goc_gearvn,
                        url_gearvn = EXCLUDED.url_gearvn,
                        gia_ban_cellphones = EXCLUDED.gia_ban_cellphones,
                        gia_goc_cellphones = EXCLUDED.gia_goc_cellphones,
                        url_cellphones = EXCLUDED.url_cellphones,
                        so_website_co_hang = EXCLUDED.so_website_co_hang,
                        source_file = EXCLUDED.source_file,
                        updated_at = NOW()
                    """,
                    (
                        comparison_date,
                        clean_text(row.get("model_key")),
                        clean_text(row.get("ten")),
                        clean_text(row.get("brand")),
                        clean_number(row.get("gia_ban_phongvu")),
                        clean_number(row.get("gia_goc_phongvu")),
                        clean_text(row.get("url_phongvu")),
                        clean_number(row.get("gia_ban_gearvn")),
                        clean_number(row.get("gia_goc_gearvn")),
                        clean_text(row.get("url_gearvn")),
                        clean_number(row.get("gia_ban_cellphones")),
                        clean_number(row.get("gia_goc_cellphones")),
                        clean_text(row.get("url_cellphones")),
                        int(clean_number(row.get("so_website_co_hang")) or 0),
                        str(path),
                    ),
                )
                processed += 1

    print(f"Da import comparison CSV vao DB: {path.name} ({processed} dong)")
    return processed


def sync_files_to_database(raw_files, comparison_file, run_id=None):
    init_database()
    for raw_file in raw_files:
        import_raw_csv(raw_file, run_id=run_id)
    import_comparison_csv(comparison_file)


def latest_files(directory, pattern):
    files = sorted(Path(directory).glob(pattern))
    return files[-1:] if files else []


def import_existing_latest_files():
    init_database()

    raw_files = []
    for source in ("phongvu", "gearvn", "cellphones"):
        for brand in ("acer", "asus", "msi"):
            raw_files.extend(latest_files(RAW_DIR, f"{source}_{brand}_laptop_*.csv"))

    processed_files = latest_files(PROCESSED_DIR, "laptop_price_compare_*.csv")
    if not processed_files:
        processed_files = latest_files(FALLBACK_PROCESSED_DIR, "laptop_price_compare_*.csv")

    run_id = create_crawl_run(note="Import existing latest CSV files")
    try:
        for raw_file in raw_files:
            import_raw_csv(raw_file, run_id=run_id)
        for processed_file in processed_files:
            import_comparison_csv(processed_file)
        finish_crawl_run(run_id, status="success")
    except Exception as exc:
        finish_crawl_run(run_id, status="failed", note=str(exc))
        raise


def test_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version()")
            database_name, user_name, version = cur.fetchone()

    print(f"Database: {database_name}")
    print(f"User: {user_name}")
    print(f"Version: {version}")


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL tools for laptop price project")
    parser.add_argument(
        "command",
        choices=["test", "init", "import-existing"],
        help="test: kiem tra ket noi, init: tao bang, import-existing: import CSV moi nhat",
    )
    args = parser.parse_args()

    if args.command == "test":
        test_connection()
    elif args.command == "init":
        init_database()
    elif args.command == "import-existing":
        import_existing_latest_files()


if __name__ == "__main__":
    main()
