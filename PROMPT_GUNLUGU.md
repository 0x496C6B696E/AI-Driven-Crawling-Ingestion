# Prompt Günlüğü

Araç: **Claude (Anthropic) — Claude masaüstü uygulaması, bilgisayarıma bağlı oturum.** Kod bulut çalışma alanında yazıldı, bilgisayarımdaki `Documents/kitap-scraper` klasöründe çalıştırıldı.

Aşağıda kullandığım en önemli promptlar, AI'ın ürettiği, çalışıp çalışmadığı ve nasıl düzelttiğim var.

---

### 1. Ödev metninin tamamını yapıştırdım
**Prompt:** (ödev metni) *"Bu ödevi yap."*
**AI ne üretti:** Önce görevleri 4 adıma böldü (scraper, çalıştırma/doğrulama, analiz, belgeler) ve bir görev listesi açtı. Başlamadan önce kendi ortamından siteye erişimi denedi.
**Çalıştı mı:** Kısmen. AI'ın bulut ortamından `books.toscrape.com` proxy tarafından engellendi (403). AI bunu fark edip kodu **benim bilgisayarımda** çalıştırmayı önerdi ve `Documents` klasörüne erişim istedi.
**Düzeltme:** Klasör erişimini onayladım; bu sayede scraper gerçek ağ üzerinden çalıştı.

### 2. Scraper'ın ilk yazımı
**Prompt (AI'ın kendi planı + benim kısıtım):** *"requests + BeautifulSoup ile tüm sayfaları gez, her istekten sonra 0.5 sn bekle, bir sayfa açılmazsa çökme."*
**AI ne üretti:** `scrape.py`: `fetch()` fonksiyonu (timeout 15 sn, 3 tekrar, 404'te vazgeç, artan bekleme), liste sayfasından `li.next a` ile sayfalama, her kitap için `try/except`.
**Çalıştı mı:** Evet. Önemli olan, AI'ın **kategori bilgisinin liste sayfasında olmadığını** baştan fark edip her kitabın detay sayfasını (breadcrumb'ın 3. öğesi) çekmesiydi — ödev ipucundaki tuzak buydu.
**Not:** Bu, 50 istek yerine ~1050 istek demek; 0.5 sn beklemeyle ~10 dk sürüyor. AI bunu README'ye yazdı.

### 3. Encoding sorunu (Â£ karakteri)
**Prompt:** *"Fiyat sütununda `Â£` gibi bozuk karakterler olabilir mi? Site latin-1 başlığı gönderiyor."*
**AI ne üretti:** `resp.encoding = resp.apparent_encoding` satırını ekledi; ayrıca fiyat zaten regex ile `[\d.]+` olarak parse edildiği için sembolün CSV'ye hiç girmediğini açıkladı.
**Çalıştı mı:** Evet; kitap adlarında da (örn. "It's Only the Himalayas") özel karakterler doğru çıktı.

### 4. Puanın sayıya çevrilmesi
**Prompt:** *"Puan `<p class="star-rating Three">` şeklinde geliyor, 1-5 sayı olmalı."*
**AI ne üretti:** `RATING_MAP = {"One":1,...}` sözlüğü ve class listesi üzerinde arama yapan `parse_rating()`; sınıf bulunamazsa `None`.
**Çalıştı mı:** Evet. CSV'de `puan` sütunu tamamen 1-5 tam sayı.

### 5. Sayı doğrulaması
**Prompt:** *"Çekilen kitap sayısını sitede yazan toplamla karşılaştır; eşleşmezse uyar."*
**AI ne üretti:** Ana sayfadaki `form.form-horizontal strong` etiketinden `1000` değerini okuyup `len(tum_kitaplar)` ile karşılaştıran, eşleşmezse `exit code 1` dönen kontrol.
**Çalıştı mı:** Evet — sonuç **1000 / 1000**, 50 sayfa, 0 hata, hiç boş alan yok.

### 6. Analiz ve grafikler
**Prompt:** *"kitaplar.csv'den: en pahalı 10 kategori (ortalama fiyat) ve puan dağılımı grafiklerini PNG olarak üret; 'puanı yüksek kitaplar daha mı pahalı?' sorusunu sayıyla cevapla."*
**AI ne üretti:** `analiz.py`: iki bar grafiği + ek bir kutu grafiği, Pearson korelasyonu, `analiz_sonuc.txt`.
**Çalıştı mı:** İlk sürümde `matplotlib` sunucu/başsız ortamda pencere açmaya çalışabilirdi; AI `matplotlib.use("Agg")` ile çözdü. Ayrıca tek kitaplı kategorilerin ortalamayı yanıltacağını söyleyip `adet >= 2` filtresi ve etiketlerde `n=` ekledi — bunu ben istememiştim, iyi bir ekleme oldu.

### 7. Kural dosyası (bonus)
**Prompt:** *"Bu projeye özel bir kural dosyası yaz: bekleme ekle, hataları logla, CSV'ye yaz, sayıyı doğrula."*
**AI ne üretti:** `CLAUDE.md` — scraping, veri ve analiz kuralları.
**Çalıştı mı:** Evet; sonraki promptlarda AI bu kurallara (ör. "çalıştı demeden önce gerçekten çalıştır") uydu.

### 8. Çalıştırma: ağ engeli ve tarayıcıya geçiş
**Prompt:** *"Bilgisayarımda çalıştır, logu göster."*
**AI ne üretti / sonuç:** Bilgisayarımdaki Claude çalışma ortamı da siteye erişemedi (`curl: Received HTTP code 403 from proxy`). AI bunu bildirdi ve veriyi uygulamanın **yerleşik tarayıcısı** üzerinden çekmeyi önerdi: siteyi tarayıcıda açtı, JavaScript ile `scrape.py`'deki aynı mantığı (aynı seçiciler, 0.5 sn bekleme, 3 tekrar, hata listesi) sayfa içinde çalıştırdı.
**Çalışmadı → düzeltme:** İlk denemede araç 45 sn'de zaman aşımına uğradı (script arka planda devam etti). İkinci sorun: tarayıcı sekmesi gizliyken Chrome, 5 dakikadan sonra `setTimeout`'u dakikada bire kısıyor; çekim 1 sayfa/2 dk'ya düştü. AI önce `Atomics.wait` denedi (`SharedArrayBuffer is not defined` hatası), sonra beklemeyi bir **Web Worker** içine taşıdı (worker zamanlayıcıları kısıtlanmıyor). Bu sürüm 1000 kitabı **681 saniyede** (istek başına ~0.65 sn) hatasız çekti.

### 9. Python parse fonksiyonlarının gerçek HTML ile testi
**Prompt:** *"scrape.py'deki parse fonksiyonlarını gerçek bir liste ve detay sayfasıyla test et."*
**AI ne üretti:** Tarayıcıdan `page-50.html` ve bir detay sayfasının HTML'ini alıp `parse_price`, `parse_rating`, `parse_stock_count`, `next_page_url` ve breadcrumb mantığını BeautifulSoup ile çalıştırdı.
**Çalıştı mı:** Evet: son sayfada `next = None`, "Frankenstein 38.0 2", kategori "Travel", stok 19. Yani Python kodu ile tarayıcıda çalışan kod aynı sonuçları veriyor.

### 10. CSV doğrulaması
**Prompt:** *"CSV'yi pandas ile aç; satır sayısı, tipler, boş değerler, puan değerleri ve kategori sayısını göster."*
**AI ne üretti:** `(1000, 7)`, `fiyat float64`, `puan int64`, tüm sütunlarda 0 boş değer, puan yalnızca 1–5, 50 kategori. Rastgele bir kitabı ("It's Only the Himalayas", £45.17, 2 yıldız, Travel) siteyle karşılaştırdı.
**Çalıştı mı:** Evet.
