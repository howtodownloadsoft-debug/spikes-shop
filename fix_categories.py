import os
import re
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def classify_product(name: str, desc: str):
    n = name.lower()
    d = desc.lower()
    text = n + " " + d

    # 1. ШИПОВКИ (строгий приоритет, ТОЛЬКО по названию)
    spike_models = [
        "spike", "spikes", "шиповк", "dragonfly", "maxfly", "prime sp", "adizero lj",
        "adizero tj", "adizero hj", "adizero pv", "adizero md", "finesse", "ambition",
        "avanti", "sprintstar", "distancestar", "evospeed", "cloudspike", "nitro elite",
        "rival sprint", "rival distance", "rival multi", "rival sd", "rival xc", "rival m",
        "terminal vt", "zoom mamba", "zoom victory", "hyper ld", "hyper md",
        "hyper sprint", "celd", "superfly", "zoom 400", "ja fly", "sd 4", "prep sprint"
    ]

    # Шиповки определяем ТОЛЬКО по имени, чтобы описание не ломало категории
    if any(re.search(rf"\b{re.escape(m)}\b", n) for m in spike_models) or "шиповк" in n:
        return "Обувь", "Шиповки"

    # 2. КРОССОВКИ (тоже только по названию)
    sneaker_models = [
        "shoe", "shoes", "кроссовк", "pegasus", "vaporfly", "alphafly", "boston",
        "adios pro", "novablast", "cumulus", "nimbus", "ultraboost", "superblast",
        "invincible", "infinity run"
    ]

    if any(re.search(rf"\b{re.escape(m)}\b", n) for m in sneaker_models):
        return "Обувь", "Кроссовки"

    # 3. ОДЕЖДА - НИЗ (Шорты, тайтсы, штаны)
    bottoms = [
        "short", "shorts", "tight", "tights", "pant", "pants", "legging", "leggings",
        "brief", "briefs", "trouser", "trousers", "jogger",
        "шорты", "тайтсы", "штаны", "брюки", "плавки"
    ]
    if any(re.search(rf"\b{re.escape(m)}\b", n) for m in bottoms) or any(m in d for m in ["шорты", "тайтсы", "штаны"]):
        return "Одежда", "Низ"

    # 4. ОДЕЖДА - ВЕРХ (Футболки, куртки, топы, бра)
    tops = [
        "jacket", "jckt", "jkt", "hoodie", "windbreaker", "singlet", "tee", "t-shirt",
        "shirt", "top", "vest", "sweat", "sweatshirt", "jsy", "jersey", "crew",
        "parka", "bra", "tank", "polo",
        "футболк", "майк", "куртк", "ветровк", "толстовк", "худи", "свитшот"
    ]
    if any(re.search(rf"\b{re.escape(m)}\b", n) for m in tops) or any(
        m in d for m in ["футболк", "майк", "куртк", "бра", "топ"]
    ):
        return "Одежда", "Верх"

    # 5. ОДЕЖДА - КОСТЮМЫ
    if re.search(r"\b(tracksuit|suit|костюм)\b", text):
        return "Одежда", "Костюмы"

    # 6. АКСЕССУАРЫ - НОСКИ
    if re.search(r"\b(sock|socks|носк|носки)\b", text):
        return "Аксессуары", "Носки"

    # 7. АКСЕССУАРЫ - СУМКИ
    if re.search(r"\b(bag|backpack|sack|gymsack|duffel|сумк|сумка|рюкзак|мешок)\b", text):
        return "Аксессуары", "Рюкзаки/Сумки"

    # 8. ВСЁ ОСТАЛЬНОЕ — прочие аксессуары
    return "Аксессуары", "Разное"


def determine_distance(name: str, desc: str) -> list:
    n = name.lower()
    d = desc.lower()
    text = n + " " + d

    # Универсальные / кросс — без тегов дистанции
    if re.search(r"\bmulti\b|\ball-round\b|\bxc\b|\bcross\b", n):
        return []

    res = set()

    # МЕТАНИЯ
    if re.search(r"\bsd\b|\bthrow\b|\bshot put\b|\bdiscus\b|\bhammer\b|\bjavelin\b|\bметан\b|\bядро\b|\bдиск\b|\bкопь\b", text):
        res.add("Метания")

    # ПРЫЖКИ
    if re.search(r"\blj\b|\btj\b|\bhj\b|\bpv\b|\bjump\b|\bvault\b|\btriple\b|\bпрыжк\b", text):
        res.add("Прыжки")

    # СПРИНТ
    sprint_models = [
        "maxfly", "sprintstar", "prime sp", "finesse", "rival sprint",
        "superfly", "hyper sprint", "evospeed sprint", "zoom 400", "prep sprint"
    ]
    if any(m in n for m in sprint_models) or re.search(
        r"\bsprint\b|\bспринт\b|\b100m\b|\b200m\b|\b400m\b|\bsp\b",
        text
    ):
        res.add("Спринт")

    # СРЕДНИЕ / ДЛИННЫЕ
    mid_models = ["ambition", "md", "zoom mamba", "victory", "rival m"]
    if any(m in n for m in mid_models) or re.search(
        r"\b800m\b|\b1500m\b|\bsteeple\b|\bсредн\b",
        text
    ):
        res.add("Средние")

    long_models = ["distancestar", "ld", "cloudspike", "terminal vt", "avanti"]
    if any(m in n for m in long_models) or re.search(
        r"\b3000m\b|\b5000m\b|\b10000m\b|\bдлинн\b",
        text
    ):
        res.add("Длинные")

    # Смешанные модели (Средние + Длинные)
    if "dragonfly" in n or "rival distance" in n:
        res.add("Средние")
        res.add("Длинные")

    return list(res)


def run_fix():
    print("🧹 НАЧИНАЕМ ГЛОБАЛЬНУЮ ПЕРЕСОРТИРОВКУ БАЗЫ...")

    resp = supabase.table("products_v2").select(
        "id, name, description, main_category, sub_category, attributes"
    ).execute()
    products = resp.data or []
    print(f"📦 Загружено: {len(products)} товаров\n")

    fixed = 0
    for p in products:
        name = p.get("name", "")
        desc = p.get("description", "")

        main_cat, sub_cat = classify_product(name, desc)

        new_attr = {}
        if sub_cat == "Шиповки":
            dist = determine_distance(name, desc)
            if dist:
                new_attr = {"distance": dist}

        old_main = p.get("main_category")
        old_sub = p.get("sub_category")
        old_attr = p.get("attributes") or {}

        # Если хоть что-то отличается — перезаписываем
        if main_cat != old_main or sub_cat != old_sub or new_attr != old_attr:
            supabase.table("products_v2").update({
                "main_category": main_cat,
                "sub_category": sub_cat,
                "attributes": new_attr
            }).eq("id", p["id"]).execute()

            dist_str = f" | 📍 {new_attr['distance']}" if new_attr else ""
            print(f"✅ {name[:40]}")
            print(f"   Было: {old_main}/{old_sub} -> Стало: {main_cat}/{sub_cat}{dist_str}")
            fixed += 1

    print(f"\n🎯 ГОТОВО! Пересортировано {fixed} товаров.")


if __name__ == "__main__":
    run_fix()
