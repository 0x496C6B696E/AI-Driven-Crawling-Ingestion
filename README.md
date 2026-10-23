# books.toscrape.com Scraper & Analiz

[books.toscrape.com](https://books.toscrape.com) sitesindeki **1000 kitabın** adını, fiyatını, puanını, stok durumunu ve kategorisini çeker, temiz bir CSV'ye yazar ve pandas + matplotlib ile basit bir analiz üretir. Proje bir "AI destekli scraping" ödevi için Claude Code ile birlikte geliştirildi; AI'a verilen kural dosyası, prompt günlüğü ve yansıma raporu da repodadır.

## İçindekiler

- [Klasör yapısı](#klasör-yapısı)
- [Kurulum](#kurulum)
- [Çalıştırma](#çalıştırma)
- [Testler](#testler)
- [Çıktılar](#çıktılar)
- [Nasıl çalışır](#nasıl-çalışır)
- [Hata yönetimi ve etik kurallar](#hata-yönetimi-ve-etik-kurallar)
- [AI ile çalışma (bonus)](#ai-ile-çalışma-bonus)
- [Teslim kontrol listesi](#teslim-kontrol-listesi)

## Klasör yapısı

```text
.
├── src/
│   ├── scrape.py              # veri çekme: 50 liste sayfası + 1000 detay sayfası -> data/kitaplar.csv
│   └── analiz.py              # analiz: CSV -> charts/*.png + docs/analiz_sonuc.txt
├── data/
│   └── kitaplar.csv           # çıktı verisi (1000 satır, UTF-8, başlık satırlı)
├── charts/
│   ├── grafik_kategori_fiyat.png   # en pahalı 10 kategori (ortalama fiyat)
│   ├── grafik_puan_dagilimi.png    # 1-5 puan dağılımı
│   └── grafik_puan_fiyat.png       # puana göre fiyat kutu grafiği (ek)
├── logs/
│   └── scrape.log             # çekim logu: sayfa sayfa ilerleme, hatalar, özet
├── docs/
│   ├── PROMPT_GUNLUGU.md      # kullanılan önemli promptlar ve sonuçları
│   ├── YANSIMA_RAPORU.md      # yansıma raporu (+ bonus: MCP / kural dosyası)
│   └── analiz_sonuc.txt       # sayısal özet ve "puanı yüksek kitaplar daha mı pahalı?" cevabı
├── tests/
│   ├── conftest.py            # src/ klasörünü import yoluna ekler
│   ├── unit/                  # ağ gerektirmez: parse fonksiyonları, hata durumları
│   ├── integration/           # gerçek siteye birkaç istek: toplam 1000, son sayfa, detay sayfası
│   └── e2e/                   # uçtan uca: scrape.py (1 sayfa) -> analiz.py -> PNG + özet
├── tools/
│   └── scrape_browser.js      # scrape.py'nin tarayıcı konsolu sürümü (bkz. yansıma raporu)
├── CLAUDE.md                  # AI aracına (Claude Code) verilen proje kural dosyası
├── requirements.txt           # çalışma bağımlılıkları
├── requirements-dev.txt       # + pytest
├── pytest.ini
└── .gitignore
```

## Kurulum

Python 3.10+ gerekir.

```bash
python -m venv .venv
# Windows:        .venv\Scripts\activate
# Linux / macOS:  source .venv/bin/activate
pip install -r requirements.txt          # sadece çalıştırmak için
pip install -r requirements-dev.txt      # testleri de çalıştırmak için
```

> **Windows notu:** `python` komutu Microsoft Store yönlendirmesine takılıp *"Python was not found"* diyorsa, sürümlü komutu kullanın: `python3.12 src/scrape.py`.

## Çalıştırma

```bash
python src/scrape.py      # ~1050 istek, 0.5 sn bekleme ile yaklaşık 12-13 dakika
python src/analiz.py      # grafikleri ve docs/analiz_sonuc.txt'yi üretir
```

Komutlar proje kökünden bağımsız çalışır: çıktı yolları `src/` klasörüne göre hesaplanır, dolayısıyla hangi klasörde olursanız olun `data/`, `charts/`, `logs/` ve `docs/` altına yazılır. Klasörler yoksa oluşturulur.

### `scrape.py` seçenekleri

| Seçenek | Varsayılan | Açıklama |
| --- | --- | --- |
| `--out` | `data/kitaplar.csv` | CSV çıktı yolu |
| `--log` | `logs/scrape.log` | Log dosyası yolu |
| `--max-pages N` | sınırsız | En fazla N liste sayfası çek (hızlı deneme; site toplamıyla karşılaştırma atlanır) |
| `--delay S` | `0.5` | İstekler arası bekleme (saniye); 0.5'in altı kabul edilmez |

Tam çekim bitince script, çektiği kitap sayısını sitenin ana sayfasında yazan toplamla (1000) karşılaştırır; eşleşmezse `UYARI` loglar ve çıkış kodu **1** döner.

### `analiz.py` seçenekleri

| Seçenek | Varsayılan |
| --- | --- |
| `--csv` | `data/kitaplar.csv` |
| `--charts-dir` | `charts/` |
| `--out` | `docs/analiz_sonuc.txt` |

## Testler

```bash
python -m pytest                       # hepsi (unit + integration + e2e), ~30 sn
python -m pytest tests/unit            # ağ gerektirmez, < 1 sn
python -m pytest tests/integration     # gerçek siteye 4-5 istek
python -m pytest tests/e2e             # scrape.py --max-pages 1 -> analiz.py, geçici klasörde
```

| Katman | Dosya | Ne doğrular |
| --- | --- | --- |
| Unit | `tests/unit/test_parsers.py` | `£51.77 → 51.77`, `Three → 3`, `(22 available) → 22`, breadcrumb'dan kategori, son sayfada `next = None`, bozuk kitapta `None` (exception yok), ağ hatasında `fetch` → `None` |
| Integration | `tests/integration/test_live_site.py` | Ana sayfadaki toplam 1000; 50. sayfada 20 kitap ve `next` yok; gerçek detay sayfasından kategori "Poetry" ve stok adedi; olmayan sayfa atlanıyor |
| E2E | `tests/e2e/test_pipeline.py` | 1 sayfa çekimi → 20 satırlık CSV, `fiyat` float, `puan` int (1-5), log yazıldı → analiz → 3 PNG + özet metni |

## Çıktılar

### `data/kitaplar.csv`

| Sütun | Tip | Örnek |
| --- | --- | --- |
| `kitap_adi` | str | `A Light in the Attic` |
| `fiyat` | float (£) | `51.77` |
| `puan` | int (1–5) | `3` |
| `stok` | str | `In stock (22 available)` |
| `stok_adedi` | int | `22` |
| `kategori` | str | `Poetry` |
| `url` | str | kitabın detay sayfası |

Eksik veya parse edilemeyen alan boş hücre (`None`) olarak yazılır; satır atlanmaz.

### Grafikler ve özet

- `charts/grafik_kategori_fiyat.png` — Kategori başına ortalama fiyat, en pahalı 10 kategori. Tek kitaplı kategoriler ortalamayı yanılttığı için **en az 2 kitabı olan** kategoriler alınır; etiketlerde `n=` gösterilir.
- `charts/grafik_puan_dagilimi.png` — 1–5 puan dağılımı.
- `charts/grafik_puan_fiyat.png` — Puana göre fiyat kutu grafiği ve Pearson korelasyonu (ek).
- `docs/analiz_sonuc.txt` — Sayısal özet ve **"Puanı yüksek kitaplar daha mı pahalı?"** sorusunun cevabı (kısaca: hayır, r ≈ 0.03; puan gruplarının ortalaması £34–36 bandında).

## Nasıl çalışır

1. `catalogue/page-1.html`'den başlar, her sayfadaki `li.next a` bağlantısını izleyerek 50 liste sayfasını gezer (sayfa sayısı sabit kodlanmaz).
2. Liste sayfasında ad, fiyat (`p.price_color`) ve puan (`p.star-rating <Sayı>` sınıfı) vardır. **Kategori ve stok adedi liste sayfasında yoktur**; her kitabın detay sayfası çekilir, kategori breadcrumb'ın 3. öğesinden (`Home > Books > Kategori > Kitap`), stok `p.instock.availability` metninden alınır.
3. Fiyat regex ile sayıya (`£51.77 → 51.77`), puan sözlükle tam sayıya (`Three → 3`) çevrilir.
4. Tüm kitaplar `data/kitaplar.csv`'ye yazılır, özet loglanır, sitedeki toplam ile karşılaştırılır.

## Hata yönetimi ve etik kurallar

- **Bekleme:** her HTTP isteğinden sonra 0.5 sn (`--delay` ile artırılabilir); paralel/çok iş parçacıklı istek yok.
- **Timeout + tekrar:** her istek 15 sn timeout, en fazla 3 deneme, denemeler arasında artan bekleme; 404'te tekrar denenmez. Yine açılmazsa sayfa **loglanıp atlanır**, program çökmez.
- **Kitap başına `try/except`:** bir kitabın HTML'i bozuksa yalnızca o kitabın alanları `None` olur, diğerleri etkilenmez.
- **Tanımlayıcı `User-Agent`** gönderilir.
- **Log:** hem konsola hem `logs/scrape.log` dosyasına (UTF-8).
- **Sayı doğrulaması:** çekilen kitap sayısı sitedeki toplamla karşılaştırılır.

## AI ile çalışma (bonus)

- [`CLAUDE.md`](CLAUDE.md): Claude Code'un her oturumda otomatik okuduğu proje kural dosyası. Bekleme süresi, timeout/retry, `None` kuralı, loglama, CSV formatı, sayı doğrulaması ve grafik kuralları burada tanımlı; AI kodu bu kurallara göre yazdı.
- [`docs/PROMPT_GUNLUGU.md`](docs/PROMPT_GUNLUGU.md): kullanılan en önemli promptlar, AI'ın ürettiği, çalışıp çalışmadığı ve düzeltmeler.
- [`docs/YANSIMA_RAPORU.md`](docs/YANSIMA_RAPORU.md): AI nerede yardımcı oldu / yanıldı, sonuçlar nasıl doğrulandı, bonus bölümü (kural dosyası, tarayıcı ve dosya sistemi araçları).
- [`tools/scrape_browser.js`](tools/scrape_browser.js): ilk oturumda AI ortamından siteye ağ erişimi olmadığı için verinin ilk kez çekildiği tarayıcı sürümü. Daha sonra `scrape.py` yerel makinede çalıştırılıp iki çıktı karşılaştırıldı (ayrıntı yansıma raporunda).

## Teslim kontrol listesi

| Ödev maddesi | Nerede |
| --- | --- |
| Kod + çalıştırma talimatı | `src/`, bu README |
| `kitaplar.csv` | `data/kitaplar.csv` |
| Grafikler (≥ 2) | `charts/` (3 adet) |
| "Puanı yüksek kitaplar daha mı pahalı?" | `docs/analiz_sonuc.txt`, `docs/YANSIMA_RAPORU.md` |
| Hata yönetimi + bekleme | `src/scrape.py` (`fetch`, `parse_listing`), `tests/` |
| Prompt günlüğü | `docs/PROMPT_GUNLUGU.md` |
| Yansıma raporu | `docs/YANSIMA_RAPORU.md` |
| Bonus: kural dosyası / MCP | `CLAUDE.md`, yansıma raporu "Bonus" bölümü |
