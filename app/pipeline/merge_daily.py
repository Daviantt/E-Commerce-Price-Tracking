import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.crawlers.common import (
    TECHNICAL_COLUMNS,
    classify_price_segment,
    clean_spec_value,
    clean_url,
    compute_discount_percent,
    extract_specs_from_text,
    normalize_spec_value,
    normalize_price_pair,
    specs_to_display,
)


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
    if {"current_price", "original_price"}.issubset(df.columns):
        prices = [
            normalize_price_pair(current_price, original_price)
            for current_price, original_price in zip(
                df["current_price"], df["original_price"]
            )
        ]
        df["current_price"] = [current_price for current_price, _ in prices]
        df["original_price"] = [original_price for _, original_price in prices]
    if "image_url" in df.columns:
        df["image_url"] = df["image_url"].map(clean_url)
    if "url" in df.columns:
        df["url"] = df["url"].map(clean_url)
    inferred_specs = df["name"].map(extract_specs_from_text)
    for column in TECHNICAL_COLUMNS:
        if column not in df.columns:
            df[column] = None
        df[column] = [
            normalize_spec_value(column, value) or inferred.get(column)
            for value, inferred in zip(df[column], inferred_specs)
        ]
    if "discount_percent" not in df.columns:
        df["discount_percent"] = [
            compute_discount_percent(current_price, original_price)
            for current_price, original_price in zip(
                df.get("current_price", []),
                df.get("original_price", []),
            )
        ]
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


def source_rank(source):
    try:
        return IMAGE_SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(IMAGE_SOURCE_PRIORITY)


def count_row_specs(row):
    return sum(bool(normalize_spec_value(column, row.get(column))) for column in TECHNICAL_COLUMNS)


def choose_specs(group):
    ranked = sorted(
        (row for _, row in group.iterrows()),
        key=lambda row: (-count_row_specs(row), source_rank(row.get("source"))),
    )
    specs = {}
    for column in TECHNICAL_COLUMNS:
        for row in ranked:
            value = normalize_spec_value(column, row.get(column))
            if value:
                specs[column] = value
                break
    return specs


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
        specs = choose_specs(group)
        row.update({column: specs.get(column) for column in TECHNICAL_COLUMNS})
        row["technical_specs"] = specs_to_display(specs)
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
        available_current_prices = [
            row[f"gia_ban_{source}"]
            for source in SOURCES
            if pd.notna(row[f"gia_ban_{source}"])
        ]
        row["price_segment"] = (
            classify_price_segment(min(available_current_prices))
            if available_current_prices
            else None
        )
        row["discount_percent"] = max(
            [
                compute_discount_percent(
                    row[f"gia_ban_{source}"],
                    row[f"gia_goc_{source}"],
                )
                for source in SOURCES
                if pd.notna(row[f"gia_ban_{source}"])
            ]
            or [0]
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
    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"laptop_price_compare_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    return filename


def print_match_summary(df):
    print("Match summary by number of available websites:")
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
    print(f"Saved merged comparison file: {output_file}")
    return output_file


if __name__ == "__main__":
    merge_latest_daily_files()
