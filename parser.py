import asyncio
import re
import os
import json
from dotenv import load_dotenv
from supabase import create_client
from playwright.async_api import async_playwright
from groq import Groq

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MARKUP = float(os.getenv("MARKUP", 1.0))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORY_URL = "https://top4running.com/c/athletics"
LIMIT = 800

# Жесткие разрешенные значения
ALLOWED_DISTANCES = ["Спринт", "Средние", "Длинные", "Прыжки", "Метания", "Кросс", "Универсальные"]
ALLOWED_SUB_CATS = {
    "Обувь": ["Шиповки", "Кроссовки"],
    "Одежда": ["Верх", "Низ", "Костюмы"],
    "Аксессуары": ["Рюкзаки/Сумки", "Носки", "Разное"],
}

def get_eur_rub():
    import requests
    try:
        r = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=10)
        match = re.search(r"<CharCode>EUR</CharCode>.*?<Value>([\d,]+)</Value>", r.text, re.DOTALL)
        if match:
            rate = float(match.group(1).replace(",", "."))
            print(f"💱 Курс EUR/RUB: {rate}")
            return rate
    except Exception as e:
        print(f"⚠️ Ошибка курса: {e}")
    return 105.0

def detect_distance(name: str, description: str) -> str:
    """
    Определяем дистанцию через название (приоритет) и текст.
    Аббревиатуры в имени имеют наивысший приоритет.
    """
    n = name.lower()
    d = description.lower()
    combined = n + " " + d

    # ── ПРИОРИТЕТ 1: Прямые паттерны в НАЗВАНИИ ТОВАРА ──────────────────────

    # Метания: SD (Shot/Discus), throws
    if re.search(r'\bsd\b|\bsd\s|\bsd\d', n) or any(w in n for w in ["throw", "shot", "discus", "hammer", "javelin"]):
        return "Метания"

    # Прыжки: LJ, TJ, HJ, PV
    if re.search(r'\blj\b|\btj\b|\bhj\b|\bpv\b', n) or any(w in n for w in ["jump", "vault", "triple"]):
        return "Прыжки"

    # Кросс: XC
    if re.search(r'\bxc\b|\bxc\d', n) or "cross country" in n or "cloudspike" in n:
        return "Кросс"

    # Универсальные: multi в НАЗВАНИИ = сразу универсальные, без вопросов
    if any(w in n for w in ["multi", "all-round", "allround", "versatile"]):
        return "Универсальные"

    # Спринт: SP (аббревиатура!), sprint, sprintstar
    if re.search(r'\bsp\b|\bsp\d|\bsp\s', n) or any(w in n for w in ["sprint", "sprintstar"]):
        return "Спринт"

    # Средние/Длинные: distance, ambition, distancestar, finesse
    if any(w in n for w in ["distancestar", "ambition", "finesse"]):
        return "Средние"
    if "rival distance" in n or "zoom rival distance" in n:
        return "Средние"

    # ── ПРИОРИТЕТ 2: Ключевые слова в ТЕКСТЕ ОПИСАНИЯ ───────────────────────
    found = set()

    if any(w in combined for w in ["sprint", "100m", "100 m", "200m", "200 m", "400m", "400 m", "short distance"]):
        found.add("Спринт")
    if any(w in combined for w in ["middle", "800m", "800 m", "1500m", "1 500", "1,500", "mile", "steeplechase"]):
        found.add("Средние")
    if any(w in combined for w in ["3000m", "5000m", "10000m", "10 000", "marathon", "long distance"]):
        found.add("Длинные")
    if any(w in combined for w in [" lj ", " tj ", " hj ", "long jump", "triple jump", "high jump", "pole vault"]):
        found.add("Прыжки")
    if any(w in combined for w in ["shot put", "discus", "hammer throw", "javelin", "throws"]):
        found.add("Метания")
    if any(w in combined for w in ["cross country", " xc ", "trail"]):
        found.add("Кросс")

    if len(found) >= 2:
        return "Универсальные"
    elif len(found) == 1:
        return list(found)[0]

    # Если совсем ничего не нашли — универсальные (лучше перестраховаться)
    return "Универсальные"

def analyze_product_data(raw_text, product_name, breadcrumbs):
    """ИИ занимается ТОЛЬКО описанием, полом и категориями. Дистанцию он не трогает."""
    if not raw_text or len(raw_text) < 30:
        raw_text = "Подробное описание отсутствует."

    try:
        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""
        Ты — продающий копирайтер магазина спортивной экипировки.
        Товар: {product_name}
        Крошки сайта: {breadcrumbs}
        Текст с сайта: {raw_text[:1500]}
        
        ЗАДАЧА: Вернуть валидный JSON строго по шаблону.
        
        ПРАВИЛА:
        1. gender: ОДНО из ["Мужское", "Женское", "Детское", "Унисекс"].
        2. main_category: ОДНО из ["Обувь", "Одежда", "Аксессуары"].
        3. sub_category:
           - Обувь: "Шиповки" или "Кроссовки"
           - Одежда: "Верх" или "Низ" или "Костюмы"
           - Аксессуары: "Рюкзаки/Сумки" или "Носки" или "Разное"
        4. description: РОВНО 3 предложения на русском:
           - 1-е: Суть товара (что это и для чего).
           - 2-е: Ключевые технологии (ТОЛЬКО если они прямо указаны в тексте! Не выдумывай. Не используй слово "пенопласт").
           - 3-е: Для каких условий или дистанций лучше всего.
           После 3-го предложения обязательно добавь: "Для более подробной консультации обращайтесь к менеджеру."
        
        ШАБЛОН JSON (строго такой, ничего лишнего):
        {{
            "description": "...",
            "gender": "...",
            "main_category": "...",
            "sub_category": "..."
        }}
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content.strip())

    except Exception as e:
        print(f"   ⚠️ Ошибка Groq: {e}")
        return {
            "description": "Для более подробной консультации обращайтесь к менеджеру.",
            "gender": "Унисекс",
            "main_category": "Аксессуары",
            "sub_category": "Разное"
        }

def build_product_dict(ai_data, detected_distance, name, brand, price_eur,
                       original_price_eur, price_rub, images, source_url, eur_rub):
    """Собираем финальный словарь товара с Python-валидацией всех полей."""

    main_cat = ai_data.get("main_category", "Аксессуары")
    sub_cat = ai_data.get("sub_category", "Разное")
    gender = ai_data.get("gender", "Унисекс")
    desc = ai_data.get("description", "")

    # Валидация main_category
    if main_cat not in ["Обувь", "Одежда", "Аксессуары"]:
        main_cat = "Аксессуары"

    # Валидация sub_category
    allowed_subs = ALLOWED_SUB_CATS.get(main_cat, ["Разное"])
    if sub_cat not in allowed_subs:
        sub_cat = allowed_subs[0]

    # Валидация gender
    if gender not in ["Мужское", "Женское", "Детское", "Унисекс"]:
        gender = "Унисекс"

    # Страховка для описания
    if "менеджеру" not in desc.lower():
        desc = desc.strip() + " Для более подробной консультации обращайтесь к менеджеру."

    # Дистанция — только для шиповок, только из допустимого списка
    attributes = {}
    if sub_cat == "Шиповки" and detected_distance in ALLOWED_DISTANCES:
        # ВАЖНО: всегда список, чтобы фронт не сходил с ума
        attributes = {"distance": [detected_distance]}

    return {
        "name": name,
        "brand": brand,
        "price_eur": price_eur,
        "original_price_eur": original_price_eur if original_price_eur and original_price_eur > price_eur else None,
        "price_rub": price_rub,
        "images": images,
        "source_url": source_url,
        "description": desc,
        "gender": gender,
        "main_category": main_cat,
        "sub_category": sub_cat,
        "attributes": attributes,
    }


def save_to_supabase(product):
    try:
        existing = supabase.table("products_v2").select("id, images, source_url").eq("name", product["name"]).execute()

        if existing.data:
            existing_product = existing.data[0]
            if existing_product.get("source_url") == product["source_url"]:
                return "skip"
            old_images = existing_product.get("images") or []
            if product["images"]:
                new_image = product["images"][0]
                if new_image not in old_images:
                    old_images.append(new_image)
                    supabase.table("products_v2").update({"images": old_images}).eq("id", existing_product["id"]).execute()
                    return "updated"
                else:
                    return "color_exists"
            return "color_exists"

        supabase.table("products_v2").insert(product).execute()
        return "new"
    except Exception as e:
        print(f"   ❌ Ошибка Supabase: {e}")
        return "error"

async def collect_product_links(page):
    product_links = []
    page_num = 1

    await page.goto(CATEGORY_URL, wait_until="domcontentloaded", timeout=30000)

    while True:
        print(f"\n   Страница {page_num} — ищем ссылки...")

        if page_num > 1:
            next_url = f"{CATEGORY_URL}?page={page_num}"
            try:
                await page.goto(next_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"   ⚠️ Ошибка: {e}")
                break

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

        links = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        new_links = [l for l in links if "/p/" in l and l not in product_links]

        # Пробуем alt-формат пагинации если ничего не нашли
        if not new_links and page_num > 1:
            try:
                await page.goto(f"{CATEGORY_URL}/page-{page_num}", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                links = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                new_links = [l for l in links if "/p/" in l and l not in product_links]
            except:
                pass

        if not new_links:
            print("   ✅ Страницы закончились.")
            break

        product_links.extend(new_links)
        print(f"   Новых: {len(new_links)} | Всего: {len(product_links)}")

        if page_num >= 40:
            print("   ⚠️ Достигнут лимит страниц.")
            break

        page_num += 1

    unique_links = list(dict.fromkeys(product_links))
    print(f"\n   📦 Итого уникальных ссылок: {len(unique_links)}")
    return unique_links

async def parse_product(page, url, eur_rub):
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2500)

    # ── Название
    name = ""
    for sel in ["h1", "[class*='product-name']", "[class*='productName']"]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                txt = (await el.inner_text()).strip()
                if len(txt) > 3:
                    name = txt
                    break
        except:
            pass
    if not name:
        title = await page.title()
        name = title.split("|")[0].strip()
    for prefix in ["Track shoes/Spikes ", "Running shoes ", "Track shoes ", "Spikes ", "T-shirt ", "Shorts "]:
        if name.startswith(prefix):
            name = name[len(prefix):]

    # ── Бренд
    brand = ""
    for word in ["Nike", "Adidas", "Puma", "Saucony", "Hoka", "On Running",
                 "New Balance", "Asics", "Keyena", "Brooks", "Under Armour", "Craft", "Salomon"]:
        if word.lower() in name.lower():
            brand = word
            break

    # ── Хлебные крошки
    breadcrumbs = ""
    try:
        crumbs = await page.evaluate("""() => {
            const els = document.querySelectorAll('nav[aria-label*="readcrumb"] a, .breadcrumbs a, .breadcrumb a');
            return Array.from(els).map(e => e.innerText.trim()).join(' > ');
        }""")
        breadcrumbs = crumbs
    except:
        pass

    # ── Цена
    price_eur = 0
    original_price_eur = 0
    try:
        price_result = await page.evaluate("""() => {
            const addToCart = document.querySelector('[class*="add-to-cart"], [class*="addToCart"], button[type="submit"]');
            let priceBlock = null;
            if (addToCart) {
                let parent = addToCart.parentElement;
                for (let i = 0; i < 5; i++) {
                    if (!parent) break;
                    const priceEl = parent.querySelector('[class*="price"]');
                    if (priceEl) { priceBlock = priceEl; break; }
                    parent = parent.parentElement;
                }
            }
            if (!priceBlock) {
                const candidates = document.querySelectorAll('[class*="price"]');
                for (const el of candidates) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 50 && rect.top > 0 && rect.top < 800) { priceBlock = el; break; }
                }
            }
            if (!priceBlock) return { current: 0, original: 0 };
            const txt = priceBlock.innerText || '';
            const allPrices = txt.match(/[€]\s*[\d]+[,\.][\d]{2}/g) || [];
            const prices = allPrices.map(p => parseFloat(p.replace('€','').replace(',','.').trim())).filter(p => p > 10 && p < 2000);
            if (prices.length === 0) return { current: 0, original: 0 };
            if (prices.length === 1) return { current: prices[0], original: 0 };
            return { current: Math.min(...prices), original: Math.max(...prices) };
        }""")
        price_eur = price_result.get("current", 0)
        original_price_eur = price_result.get("original", 0)
    except:
        pass

    if price_eur <= 0:
        try:
            price_meta = await page.get_attribute('meta[property="product:price:amount"]', "content")
            if price_meta:
                price_eur = float(price_meta)
        except:
            pass

    # ── Описание
    raw_description = ""
    try:
        raw_description = await page.evaluate("""() => {
            const selectors = ['[class*="description"]', '[class*="product-detail__text"]',
                               '[class*="product__text"]', '[itemprop="description"]'];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const txt = el.innerText.trim();
                    if (txt.length > 40) return txt.slice(0, 2000);
                }
            }
            return '';
        }""")
    except:
        pass

    # 🎯 Дистанцию определяем Python-методом (имя товара имеет приоритет!)
    detected_distance = detect_distance(name, raw_description)

    # 🔥 AI делает только описание + категории
    ai_data = analyze_product_data(raw_description, name, breadcrumbs)

    # ── Фото
    images = []
    try:
        og_image = await page.get_attribute('meta[property="og:image"]', "content")
        if og_image and og_image.startswith("http") and not og_image.endswith(".svg"):
            images = [og_image]
    except:
        pass

    if not images:
        try:
            raw_images = await page.evaluate("""() => {
                const allImgs = Array.from(document.querySelectorAll('img'));
                return allImgs
                    .map(img => img.src || img.dataset.src || '')
                    .filter(src => src.startsWith('http') && !src.endsWith('.svg') && !src.includes('logo')
                                   && (src.includes('/products/') || src.endsWith('.webp') || src.endsWith('.jpg')));
            }""")
            if raw_images:
                images = [raw_images[0]]
        except:
            pass

    if not name or price_eur <= 0:
        return None

    price_rub = int(round((price_eur * eur_rub * MARKUP) / 100) * 100)

    return build_product_dict(ai_data, detected_distance, name, brand,
                              price_eur, original_price_eur, price_rub,
                              images, url, eur_rub)

async def main():
    print(f"🚀 Парсер запущен...\n")
    eur_rub = get_eur_rub()
    added = updated_colors = skipped = errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("📄 Собираем ссылки на товары...")
        product_links = await collect_product_links(page)

        if not product_links:
            print("❌ Ссылки не найдены")
            await browser.close()
            return

        product_links = product_links[:LIMIT]
        print(f"\n🔄 Парсим {len(product_links)} товаров...\n")

        for i, url in enumerate(product_links, 1):
            try:
                print(f"[{i}/{len(product_links)}] {url.split('/')[-1]}")
                product = await parse_product(page, url, eur_rub)

                if not product:
                    errors += 1
                    continue

                result = save_to_supabase(product)

                if result == "new":
                    added += 1
                    dist = product.get("attributes", {}).get("distance", "—")
                    print(f"   ✅ {product['name'][:30]} | {product['sub_category']} | 📍 {dist}")
                    print(f"      💰 {product['price_eur']}€ → {product['price_rub']:,}₽")
                elif result == "updated":
                    updated_colors += 1
                    print(f"   🎨 Новый цвет добавлен")
                elif result in ["color_exists", "skip"]:
                    skipped += 1
                    print(f"   ⏭️ Пропущен")
                else:
                    errors += 1

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                errors += 1

            await asyncio.sleep(2.0)

        await browser.close()

    print(f"\n{'='*50}")
    print(f"✅ Новых: {added} | 🎨 Цветов: {updated_colors} | ⏭️ Пропущено: {skipped} | ❌ Ошибок: {errors}")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())
