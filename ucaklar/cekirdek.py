"""İstanbul semaları: OpenSky durum vektörlerini okuyup sayan saf fonksiyonlar.

Ağ erişimi yok; hepsi test edilebilir.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# OpenSky'dan istenen kutu (1 kredi: alan < 25 derece kare). Haritada çevre de görünsün diye
# il sınırından geniş.
KUTU = {"lamin": 40.30, "lomin": 27.40, "lamax": 41.95, "lomax": 30.40}

TR = timezone(timedelta(hours=3))  # Türkiye 2016'dan beri yaz saati uygulamıyor

IL_SINIRI = json.loads((Path(__file__).with_name("istanbul.geojson")).read_text())["coordinates"][0]


@dataclass(frozen=True)
class Havalimani:
    kod: str
    ad: str
    lat: float
    lon: float
    rakim_m: float


HAVALIMANLARI = (
    Havalimani("IST", "İstanbul Havalimanı", 41.2753, 28.7519, 99.0),
    Havalimani("SAW", "Sabiha Gökçen", 40.8986, 29.3092, 95.0),
)

# Kalkış/iniş tahmini bölgesi: havalimanına YARICAP_KM'den yakın, pist seviyesinin
# ALT_M ile UST_M üstünde, dikey hızı |ESIK_MS|'den büyük uçaklar.
YARICAP_KM = 22.0
ALT_M = 150.0
UST_M = 1000.0
ESIK_MS = 1.5


@dataclass(frozen=True)
class Ucak:
    icao: str
    cagri: str
    ulke: str
    lat: float
    lon: float
    irtifa_m: float | None  # GNSS (geo) varsa o, yoksa barometrik
    baro_m: float | None
    yerde: bool
    hiz_ms: float | None
    yon: float | None
    dikey_ms: float | None
    son_temas: int
    konum_zamani: int  # konumun en son güncellendiği an; eski konumlar tekrar gelebiliyor
    kategori: int | None


def _f(x):
    return None if x is None else float(x)


def ayristir(veri: dict) -> list[Ucak]:
    """OpenSky /states/all yanıtını Ucak listesine çevirir; konumu olmayanları atar."""
    sonuc = []
    for s in veri.get("states") or []:
        lon, lat = s[5], s[6]
        if lat is None or lon is None:
            continue
        geo, baro = _f(s[13]), _f(s[7])
        sonuc.append(
            Ucak(
                icao=s[0],
                cagri=(s[1] or "").strip(),
                ulke=s[2] or "",
                lat=float(lat),
                lon=float(lon),
                irtifa_m=geo if geo is not None else baro,
                baro_m=baro,
                yerde=bool(s[8]),
                hiz_ms=_f(s[9]),
                yon=_f(s[10]),
                dikey_ms=_f(s[11]),
                son_temas=int(s[4] or 0),
                konum_zamani=int(s[3] or 0),
                kategori=s[17] if len(s) > 17 else None,
            )
        )
    return sonuc


def icinde(lon: float, lat: float, cokgen=IL_SINIRI) -> bool:
    """Işın atma ile nokta-çokgen testi."""
    ic = False
    j = len(cokgen) - 1
    for i in range(len(cokgen)):
        xi, yi = cokgen[i]
        xj, yj = cokgen[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            ic = not ic
        j = i
    return ic


def mesafe_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def havalimani_durumu(u: Ucak, h: Havalimani) -> str | None:
    """'inis', 'kalkis' ya da None. Bölge tanımı yukarıdaki sabitlerde."""
    if u.yerde or u.irtifa_m is None or u.dikey_ms is None:
        return None
    if mesafe_km(u.lat, u.lon, h.lat, h.lon) > YARICAP_KM:
        return None
    yukseklik = u.irtifa_m - h.rakim_m
    if not (ALT_M <= yukseklik <= UST_M):
        return None
    if u.dikey_ms <= -ESIK_MS:
        return "inis"
    if u.dikey_ms >= ESIK_MS:
        return "kalkis"
    return None


def saatlik_hiz(dikey_ms: float) -> float:
    """Bir uçağın bu anlık görüntüde saatlik iniş/kalkış sayısına katkısı.

    Uçak (UST_M - ALT_M) metrelik dilimi |dikey_ms| hızla W = dilim/|v| saniyede geçer.
    Rastgele bir anda bölgede görülme olasılığı W/T olduğundan, her görülen uçağı
    T/W ile tartmak saatlik geçiş sayısının yansız tahminidir (Little yasası).
    """
    return abs(dikey_ms) * 3600.0 / (UST_M - ALT_M)


IRTIFA_KATMANLARI = ((0, 3000, "alcak"), (3000, 8000, "orta"), (8000, 99999, "yuksek"))


def katman(irtifa_m: float | None) -> str:
    if irtifa_m is None:
        return "bilinmiyor"
    for a, b, ad in IRTIFA_KATMANLARI:
        if a <= irtifa_m < b:
            return ad
    return "yuksek"


TAZELIK_SN = 30  # konumu bundan eski uçaklar sayılmaz


def taze_mi(u: Ucak, t: int) -> bool:
    return t - u.konum_zamani <= TAZELIK_SN


def ornek_ozeti(veri: dict, kalan_kredi: int | None = None) -> dict:
    """Bir anlık görüntüden tarihçeye yazılacak tek satır."""
    ucaklar = ayristir(veri)
    t = int(veri.get("time") or 0)
    taze = [u for u in ucaklar if taze_mi(u, t)]
    il = [u for u in taze if icinde(u.lon, u.lat)]
    havada = [u for u in il if not u.yerde]
    satir = {
        "t": t,
        "havada": len(havada),
        "yerde": len(il) - len(havada),
        "kutuda": len(taze),
        **{k: sum(1 for u in havada if katman(u.irtifa_m) == k) for _, _, k in IRTIFA_KATMANLARI},
    }
    for h in HAVALIMANLARI:
        for yon in ("inis", "kalkis"):
            secili = [u for u in taze if havalimani_durumu(u, h) == yon]
            satir[f"{h.kod}_{yon}_n"] = len(secili)
            satir[f"{h.kod}_{yon}_saat"] = round(sum(saatlik_hiz(u.dikey_ms) for u in secili), 2)
    if kalan_kredi is not None:
        satir["kredi"] = kalan_kredi
    return satir


def harita_verisi(veri: dict) -> dict:
    """Tarayıcıya gidecek sade anlık görüntü."""
    ucaklar = ayristir(veri)
    t = int(veri.get("time") or 0)
    liste = []
    for u in ucaklar:
        if not taze_mi(u, t):
            continue
        durum = None
        for h in HAVALIMANLARI:
            d = havalimani_durumu(u, h)
            if d:
                durum = f"{h.kod}_{d}"
        liste.append(
            {
                "c": u.cagri,
                "u": u.ulke,
                "la": round(u.lat, 4),
                "lo": round(u.lon, 4),
                "a": None if u.irtifa_m is None else round(u.irtifa_m),
                "h": None if u.hiz_ms is None else round(u.hiz_ms * 3.6),
                "y": None if u.yon is None else round(u.yon),
                "v": None if u.dikey_ms is None else round(u.dikey_ms, 1),
                "g": u.yerde,
                "i": icinde(u.lon, u.lat),
                "d": durum,
            }
        )
    return {"t": t, "ucaklar": liste}


# --- Gün / gece: NOAA güneş denklemi (dakika hassasiyeti yeter) -----------------

def gunes_yuksekligi(t_utc: datetime, lat: float = 41.01, lon: float = 28.98) -> float:
    """Güneşin ufuktan yüksekliği (derece)."""
    gun = t_utc.timetuple().tm_yday
    saat = t_utc.hour + t_utc.minute / 60 + t_utc.second / 3600
    g = 2 * math.pi / 365 * (gun - 1 + (saat - 12) / 24)
    denk = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                     - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    egim = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    gercek = saat * 60 + denk + 4 * lon
    aci = math.radians(gercek / 4 - 180)
    la = math.radians(lat)
    cos_z = math.sin(la) * math.sin(egim) + math.cos(la) * math.cos(egim) * math.cos(aci)
    return 90 - math.degrees(math.acos(max(-1, min(1, cos_z))))


def gece_mi(t: int) -> bool:
    """Güneş ufkun altındaysa gece (−0,833°: kırılma ve güneş yarıçapı)."""
    return gunes_yuksekligi(datetime.fromtimestamp(t, timezone.utc)) < -0.833
