"""Birim testleri: ağ yok, sabit HTML parçalarıyla parse fonksiyonları."""
import requests
from bs4 import BeautifulSoup

import scrape

LISTING_HTML = """
<html><body>
<article class="product_pod">
  <h3><a href="a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
  <p class="star-rating Three"></p>
  <p class="price_color">£51.77</p>
</article>
<article class="product_pod">
  <h3><a href="bozuk_1/index.html" title="Bozuk Kitap">Bozuk</a></h3>
  <p class="star-rating Yok"></p>
</article>
<ul class="pager"><li class="next"><a href="page-2.html">next</a></li></ul>
</body></html>
"""

DETAIL_HTML = """
<ul class="breadcrumb">
  <li><a href="/">Home</a></li><li><a href="/books">Books</a></li>
  <li><a href="/poetry">Poetry</a></li><li class="active">A Light in the Attic</li>
</ul>
<p class="instock availability"><i class="icon-ok"></i>
    In stock (22 available)
</p>
"""


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_parse_price():
    assert scrape.parse_price("£51.77") == 51.77
    assert scrape.parse_price("Â£10.00") == 10.0      # encoding bozulsa bile sayı çıkar
    assert scrape.parse_price("") is None
    assert scrape.parse_price(None) is None
    assert scrape.parse_price("fiyat yok") is None


def test_parse_rating():
    assert scrape.parse_rating(soup('<p class="star-rating Three"></p>').p) == 3
    assert scrape.parse_rating(soup('<p class="star-rating Five"></p>').p) == 5
    assert scrape.parse_rating(soup('<p class="star-rating"></p>').p) is None
    assert scrape.parse_rating(None) is None


def test_parse_stock_count():
    assert scrape.parse_stock_count("In stock (22 available)") == 22
    assert scrape.parse_stock_count("Out of stock") is None
    assert scrape.parse_stock_count(None) is None


def test_next_page_url():
    s = soup(LISTING_HTML)
    assert scrape.next_page_url(s, "https://books.toscrape.com/catalogue/page-1.html") == \
        "https://books.toscrape.com/catalogue/page-2.html"
    assert scrape.next_page_url(soup("<html></html>"), "x") is None   # son sayfa


def test_parse_detail_soup():
    d = scrape.parse_detail_soup(soup(DETAIL_HTML))
    assert d == {"kategori": "Poetry", "stok": "In stock (22 available)", "stok_adedi": 22}
    assert scrape.parse_detail_soup(soup("<html></html>")) == {"kategori": None, "stok": None, "stok_adedi": None}


def test_site_total():
    assert scrape.site_total(soup('<form class="form-horizontal"><strong>1000</strong> results</form>')) == 1000
    assert scrape.site_total(soup("<html></html>")) is None


def test_parse_listing_without_network(monkeypatch):
    monkeypatch.setattr(scrape, "fetch", lambda url: soup(DETAIL_HTML))  # detay sayfası sahte
    kitaplar = scrape.parse_listing(soup(LISTING_HTML), "https://books.toscrape.com/catalogue/page-1.html")
    assert len(kitaplar) == 2
    k = kitaplar[0]
    assert (k.kitap_adi, k.fiyat, k.puan, k.kategori, k.stok_adedi) == ("A Light in the Attic", 51.77, 3, "Poetry", 22)
    assert k.url == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    bozuk = kitaplar[1]                      # eksik alanlar None, exception yok
    assert bozuk.fiyat is None and bozuk.puan is None and bozuk.kitap_adi == "Bozuk Kitap"


def test_fetch_failure_returns_none_not_exception(monkeypatch):
    class BozukSession:
        def get(self, url, timeout):
            raise requests.ConnectionError("ag yok")
    monkeypatch.setattr(scrape, "session", BozukSession())
    monkeypatch.setattr(scrape, "REQUEST_DELAY", 0)
    assert scrape.fetch("https://example.invalid/") is None
