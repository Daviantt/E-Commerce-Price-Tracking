import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd


RAW_DIR = Path("D:/Data/raw")
MERGED_DIR = Path("D:/Data/processed")
FALLBACK_MERGED_DIR = Path("output")
SOURCES = ("phongvu", "gearvn", "cellphones")
IMAGE_SOURCE_PRIORITY = ("gearvn", "phongvu", "cellphones")
BRANDS = ("acer", "asus", "msi")


def strip_accents(text):
    text = unicodedata.normalize("NFD", str(text))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def normalize_text(text):
    text = strip_accents(text).upper()
    text = text.split("(")[0]
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_model_token(token):
    return bool(re.search(r"[A-Z]", token) and re.search(r"\d", token))


def is_model_suffix_token(token):
    return is_model_token(token) or bool(re.fullmatch(r"\d{3,5}", token))


def extract_model_key(name):
    """
    Tạo khóa model tương đối bền giữa các website.

    Ví dụ:
    - "AG15-52P-52WT" và "AG15 52P 52WT" -> "AG15-52P-52WT"
    - "FX607VU-RL045W" -> "FX607VU-RL045W"
    - "A13VE 2410VN" -> "A13VE-2410VN"
    """
    tokens = normalize_text(name).split()
    candidates = []

    for start in range(len(tokens)):
        for size in (3, 2):
            group = tokens[start : start + size]
            if len(group) != size:
                continue
            if not is_model_token(group[0]):
                continue
            if not all(is_model_suffix_token(token) for token in group[1:]):
                continue
            candidates.append((start + size, size, group))

    if not candidates:
        return None

    # Model laptop thường nằm gần cuối phần tên.
    # Nếu nhiều cụm cùng kết thúc ở một vị trí, ưu tiên cụm dài hơn để giữ đủ tiền tố.
    _, _, best = max(candidates, key=lambda item: (item[0], item[1]))
    return "-".join(best)


def latest_file(source, brand):
    pattern = f"{source}_{brand}_laptop_*.csv"
    files = sorted(RAW_DIR.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy file theo mẫu: {pattern}")
    return files[-1]


def read_source_file(source, brand):
    path = latest_file(source, brand)
    df = pd.read_csv(path)
    df["model_key"] = df["name"].map(extract_model_key)
    df = df[df["model_key"].notna()].copy()
    df["crawl_date"] = pd.to_datetime(df["crawled_at"]).dt.date.astype(str)
    return df


def choose_display_name(group):
    for source in SOURCES:
        rows = group[group["source"] == source]
        if not rows.empty:
            return rows.iloc[0]["name"]
    return group.iloc[0]["name"]


def build_brand_merged_frame(brand):
    frames = [read_source_file(source, brand) for source in SOURCES]
    all_rows = pd.concat(frames, ignore_index=True)

    merged_rows = []
    for model_key, group in all_rows.groupby("model_key", sort=True):
        row = {
            "model_key": model_key,
            "ten": choose_display_name(group),
            "brand": brand,
            "ngay_crawl": max(group["crawl_date"]),
        }
        image_url = None
        for source in IMAGE_SOURCE_PRIORITY:
            source_rows = group[group["source"] == source]
            if not source_rows.empty and "image_url" in source_rows.columns:
                candidate = source_rows.iloc[0].get("image_url")
                if pd.notna(candidate) and candidate:
                    image_url = candidate
                    break

        row["image_url"] = image_url

        for source in SOURCES:
            source_rows = group[group["source"] == source]
            if source_rows.empty:
                row[f"gia_ban_{source}"] = None
                row[f"gia_goc_{source}"] = None
                row[f"url_{source}"] = None
            else:
                first = source_rows.iloc[0]
                row[f"gia_ban_{source}"] = first["current_price"]
                row[f"gia_goc_{source}"] = first["original_price"]
                row[f"url_{source}"] = first["url"]

        row["so_website_co_hang"] = sum(
            pd.notna(row[f"gia_ban_{source}"]) for source in SOURCES
        )
        merged_rows.append(row)

    return pd.DataFrame(merged_rows)


def build_all_merged_frame():
    frames = [build_brand_merged_frame(brand) for brand in BRANDS]
    return pd.concat(frames, ignore_index=True)


def save_merged_frame(df):
    output_dir = MERGED_DIR
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        output_dir = FALLBACK_MERGED_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    filename = output_dir / f"laptop_price_compare_{date_str}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    return filename


def print_match_summary(df):
    print("Tổng hợp mức độ ghép theo số website có mặt:")
    summary = (
        df.groupby(["brand", "so_website_co_hang"])
        .size()
        .rename("so_model")
        .reset_index()
    )
    print(summary.to_string(index=False))


def merge_latest_daily_files():
    merged_df = build_all_merged_frame()
    output_file = save_merged_frame(merged_df)
    print_match_summary(merged_df)
    print(f"Đã lưu file đối chiếu → {output_file}")
    return output_file


if __name__ == "__main__":
    merge_latest_daily_files()
