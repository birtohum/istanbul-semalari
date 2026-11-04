"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const fmt = (x, b = 0) => x == null ? "–" : Number(x).toLocaleString("tr-TR", { maximumFractionDigits: b, minimumFractionDigits: b });
  const saatYaz = (t) => new Date(t * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" });
  const tarihYaz = (t) => new Date(t * 1000).toLocaleDateString("tr-TR", { day: "numeric", month: "long", timeZone: "Europe/Istanbul" });
  const HL = {
    IST: { ad: "İstanbul Havalimanı", kisa: "İstanbul Hv.", lat: 41.2753, lon: 28.7519, renk: "var(--ist)" },
    SAW: { ad: "Sabiha Gökçen", kisa: "Sabiha Gökçen", lat: 40.8986, lon: 29.3092, renk: "var(--saw)" },
  };
  const SIRKET = {
    THY: "Türk Hava Yolları", PGT: "Pegasus", TKJ: "AJet", SXS: "SunExpress", CAI: "Corendon", KKK: "Atlasglobal",
    UAE: "Emirates", QTR: "Qatar Airways", ETD: "Etihad", DLH: "Lufthansa", AFR: "Air France", KLM: "KLM",
    BAW: "British Airways", AUA: "Austrian", SWR: "Swiss", AZR: "Azerbaijan Airlines", AFL: "Aeroflot",
    SVA: "Saudia", RJA: "Royal Jordanian", MEA: "Middle East Airlines", IRA: "Iran Air", SYR: "Syrian Air",
    WZZ: "Wizz Air", RYR: "Ryanair", EZY: "easyJet", ELY: "El Al", AIC: "Air India", CCA: "Air China",
    CSN: "China Southern", KAL: "Korean Air", MSR: "EgyptAir", FDB: "flydubai", ABY: "Air Arabia",
    JZR: "Jazeera", KAC: "Kuwait Airways", GFA: "Gulf Air", OMA: "Oman Air", UZB: "Uzbekistan Airways",
    TRK: "Turkish Airlines (kargo)", MNB: "MNG Kargo", ACB: "ACT Kargo", FDX: "FedEx", UPS: "UPS",
    IGO: "IndiGo", BTI: "airBaltic", LOT: "LOT", ROT: "TAROM", AEE: "Aegean", BUL: "Bulgaria Air",
    SAS: "SAS", FIN: "Finnair", ITY: "ITA Airways", IBE: "Iberia", VLG: "Vueling", TAP: "TAP",
    EXS: "Jet2", TOM: "TUI", STW: "South Wind", MGH: "MAI", SEH: "Sky Express", AXY: "Air Explore",
  };
  const ULKE = { Turkey: "Türkiye", Germany: "Almanya", "United Kingdom": "Birleşik Krallık", "United Arab Emirates": "BAE",
    Qatar: "Katar", "United States": "ABD", Russia: "Rusya", "Russian Federation": "Rusya", France: "Fransa",
    Netherlands: "Hollanda", Italy: "İtalya", Spain: "İspanya", Greece: "Yunanistan", Azerbaijan: "Azerbaycan",
    "Saudi Arabia": "Suudi Arabistan", India: "Hindistan", China: "Çin", Austria: "Avusturya",
    Switzerland: "İsviçre", Malta: "Malta", Ireland: "İrlanda", Hungary: "Macaristan", Poland: "Polonya",
    Ukraine: "Ukrayna", Iran: "İran", "Iran, Islamic Republic of": "İran", Egypt: "Mısır", Bulgaria: "Bulgaristan",
    Romania: "Romanya", Kuwait: "Kuveyt", Jordan: "Ürdün", Lebanon: "Lübnan", "Syrian Arab Republic": "Suriye",
    Uzbekistan: "Özbekistan", Kazakhstan: "Kazakistan", Georgia: "Gürcistan", Israel: "İsrail" };

  // ---- gökyüzü teması: İstanbul'da güneş nerede? --------------------------------
  function gunesYuksekligi(d) {
    const gun = Math.floor((d - Date.UTC(d.getUTCFullYear(), 0, 0)) / 864e5);
    const saat = d.getUTCHours() + d.getUTCMinutes() / 60;
    const g = 2 * Math.PI / 365 * (gun - 1 + (saat - 12) / 24);
    const denk = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g) - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
    const egim = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g) - 0.002697 * Math.cos(3 * g) + 0.00148 * Math.sin(3 * g);
    const aci = ((saat * 60 + denk + 4 * 28.98) / 4 - 180) * Math.PI / 180;
    const la = 41.01 * Math.PI / 180;
    const c = Math.sin(la) * Math.sin(egim) + Math.cos(la) * Math.cos(egim) * Math.cos(aci);
    return 90 - Math.acos(Math.max(-1, Math.min(1, c))) * 180 / Math.PI;
  }
  function temaUygula() {
    const h = gunesYuksekligi(new Date());
    document.body.classList.toggle("gece", h < -4);
    document.body.classList.toggle("aksam", h >= -4 && h < 6);
    return h < -4;
  }
  let geceMi = temaUygula();

  // ---- harita -----------------------------------------------------------------
  const harita = L.map("harita", { zoomControl: true, scrollWheelZoom: false, zoomSnap: 0.25, minZoom: 7, maxZoom: 13 })
    .setView([41.05, 28.95], 9);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıcıları · Uçaklar: <a href="https://opensky-network.org">OpenSky Network</a>',
  }).addTo(harita);
  if (window.IL_SINIRI) {
    const sinir = L.polygon(window.IL_SINIRI.map(([lo, la]) => [la, lo]), {
      color: "#ffb703", weight: 2, dashArray: "6 6", fill: true, fillOpacity: 0.04, interactive: false,
    }).addTo(harita);
    // Kapsayıcı boyutunu geç alabiliyor (yazı tipleri, arka plan sekmesi): boyut her değiştiğinde
    // kullanıcı haritayı oynatmadıysa ili yeniden sığdır.
    let oynatildi = false;
    harita.on("dragstart zoomstart", (e) => { if (e.hard !== false && !harita._sigdiriliyor) oynatildi = true; });
    const sigdir = () => {
      harita.invalidateSize();
      if (oynatildi || !harita.getSize().y) return;
      harita._sigdiriliyor = true;
      harita.fitBounds(sinir.getBounds(), { padding: [8, 8], animate: false });
      harita._sigdiriliyor = false;
    };
    sigdir();
    new ResizeObserver(sigdir).observe(document.getElementById("harita"));
  }
  for (const [kod, h] of Object.entries(HL)) {
    L.marker([h.lat, h.lon], {
      interactive: false, keyboard: false,
      icon: L.divIcon({ className: "", html: `<span class="hl-etiket" style="color:${h.renk}">${kod}</span>`, iconSize: [40, 20], iconAnchor: [20, -6] }),
    }).addTo(harita);
  }
  const ucakKatmani = L.layerGroup().addTo(harita);

  function renk(a) { return a == null ? "#bbb" : a < 3000 ? "var(--alcak)" : a < 8000 ? "var(--orta)" : "var(--yuksek)"; }
  function ikon(u, secik) {
    const boy = u.i ? 26 : 20;
    const svg = `<svg width="${boy}" height="${boy}" viewBox="0 0 24 24" style="rotate:${u.y || 0}deg"><path fill="${renk(u.a)}" stroke="#0b1530" stroke-width="1" d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg>`;
    return L.divIcon({ className: "ucak-ikon" + (u.i ? "" : " disarda") + (secik ? " secik" : ""), html: svg, iconSize: [boy, boy], iconAnchor: [boy / 2, boy / 2] });
  }

  let seciliCagri = null;
  function kartGoster(u) {
    const k = $("secili");
    if (!u) { k.hidden = true; seciliCagri = null; return; }
    seciliCagri = u.c || u.la + "," + u.lo;
    const sirket = SIRKET[(u.c || "").slice(0, 3)];
    const v = u.v;
    const hareket = u.g ? "Yerde" : v == null ? "–" : v <= -1.5 ? "Alçalıyor ↓" : v >= 1.5 ? "Tırmanıyor ↑" : "Düz uçuyor →";
    const d = u.d ? (u.d.endsWith("inis") ? `${HL[u.d.slice(0, 3)].ad}'na iniyor olabilir` : `${HL[u.d.slice(0, 3)].ad}'ndan kalkmış olabilir`) : null;
    k.innerHTML = `<button aria-label="Kapat">×</button>
      <div class="cagri">${u.c || "Çağrı adı yok"}</div>
      <div class="sirket">${sirket || "Şirket bilinmiyor"} · kayıt: ${ULKE[u.u] || u.u || "–"}</div>
      <dl>
        <dt>Yükseklik</dt><dd>${u.a == null ? "–" : fmt(u.a) + " m"}</dd>
        <dt>Hız</dt><dd>${u.h == null ? "–" : "saatte " + fmt(u.h) + " km"}</dd>
        <dt>Durum</dt><dd>${hareket}</dd>
        ${d ? `<dt>Tahmin</dt><dd>${d}</dd>` : ""}
      </dl>`;
    k.querySelector("button").onclick = () => { kartGoster(null); ciz(sonVeri); };
    k.hidden = false;
  }

  let sonVeri = null;
  function ciz(veri) {
    if (!veri) return;
    ucakKatmani.clearLayers();
    const liste = veri.ucaklar.filter((u) => !u.g).sort((a, b) => (a.a || 0) - (b.a || 0));
    for (const u of liste) {
      const anahtar = u.c || u.la + "," + u.lo;
      const m = L.marker([u.la, u.lo], { icon: ikon(u, anahtar === seciliCagri), title: u.c || "", riseOnHover: true });
      m.on("click", () => { kartGoster(u); ciz(sonVeri); });
      m.addTo(ucakKatmani);
    }
  }

  function hlSimdi(oz) {
    $("hl-simdi").innerHTML = Object.entries(HL).map(([kod, h]) => `
      <div class="hl" style="--renk:${h.renk}">
        <div class="ad">${h.ad}</div>
        <div class="satir"><span><b>${oz[kod + "_inis_n"]}</b>iniyor</span><span><b>${oz[kod + "_kalkis_n"]}</b>kalkıyor</span></div>
      </div>`).join("");
  }

  async function canliYukle() {
    try {
      const r = await fetch("veri/son.json?" + Math.floor(Date.now() / 60000), { cache: "no-store" });
      const veri = await r.json();
      sonVeri = veri;
      const oz = veri.ozet;
      $("sayi").textContent = oz.havada;
      const dk = Math.max(0, Math.round((Date.now() / 1000 - veri.t) / 60));
      const ne = dk <= 1 ? "az önce" : dk < 90 ? `${dk} dakika önce` : `${tarihYaz(veri.t)} ${saatYaz(veri.t)}`;
      $("altyazi").innerHTML = `İl sınırı içinde, havada. Fotoğraf <b>${saatYaz(veri.t)}</b>'de çekildi (${ne}).`;
      $("tazelik").textContent = `Haritada il dışındaki uçaklar da soluk görünür (toplam ${veri.ucaklar.length}). Bir uçağa dokun, bilgisi açılsın.`;
      hlSimdi(oz);
      ciz(veri);
      document.title = `${oz.havada} uçak · İstanbul semaları`;
    } catch (e) {
      $("altyazi").textContent = "Şu an veri alınamadı. Birazdan tekrar denenecek.";
    }
  }

  // ---- defter (tarihçe) ---------------------------------------------------------
  async function defterYukle() {
    let o;
    try { o = await (await fetch("veri/ozet.json?" + Math.floor(Date.now() / 600000))).json(); } catch (e) { return; }
    if (!o.ornek) { $("defter-not").textContent = "Defter henüz boş."; return; }
    const gunSayisi = (o.son - o.ilk) / 86400;
    $("defter-not").textContent = `${tarihYaz(o.ilk)} ${saatYaz(o.ilk)}'den beri ${fmt(o.ornek)} fotoğraf` +
      ` (genelde ${Math.round(o.aralik_medyan_sn / 60)} dakikada bir).` + (gunSayisi < 7 ? " Defter yeni; sayılar her gün biraz daha sağlamlaşacak." : "");

    const doluSaat = o.saat.filter((s) => s.ornek >= 3);
    const tepe = doluSaat.length ? doluSaat.reduce((a, b) => (b.havada > a.havada ? b : a)) : null;
    const dip = doluSaat.length ? doluSaat.reduce((a, b) => (b.havada < a.havada ? b : a)) : null;
    const b = [];
    b.push(`<div class="buyuk"><div class="etiket">Ortalama</div><div class="deger">${fmt(o.havada_ort)}</div><div class="ek">uçak aynı anda havada</div></div>`);
    b.push(`<div class="buyuk"><div class="etiket">Gördüğümüz en kalabalık an</div><div class="deger">${o.en_kalabalik.havada}</div><div class="ek">${tarihYaz(o.en_kalabalik.t)} ${saatYaz(o.en_kalabalik.t)}</div></div>`);
    if (o.gunduz.ornek && o.gece.ornek)
      b.push(`<div class="buyuk"><div class="etiket">Gündüz ☀ / Gece ☾</div><div class="deger">${fmt(o.gunduz.havada)} / ${fmt(o.gece.havada)}</div><div class="ek">ortalama uçak (güneşin doğuşuna ve batışına göre)</div></div>`);
    if (tepe && dip && tepe !== dip)
      b.push(`<div class="buyuk"><div class="etiket">En kalabalık / en sakin saat</div><div class="deger">${String(tepe.saat).padStart(2, "0")}:00 / ${String(dip.saat).padStart(2, "0")}:00</div><div class="ek">${fmt(tepe.havada)} ve ${fmt(dip.havada)} uçak ortalama</div></div>`);
    $("buyukler").innerHTML = b.join("");

    const enCok = Math.max(1, ...o.saat.map((s) => s.havada || 0));
    const gecesaat = (h) => (o.saat[h].gece || 0) > 0.5; // o saatteki fotoğrafların çoğu karanlıkta mı
    $("saat-grafik").innerHTML = o.saat.map((s) => s.ornek < 3
      ? `<div class="cubuk bos" title="${s.saat}:00 için henüz yeterli fotoğraf yok"></div>`
      : `<div class="cubuk ${tepe && s.saat === tepe.saat ? "tepe" : gecesaat(s.saat) ? "gece" : ""}" style="height:${(s.havada / enCok) * 100}%" title="${s.saat}:00 · ${fmt(s.havada, 1)} uçak · ${s.ornek} fotoğraf"><span class="d">${fmt(s.havada)}</span></div>`).join("");
    $("saat-grafik").insertAdjacentHTML("afterend", `<div class="saatler">${o.saat.map((s) => `<span>${s.saat}</span>`).join("")}</div>`);

    // havalimanları: gün boyu ortalama saatlik tahmin
    const ort = (k) => { const xs = o.saat.filter((s) => s.ornek >= 3 && s[k] != null); return xs.length ? xs.reduce((a, s) => a + s[k], 0) / xs.length : null; };
    const satirlar = [];
    for (const [kod, h] of Object.entries(HL)) for (const [y, ad] of [["inis", "iniş"], ["kalkis", "kalkış"]]) satirlar.push({ kod, h, ad, v: ort(`${kod}_${y}`) });
    const en = Math.max(1, ...satirlar.map((s) => s.v || 0));
    const tam = o.gunluk.filter((g) => g.IST_inis != null);
    $("hl-tablo").innerHTML = satirlar.map((s) => `<div class="hl-satir"><div class="ad">${s.h.kisa} ${s.ad}</div>
      <div class="hl-cizgi"><div class="hl-cubuk" style="--renk:${s.h.renk};width:${((s.v || 0) / en) * 80}%"></div><span>saatte ~${fmt(s.v)}</span></div></div>`).join("") +
      `<p class="not">Saatlik ortalama tahmin (gün boyu saat ortalamalarının ortalaması). Gece uçuşları azaldığı için yoğun saatler bunun üstündedir.${tam.length ? "" : " Günlük toplam için en az 18 farklı saatte fotoğraf gerekiyor; birikiyor."}</p>`;

    const kisa = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
    $("gun-grafik").innerHTML = o.gun.map((g, i) => g.ornek >= 30
      ? `<div class="gun"><div class="k">${kisa[i]}</div><div class="v">${fmt(g.havada)}</div></div>`
      : `<div class="gun yok" title="Bu gün için henüz yeterli fotoğraf yok"><div class="k">${kisa[i]}</div><div class="v">?</div></div>`).join("") ;

    if (o.gunluk.length) {
      $("gunluk-baslik").hidden = false;
      $("gunluk").innerHTML = `<table><thead><tr><th>Gün</th><th>Fotoğraf</th><th>Ort. havada</th><th>IST iniş+kalkış</th><th>SAW iniş+kalkış</th></tr></thead><tbody>` +
        o.gunluk.slice(-14).reverse().map((g) => `<tr><td>${new Date(g.gun + "T12:00:00+03:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short", weekday: "short" })}</td>
          <td>${g.ornek}</td><td>${fmt(g.havada_ort, 1)}</td>
          <td>${g.IST_inis != null ? "~" + fmt(g.IST_inis + g.IST_kalkis) : "–"}</td>
          <td>${g.SAW_inis != null ? "~" + fmt(g.SAW_inis + g.SAW_kalkis) : "–"}</td></tr>`).join("") + "</tbody></table>";
    }
    if (o.dogrulama) { const m = $("dogrulama-madde"); m.innerHTML = o.dogrulama; m.hidden = false; }
  }

  canliYukle();
  defterYukle();
  setInterval(canliYukle, 60000);
  setInterval(() => {
    const yeni = temaUygula();
    if (yeni !== geceMi) geceMi = yeni;
  }, 300000);
  harita.on("click", () => { if (seciliCagri) { kartGoster(null); ciz(sonVeri); } });
})();
