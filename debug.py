import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

url = "https://top4running.com/c/track-shoes-spikes"
r = requests.get(url, headers=HEADERS, timeout=15)
soup = BeautifulSoup(r.content, "html.parser")

print("=== ВСЕ ССЫЛКИ НА СТРАНИЦЕ ===")
all_links = soup.find_all("a", href=True)
print(f"Всего ссылок: {len(all_links)}\n")

# Показываем первые 40 ссылок
for i, a in enumerate(all_links[:40]):
    print(f"[{i}] href={a['href']!r}  text={a.get_text(strip=True)[:50]!r}")

print("\n\n=== СОХРАНЯЕМ HTML В ФАЙЛ ===")
with open("page_dump.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Файл page_dump.html создан — открой его в браузере")
