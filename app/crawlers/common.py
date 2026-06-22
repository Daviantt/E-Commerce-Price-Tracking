import math
import re
from html import unescape


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

    if current_price is None or current_price <= 0:
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


TECHNICAL_COLUMNS = (
    "cpu",
    "gpu",
    "ram",
    "storage",
    "screen_size",
    "screen_resolution",
    "refresh_rate",
    "os",
    "weight",
    "battery",
)

SPEC_DISPLAY_LABELS = {
    "cpu": "CPU",
    "gpu": "GPU",
    "ram": "RAM",
    "storage": "Storage",
    "screen_size": "Screen size",
    "screen_resolution": "Resolution",
    "refresh_rate": "Refresh rate",
    "os": "Operating system",
    "weight": "Weight",
    "battery": "Battery",
}

SPEC_KEYWORDS = {
    "cpu": ("cpu", "processor", "chip", "bo xu ly", "vi xu ly"),
    "gpu": ("gpu", "graphics", "card do hoa", "vga", "display card"),
    "ram": ("ram", "memory", "bo nho"),
    "storage": ("storage", "ssd", "hdd", "o cung", "hard drive"),
    "screen_size": ("screen size", "display size", "kich thuoc man hinh", "man hinh"),
    "screen_resolution": ("resolution", "do phan giai"),
    "refresh_rate": ("refresh", "tan so", "hz"),
    "os": ("os", "operating system", "he dieu hanh"),
    "weight": ("weight", "can nang", "trong luong"),
    "battery": ("battery", "pin"),
}


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def strip_accents_ascii(value):
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


def clean_spec_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value if item is not None)
    if isinstance(value, dict):
        return None

    text = strip_html(value)
    text = text.strip(" :-|,;")
    lowered = text.lower()
    if not text or lowered in {"nan", "none", "null", "n/a", "true", "false"}:
        return None
    if URL_OR_IMAGE_PATTERN.search(text):
        return None
    return text[:180]


def normalize_spec_value(column, value):
    text = clean_spec_value(value)
    if not text:
        return None

    lowered = text.lower().strip()
    if lowered in {"0", "0.0", "1", "1.0"}:
        return None

    numeric_match = re.fullmatch(r"\d+(?:\.\d+)?", lowered)
    numeric_value = float(lowered) if numeric_match else None

    if column == "ram":
        if numeric_value is not None:
            return f"{int(numeric_value)}GB" if 4 <= numeric_value <= 128 else None
        return text if re.search(r"\b\d{1,3}\s*GB\b", text, re.IGNORECASE) else None

    if column == "storage":
        if numeric_value is not None:
            return f"{int(numeric_value)}GB" if numeric_value >= 128 else None
        return text if re.search(r"\b\d+(?:\.\d+)?\s*(GB|TB)\b", text, re.IGNORECASE) else None

    if column == "screen_size":
        if numeric_value is not None:
            return f'{numeric_value:g}"' if 10 <= numeric_value <= 20 else None
        return text if re.search(r"\b\d{2}(?:\.\d)?\s*(?:inch|inches|\"|-inch)\b", text, re.IGNORECASE) else None

    if column == "refresh_rate":
        if numeric_value is not None:
            return f"{int(numeric_value)}Hz" if 30 <= numeric_value <= 360 else None
        return text if re.search(r"\b\d{2,3}\s*Hz\b", text, re.IGNORECASE) else None

    if column == "weight":
        if numeric_value is not None:
            return f"{numeric_value:g}kg" if 0.5 <= numeric_value <= 5 else None
        return text if re.search(r"\b\d(?:\.\d{1,2})?\s*kg\b", text, re.IGNORECASE) else None

    if column == "battery":
        if numeric_value is not None:
            return f"{int(numeric_value)}Wh" if 20 <= numeric_value <= 120 else None
        return text if re.search(r"\b\d{2,3}\s*Wh\b", text, re.IGNORECASE) else None

    if column == "screen_resolution":
        if re.fullmatch(r"(HD|FHD|WUXGA|QHD|WQHD|WQXGA|UHD|2\.?5K|2\.?8K|3K|4K)", text, re.IGNORECASE):
            return text.upper()
        return text if re.fullmatch(r"\d{3,4}\s*[xX]\s*\d{3,4}", text) else None

    if column == "os":
        return text if re.search(r"\b(windows|macos|chrome\s*os|linux|freedos|dos)\b", text, re.IGNORECASE) else None

    if column in {"cpu", "gpu"}:
        return text if re.search(r"[A-Za-z]", text) and len(text) >= 3 else None

    return text


def find_spec_column(label):
    normalized = strip_accents_ascii(label)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    for column, keywords in SPEC_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return column
    return None


def merge_specs(*specs_list):
    merged = {}
    for specs in specs_list:
        if not isinstance(specs, dict):
            continue
        for column in TECHNICAL_COLUMNS:
            value = normalize_spec_value(column, specs.get(column))
            if value and not merged.get(column):
                merged[column] = value
    return merged


def specs_to_display(specs):
    display_specs = {}
    for column, value in (specs or {}).items():
        normalized = normalize_spec_value(column, value)
        if column in SPEC_DISPLAY_LABELS and normalized:
            display_specs[SPEC_DISPLAY_LABELS[column]] = normalized
    return display_specs


def extract_specs_from_text(*values):
    text = " ".join(strip_html(value) for value in values if value is not None)
    if not text:
        return {}

    specs = {}
    normalized = text.replace("™", "").replace(",", ".")

    cpu_patterns = [
        r"\bUltra\s+[579]\s*[- ]?\s*\w{2,8}\b",
        r"\b(?:Intel\s+)?Core\s+Ultra\s+[579]\s*[- ]?\s*\w{2,8}\b",
        r"\b(?:Intel\s+)?Core\s+i[3579]\s*[- ]?\s*\d{3,5}[A-Z]{0,3}\b",
        r"\b(?:AMD\s+)?Ryzen\s+[3579]\s*[- ]?\s*\d{3,5}[A-Z]{0,3}\b",
        r"\bAMD\s+R[3579]\s*[- ]?\s*\d{2,5}[A-Z]{0,3}\b",
        r"\bSnapdragon\s+X\s+\w+\b",
        r"\bApple\s+M\d(?:\s+\w+)?\b",
        r"\b(?:Intel\s+)?(?:Celeron|Pentium)\s+\w+\b",
    ]
    for pattern in cpu_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            specs["cpu"] = re.sub(r"\s+", " ", match.group(0)).strip()
            break

    gpu_patterns = [
        r"\b(?:NVIDIA\s+|GeForce\s+)?RTX\s*\d{4}\s*(?:Ti|SUPER)?\b",
        r"\b(?:NVIDIA\s+|GeForce\s+)?GTX\s*\d{3,4}\s*(?:Ti)?\b",
        r"\bIntel\s+(?:Arc|Iris\s+Xe|UHD)\s*(?:Graphics)?\b",
        r"\bAMD\s+Radeon\s+[\w\s]{2,20}\b",
    ]
    for pattern in gpu_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            specs["gpu"] = re.sub(r"\s+", " ", match.group(0)).strip()
            break

    ram_match = re.search(
        r"\b(\d{1,3})\s*GB\s*(?:DDR\d|LPDDR\dX?|RAM|Memory)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if not ram_match:
        ram_candidates = [
            int(match.group(1))
            for match in re.finditer(r"\b(\d{1,3})\s*GB\b", normalized, flags=re.IGNORECASE)
            if 4 <= int(match.group(1)) <= 128
        ]
        if ram_candidates:
            ram_match_value = ram_candidates[0]
            specs["ram"] = f"{ram_match_value}GB"
    else:
        specs["ram"] = f"{ram_match.group(1)}GB"

    storage_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(TB|GB)\s*(?:SSD|HDD|NVMe|PCIe)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if not storage_match:
        tb_match = re.search(r"\b(\d+(?:\.\d+)?)\s*TB\b", normalized, flags=re.IGNORECASE)
        gb_candidates = [
            int(match.group(1))
            for match in re.finditer(r"\b(\d{3,4})\s*GB\b", normalized, flags=re.IGNORECASE)
            if int(match.group(1)) >= 128
        ]
        if tb_match:
            specs["storage"] = f"{tb_match.group(1)}TB"
        elif gb_candidates:
            specs["storage"] = f"{gb_candidates[0]}GB"
    else:
        specs["storage"] = f"{storage_match.group(1)}{storage_match.group(2).upper()}"

    screen_match = re.search(
        r"\b(\d{2}(?:\.\d)?)\s*(?:inch|inches|\"|-inch)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if screen_match:
        specs["screen_size"] = f'{screen_match.group(1)}"'

    resolution_match = re.search(
        r"\b(HD|FHD|WUXGA|QHD|WQHD|WQXGA|UHD|2\.?5K|2\.?8K|3K|4K|"
        r"\d{3,4}\s*[xX]\s*\d{3,4})\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if resolution_match:
        specs["screen_resolution"] = resolution_match.group(1).upper().replace(" ", "")

    refresh_match = re.search(r"\b(\d{2,3})\s*Hz\b", normalized, flags=re.IGNORECASE)
    if refresh_match:
        specs["refresh_rate"] = f"{refresh_match.group(1)}Hz"

    os_match = re.search(
        r"\b(Windows\s+11(?:\s+Home|\s+Pro)?|Windows\s+10|Win\s+11|FreeDOS|DOS)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if os_match:
        specs["os"] = re.sub(r"\s+", " ", os_match.group(1)).strip()

    weight_match = re.search(r"\b(\d(?:\.\d{1,2})?)\s*kg\b", normalized, flags=re.IGNORECASE)
    if weight_match:
        specs["weight"] = f"{weight_match.group(1)}kg"

    battery_match = re.search(r"\b(\d{2,3})\s*Wh\b", normalized, flags=re.IGNORECASE)
    if battery_match:
        specs["battery"] = f"{battery_match.group(1)}Wh"

    return specs


def extract_structured_specs(value):
    specs = {}

    def visit(node):
        if isinstance(node, dict):
            label = (
                node.get("label")
                or node.get("name")
                or node.get("title")
                or node.get("displayName")
                or node.get("attributeName")
            )
            raw_value = (
                node.get("value")
                or node.get("displayValue")
                or node.get("attributeValue")
                or node.get("text")
            )
            if label and raw_value:
                column = find_spec_column(label)
                cleaned = normalize_spec_value(column, raw_value)
                if column and cleaned and not specs.get(column):
                    specs[column] = cleaned

            for key, child in node.items():
                column = find_spec_column(key)
                cleaned = normalize_spec_value(column, child)
                if column and cleaned and not specs.get(column):
                    specs[column] = cleaned
                if isinstance(child, (dict, list, tuple)):
                    visit(child)

        elif isinstance(node, (list, tuple)):
            for item in node:
                visit(item)

    visit(value)
    return specs


def extract_specs_from_product(item, *text_sources):
    structured_specs = extract_structured_specs(item)
    text_specs = extract_specs_from_text(*text_sources)
    if isinstance(item, dict):
        text_fields = []
        for key in ("name", "title", "sku", "body_html", "description", "short_description"):
            value = item.get(key)
            if value:
                text_fields.append(value)
        text_specs = merge_specs(text_specs, extract_specs_from_text(*text_fields))
    return merge_specs(structured_specs, text_specs)


def compute_discount_percent(current_price, original_price):
    current_price, original_price = normalize_price_pair(current_price, original_price)
    if current_price is None or original_price is None or original_price <= current_price:
        return 0
    return round((original_price - current_price) / original_price * 100, 2)


def classify_price_segment(price):
    price = clean_price(price)
    if price is None:
        return None
    if price < 15_000_000:
        return "budget"
    if price < 25_000_000:
        return "mainstream"
    if price < 40_000_000:
        return "upper_mid"
    return "premium"
