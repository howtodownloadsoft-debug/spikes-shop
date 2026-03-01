import asyncio
import re
import os
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

CATEGORY_URL = "https://top4running.com/c/running-track-shoes-spikes"
CATEGORY_NAME = "spikes"
LIMIT = 173

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

def generate_description(raw_text, product_name):
    if not raw_text or len(raw_text) < 30:
        return ""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": (
                    "Ты — профессиональный эксперт по легкоатлетической экипировке.\n"
                    "Твоя задача — составить краткое и емкое описание шиповок на русском языке, опираясь ТОЛЬКО на предоставленный английский текст.\n\n"
                    f"Текст с сайта:\n{raw_text[:1500]}\n\n"
                    "Правила, которые строго нужно соблюдать:\n"
                    "1. Называй товар ТОЛЬКО словом «шиповки» или «модель». КАТЕГОРИЧЕСКИ запрещено использовать слова «кроссовки», «обувь», «ботинки».\n"
                    "2. Напиши 2–3 предложения, в которых выдели самую суть: главные технологии (какая пена, пластина, материал верха), особенности посадки и количество/тип шипов.\n"
                    "3. Обязательно укажи, для каких дистанций или дисциплин предназначены эти шиповки (если это указано в тексте).\n"
                    "4. Пиши строго по фактам из текста, без воды, без выдумок и без восторженных рекламных фраз.\n"
                    "5. Не начинай текст с названия товара.\n"
                    "6. В самом конце, обязательно с НОВОЙ СТРОКИ, добавь ровно эту фразу (без кавычек):\n"
                    "Для более подробной консультации обращайтесь к менеджеру."
                )
            }],
            max_tokens=250,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ⚠️ Groq: {e}")
        return ""

def parse_distance(text):
    result = []
    t = text.lower()
    if "sprint" in t or "short" in t:
        result.append("Спринт")
    if "mid" in t or "middle" in t:
        result.append("Средние дистанции")
    if "long" in t:
        result.append("Длинные дистанции")
    if "hurdle" in t:
        result.append("Барьеры")
    if "cross" in t or "xc" in t:
        result.append("Кросс")
    if "jump" in t or "pole vault" in t or "triple" in t:
        result.append("Прыжки")
    if not result and ("running" in t or "multi" in t or "all" in t or "versatile" in t):
        return "Спринт, Средние дистанции, Длинные дистанции"
    return ", ".join(result) if result else "Спринт, Средние дистанции, Длинные дистанции"

def save_to_supabase(product):
    try:
        existing = supabase.table("products").select("id, images, source_url").eq("name", product["name"]).execute()

        if existing.data:
            existing_product = existing.data[0]

            if existing_product.get("source_url") == product["source_url"]:
                return "skip"

            old_images = existing_product.get("images") or []

            if product["images"]:
                new_image = product["images"][0]
                if new_image not in old_images:
                    old_images.append(new_image)
                    supabase.table("products").update({"images": old_images}).eq("id", existing_product["id"]).execute()
                    return "updated"
                else:
                    return "color_exists"

            return "color_exists"

        supabase.table("products").insert(product).execute()
        return "new"
    except Exception as e:
        print(f"   ❌ Supabase: {e}")
        return "error"

async def collect_product_links(page):
    product_links = []
    page_num = 1

    while True:
        print(f"\n   Страница {page_num} — ищем ссылки...")
        if page_num > 1:
            next_url = f"{CATEGORY_URL}/page-{page_num}"
            try:
                await page.goto(next_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"   ⚠️ Ошибка загрузки страницы {page_num}: {e}")
                break
        else:
            await page.wait_for_timeout(2500)

        try:
            await page.wait_for_selector("a[href*='/p/']", timeout=8000)
        except:
            pass

        links = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        new_links = [l for l in links if "/p/" in l and l not in product_links]

        if not new_links:
            print("   ✅ Ссылки закончились. Завершаем сбор.")
            break

        product_links.extend(new_links)
        print(f"   Новых: {len(new_links)} | Всего: {len(product_links)}")

        if page_num >= 20:
            print("   ⚠️ Достигнут лимит страниц в категории.")
            break

        page_num += 1

    print(f"\n   📦 Итого найдено: {len(product_links)}")
    return product_links

async def parse_product(page, url, eur_rub):
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2500)

    # ── Название ─────────────────────────────────────────────────────────────
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
    for prefix in ["Track shoes/Spikes ", "Running shoes ", "Track shoes ", "Spikes "]:
        if name.startswith(prefix):
            name = name[len(prefix):]

    # ── Бренд ─────────────────────────────────────────────────────────────────
    brand = ""
    for word in ["Nike", "Adidas", "Puma", "Saucony", "Hoka", "On Running",
                 "New Balance", "Asics", "Keyena", "Brooks"]:
        if word.lower() in name.lower():
            brand = word
            break

    # ── Цена ──────────────────────────────────────────────────────────────────
    price_eur = 0
    original_price_eur = 0
    try:
        price_result = await page.evaluate("""() => {
            const addToCart = document.querySelector(
                '[class*="add-to-cart"], [class*="addToCart"], button[type="submit"]'
            );
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
                    if (rect.width > 50 && rect.top > 0 && rect.top < 800) {
                        priceBlock = el;
                        break;
                    }
                }
            }
            if (!priceBlock) return { current: 0, original: 0 };
            const txt = priceBlock.innerText || '';
            const allPrices = txt.match(/[€]\s*[\d]+[,\.][\d]{2}/g) || [];
            const prices = allPrices
                .map(p => parseFloat(p.replace('€','').replace(',','.').trim()))
                .filter(p => p > 20 && p < 2000);
            if (prices.length === 0) return { current: 0, original: 0 };
            if (prices.length === 1) return { current: prices[0], original: 0 };
            return { current: Math.min(...prices), original: Math.max(...prices) };
        }""")
        price_eur = price_result.get("current", 0)
        original_price_eur = price_result.get("original", 0)
    except Exception as e:
        print(f"   ⚠️ Ошибка цены: {e}")
    if price_eur <= 0:
        try:
            price_meta = await page.get_attribute('meta[property="product:price:amount"]', "content")
            if price_meta:
                price_eur = float(price_meta)
        except:
            pass

    # ── Дистанция ─────────────────────────────────────────────────────────────
    distance = ""
    try:
        page_text = await page.inner_text("body")
        match = re.search(r'(?mi)^\s*Distance\s*[:\n]\s*([^\n]{3,50})', page_text)
        if match:
            distance = parse_distance(match.group(1).strip())
        if not distance:
            distance = parse_distance(name)
        if not distance:
            distance = "Спринт, Средние дистанции, Длинные дистанции"
    except:
        distance = "Спринт, Средние дистанции, Длинные дистанции"

    # ── Описание ──────────────────────────────────────────────────────────────
    raw_description = ""
    try:
        raw_description = await page.evaluate("""() => {
            const selectors = [
                '[class*="description"]', '[class*="product-detail__text"]',
                '[class*="product__text"]', '[itemprop="description"]',
                '[class*="tabs__content"]', '[class*="tab-content"]'
            ];
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
    description = generate_description(raw_description, name)

    # ── Фото: og:image даёт уникальное фото конкретного цвета ─────────────────
    images = []
    try:
        # og:image — всегда указывает на фото именно этого цвета/варианта
        og_image = await page.get_attribute('meta[property="og:image"]', "content")
        if og_image and og_image.startswith("http") and not og_image.endswith(".svg"):
            images = [og_image]
            print(f"      🖼️  og:image: {og_image.split('/')[-1]}")
    except:
        pass

    # Fallback если og:image не нашли
    if not images:
        try:
            raw_images = await page.evaluate("""() => {
                const allImgs = Array.from(document.querySelectorAll('img'));
                const validSrcs = allImgs
                    .map(img => img.src || img.dataset.src || '')
                    .filter(src =>
                        src.startsWith('http') &&
                        !src.endsWith('.svg') &&
                        !src.includes('logo') &&
                        !src.includes('icon') &&
                        !src.includes('banner') &&
                        !src.includes('brand') &&
                        (src.includes('/products/') || src.includes('/catalog/') || src.endsWith('.webp') || src.endsWith('.jpg'))
                    );
                return validSrcs.length > 0 ? [validSrcs[0]] : [];
            }""")
            images = raw_images
            print(f"      🖼️  fallback img: {images[0].split('/')[-1] if images else 'none'}")
        except:
            pass

    if not name:
        return None
    if price_eur <= 0:
        print(f"   ⚠️ Цена не найдена: {name}")
        return None

    return {
        "name": name,
        "brand": brand,
        "price_eur": price_eur,
        "original_price_eur": original_price_eur if original_price_eur > price_eur else None,
        "price_rub": int(round((price_eur * eur_rub * MARKUP) / 100) * 100),
        "images": images,
        "description": description,
        "category": CATEGORY_NAME,
        "source_url": url,
        "distance": distance,
    }

async def main():
    print(f"🚀 Парсер | Лимит: {LIMIT} товаров\n")
    eur_rub = get_eur_rub()
    added = updated_colors = skipped = errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        print("📄 Открываем страницу категории...")
        await page.goto(CATEGORY_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

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
                    imgs = len(product.get("images", []))
                    has_desc = "✅" if product.get("description") else "❌"
                    print(f"   ✅ Создан: {product['name'][:45]}")
                    print(f"      💰 {product['price_eur']}€ → {product['price_rub']:,}₽  📷 {imgs}  📝 {has_desc}")

                elif result == "updated":
                    updated_colors += 1
                    print(f"   🎨 Новый цвет: {product['name'][:45]}")

                elif result == "color_exists":
                    skipped += 1
                    print(f"   🔁 Цвет уже есть: {product['name'][:45]}")

                elif result == "skip":
                    skipped += 1
                    print(f"   ⏭️  Дубль URL — пропущено")

                else:
                    errors += 1

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                errors += 1

            await asyncio.sleep(1.5)

        await browser.close()

    print(f"\n{'='*50}")
    print(f"✅ Создано новых моделей:  {added}")
    print(f"🎨 Добавлено расцветок:    {updated_colors}")
    print(f"🔁 Цвет уже был в базе:    {skipped}")
    print(f"❌ Ошибок:                 {errors}")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())
