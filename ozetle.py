"""veri/ornekler/*.jsonl → site/veri/ozet.json (sitenin tarihçe bölümü)."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from ucaklar.cekirdek import HAVALIMANLARI, TR, gece_mi

KOK = Path(__file__).parent
ORNEKLER = KOK / "veri" / "ornekler"
CIKTI = KOK / "site" / "veri" / "ozet.json"
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
HAREKET = [f"{h.kod}_{y}" for h in HAVALIMANLARI for y in ("inis", "kalkis")]
GUN_ESIK_SAAT = 18  # bir günün toplam tahmini için en az bu kadar farklı saatte örnek


def oku(klasor: Path = ORNEKLER) -> list[dict]:
    satirlar = []
    for p in sorted(klasor.glob("*.jsonl")):
        for s in p.read_text(encoding="utf-8").splitlines():
            if s.strip():
                satirlar.append(json.loads(s))
    satirlar.sort(key=lambda s: s["t"])
    return satirlar


def _ort(xs, basamak=1):
    return round(mean(xs), basamak) if xs else None


def ozetle(satirlar: list[dict]) -> dict:
    iyi = [s for s in satirlar if "hata" not in s]
    hatali = len(satirlar) - len(iyi)
    if not iyi:
        return {"ornek": 0, "hatali": hatali}

    saat = defaultdict(list)
    gun = defaultdict(list)
    gece = {True: [], False: []}
    saat_hareket = {k: defaultdict(list) for k in HAREKET}
    takvim = defaultdict(list)
    for s in iyi:
        z = datetime.fromtimestamp(s["t"], TR)
        saat[z.hour].append(s)
        gun[z.weekday()].append(s)
        gece[gece_mi(s["t"])].append(s["havada"])
        takvim[z.strftime("%Y-%m-%d")].append(s)
        for k in HAREKET:
            saat_hareket[k][z.hour].append(s[f"{k}_saat"])

    gunluk = []
    for g, ss in sorted(takvim.items()):
        saatler = {datetime.fromtimestamp(s["t"], TR).hour for s in ss}
        kayit = {"gun": g, "ornek": len(ss), "saat_kapsami": len(saatler), "havada_ort": _ort([s["havada"] for s in ss])}
        if len(saatler) >= GUN_ESIK_SAAT:
            # saat başına ortalama al, sonra 24 saatle topla: örneklerin saatlere eşit dağılmamasını dengeler
            for k in HAREKET:
                saatlik = defaultdict(list)
                for s in ss:
                    saatlik[datetime.fromtimestamp(s["t"], TR).hour].append(s[f"{k}_saat"])
                kayit[k] = round(mean(mean(v) for v in saatlik.values()) * 24)
        gunluk.append(kayit)

    en = max(iyi, key=lambda s: s["havada"])
    aralik = [b["t"] - a["t"] for a, b in zip(iyi, iyi[1:])]
    aralik.sort()
    return {
        "uretim": int(datetime.now(TR).timestamp()),
        "ilk": iyi[0]["t"],
        "son": iyi[-1]["t"],
        "ornek": len(iyi),
        "hatali": hatali,
        "aralik_medyan_sn": aralik[len(aralik) // 2] if aralik else None,
        "en_buyuk_bosluk_sn": aralik[-1] if aralik else None,
        "havada_ort": _ort([s["havada"] for s in iyi]),
        "en_kalabalik": {"t": en["t"], "havada": en["havada"]},
        "saat": [
            {"saat": h, "ornek": len(saat[h]), "havada": _ort([s["havada"] for s in saat[h]]),
             "gece": _ort([1 if gece_mi(s["t"]) else 0 for s in saat[h]], 2),
             **{k: _ort(saat_hareket[k][h]) for k in HAREKET}}
            for h in range(24)
        ],
        "gun": [{"gun": GUNLER[d], "ornek": len(gun[d]), "havada": _ort([s["havada"] for s in gun[d]])} for d in range(7)],
        "gece": {"ornek": len(gece[True]), "havada": _ort(gece[True])},
        "gunduz": {"ornek": len(gece[False]), "havada": _ort(gece[False])},
        "katman": {k: _ort([s[k] for s in iyi]) for k in ("alcak", "orta", "yuksek")},
        "gunluk": gunluk,
    }


def main():
    o = ozetle(oku())
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(o, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{o['ornek']} örnek, {o['hatali']} hatalı -> {CIKTI}")


if __name__ == "__main__":
    main()
