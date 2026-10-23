"""
books.toscrape.com scraper
--------------------------
Sitedeki TÜM kitapları (50 liste sayfası, 1000 kitap) çekip data/kitaplar.csv'ye yazar.

Alanlar: kitap_adi, fiyat (float), puan (int 1-5), stok (str), stok_adedi (int), kategori, url

Tasarım kararları:
- Liste sayfasında ad, fiyat, puan var; KATEGORİ ve stok adedi yalnızca kitabın kendi
  sayfasında (breadcrumb). Bu yüzden her kitabın detay sayfası da çekilir (~1050 istek).
- Her istekten sonra REQUEST_DELAY kadar beklenir (siteyi yormamak için). Paralel istek yok.
- Her istek retry'lı ve timeout'lu; bir sayfa açılmazsa loglanır ve atlanır, program çökmez.
- Boş/eksik alanlar None olarak yazılır; işlem sonunda özet rapor basılır.

Kullanım:
    python src/scrape.py                   # tam çekim -> data/kitaplar.csv, logs/scrape.log
    python src/scrape.py --max-pages 2     # hızlı deneme (e2e testte kullanılır)
    python src/scrape.py --out x.csv --log y.log --delay 1.0
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]           # proje kök klasörü
DEFAULT_CSV = ROOT / "data" / "kitaplar.csv"
DEFAULT_LOG = ROOT / "logs" / "scrape.log"

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
REQUEST_DELAY = 0.5      # saniye - istekler arası bekleme (CLAUDE.md: en az 0.5)
TIMEOUT = 15             # saniye
MAX_RETRIES = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (ders odevi scraper; books.toscrape.com egitim sitesi)"}

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

log = logging.getLogger("scrape")
session = requests.Session()
session.headers.update(HEADERS)


@dataclass
class Kitap:
    kitap_adi: Optional[str]
    fiyat: Optional[float]
    puan: Optional[int]
    stok: Optional[str]
    stok_adedi: Optional[int]
    kategori: Optional[str]
    url: str


def setup_logging(log_path: Path) -> None:
    """Hem konsola hem dosyaya logla (log mesajları ASCII tutulur: Windows konsolu için)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        force=True,
    )


def fetch(url: str) -> Optional[BeautifulSoup]:
    """URL'yi retry ile çeker; başarısızsa None döner (asla exception fırlatmaz)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code == 200:
                # Site latin-1 başlığı gönderiyor ama içerik utf-8; apparent_encoding doğru çözer
                resp.encoding = resp.apparent_encoding or "utf-8"
                time.sleep(REQUEST_DELAY)
                return BeautifulSoup(resp.text, "html.parser")
            log.warning("HTTP %s  %s (deneme %d/%d)", resp.status_code, url, attempt, MAX_RETRIES)
            if resp.status_code == 404:
                break  # tekrar denemenin anlamı yok
        except requests.RequestException as exc:
            log.warning("Istek hatasi %s: %s (deneme %d/%d)", url, exc, attempt, MAX_RETRIES)
        time.sleep(REQUEST_DELAY * attempt)  # her denemede biraz daha bekle
    log.error("ATLANDI: %s", url)
    return None


# ---------------------------------------------------------------- parse fonksiyonları
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


def parse_detail_soup(soup: BeautifulSoup) -> dict:
    """Detay sayfası HTML'inden kategori (breadcrumb) ve stok bilgisini çıkarır."""
    out = {"kategori": None, "stok": None, "stok_adedi": None}
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
    except Exception as exc:  # parse hatası programı durdurmasın
        log.warning("Detay parse hatasi: %s", exc)
    return out


def parse_detail(url: str) -> dict:
    """Kitabın kendi sayfasını çekip kategori ve stok bilgisini alır; sayfa açılmazsa None'lar."""
    soup = fetch(url)
    if soup is None:
        return {"kategori": None, "stok": None, "stok_adedi": None}
    return parse_detail_soup(soup)


def parse_listing(soup: BeautifulSoup, page_url: str) -> list[Kitap]:
    """Bir liste sayfasındaki 20 kitabı (detay sayfalarıyla birlikte) döner."""
    kitaplar: list[Kitap] = []
    for art in soup.select("article.product_pod"):
        try:  # bir kitap bozuksa diğerleri etkilenmesin
            a = art.select_one("h3 a")
            title = a.get("title") if a else None
            href = a.get("href") if a else None
            detail_url = urljoin(page_url, href) if href else page_url
            price_tag = art.select_one("p.price_color")
            price = parse_price(price_tag.get_text() if price_tag else None)
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
    """'next' bağlantısı varsa tam URL'sini, son sayfadaysa None döner."""
    nxt = soup.select_one("li.next a")
    return urljoin(current_url, nxt["href"]) if nxt and nxt.get("href") else None


def site_total(home_soup: BeautifulSoup) -> Optional[int]:
    """Ana sayfadaki '1000 results' sayısını okur; bulamazsa None."""
    strong = home_soup.select_one("form.form-horizontal strong")
    text = strong.get_text(strip=True) if strong else ""
    return int(text) if text.isdigit() else None


# ---------------------------------------------------------------- ana akış
def write_csv(kitaplar: list[Kitap], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[fl.name for fl in fields(Kitap)])
        writer.writeheader()
        for k in kitaplar:
            writer.writerow(asdict(k))


def main(argv: Optional[list[str]] = None) -> int:
    global REQUEST_DELAY
    p = argparse.ArgumentParser(description="books.toscrape.com scraper")
    p.add_argument("--out", type=Path, default=DEFAULT_CSV, help="CSV çıktı yolu")
    p.add_argument("--log", type=Path, default=DEFAULT_LOG, help="log dosyası yolu")
    p.add_argument("--max-pages", type=int, default=None, help="en fazla kaç liste sayfası (deneme için)")
    p.add_argument("--delay", type=float, default=REQUEST_DELAY, help="istekler arası bekleme, saniye (en az 0.5)")
    args = p.parse_args(argv)
    REQUEST_DELAY = max(args.delay, 0.5)  # CLAUDE.md kuralı: 0.5 sn'nin altına inme
    setup_logging(args.log)

    tum_kitaplar: list[Kitap] = []
    url: Optional[str] = START_URL
    page_no = 0
    while url and (args.max_pages is None or page_no < args.max_pages):
        page_no += 1
        log.info("Sayfa %d: %s", page_no, url)
        soup = fetch(url)
        if soup is None:
            # Liste sayfası açılmadıysa bir sonraki sayfayı tahmin ederek devam et
            m = re.search(r"page-(\d+)\.html", url)
            if m and page_no < 200:
                url = urljoin(BASE_URL, f"catalogue/page-{int(m.group(1)) + 1}.html")
                continue
            break
        kitaplar = parse_listing(soup, url)
        log.info("  %d kitap bulundu (toplam %d)", len(kitaplar), len(tum_kitaplar) + len(kitaplar))
        tum_kitaplar.extend(kitaplar)
        url = next_page_url(soup, url)

    write_csv(tum_kitaplar, args.out)

    eksik = {alan: sum(1 for k in tum_kitaplar if getattr(k, alan) is None)
             for alan in ("kitap_adi", "fiyat", "puan", "stok", "kategori")}
    log.info("=== OZET ===")
    log.info("Cekilen kitap: %d | Sayfa: %d | Eksik alan sayilari: %s", len(tum_kitaplar), page_no, eksik)
    log.info("CSV yazildi: %s", args.out)

    if args.max_pages is not None:
        log.info("Kismi cekim (--max-pages=%d): site toplamiyla karsilastirma atlandi.", args.max_pages)
        return 0

    # Sitenin ana sayfasında yazan toplam ile karşılaştır
    home = fetch(BASE_URL)
    toplam = site_total(home) if home else None
    log.info("Sitede yazan toplam: %s", toplam)
    if toplam is not None and toplam != len(tum_kitaplar):
        log.warning("UYARI: cekilen kitap sayisi (%d) sitedeki toplamla (%d) eslesmiyor!",
                    len(tum_kitaplar), toplam)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("Kullanici durdurdu.")
        sys.exit(130)
