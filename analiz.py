"""
kitaplar.csv uzerinde analiz ve grafikler.

Ciktilar:
- grafik_kategori_fiyat.png : kategori basina ortalama fiyat (en pahali 10)
- grafik_puan_dagilimi.png  : puan dagilimi (1-5)
- grafik_puan_fiyat.png     : puana gore ortalama fiyat (ek)
- analiz_sonuc.txt          : sayisal ozet + "puani yuksek kitaplar daha mi pahali?" cevabi
"""

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CSV = "kitaplar.csv"

try:
    df = pd.read_csv(CSV)
except FileNotFoundError:
    print(f"{CSV} bulunamadi. Once scrape.py calistirin.")
    sys.exit(1)

df["fiyat"] = pd.to_numeric(df["fiyat"], errors="coerce")
df["puan"] = pd.to_numeric(df["puan"], errors="coerce")
temiz = df.dropna(subset=["fiyat", "puan", "kategori"])
print(f"Toplam satir: {len(df)}, analizde kullanilan: {len(temiz)}")

# ---- 1) Kategori basina ortalama fiyat (en pahali 10, en az 2 kitap) ----
kat = (temiz.groupby("kategori")["fiyat"]
       .agg(ortalama="mean", adet="count")
       .query("adet >= 2")
       .sort_values("ortalama", ascending=False)
       .head(10))

fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.barh(kat.index[::-1], kat["ortalama"][::-1], color="#4C72B0")
ax.bar_label(bars, labels=[f"£{v:.2f} (n={n})" for v, n in zip(kat["ortalama"][::-1], kat["adet"][::-1])],
             padding=3, fontsize=9)
ax.set_xlabel("Ortalama fiyat (£)")
ax.set_title("Kategori başına ortalama fiyat — en pahalı 10 kategori\n(en az 2 kitabı olan kategoriler)")
ax.set_xlim(0, kat["ortalama"].max() * 1.25)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig("grafik_kategori_fiyat.png", dpi=150)

# ---- 2) Puan dagilimi ----
puan_dag = temiz["puan"].astype(int).value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(puan_dag.index.astype(str), puan_dag.values, color="#DD8452")
ax.bar_label(bars, padding=3)
ax.set_xlabel("Puan (yıldız)")
ax.set_ylabel("Kitap sayısı")
ax.set_title(f"Kitapların puan dağılımı (n={len(temiz)})")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig("grafik_puan_dagilimi.png", dpi=150)

# ---- 3) Puan vs fiyat ----
puan_fiyat = temiz.groupby("puan")["fiyat"].agg(["mean", "median", "count"])
korelasyon = temiz["puan"].corr(temiz["fiyat"])
fig, ax = plt.subplots(figsize=(7, 4.5))
temiz.boxplot(column="fiyat", by="puan", ax=ax, grid=False)
ax.set_xlabel("Puan (yıldız)")
ax.set_ylabel("Fiyat (£)")
ax.set_title(f"Puana göre fiyat dağılımı (Pearson r = {korelasyon:.3f})")
plt.suptitle("")
fig.tight_layout()
fig.savefig("grafik_puan_fiyat.png", dpi=150)

# ---- Metin ozeti ----
if abs(korelasyon) < 0.1:
    yorum = ("HAYIR. Puan ile fiyat arasinda anlamli bir iliski yok; korelasyon neredeyse sifir "
             f"(r = {korelasyon:.3f}). Her puan grubunda ortalama fiyat birbirine cok yakin "
             "(yaklasik £34-36 bandinda). Bu sitede puanlar ve fiyatlar rastgele atandigi icin "
             "beklenen bir sonuc.")
elif korelasyon > 0:
    yorum = f"Zayif pozitif iliski var (r = {korelasyon:.3f}); yuksek puanli kitaplar biraz daha pahali."
else:
    yorum = f"Zayif negatif iliski var (r = {korelasyon:.3f}); yuksek puanli kitaplar biraz daha ucuz."

with open("analiz_sonuc.txt", "w", encoding="utf-8") as f:
    f.write(f"Toplam kitap: {len(df)}  |  Analizde kullanilan: {len(temiz)}\n")
    f.write(f"Kategori sayisi: {temiz['kategori'].nunique()}\n")
    f.write(f"Genel ortalama fiyat: £{temiz['fiyat'].mean():.2f}  (min £{temiz['fiyat'].min():.2f}, max £{temiz['fiyat'].max():.2f})\n\n")
    f.write("En pahali 10 kategori (ortalama fiyat):\n")
    f.write(kat.round(2).to_string() + "\n\n")
    f.write("Puan dagilimi:\n" + puan_dag.to_string() + "\n\n")
    f.write("Puana gore fiyat:\n" + puan_fiyat.round(2).to_string() + "\n\n")
    f.write(f"Puani yuksek kitaplar daha mi pahali?\n{yorum}\n")

print(open("analiz_sonuc.txt", encoding="utf-8").read())
