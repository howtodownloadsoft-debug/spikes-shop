import os
import re
import time
import html as html_lib
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("В .env должны быть SUPABASE_URL и SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE_NAME = "products_v2"
REQUEST_TIMEOUT = 25
SLEEP_BETWEEN = 0.2
DRY_RUN = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}


def norm(text: str) -> str:
    if not text:
        return ""
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ")
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_html(session: requests.Session, url: str) -> str:
    r = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def text_only(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    return norm(html)


def find_field(html: str, field_name: str) -> Optional[str]:
    txt = text_only(html)

    patterns = [
        rf"{re.escape(field_name.lower())}\s*:\s*([^\n\r]+)",
        rf"{re.escape(field_name.lower())}\s*([^\n\r]+)",
    ]

    for p in patterns:
        m = re.search(p, txt, flags=re.I)
        if m:
            val = m.group(1).strip(" :-|")
            val = re.split(r"(reviews|description|manufacturer|close this section|find the right shoe)", val, flags=re.I)[0]
            return val.strip(" :-|")[:300]

    return None


def extract_structured_fields(html: str) -> Dict[str, str]:
    fields = {}
    for key in [
        "Category",
        "Types of shoes",
        "Distance",
        "Discipline",
        "Spike Type",
        "Terrain",
        "Sport",
        "Model",
    ]:
        val = find_field(html, key)
        if val:
            fields[key] = val
    return fields


def contains_word(text: str, word: str) -> bool:
    t = norm(text)
    w = norm(word)
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", t)) or w in t


def any_word(text: str, words: List[str]) -> bool:
    return any(contains_word(text, w) for w in words)


def classify_by_fields(name: str, source_url: str, fields: Dict[str, str]) -> Tuple[Optional[str], Optional[str], Dict]:
    name_n = norm(name)
    slug_n = norm(source_url.split("/p/")[-1] if "/p/" in source_url else source_url.rsplit("/", 1)[-1])

    category = norm(fields.get("Category", ""))
    shoe_type = norm(fields.get("Types of shoes", ""))
    distance = norm(fields.get("Distance", ""))
    discipline = norm(fields.get("Discipline", ""))
    model = norm(fields.get("Model", ""))

    source = " | ".join([name_n, slug_n, category, shoe_type, distance, discipline, model])

    top_words = [
        "jacket", "jkt", "jckt", "hoodie", "crew", "sweatshirt", "sweater",
        "windbreaker", "tee", "t-shirt", "shirt", "jersey", "jsy",
        "singlet", "tank", "top", "vest", "bra", "parka", "anorak",
    ]
    bottom_words = [
        "short", "shorts", "pant", "pants", "tight", "tights", "legging",
        "leggings", "brief", "briefs", "skirt", "jogger", "trouser",
        "trousers", "3in", "2in", "4in", "5in", "7in",
    ]
    bag_words = ["bag", "backpack", "gymsack", "duffel", "sack"]
    sock_words = ["sock", "socks"]
    other_accessories = ["bottle", "cap", "hat", "beanie", "glove", "gloves", "headband", "insole", "laces", "keyena"]

    # 1) Сначала явные НЕ-обувные вещи
    if any_word(source, sock_words):
        return "Аксессуары", "Носки", {}
    if any_word(source, bag_words):
        return "Аксессуары", "Рюкзаки/Сумки", {}
    if any_word(source, bottom_words):
        return "Одежда", "Низ", {}
    if any_word(source, top_words):
        return "Одежда", "Верх", {}
    if any_word(source, ["tracksuit", "track suit", "suit", "set"]):
        return "Одежда", "Костюмы", {}
    if any_word(source, other_accessories):
        return "Аксессуары", "Разное", {}

    # 2) Явные шиповки по структурным полям
    if "track shoes/spikes" in category or "track shoes/spikes" in shoe_type or "track shoes/ spikes" in shoe_type:
        attrs = build_distance(distance, discipline, name_n, slug_n, model)
        return "Обувь", "Шиповки", attrs

    # 3) Резерв по модели/дисциплине
    spike_words = [
        "maxfly", "dragonfly", "superfly", "ja fly", "victory", "mamba",
        "rival sprint", "rival distance", "rival multi", "rival sd", "rival xc",
        "prime sp", "finesse", "ambition", "distancestar", "avanti",
        "terminal vt", "cloudspike", "evospeed", "nitro elite",
        "hyper ld", "hyper md", "hyper sprint", "zoom 400",
        "long jump", "triple jump", "high jump", "pole vault",
        "shot put", "discus", "hammer", "javelin", "spike", "spikes",
    ]
    if any_word(source, spike_words):
        attrs = build_distance(distance, discipline, name_n, slug_n, model)
        return "Обувь", "Шиповки", attrs

    # 4) Если ничего уверенного нет — НЕ трогаем
    return None, None, {}


def build_distance(distance: str, discipline: str, name_n: str, slug_n: str, model: str) -> Dict:
    src = " | ".join([distance, discipline, name_n, slug_n, model])
    found = []

    # Если Multi — раскладываем в три вкладки
    if any_word(src, ["multi", "rival multi", "multi-event"]):
        return {"distance": ["Спринт", "Средние", "Длинные"]}

    # XC не создаем отдельной вкладкой
    if any_word(src, ["xc", "cross country"]):
        return {}

    # Метания
    if any_word(src, ["shot put", "discus", "hammer", "javelin", "throws"]) or re.search(r"(?<![a-z0-9])sd(?![a-z0-9])", src):
        return {"distance": ["Метания"]}

    # Прыжки
    if any_word(src, ["long jump", "triple jump", "high jump", "pole vault"]) or re.search(r"(?<![a-z0-9])(lj|tj|hj|pv)(?![a-z0-9])", src):
        return {"distance": ["Прыжки"]}

    # Спринт/средние/длинные по явному полю Distance
    if any_word(src, ["sprint"]):
        found.append("Спринт")
    if any_word(src, ["mid-distance", "middle distance", "mid distance"]):
        found.append("Средние")
    if any_word(src, ["long-distance", "long distance"]):
        found.append("Длинные")

    # Резерв по моделям
    if any_word(src, ["maxfly", "superfly", "sprintstar", "prime sp", "rival sprint", "hyper sprint", "prep sprint"]):
        if "Спринт" not in found:
            found.append("Спринт")

    if any_word(src, ["ambition", "victory", "mamba", "hyper md"]):
        if "Средние" not in found:
            found.append("Средние")

    if any_word(src, ["distancestar", "avanti", "hyper ld", "terminal vt", "cloudspike"]):
        if "Длинные" not in found:
            found.append("Длинные")

    if any_word(src, ["dragonfly", "rival distance", "distance nitro elite", "distance nitro"]):
        if "Средние" not in found:
            found.append("Средние")
        if "Длинные" not in found:
            found.append("Длинные")

    return {"distance": found} if found else {}


def get_all_products() -> List[Dict]:
    rows = []
    page_size = 1000
    offset = 0

    while True:
        resp = (
            supabase.table("products_v2")
            .select("id,name,source_url,main_category,sub_category,attributes")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def update_row(product_id: str, main_category: str, sub_category: str, attributes: Dict):
    if DRY_RUN:
        return
    (
        supabase.table(TABLE_NAME)
        .update({
            "main_category": main_category,
            "sub_category": sub_category,
            "attributes": attributes,
        })
        .eq("id", product_id)
        .execute()
    )


def run():
    session = requests.Session()
    session.headers.update(HEADERS)

    rows = get_all_products()
    print(f"📦 Загружено товаров: {len(rows)}\n")

    fixed = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        name = row.get("name", "")
        url = row.get("source_url", "")
        old_main = row.get("main_category")
        old_sub = row.get("sub_category")
        old_attr = row.get("attributes") or {}

        print(f"[{i}/{len(rows)}] {name[:70]}")

        if not url:
            print("   ❌ Нет source_url")
            errors += 1
            continue

        try:
            html = fetch_html(session, url)
            fields = extract_structured_fields(html)
            new_main, new_sub, new_attr = classify_by_fields(name, url, fields)

            # Нет уверенного результата — ничего не ломаем
            if not new_main or not new_sub:
                print("   ⏭️ Недостаточно структурных данных, пропущен")
                skipped += 1
                time.sleep(SLEEP_BETWEEN)
                continue

            if new_main == old_main and new_sub == old_sub and new_attr == old_attr:
                print("   ⏭️ Без изменений")
                skipped += 1
            else:
                update_row(row["id"], new_main, new_sub, new_attr)
                dist = ", ".join(new_attr.get("distance", [])) if new_attr.get("distance") else "—"
                print(f"   🔧 {old_main}/{old_sub} -> {new_main}/{new_sub} | 📍 {dist}")
                fixed += 1

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            errors += 1

        time.sleep(SLEEP_BETWEEN)

    print("\n" + "=" * 50)
    print(f"🔧 Исправлено: {fixed}")
    print(f"⏭️ Пропущено: {skipped}")
    print(f"❌ Ошибок: {errors}")
    print("=" * 50)


if __name__ == "__main__":
    run()
