import random
from datetime import datetime

from ozetle import ozetle
from ucaklar.cekirdek import (
    ALT_M, HAVALIMANLARI, iz_guncelle, TR, UST_M, Ucak, ayristir, gece_mi, havalimani_durumu, icinde,
    ornek_ozeti, saatlik_hiz,
)

IST, SAW = HAVALIMANLARI


def durum(icao="abc", lat=41.0, lon=29.0, baro=1000.0, yerde=False, dikey=0.0, geo=None, temas=100):
    # OpenSky sırası: icao24, callsign, origin_country, time_position, last_contact, lon, lat,
    # baro_altitude, on_ground, velocity, true_track, vertical_rate, sensors, geo_altitude, ...
    return [icao, "THY1  ", "Turkey", temas, temas, lon, lat, baro, yerde, 80.0, 90.0, dikey,
            None, geo, None, False, 0, 0]


def ucak(**kw):
    return ayristir({"time": 100, "states": [durum(**kw)]})[0]


def test_il_siniri():
    assert icinde(28.985, 41.037)          # Taksim
    assert icinde(29.31, 40.90)            # Sabiha Gökçen
    assert icinde(28.75, 41.27)            # İstanbul Havalimanı
    assert not icinde(32.85, 39.93)        # Ankara
    assert not icinde(29.06, 40.18)        # Bursa
    assert not icinde(27.5, 41.0)          # Tekirdağ tarafı


def test_ayristir_konumsuzu_atar_ve_geo_irtifayi_secer():
    v = {"time": 100, "states": [durum(baro=1000, geo=1100), durum(icao="x", lat=None)]}
    u = ayristir(v)
    assert len(u) == 1 and u[0].irtifa_m == 1100 and u[0].baro_m == 1000 and u[0].cagri == "THY1"


def test_havalimani_bolgesi():
    assert havalimani_durumu(ucak(lat=IST.lat + 0.05, lon=IST.lon, baro=600, dikey=-4), IST) == "inis"
    assert havalimani_durumu(ucak(lat=IST.lat, lon=IST.lon + 0.05, baro=600, dikey=8), IST) == "kalkis"
    assert havalimani_durumu(ucak(lat=IST.lat, lon=IST.lon, baro=600, dikey=0.5), IST) is None  # düz uçuş
    assert havalimani_durumu(ucak(lat=IST.lat, lon=IST.lon, baro=3000, dikey=-4), IST) is None  # yüksek
    assert havalimani_durumu(ucak(lat=IST.lat, lon=IST.lon, baro=600, dikey=-4, yerde=True), IST) is None
    assert havalimani_durumu(ucak(lat=SAW.lat, lon=SAW.lon, baro=600, dikey=-4), IST) is None  # uzak


def test_tahmin_yansiz():
    """Sabit hızla alçalan, rastgele zamanlarda gelen uçaklar: anlık görüntü tahmini gerçek
    saatlik geliş sayısına yakınsamalı."""
    rnd = random.Random(1)
    T = 200 * 3600
    gelisler = []
    t = 0.0
    while t < T:
        t += rnd.expovariate(40 / 3600)  # saatte 40 iniş
        gelisler.append((t, rnd.uniform(3, 7)))  # dikey hız m/sn
    gercek = len(gelisler) / (T / 3600)
    tahminler = []
    for _ in range(4000):
        an = rnd.uniform(3600, T - 3600)
        tahmin = 0.0
        for g, v in gelisler:
            sure = (UST_M - ALT_M) / v
            if g <= an < g + sure:
                tahmin += saatlik_hiz(-v)
        tahminler.append(tahmin)
    ort = sum(tahminler) / len(tahminler)
    assert abs(ort - gercek) / gercek < 0.05


def test_gece_gunduz():
    def ts(s):
        return int(datetime(2026, 6, 21, s, 0, tzinfo=TR).timestamp())
    assert not gece_mi(ts(12)) and not gece_mi(ts(7))
    assert gece_mi(ts(1)) and gece_mi(ts(22))
    # Kasımda 18:00 karanlık
    assert gece_mi(int(datetime(2026, 11, 4, 18, 0, tzinfo=TR).timestamp()))


def test_ornek_ozeti_ve_eski_kayit():
    v = {"time": 1000, "states": [
        durum(icao="a", lat=41.03, lon=28.98, baro=10000, temas=1000),
        durum(icao="b", lat=41.03, lon=28.98, baro=500, temas=1000),
        durum(icao="c", lat=41.03, lon=28.98, baro=500, temas=800),   # 200 sn eski: sayılmaz
        ["f", "X", "Turkey", 900, 1000, 28.98, 41.03, 500, False, 80, 90, -3, None, 500, None, False, 0, 0],  # temas taze, konum eski
        durum(icao="d", lat=39.9, lon=32.8, baro=500, temas=1000),    # il dışı
        durum(icao="e", lat=41.03, lon=28.98, baro=None, yerde=True, temas=1000),
    ]}
    s = ornek_ozeti(v, 123)
    assert (s["havada"], s["yerde"], s["kutuda"], s["kredi"]) == (2, 1, 4, 123)
    assert s["yuksek"] == 1 and s["alcak"] == 1


def test_ozetle_saat_ve_hata():
    t0 = int(datetime(2026, 11, 2, 0, 0, tzinfo=TR).timestamp())  # pazartesi
    satirlar = []
    for i in range(48):
        s = {"t": t0 + i * 1800, "havada": i % 24, "yerde": 0, "kutuda": 0, "alcak": 0, "orta": 0, "yuksek": 0}
        for h in ("IST", "SAW"):
            for y in ("inis", "kalkis"):
                s[f"{h}_{y}_n"] = 1
                s[f"{h}_{y}_saat"] = 10.0
        satirlar.append(s)
    satirlar.append({"t": t0 + 99, "hata": "HTTP 429"})
    o = ozetle(satirlar)
    assert o["ornek"] == 48 and o["hatali"] == 1
    assert o["saat"][0]["ornek"] == 2 and o["gun"][0]["ornek"] == 48
    assert o["gunluk"][0]["IST_inis"] == 240
    assert o["aralik_medyan_sn"] == 1800


def test_iz():
    h1 = {"t": 1000, "ucaklar": [{"k": "a", "g": False, "la": 41.0, "lo": 29.0}, {"k": "b", "g": False, "la": 41.1, "lo": 29.1}]}
    iz = iz_guncelle(None, h1)
    h2 = {"t": 1240, "ucaklar": [{"k": "a", "g": False, "la": 41.05, "lo": 29.05}, {"k": "y", "g": True, "la": 41, "lo": 29}]}
    iz = iz_guncelle(iz, h2)
    assert iz["izler"] == {"a": [[1000, 41.0, 29.0], [1240, 41.05, 29.05]]}
    h3 = {"t": 1000 + 31 * 60, "ucaklar": [{"k": "a", "g": False, "la": 41.2, "lo": 29.2}]}
    assert len(iz_guncelle(iz, h3)["izler"]["a"]) == 2  # 31 dk önceki nokta düştü
