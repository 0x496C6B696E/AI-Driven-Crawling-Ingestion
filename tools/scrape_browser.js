// scrape.py'nin tarayıcı (DevTools konsolu) sürümü.
// Neden var: AI'ın çalışma ortamlarından siteye ağ erişimi yoktu; veri, Claude'un yerleşik
// tarayıcısında bu kod çalıştırılarak çekildi. Mantık scrape.py ile birebir aynı:
// aynı seçiciler, her istekten sonra 0.5 sn bekleme, 3 tekrar, hata listesi, kitap başına try/catch.
// Bekleme bir Web Worker içinde yapılır; çünkü Chrome gizli sekmelerde sayfa zamanlayıcılarını
// 5 dakikadan sonra dakikada bire kısar, worker zamanlayıcılarını kısmaz.
//
// Kullanım: https://books.toscrape.com açıkken konsola yapıştırın. Bitince window.__done = true,
// veri window.__rows içinde; CSV için alttaki toCsv() fonksiyonunu çağırın.

window.__rows = []; window.__errors = []; window.__pages = 0; window.__done = false; window.__t0 = Date.now();
const RATING = { One: 1, Two: 2, Three: 3, Four: 4, Five: 5 };

const workerSrc = `
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function get(url) {
  for (let i = 1; i <= 3; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) { const t = await r.text(); await sleep(500); return t; }
      if (r.status === 404) break;
    } catch (e) {}
    await sleep(500 * i);
  }
  return null;
}
onmessage = async (e) => { const html = await get(e.data.url); postMessage({ id: e.data.id, url: e.data.url, html }); };
`;
const worker = new Worker(URL.createObjectURL(new Blob([workerSrc], { type: 'text/javascript' })));
const pending = new Map(); let seq = 0;
const fetchHtml = url => new Promise(res => { const id = ++seq; pending.set(id, res); worker.postMessage({ id, url }); });
worker.onmessage = e => { const r = pending.get(e.data.id); pending.delete(e.data.id); r(e.data.html); };
worker.onerror = e => window.__errors.push('workererr:' + e.message);
const parse = html => new DOMParser().parseFromString(html, 'text/html');

(async () => {
  let url = 'https://books.toscrape.com/catalogue/page-1.html';
  while (url) {
    const html = await fetchHtml(url); window.__pages++;
    if (!html) {  // liste sayfası açılmadı: logla, bir sonrakini dene
      window.__errors.push(url);
      const m = url.match(/page-(\d+)\.html/);
      url = m && +m[1] < 200 ? `https://books.toscrape.com/catalogue/page-${+m[1] + 1}.html` : null;
      continue;
    }
    const doc = parse(html);
    for (const art of doc.querySelectorAll('article.product_pod')) {
      try {
        const a = art.querySelector('h3 a');
        const durl = new URL(a.getAttribute('href'), url).href;
        const pm = (art.querySelector('p.price_color')?.textContent || '').match(/[\d.]+/);
        const rc = [...(art.querySelector('p.star-rating')?.classList || [])].find(c => RATING[c]);
        const dh = await fetchHtml(durl);
        let kategori = null, stok = null, stok_adedi = null;
        if (dh) {
          const d = parse(dh);
          const cr = d.querySelectorAll('ul.breadcrumb li a');
          if (cr.length >= 3) kategori = cr[2].textContent.trim();
          const st = d.querySelector('p.instock.availability');
          if (st) { stok = st.textContent.replace(/\s+/g, ' ').trim(); const sm = stok.match(/\((\d+) available\)/); stok_adedi = sm ? +sm[1] : null; }
        } else window.__errors.push(durl);
        window.__rows.push({ kitap_adi: a.title || null, fiyat: pm ? +pm[0] : null, puan: rc ? RATING[rc] : null, stok, stok_adedi, kategori, url: durl });
      } catch (e) { window.__errors.push('parse:' + e.message); }
    }
    const nx = doc.querySelector('li.next a');
    url = nx ? new URL(nx.getAttribute('href'), url).href : null;
  }
  window.__done = true; window.__secs = (Date.now() - window.__t0) / 1000;
})();

function toCsv() {
  const cols = ['kitap_adi', 'fiyat', 'puan', 'stok', 'stok_adedi', 'kategori', 'url'];
  const q = v => { if (v == null) return ''; const s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  return [cols.join(','), ...window.__rows.map(r => cols.map(c => q(r[c])).join(','))].join('\n');
}
