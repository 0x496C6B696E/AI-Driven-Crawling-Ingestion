# Yansıma Raporu

**Araç:** Claude (Anthropic), Claude masaüstü uygulaması üzerinden bilgisayarıma bağlı oturum. **Dil:** Python (requests + BeautifulSoup, pandas, matplotlib) — ödevin önerdiği yığın.

## AI en çok nerede yardımcı oldu?
En büyük katkı, ödevdeki tuzağı baştan görmesiydi: kategori ve stok adedi liste sayfasında yok, her kitabın kendi sayfasından (breadcrumb) alınmalı. İlk sürüm zaten 50 liste sayfasının tamamını `li.next` ile geziyor ve her kitap için detay sayfasına giriyordu; "ilk kod hepsini çekiyor mu?" kontrolünü yapmak zorunda kalmadım. İkinci büyük katkı hata yönetimi iskeletiydi: timeout, 3 tekrar, artan bekleme, kitap başına `try/except`, hem konsola hem dosyaya log. Bunları tek tek yazmak yerine kural dosyasına yazıp AI'a uygulatmak çok zaman kazandırdı. Analizde de istemediğim ama doğru olan bir ekleme yaptı: tek kitaplı kategorileri "en pahalı kategori" listesinden filtreleyip grafikte `n=` gösterdi.

## AI nerede yanıldı veya eksik kaldı?
- **Ortam/ağ:** AI'ın bulut ortamı da, bilgisayarımdaki Claude çalışma ortamı da siteye erişemedi (proxy 403). AI önce bilgisayarımdaki klasöre erişim isteyip orada çalıştırmayı denedi; o da olmayınca veriyi uygulamanın yerleşik tarayıcısında, `scrape.py` ile aynı mantığı JavaScript'e taşıyarak çekti. Dolayısıyla teslimdeki `kitaplar.csv`, Python scripti tarafından değil, aynı seçicileri/bekleme kuralını uygulayan tarayıcı sürümü tarafından üretildi; Python scriptinin parse fonksiyonları gerçek HTML ile ayrıca test edildi (prompt 9). Kendi bilgisayarımda `python scrape.py` çalıştırarak aynı CSV'yi yeniden üretebiliyorum.
- **Tarayıcı zamanlayıcı kısıtlaması:** AI'ın ilk tarayıcı sürümü gizli sekmede Chrome'un 5 dakika sonra devreye giren "intensive throttling" kuralına takıldı ve çekim 20 kat yavaşladı. AI bunu kendi fark etmedi; "neden 1 sayfa 2 dakika sürüyor?" diye sorunca teşhis etti. İlk önerisi (`Atomics.wait`) bu sayfada çalışmadı; ikincisi (Web Worker) çalıştı.
- **Zaman tahmini:** README'ye "~10-12 dakika" yazdı; gerçek süre 11.4 dakika oldu — bu seferlik tuttu ama tahmini test etmeden yazmıştı.

## Sonuçların doğru olduğundan nasıl emin oldum?
1. **Sayı kontrolü:** Script, sitenin ana sayfasında yazan toplam (1000) ile çekilen satır sayısını karşılaştırıyor; sonuç **1000 = 1000**, 50 sayfa, URL'ye göre 1000 benzersiz kayıt (tekrar yok).
2. **Eksik alan sayımı:** Her alan için `None` sayısı basılıyor; **tüm alanlarda 0**, hata listesi boş.
3. **Örnekleme:** CSV'den rastgele birkaç kitabı (ör. "A Light in the Attic", £51.77, 3 yıldız, Poetry) sitede açıp karşılaştırdım.
4. **Tip kontrolü:** `pandas` ile `fiyat` float, `puan` int olarak okunuyor; `puan` yalnızca 1–5 değerlerini içeriyor, 50 kategori var.
5. **Bilinen gerçek:** Bu sitede fiyat ve puanlar rastgele atandığı için puan–fiyat korelasyonunun ~0 çıkması beklenen sonuçtu; **r = 0.028** çıktı (puan gruplarının ortalaması £34.56–£36.09 bandında), bu da parse'ın bozuk olmadığını destekliyor. Puan dağılımı da neredeyse düz (226/196/203/179/196) — rastgele atamayla tutarlı.

## Bir dahaki sefere neyi farklı yapardım?
- 1050 istek × 0.5 sn ≈ 10 dakika. Kategori sayfalarını (50 adet) gezip kitap→kategori eşlemesini oradan çıkarmak, detay sayfalarını atlayıp yalnızca ~100 istekle bitirirdi. Stok adedi için detay sayfası gerekse de "In stock" bilgisi listede var; ödev yalnızca "stok durumu" istediği için bu yeterli olurdu.
- Ortam sorununu (AI sandbox'ının siteye erişememesi) baştan sormak: "Siteye senin ortamından erişim var mı, yoksa benim bilgisayarımda mı çalıştıracaksın?"
- CSV'yi tek seferde yazmak yerine her sayfadan sonra ara kayıt (checkpoint) almak; uzun çalışmada kesinti olursa baştan başlamamak için.

## Bonus: MCP / skill kullanımı
**Ne kullandım:** Üç şey.
1. **Kural/skill dosyası `CLAUDE.md`** (teslime ekli). Claude bu dosyayı proje klasöründe otomatik okur. İçinde "her istekten sonra bekle, timeout+retry, boş alanda None, hem dosyaya hem konsola logla, bitince 1000 ile karşılaştır, PNG'leri Agg backend ile üret" gibi kurallar var.
2. **Tarayıcı MCP'si (Claude masaüstü uygulamasının yerleşik tarayıcısı, `Claude_Browser` araçları):** AI siteyi tarayıcıda açıp önce seçicileri tek bir kitapta doğruladı (breadcrumb, `star-rating Three`, `In stock (22 available)`, toplam `1000`), sonra ağ engeli yüzünden asıl veri çekimini de bu tarayıcı üzerinden yaptı ve CSV'yi oradan aldı.
3. **Dosya sistemi / cihaz MCP'si (`remote-devices`):** AI `Documents` klasörüme erişim istedi; onayladıktan sonra proje dosyalarını `Documents/kitap-scraper` klasörüme yazdı ve oradaki Linux çalışma alanında Python kütüphanelerini kontrol etti.

**Nasıl kurdum:** (1) `CLAUDE.md`'yi proje kök klasörüne koymak yeterli — ek konfigürasyon yok. (2) Tarayıcı: AI'ın `books.toscrape.com` için gönderdiği site erişim isteğini uygulamada onayladım; uygulamanın yan panelindeki tarayıcı sekmesi açıldı. (3) Klasör: AI'ın "klasör erişimi" isteğini onayladım (alternatif: `+` menüsünden "Add folder"); uygulama arka planda izole bir Linux ortamı indirip klasörü bağladı.

**Ne kazandırdı:** Kural dosyası sayesinde her promptta "bekleme ekle, hataları yakala" diye tekrar etmedim; AI ilk seferde doğru iskeleti kurdu. Tarayıcı MCP'si olmasaydı ödev bu ortamda hiç tamamlanamazdı: AI'ın hiçbir shell'i siteye ulaşamıyordu; tarayıcı hem seçicileri gerçek sayfada doğrulamayı hem de 1000 kitabı çekmeyi sağladı. Klasör bağlantısı sayesinde dosyaları kopyala-yapıştır yapmadan doğrudan bilgisayarıma yazdı. Kullanmasaydım: HTML'i elle sohbete yapıştırıp seçici sormam, kodu kendim çalıştırıp hataları yapıştırmam gerekecekti ve AI "çalıştı" dediğinde gerçekten çalışıp çalışmadığını yalnızca ben görebilecektim.
