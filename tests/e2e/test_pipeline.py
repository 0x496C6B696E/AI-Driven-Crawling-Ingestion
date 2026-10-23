"""Uçtan uca test: scrape.py (1 sayfa) -> CSV -> analiz.py -> PNG'ler + özet. Ağ gerekir."""
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def run(*args: object) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", cwd=ROOT, env=env, timeout=300)


def test_scrape_then_analyze(tmp_path: Path):
    csv_path, log_path = tmp_path / "kitaplar.csv", tmp_path / "scrape.log"
    charts, out = tmp_path / "charts", tmp_path / "analiz_sonuc.txt"

    r = run(SRC / "scrape.py", "--max-pages", "1", "--out", csv_path, "--log", log_path)
    assert r.returncode == 0, r.stdout + r.stderr

    df = pd.read_csv(csv_path)
    assert len(df) == 20                                   # 1 sayfa = 20 kitap
    assert df["fiyat"].dtype.kind == "f"                   # float
    assert df["puan"].dtype.kind == "i"                    # int
    assert df["puan"].between(1, 5).all()
    assert df["kategori"].notna().all() and df["kitap_adi"].notna().all()
    assert "OZET" in log_path.read_text(encoding="utf-8")  # log dosyası yazıldı

    r = run(SRC / "analiz.py", "--csv", csv_path, "--charts-dir", charts, "--out", out)
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.name for p in charts.glob("*.png")) == [
        "grafik_kategori_fiyat.png", "grafik_puan_dagilimi.png", "grafik_puan_fiyat.png"]
    assert "daha mi pahali" in out.read_text(encoding="utf-8")
