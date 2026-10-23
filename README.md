# books.toscrape.com Scraper & Analiz

`https://books.toscrape.com` sitesindeki **1000 kitabın** adını, fiyatını, puanını, stok durumunu ve kategorisini çeker, `kitaplar.csv`'ye yazar ve basit bir analiz yapar.

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `scrape.py` | Veri çekme. Tüm liste sayfalarını (50) ve her kitabın detay sayfasını gezer. |
| `analiz.py` | CSV'den grafikleri ve özet metni üretir. |
| `scrape_browser.js` | `scrape.py`'nin tarayıcı konsolu sürümü (aynı mantık). Teslimdeki `kitaplar.csv` bu sürümle, Claude'un yerleşik tarayıcısında çekildi — AI ortamlarından siteye ağ erişimi yoktu (bkz. yansıma raporu). |
| `kitaplar.csv` | Çıktı verisi (1000 satır). |
| `grafik_kategori_fiyat.png` | Kategori başına ortalama fiyat — en pahalı 10 kategori. |
| `grafik_puan_dagilimi.png` | Puan dağılımı (1–5). |
| `grafik_puan_fiyat.png` | Puana göre fiyat kutu grafiği (ek). |
| `analiz_sonuc.txt` | Sayısal özet ve "puanı yüksek kitaplar daha mı pahalı?" cevabı. |
| `scrape.log` | Çalışma logu (hatalar, atlanan sayfalar, özet). |
| `CLAUDE.md` | AI aracına verilen proje kural dosyası (bonus). |
| `PROMPT_GUNLUGU.md` | Kullanılan önemli promptlar ve sonuçları. |
| `YANSIMA_RAPORU.md` | Yansıma raporu. |

## Çalıştırma

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python scrape.py     # ~1050 istek, 0.5 sn bekleme ile yaklaşık 10-12 dakika sürer
python analiz.py     # grafikleri ve analiz_sonuc.txt'yi üretir
```

`scrape.py` bittiğinde çekilen kitap sayısını sitedeki toplamla karşılaştırır; eşleşmezse uyarı verir ve çıkış kodu 1 döner.

## CSV sütunları

`kitap_adi, fiyat (float, £), puan (int 1-5), stok (metin), stok_adedi (int), kategori, url`

## Hata yönetimi ve etik

- Her istek 15 sn timeout + 3 tekrar; açılmayan sayfa loglanıp atlanır.
- Boş alanlar `None`/boş hücre olarak yazılır, program çökmez.
- İstekler arasında 0.5 sn bekleme; tekrar denemelerde artan bekleme.
"# AI-Driven-Crawling-Ingestion" 
