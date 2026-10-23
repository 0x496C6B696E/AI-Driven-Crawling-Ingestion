# Prompt Günlüğü

Araç: **Claude (Anthropic).** İlk oturum: Claude masaüstü uygulaması, bilgisayarıma bağlı bulut çalışma alanı (prompt 1–10). Son oturum: **Claude Code (VS Code eklentisi)**, doğrudan bilgisayarımdaki proje klasöründe (prompt 11–12).

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

### 11. Yerel makinede gerçek çalıştırma (Claude Code, VS Code)
**Prompt:** (ödev metni) *"Ödev bu, başla; bitince git'e gönder."*
**AI ne üretti:** Repodaki mevcut durumu okudu ve ilk oturumdaki eksiği (CSV'nin Python scripti yerine tarayıcı sürümüyle çekilmiş olması) tespit etti. Bu makinede `python` komutunun Microsoft Store yönlendirmesine takıldığını, `python3.12`'nin çalıştığını ve siteye erişimin olduğunu (HTTP 200, ana sayfada toplam 1000) doğruladı. Önce 2 istekli bir canlı sanity testi yaptı (`page-50` → `next = None`, "Frankenstein 38.0 2"), sonra `scrape.py`'yi gerçek olarak çalıştırdı.
**Çalıştı mı:** Evet. 50 sayfa, **1000 / 1000** kitap, 13 dk 20 sn, 0 uyarı / 0 hata, hiç boş alan yok (`logs/scrape.log`). Python çıktısı, ilk oturumda tarayıcıdan çekilen CSV ile pandas'la karşılaştırıldı: 1000 URL eşleşti, 6 alanın hiçbirinde fark yok, **iki dosya birebir aynı**. Grafikler ve `analiz_sonuc.txt` yeni CSV'den yeniden üretildi (aynı sonuçlar: r = 0.028).

### 12. Klasör yapısı + test katmanları
**Prompt:** *"Klasör yapısını yeniden düzenle ve maksimum profesyonel yap: loglar ve doclar ayrı klasörlerde; charts, .gitignore, data, tests (e2e, integration) ve tools klasörleri; README daha detaylı; sonunda commit + push."*
**AI ne üretti:** `src/ data/ charts/ logs/ docs/ tools/ tests/{unit,integration,e2e}` yapısı (dosyalar `git mv` ile taşındı, geçmiş korundu). Scriptlere `--out / --log / --max-pages / --delay` seçenekleri (e2e testin geçici klasöre 1 sayfa çekebilmesi için), `parse_detail`'i ağsız test edilebilsin diye `parse_detail_soup` ve `site_total` yardımcılarına ayırma. 8 birim + 4 entegrasyon + 1 uçtan uca test, `pytest.ini`, `requirements-dev.txt`, `.gitignore`, bölümlü README.
**Çalışmadı → düzeltme:** `src/scrape.py`'yi bash heredoc ile yazarken kabuk hatası aldı (*unexpected EOF while looking for matching quote*) ve dosya hiç oluşmadı; AI bunu `ls` ile fark edip dosyayı doğrudan yazma aracıyla oluşturdu. `--delay 0` verilebiliyordu; CLAUDE.md'deki "en az 0.5 sn" kuralına uysun diye alt sınır 0.5'e sabitlendi. Windows konsolunda `£` karakteri `�` görünüyordu (dosya UTF-8 ve doğruydu); `sys.stdout.reconfigure(encoding="utf-8")` ile düzeltildi. Sonuç: **13 / 13 test geçti** (unit 0.07 sn; integration + e2e 21.8 sn).
