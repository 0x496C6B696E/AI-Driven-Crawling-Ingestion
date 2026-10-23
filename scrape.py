"""
books.toscrape.com scraper
--------------------------
Sitedeki TÜM kitaplari (50 liste sayfasi, 1000 kitap) cekip kitaplar.csv'ye yazar.

Alanlar: kitap_adi, fiyat (float), puan (int 1-5), stok (str), stok_adedi (int), kategori, url

Tasarim kararlari:
- Liste sayfasinda ad, fiyat, puan var; KATEGORI ve stok adedi yalnizca kitabin
  kendi sayfasinda. Bu yuzden her kitabin detay sayfasi da cekilir (toplam ~1050 istek).
- Her istekten sonra REQUEST_DELAY kadar beklenir (siteyi yormamak icin).
- Her istek retry'li ve timeout'lu; bir sayfa acilmazsa loglanir ve atlanir, program cokmez.
- Bos/eksik alanlar None olarak yazilir; islem sonunda ozet rapor basilir.
"""

from __future__ import annotations

import csv
import logging
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
OUTPUT_CSV = "kitaplar.csv"
REQUEST_DELAY = 0.5      # saniye - istekler arasi bekleme
TIMEOUT = 15             # saniye
MAX_RETRIES = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (ders odevi scraper; books.toscrape.com egitim sitesi)"}

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("scrape.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


@dataclass
class Kitap:
    kitap_adi: Optional[str]
    fiyat: Optional[float]
    puan: Optional[int]
    stok: Optional[str]
    stok_adedi: Optional[int]
    kategori: Optional[str]
    url: str


session = requests.Session()
session.headers.update(HEADERS)


def fetch(url: str) -> Optional[BeautifulSoup]:
    """URL'yi retry ile ceker; basarisizsa None doner (asla exception firlatmaz)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code == 200:
                # Site latin-1 ile sunuluyor ama icerik utf-8; apparent_encoding dogru cozer
                resp.encoding = resp.apparent_encoding or "utf-8"
                time.sleep(REQUEST_DELAY)
                return BeautifulSoup(resp.text, "html.parser")
            log.warning("HTTP %s  %s (deneme %d/%d)", resp.status_code, url, attempt, MAX_RETRIES)
            if resp.status_code == 404:
                break  # tekrar denemenin anlami yok
        except requests.RequestException as exc:
            log.warning("Istek hatasi %s: %s (deneme %d/%d)", url, exc, attempt, MAX_RETRIES)
        time.sleep(REQUEST_DELAY * attempt)  # her denemede biraz daha bekle
    log.error("ATLANDI: %s", url)
    return None


def parse_price(text: Optional[str]) -> Optional[float]:
    """'£51.77' -> 51.77. Bozuk metinde None."""
    if not text:
        return None
    m = re.search(r"[\d.]+", text)
    try:
        return float(m.group()) if m else None
    except ValueError:
        return None


def parse_rating(tag) -> Optional[int]:
    """<p class="star-rating Three"> -> 3."""
    if tag is None:
        return None
    for cls in tag.get("class", []):
        if cls in RATING_MAP:
            return RATING_MAP[cls]
    return None


def parse_stock_count(text: Optional[str]) -> Optional[int]:
    """'In stock (22 available)' -> 22."""
    if not text:
        return None
    m = re.search(r"\((\d+) available\)", text)
    return int(m.group(1)) if m else None


def parse_detail(url: str) -> dict:
    """Kitabin kendi sayfasindan kategori ve stok bilgisini alir."""
    soup = fetch(url)
    out = {"kategori": None, "stok": None, "stok_adedi": None}
    if soup is None:
        return out
    try:
        # breadcrumb: Home > Books > <Kategori> > <Kitap>
        crumbs = soup.select("ul.breadcrumb li a")
        if len(crumbs) >= 3:
            out["kategori"] = crumbs[2].get_text(strip=True)
        stock_tag = soup.select_one("p.instock.availability")
        if stock_tag:
            stock_text = " ".join(stock_tag.get_text(" ", strip=True).split())
            out["stok"] = stock_text
            out["stok_adedi"] = parse_stock_count(stock_text)
    except Exception as exc:  # parse hatasi programi durdurmasin
        log.warning("Detay parse hatasi %s: %s", url, exc)
    return out


def parse_listing(soup: BeautifulSoup, page_url: str) -> list[Kitap]:
    kitaplar: list[Kitap] = []
    for art in soup.select("article.product_pod"):
        try:
            a = art.select_one("h3 a")
            title = a.get("title") if a else None
            href = a.get("href") if a else None
            detail_url = urljoin(page_url, href) if href else page_url
            price = parse_price(art.select_one("p.price_color").get_text() if art.select_one("p.price_color") else None)
            rating = parse_rating(art.select_one("p.star-rating"))
            detail = parse_detail(detail_url)
            kitaplar.append(Kitap(
                kitap_adi=title,
                fiyat=price,
                puan=rating,
                stok=detail["stok"],
                stok_adedi=detail["stok_adedi"],
                kategori=detail["kategori"],
                url=detail_url,
            ))
        except Exception as exc:
            log.warning("Kitap parse hatasi (%s): %s", page_url, exc)
    return kitaplar


def next_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    nxt = soup.select_one("li.next a")
    return urljoin(current_url, nxt["href"]) if nxt and nxt.get("href") else None


def main() -> int:
    tum_kitaplar: list[Kitap] = []
    url: Optional[str] = START_URL
    page_no = 0
    while url:
        page_no += 1
        log.info("Sayfa %d: %s", page_no, url)
        soup = fetch(url)
        if soup is None:
            # Liste sayfasi acilmadiysa bir sonraki sayfayi tahmin ederek devam et
            m = re.search(r"page-(\d+)\.html", url)
            if m and page_no < 200:
                url = urljoin(BASE_URL, f"catalogue/page-{int(m.group(1)) + 1}.html")
                continue
            break
        kitaplar = parse_listing(soup, url)
        log.info("  %d kitap bulundu (toplam %d)", len(kitaplar), len(tum_kitaplar) + len(kitaplar))
        tum_kitaplar.extend(kitaplar)
        url = next_page_url(soup, url)

    # Sitenin ana sayfasinda yazan toplam ile karsilastir
    home = fetch(BASE_URL)
    site_total = None
    if home:
        strong = home.select_one("form.form-horizontal strong")
        if strong and strong.get_text(strip=True).isdigit():
            site_total = int(strong.get_text(strip=True))

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(Kitap.__dataclass_fields__.keys()))
        writer.writeheader()
        for k in tum_kitaplar:
            writer.writerow(asdict(k))

    eksik = {alan: sum(1 for k in tum_kitaplar if getattr(k, alan) is None)
             for alan in ("kitap_adi", "fiyat", "puan", "stok", "kategori")}
    log.info("=== OZET ===")
    log.info("Cekilen kitap: %d | Sitede yazan: %s | Sayfa: %d", len(tum_kitaplar), site_total, page_no)
    log.info("Eksik alan sayilari: %s", eksik)
    log.info("CSV yazildi: %s", OUTPUT_CSV)
    if site_total is not None and site_total != len(tum_kitaplar):
        log.warning("UYARI: cekilen kitap sayisi sitedeki toplamla eslesmiyor!")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("Kullanici durdurdu.")
        sys.exit(130)
