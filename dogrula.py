"""Havalimanı tahminini iki yolla karşılaştırır (yerel, dakikada bir alınmış ham veriyle):

1. Anlık görüntü tahmini (sitenin kullandığı): her örnekteki saatlik_hiz toplamlarının ortalaması.
2. İz sayımı: aynı uçağı (icao24) art arda örneklerde izleyip, havalimanına 25 km'den yakın,
   pistin 1200 m altında alçalırken görülen (iniş) ya da 2500 m altında tırmanırken görülen (kalkış)
   farklı uçakları sayar.

Ayrıca DHMİ 2025 yıllık "uçak trafiği"nin (iniş+kalkış) saatlik ortalamasıyla kıyaslar.

    python dogrula.py                       # veri/ham/*.json.gz
"""
from __future__ import annotations

import glob
import gzip
import json
from collections import defaultdict
from pathlib import Path

from ucaklar.cekirdek import HAVALIMANLARI, ayristir, havalimani_durumu, mesafe_km, saatlik_hiz, taze_mi

# DHMİ 2025: İstanbul Havalimanı 549.319, Sabiha Gökçen 274.620 uçak trafiği (iniş+kalkış, yıllık)
DHMI_2025 = {"IST": 549_319, "SAW": 274_620}


def calis(dosyalar: list[str]) -> dict:
    anliklar = []
    iz = {(h.kod, y): set() for h in HAVALIMANLARI for y in ("inis", "kalkis")}
    for f in dosyalar:
        v = json.load(gzip.open(f, "rt"))
        t = v["time"]
        ucaklar = [u for u in ayristir(v) if taze_mi(u, t)]
        tahmin = defaultdict(float)
        for u in ucaklar:
            for h in HAVALIMANLARI:
                d = havalimani_durumu(u, h)
                if d:
                    tahmin[(h.kod, d)] += saatlik_hiz(u.dikey_ms)
                if u.yerde or u.irtifa_m is None or u.dikey_ms is None:
                    continue
                if mesafe_km(u.lat, u.lon, h.lat, h.lon) > 25:
                    continue
                yuk = u.irtifa_m - h.rakim_m
                if u.dikey_ms <= -1.0 and yuk < 1200:
                    iz[(h.kod, "inis")].add(u.icao)
                elif u.dikey_ms >= 2.0 and yuk < 2500:
                    iz[(h.kod, "kalkis")].add(u.icao)
        anliklar.append((t, tahmin))
    t0, t1 = anliklar[0][0], anliklar[-1][0]
    saat = (t1 - t0) / 3600
    sonuc = {"ornek": len(anliklar), "saat": round(saat, 2), "ilk": t0, "son": t1, "satir": {}}
    for anahtar, kume in iz.items():
        ort = sum(a[1][anahtar] for a in anliklar) / len(anliklar)
        sonuc["satir"]["_".join(anahtar)] = {
            "tahmin_saatte": round(ort, 1),
            "iz_saatte": round(len(kume) / saat, 1) if saat else None,
        }
    for kod, yil in DHMI_2025.items():
        sonuc["satir"][kod + "_dhmi2025_saatte_inis+kalkis"] = round(yil / 365 / 24, 1)
    return sonuc


if __name__ == "__main__":
    dosyalar = sorted(glob.glob(str(Path(__file__).parent / "veri" / "ham" / "*.json.gz")))
    print(json.dumps(calis(dosyalar), ensure_ascii=False, indent=1))
