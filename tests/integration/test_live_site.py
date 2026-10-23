"""Entegrasyon testleri: gerçek siteye birkaç istek atar (her istekten sonra 0.5 sn bekler)."""
from urllib.parse import urljoin

import pytest

import scrape

pytestmark = pytest.mark.integration


def test_home_total_is_1000():
    home = scrape.fetch(scrape.BASE_URL)
    assert home is not None
    assert scrape.site_total(home) == 1000


def test_last_listing_page_has_20_books_and_no_next():
    url = urljoin(scrape.BASE_URL, "catalogue/page-50.html")
    s = scrape.fetch(url)
    assert s is not None
    assert len(s.select("article.product_pod")) == 20
    assert scrape.next_page_url(s, url) is None


def test_detail_page_gives_category_and_stock():
    d = scrape.parse_detail(urljoin(scrape.BASE_URL, "catalogue/a-light-in-the-attic_1000/index.html"))
    assert d["kategori"] == "Poetry"
    assert d["stok"].startswith("In stock")
    assert isinstance(d["stok_adedi"], int)


def test_missing_page_is_skipped_not_raised():
    assert scrape.fetch(urljoin(scrape.BASE_URL, "catalogue/boyle-bir-sayfa-yok.html")) is None
