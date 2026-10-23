"""
data/kitaplar.csv üzerinde analiz ve grafikler.

Çıktılar (varsayılan yollar):
- charts/grafik_kategori_fiyat.png : kategori başına ortalama fiyat (en pahalı 10)
- charts/grafik_puan_dagilimi.png  : puan dağılımı (1-5)
- charts/grafik_puan_fiyat.png     : puana göre fiyat kutu grafiği (ek)
- docs/analiz_sonuc.txt            : sayısal özet + "puanı yüksek kitaplar daha mı pahalı?" cevabı

Kullanım:
    python src/analiz.py
    python src/analiz.py --csv x.csv --charts-dir out/ --out out/analiz_sonuc.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # GUI açma, PNG'ye yaz
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "kitaplar.csv"
DEFAULT_CHARTS = ROOT / "charts"
DEFAULT_OUT = ROOT / "docs" / "analiz_sonuc.txt"


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="kitaplar.csv analizi")
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--charts-dir", type=Path, default=DEFAULT_CHARTS)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolunda £ bozulmasın

    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        print(f"{args.csv} bulunamadi. Once src/scrape.py calistirin.")
        return 1
    args.charts_dir.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    df["fiyat"] = pd.to_numeric(df["fiyat"], errors="coerce")
    df["puan"] = pd.to_numeric(df["puan"], errors="coerce")
    temiz = df.dropna(subset=["fiyat", "puan", "kategori"])
    print(f"Toplam satir: {len(df)}, analizde kullanilan: {len(temiz)}")

    # ---- 1) Kategori başına ortalama fiyat (en pahalı 10; tek kitaplı kategoriler yanıltıcı, filtrele) ----
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
    ax.set_xlim(0, (kat["ortalama"].max() if len(kat) else 1.0) * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(args.charts_dir / "grafik_kategori_fiyat.png", dpi=150)

    # ---- 2) Puan dağılımı ----
    puan_dag = temiz["puan"].astype(int).value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(puan_dag.index.astype(str), puan_dag.values, color="#DD8452")
    ax.bar_label(bars, padding=3)
    ax.set_xlabel("Puan (yıldız)")
    ax.set_ylabel("Kitap sayısı")
    ax.set_title(f"Kitapların puan dağılımı (n={len(temiz)})")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(args.charts_dir / "grafik_puan_dagilimi.png", dpi=150)

    # ---- 3) Puan vs fiyat (ek) ----
    puan_fiyat = temiz.groupby("puan")["fiyat"].agg(["mean", "median", "count"])
    korelasyon = temiz["puan"].corr(temiz["fiyat"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    temiz.boxplot(column="fiyat", by="puan", ax=ax, grid=False)
    ax.set_xlabel("Puan (yıldız)")
    ax.set_ylabel("Fiyat (£)")
    ax.set_title(f"Puana göre fiyat dağılımı (Pearson r = {korelasyon:.3f})")
    plt.suptitle("")
    fig.tight_layout()
    fig.savefig(args.charts_dir / "grafik_puan_fiyat.png", dpi=150)

    # ---- Metin özeti ----
    if abs(korelasyon) < 0.1:
        yorum = ("HAYIR. Puan ile fiyat arasinda anlamli bir iliski yok; korelasyon neredeyse sifir "
                 f"(r = {korelasyon:.3f}). Her puan grubunda ortalama fiyat birbirine cok yakin "
                 "(yaklasik £34-36 bandinda). Bu sitede puanlar ve fiyatlar rastgele atandigi icin "
                 "beklenen bir sonuc.")
    elif korelasyon > 0:
        yorum = f"Zayif pozitif iliski var (r = {korelasyon:.3f}); yuksek puanli kitaplar biraz daha pahali."
    else:
        yorum = f"Zayif negatif iliski var (r = {korelasyon:.3f}); yuksek puanli kitaplar biraz daha ucuz."

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"Toplam kitap: {len(df)}  |  Analizde kullanilan: {len(temiz)}\n")
        f.write(f"Kategori sayisi: {temiz['kategori'].nunique()}\n")
        f.write(f"Genel ortalama fiyat: £{temiz['fiyat'].mean():.2f}  "
                f"(min £{temiz['fiyat'].min():.2f}, max £{temiz['fiyat'].max():.2f})\n\n")
        f.write("En pahali 10 kategori (ortalama fiyat):\n")
        f.write(kat.round(2).to_string() + "\n\n")
        f.write("Puan dagilimi:\n" + puan_dag.to_string() + "\n\n")
        f.write("Puana gore fiyat:\n" + puan_fiyat.round(2).to_string() + "\n\n")
        f.write(f"Puani yuksek kitaplar daha mi pahali?\n{yorum}\n")

    print(args.out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
