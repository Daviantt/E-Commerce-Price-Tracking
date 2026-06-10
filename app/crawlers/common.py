import math
import re


URL_OR_IMAGE_PATTERN = re.compile(
    r"https?://|www\.|cdn\.|\.jpg|\.jpeg|\.png|\.webp|\.gif",
    re.IGNORECASE,
)


def clean_price(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    if URL_OR_IMAGE_PATTERN.search(text):
        return None

    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return int(float(text))

    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return int(digits)


def normalize_price_pair(current_price, original_price):
    current_price = clean_price(current_price)
    original_price = clean_price(original_price)

    if current_price is None:
        return None, None
    if original_price is None or original_price <= 0 or original_price < current_price:
        original_price = current_price

    return current_price, original_price


def clean_url(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return None
    return text
