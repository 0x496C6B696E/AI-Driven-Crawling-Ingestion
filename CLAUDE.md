# Proje kuralları — books.toscrape.com scraping ödevi

Bu dosya AI kodlama aracına (Claude) projeye özel talimat verir. Her oturumda otomatik okunur.

## Scraping kuralları
- Her HTTP isteğinden sonra **en az 0.5 saniye** bekle (`time.sleep`). Asla paralel/çok iş parçacıklı istek atma.
- Her isteğe `timeout` ver (15 sn) ve en fazla 3 kez tekrar dene; yine olmazsa **logla ve atla**, programı çökertme.
- Boş veya beklenmeyen alanlarda `None` yaz, exception fırlatma. `try/except` bloğu her kitabı ayrı sarmalı: bir kitap bozuksa diğerleri etkilenmesin.
- Tanımlayıcı bir `User-Agent` kullan.
- Hem konsola hem `scrape.log` dosyasına logla.

## Veri kuralları
- Çıktı dosyası: `kitaplar.csv`, UTF-8, başlık satırı var.
- `fiyat` float olmalı (`£51.77` → `51.77`), `puan` int olmalı (`Three` → `3`).
- Kategori liste sayfasında yok; kitabın **detay sayfasındaki breadcrumb**'dan al.
- İş bitince çekilen kitap sayısını sitenin ana sayfasında yazan toplamla (**1000**) karşılaştır ve farklıysa uyar.

## Analiz kuralları
- pandas + matplotlib kullan; grafikleri PNG olarak kaydet (`Agg` backend, GUI açma).
- Kategori ortalamalarında tek kitaplı kategorileri yanıltıcı olduğu için filtrele ve etikette n göster.

## Genel
- Dil: Python 3.10+, bağımlılıklar `requirements.txt`'de.
- Kodu Türkçe yorumlarla açıkla; değişken adları Türkçe olabilir.
- Kullanıcıya "çalıştı" demeden önce gerçekten çalıştır ve çıktıyı doğrula.
