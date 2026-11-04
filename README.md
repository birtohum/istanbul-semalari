# İstanbul semalarında şu an kaç uçak var?

https://birtohum.github.io/istanbul-semalari/

İstanbul il sınırının üzerinde havada olan uçakları [OpenSky Network](https://opensky-network.org)'ün
açık ADS-B verisiyle sayan, haritada gösteren ve saat saat biriktiren küçük bir site.

## Nasıl çalışıyor

- `topla.py`: OpenSky `/states/all` uç noktasından İstanbul çevresini (40.30–41.95 K, 27.40–30.40 D;
  alanı 25 derece karenin altında olduğu için sorgu başına 1 kredi) çeker. Konumu 30 saniyeden eski kayıtları atar,
  il sınırı (OpenStreetMap) içinde havada olanları sayar ve `veri/ornekler/GÜN.jsonl`'a bir satır ekler.
  Haritanın kullandığı `site/veri/son.json`'u da yazar.
- `ozetle.py`: bütün örneklerden `site/veri/ozet.json`'u üretir (saat, gün, gündüz/gece ortalamaları,
  havalimanı tahminleri).
- `site/`: statik sayfa (Leaflet + OpenStreetMap altlığı). Tarayıcı OpenSky'a doğrudan bağlanamaz
  (OpenSky CORS'u kendi alan adına kısıtlıyor), bu yüzden harita son anlık görüntüyü gösterir.

## Havalimanı tahmini

Bir anlık görüntüde havalimanına 22 km'den yakın, pist seviyesinin 150–1000 m üstünde ve dikey hızı
1,5 m/sn'den büyük uçaklar "iniyor" ya da "kalkıyor" sayılır. Bir uçak bu 850 m'lik dilimi
`850 / |dikey hız|` saniyede geçer. Rastgele bir anda orada yakalanma olasılığı bu süreyle orantılı olduğundan,
her uçak `|dikey hız| × 3600 / 850` ağırlığıyla toplanır. Bu, saatlik iniş/kalkış sayısının yansız tahminidir (Little yasası)
ve örnekler düzensiz aralıklarla alınsa da çalışır. Bölge dışında dönen, düz uçan, sinyali kaybolan uçaklar
tahmini aşağı çeker. Bkz. `tests/test_cekirdek.py::test_tahmin_yansiz` ve `dogrula.py`.

## Sınırlar

- ADS-B yayını olmayan ya da hiçbir alıcının duymadığı uçaklar görünmez; sayılar gerçeğin altındadır.
- Anonim OpenSky erişimi IP başına günde 400 kredi; zamanlanmış işler en sık 5 dakikada bir çalışır ve gecikebilir.
- "İstanbul semaları" = il sınırının üstü, yükseklik sınırı yok.

## Çalıştırma

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python topla.py && .venv/Scripts/python ozetle.py
.venv/Scripts/python -m http.server -d site
.venv/Scripts/python -m pytest
```

## Veri ve lisans

Uçak verisi: The OpenSky Network, https://opensky-network.org. İl sınırı ve harita altlığı:
© OpenStreetMap katkıcıları (ODbL). Kod: Apache-2.0.
