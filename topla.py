"""Bir anlık görüntü al: OpenSky'dan İstanbul çevresini çek, tarihçeye bir satır ekle,
site/veri/son.json'u yaz.

    python topla.py            # bir kez
    python topla.py --dongu 60 --sure 180   # 60 sn'de bir, 180 dk boyunca (yerel doğrulama)
    python topla.py --ham      # ham yanıtı veri/ham/ altına da sakla (git'e girmez)
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ucaklar.cekirdek import KUTU, TR, harita_verisi, ornek_ozeti

KOK = Path(__file__).parent
ORNEKLER = KOK / "veri" / "ornekler"
HAM = KOK / "veri" / "ham"
SON = KOK / "site" / "veri" / "son.json"
URL = "https://opensky-network.org/api/states/all?" + urllib.parse.urlencode(KUTU) + "&extended=1"
AJAN = "istanbul-semalari/1.0 (+https://github.com/birtohum/istanbul-semalari)"


def cek(deneme: int = 3) -> tuple[dict, int | None]:
    son_hata = None
    for i in range(deneme):
        try:
            istek = urllib.request.Request(URL, headers={"User-Agent": AJAN})
            with urllib.request.urlopen(istek, timeout=30) as y:
                kalan = y.headers.get("X-Rate-Limit-Remaining")
                return json.load(y), (int(kalan) if kalan is not None else None)
        except urllib.error.HTTPError as e:
            son_hata = f"HTTP {e.code}"
            if e.code == 429:  # kota bitti; tekrar denemek boşuna kredi yakmaz ama anlamsız
                break
        except Exception as e:  # zaman aşımı, DNS, bağlantı reddi
            son_hata = type(e).__name__ + ": " + str(e)[:120]
        time.sleep(5 * (i + 1))
    raise RuntimeError(son_hata)


def bir_kez(ham: bool = False, klasor: Path = ORNEKLER, harita_yaz: bool = True) -> dict:
    simdi = int(time.time())
    gun = datetime.fromtimestamp(simdi, TR).strftime("%Y-%m-%d")
    klasor.mkdir(parents=True, exist_ok=True)
    try:
        veri, kalan = cek()
    except RuntimeError as e:
        satir = {"t": simdi, "hata": str(e)}
    else:
        satir = ornek_ozeti(veri, kalan)
        if not satir["t"]:
            satir["t"] = simdi
        if harita_yaz:
            harita = harita_verisi(veri)
            harita["ozet"] = satir
            SON.parent.mkdir(parents=True, exist_ok=True)
            SON.write_text(json.dumps(harita, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if ham:
            HAM.mkdir(parents=True, exist_ok=True)
            with gzip.open(HAM / f"{satir['t']}.json.gz", "wt", encoding="utf-8") as f:
                json.dump(veri, f)
    with open(klasor / f"{gun}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False, separators=(",", ":")) + "\n")
    return satir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dongu", type=int, default=0, help="saniye; 0 = bir kez")
    p.add_argument("--sure", type=int, default=0, help="dakika")
    p.add_argument("--ham", action="store_true")
    p.add_argument("--dogrulama", action="store_true",
                   help="yerel doğrulama: satırları veri/dogrulama/'ya yaz, son.json'a dokunma, ham yanıtı sakla")
    a = p.parse_args()
    bitis = time.time() + a.sure * 60
    while True:
        bas = time.time()
        s = bir_kez(a.ham or a.dogrulama, KOK / "veri" / "dogrulama" if a.dogrulama else ORNEKLER, not a.dogrulama)
        print(datetime.now(TR).strftime("%H:%M:%S"), json.dumps(s, ensure_ascii=False), flush=True)
        if not a.dongu or time.time() >= bitis or s.get("kredi") == 0:
            break
        time.sleep(max(1, a.dongu - (time.time() - bas)))


if __name__ == "__main__":
    main()
