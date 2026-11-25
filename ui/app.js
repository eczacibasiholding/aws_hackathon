/* NEXUS UI — hesap yapmaz; yalnızca agent çıktılarını Türkçe biçimde gösterir (SCOPE §4.8). */
(function () {
  "use strict";
  const CFG = window.NEXUS_CONFIG || {};
  const API = (CFG.API_URL || "").replace(/\/$/, "");
  const DEMO = !API;
  const $ = (s) => document.querySelector(s);
  const durum = { runs: [], seciliRun: null, detay: null, kararlar: [], demoKararlar: null };

  // ---------- Türkçe biçimlendirme ----------
  const sayi = (v, ondalik = 0) => v == null || v === "" ? "—" :
    Number(v).toLocaleString("tr-TR", { minimumFractionDigits: ondalik, maximumFractionDigits: ondalik });
  const sayiOto = (v) => v == null ? "—" : Number(v).toLocaleString("tr-TR", { maximumFractionDigits: 2 });
  const tl = (v) => v == null ? "—" : sayi(Math.round(v)) + " TL";
  const gun = (v) => v == null ? "—" : sayiOto(v) + " gün";
  const kg = (v) => v == null ? "—" : sayiOto(v) + " kg";
  const iki = (n) => String(n).padStart(2, "0");
  function tarihParca(v) {
    if (!v) return null;
    const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
    return m ? { y: m[1], a: m[2], g: m[3], s: m[4], d: m[5] } : null;
  }
  // Zaman damgaları çıktıdaki yerel saatle gösterilir (dönüşüm/hesap yok).
  const tarihSaat = (v) => { const p = tarihParca(v); return !p ? "—" : `${p.g}.${p.a}` + (p.s ? ` ${p.s}:${p.d}` : ""); };
  const tarih = (v) => { const p = tarihParca(v); return !p ? "—" : `${p.g}.${p.a}.${p.y}`; };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const rozet = (k) => k ? `<span class="rozet k-${esc(k)}">${esc(k)}</span>` : '<span class="rozet">—</span>';
  const alan = (b, v) => `<div class="alan"><b>${esc(b)}</b>${v}</div>`;

  // ---------- Veri ----------
  async function api(yol, secenek = {}) {
    const r = await fetch(API + yol, { ...secenek, headers: { "content-type": "application/json", "x-api-key": CFG.API_KEY || "", ...(secenek.headers || {}) } });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.hata || r.status);
    return j;
  }
  const fixture = async (ad) => (await fetch("fixtures/" + ad + ".json", { cache: "no-store" })).json();

  async function runlariGetir() { return DEMO ? (await fixture("runs")).runs : (await api("/runs")).runs || []; }
  async function detayGetir(id) {
    if (!DEMO) return api("/runs/" + encodeURIComponent(id));
    try { return await fixture(id); } catch (e) { return { run_id: id, summary: durum.runs.find((r) => r.run_id === id) }; }
  }
  async function kararlariGetir() {
    if (!DEMO) return (await api("/decisions")).decisions || [];
    if (!durum.demoKararlar) durum.demoKararlar = (await fixture("decisions")).decisions;
    return durum.demoKararlar;
  }

  // ---------- Ekran 1 ----------
  function ekran1() {
    const d = durum.detay || {}, s = d.signal, r = d.risk, oz = d.summary || durum.runs.find((x) => x.run_id === durum.seciliRun) || {};
    $("#sinyalNo").textContent = (s && s.sinyal_no) || oz.sinyal_no || "";
    $("#hamMetin").textContent = (s && (s.ham_metin || (s.kanit && s.kanit.metin_alintilari || []).join("\n"))) || "Sinyal seçilmedi.";
    $("#cikarilan").innerHTML = s ? [
      alan("İşleme kararı", esc(s.isleme_karari) + (s.ayiklama_nedeni ? " · " + esc(s.ayiklama_nedeni) : "")),
      alan("Sevkiyat", esc((s.ilgili_sevkiyat || []).join(", ") || "—")),
      alan("Malzeme", esc((s.ilgili_malzeme || []).join(", ") || "—")),
      alan("Tahmini gecikme", gun(s.tahmini_gecikme_gun)),
      alan("Olay tipi", esc(s.olay_tipi || "—")),
      alan("Ülke / bölge", esc(s.ulke_bolge || "—")),
      alan("Alternatif ipucu", esc(s.alternatif_ipucu || "—")),
      alan("Sinyal güvenilirliği", sayiOto(s.sinyal_guvenilirligi) + " / 5"),
    ].join("") : "";
    $("#riskKarti").innerHTML = r ? `<h2>Risk kartı <small>${esc(r.risk_no || "")}</small></h2>
      <div class="risk"><span>Olasılık <span class="buyuk">${sayiOto(r.olasilik)}</span></span>×
      <span>Etki <span class="buyuk">${sayiOto(r.etki)}</span></span>=
      <span>Puan <span class="buyuk">${sayiOto(r.risk_puani)}</span></span>${rozet(r.risk_kademesi)}</div>
      <p>${esc(r.aciklama || "")}</p><p class="soluk">Agent aksiyonu: ${esc(r.agent_aksiyonu || "—")}</p>`
      : `<h2>Risk kartı</h2><p class="soluk">${esc(oz.durum || "Risk çıktısı yok")} ${esc(oz.aciklama || "")}</p>`;
    $("#runTablo tbody").innerHTML = durum.runs.map((x) => `<tr data-run="${esc(x.run_id)}" class="${x.run_id === durum.seciliRun ? "secili" : ""}">
      <td>${tarihSaat(x.bitis_zamani || x.baslangic_zamani || x._guncelleme)}</td><td>${esc(x.sinyal_no || "—")}</td>
      <td>${esc(x.sevkiyat_no || "—")} / ${esc(x.malzeme_no || "—")}</td><td>${sayiOto(x.risk_puani)}</td>
      <td>${rozet(x.risk_kademesi)}</td><td>${esc(x.durum || "—")}${x.karar ? " · " + esc(x.karar) : ""}</td></tr>`).join("")
      || '<tr><td colspan="6" class="soluk">Henüz run yok.</td></tr>';
  }

  // ---------- Ekran 2 ----------
  function ekran2() {
    let i = durum.detay && durum.detay.impact;
    if (Array.isArray(i)) i = i.slice().sort((a, b) => (b.aksiyonsuz_maliyet_try || 0) - (a.aksiyonsuz_maliyet_try || 0))[0];  // malzeme başına liste → en yüksek etkili
    if (!i) { $("#etkiBaslik").textContent = ""; $("#etkiKutular").innerHTML = '<p class="soluk">Bu run için etki çıktısı yok.</p>'; $("#zaman").innerHTML = ""; $("#siparisTablo tbody").innerHTML = ""; $("#etkiDetay").innerHTML = ""; return; }
    $("#etkiBaslik").textContent = `${i.sevkiyat_no} · ${i.malzeme_no} · ${i.tesis_kodu} / ${i.hat_kodu}`;
    $("#etkiKutular").innerHTML = [
      ["Stok bitişi", tarihSaat(i.tukenme_tarihi), `${gun(i.stok_kapsama_gun)} kapsama`],
      ["Malzemenin kullanılabilir olduğu tarih", tarih(i.guncel_kullanilabilir_tarih), `planlanan ${tarih(i.planlanan_kullanilabilir_tarih)} · ${sayiOto(i.kullanilabilir_gun)}. gün`],
      ["Duruş", gun(i.acik_durus_gun), `duruş maliyeti ${tl(i.durus_maliyeti_try)}`],
      ["Aksiyonsuz maliyet", tl(i.aksiyonsuz_maliyet_try), `ceza ${tl(i.olasi_ceza_try)} · etki puanı ${sayiOto(i.etki_puani)}`],
    ].map(([b, v, a], n) => `<div class="kutu ${n >= 2 ? "kirmizi" : ""}"><b>${esc(b)}</b><span>${v}</span><div class="soluk">${a}</div></div>`).join("");
    const olaylar = i.zaman_cizelgesi || [
      { tarih: i.d0, olay: "Analiz tarihi (D0)" },
      { tarih: i.tukenme_tarihi, olay: "Stok tükenir", kritik: true },
      { tarih: i.planlanan_kullanilabilir_tarih, olay: "Planlanan kullanılabilir tarih" },
      { tarih: i.guncel_kullanilabilir_tarih, olay: "Güncel kullanılabilir tarih" },
    ];
    $("#zaman").innerHTML = olaylar.map((o) => `<li class="${o.kritik || /tükenir/i.test(o.olay) ? "kritik" : ""}"><b>${tarihSaat(o.tarih)}</b> · ${esc(o.olay)}</li>`).join("");
    $("#siparisTablo tbody").innerHTML = (i.risk_altindaki_siparisler || []).map((s) => `<tr><td>${esc(s.siparis_no)}</td><td>${esc(s.hat_kodu || "—")}</td><td>${tarih(s.gerekli_uretim_tarihi)}</td><td>${gun(s.gecikme_gun)}</td><td>${tl(s.ceza_try)}</td></tr>`).join("");
    $("#etkiDetay").innerHTML = [alan("Serbest stok", kg(i.serbest_stok)), alan("Günlük tüketim", kg(i.gunluk_tuketim) + "/gün"),
      alan("Günlük duruş maliyeti", tl(i.gunluk_durus_maliyeti_try)), alan("Yeniden başlatma", tl(i.yeniden_baslatma_maliyeti_try))].join("");
  }

  // ---------- Ekran 3 ----------
  function ekran3() {
    const o = durum.detay && durum.detay.options, d = durum.detay && durum.detay.decision;
    if (!o && !d) { $("#stratejiler").innerHTML = '<p class="soluk">Bu run için seçenek üretilmedi (kademe Yüksek/Orta değil veya akış kapandı).</p>'; $("#milpKart").innerHTML = ""; return; }
    const karsi = {}; ((d && d.karsilastirma) || []).forEach((k) => (karsi[k.strateji_kodu] = k));
    const liste = (o && o.stratejiler) || ((d && d.karsilastirma) || []).map((k) => ({ strateji_kodu: k.strateji_kodu, strateji_adi: k.strateji_adi, uygun_mu: k.uygun_mu }));
    const sirali = liste.slice().sort((a, b) => ((karsi[a.strateji_kodu] || {}).sira || 99) - ((karsi[b.strateji_kodu] || {}).sira || 99));
    $("#stratejiler").innerHTML = sirali.map((s) => {
      const k = karsi[s.strateji_kodu] || {};
      const bil = (s.bilesenler || []).map((b) => `${esc(b.tip)}: ${esc(b.kaynak)} · ${kg(b.miktar)}`).join("<br>") || "Bileşen yok (bekle)";
      return `<div class="strateji ${k.oneri ? "onerilen" : ""}">${k.oneri ? '<span class="etiket">ÖNERİLEN</span>' : ""}
        <h3>${esc(s.strateji_adi || k.strateji_adi)} <small class="soluk">${esc(s.strateji_kodu)}</small></h3>
        <dl><dt>Duruş</dt><dd>${gun(k.durus_gun)}</dd><dt>Toplam maliyet</dt><dd>${tl(k.toplam_maliyet_try)}</dd>
        <dt>CO2</dt><dd>${kg(k.co2_kg)}</dd><dt>Risk</dt><dd>${sayiOto(k.risk)}</dd>
        <dt>Skor</dt><dd>${k.agirlikli_skor == null ? "—" : sayi(k.agirlikli_skor, 3)}</dd><dt>Sıra</dt><dd>${k.sira || "—"}</dd></dl>
        <p class="soluk">${bil}</p>${s.uygun_mu === false ? `<p class="soluk">Elendi: ${esc(s.eleme_nedeni)}</p>` : ""}</div>`;
    }).join("");
    const m = d && d.milp;
    $("#milpKart").innerHTML = m ? `<h2>MILP doğrulaması</h2><div class="alanlar">${alan("Durum", esc(m.durum))}${alan("Transfer (x_T)", kg(m.x_T))}${alan("Hava (x_A)", kg(m.x_A))}${alan("Liman değişikliği (y_C)", m.y_C == null ? "—" : m.y_C ? "Evet" : "Hayır")}${alan("Amaç", tl(m.amac_try))}${alan("ÇKKV ile uyumlu", m.cckv_ile_uyumlu ? "Evet" : "Hayır")}</div>` : "";
  }

  // ---------- Ekran 4 ----------
  function ekran4() {
    const d = durum.detay && durum.detay.decision;
    const kayit = d && durum.kararlar.find((k) => k.olay_no === d.karar_kaydi_taslagi.olay_no);
    if (!d) { $("#oneriKart").innerHTML = '<h2>Öneri</h2><p class="soluk">Bu run için öneri yok.</p>'; }
    else {
      const c = d.oneri_karti, r = c.rakamlar, karar = (kayit && kayit.karar) || d.karar_kaydi_taslagi.karar;
      const acik = karar === "Onay Bekliyor";
      $("#oneriKart").innerHTML = `<h2>${esc(c.baslik)} <small>${esc(d.karar_kaydi_taslagi.olay_no)} · ${esc(c.onerilen_strateji_kodu || "")}</small></h2>
        <div class="kutular">
          <div class="kutu kirmizi"><b>Hiçbir şey yapmamanın maliyeti</b><span>${tl(r.aksiyonsuz_maliyet_try)}</span></div>
          <div class="kutu"><b>Önerilen toplam maliyet</b><span>${tl(r.toplam_maliyet_try)}</span></div>
          <div class="kutu"><b>Tasarruf</b><span style="color:var(--yesil)">${tl(r.tasarruf_try)}</span></div>
          <div class="kutu"><b>Duruş</b><span>${gun(r.durus_gun)}</span></div></div>
        <h2 style="margin-top:14px">Gerekçe</h2><div class="gerekce">${esc(c.gerekce || "Gerekçe üretilemedi (LLM hatası); rakamlar geçerlidir.")}</div>
        ${c.dikkat_notu ? `<p style="color:var(--turuncu)">Dikkat: ${esc(c.dikkat_notu)}</p>` : ""}
        <p>Karar durumu: <b>${esc(karar)}</b>${kayit && kayit.kullanici_geri_bildirimi ? " · " + esc(kayit.kullanici_geri_bildirimi) : ""}</p>
        <div class="butonlar">
          <button class="onayla" data-karar="Onayla" ${acik ? "" : "disabled"}>Onayla</button>
          <button class="reddet" data-karar="Reddet" ${acik ? "" : "disabled"}>Reddet</button>
          <label><input type="checkbox" id="yanlisAlarm"> Yanlış alarm</label>
          <button class="degistir" data-karar="Değiştir" ${acik ? "" : "disabled"}>Değiştir</button>
          <input id="revizeNot" placeholder="Değiştir notu (zorunlu)" style="flex:1;min-width:200px;padding:8px;background:#081624;color:var(--yazi);border:1px solid var(--cizgi);border-radius:6px">
          <span id="kararDurum" class="soluk"></span></div>`;
    }
    $("#kararTablo tbody").innerHTML = durum.kararlar.map((k) => `<tr><td>${esc(k.olay_no)}</td><td>${esc(k.risk_no || "")}</td><td>${esc(k.onerilen_aksiyon || k.onerilen_strateji_kodu || "—")}</td><td>${tl(k.tasarruf_try)}</td><td>${esc(k.karar)}</td><td>${k.yanlis_alarm_mi ? "Evet" : "Hayır"}</td><td>${esc(k.kullanici_geri_bildirimi || k.revize_notu || "")}</td></tr>`).join("")
      || '<tr><td colspan="7" class="soluk">Karar kaydı yok.</td></tr>';
  }

  async function kararGonder(tus) {
    const d = durum.detay.decision, not = ($("#revizeNot").value || "").trim();
    if (tus === "Değiştir" && !not) { $("#kararDurum").textContent = "Değiştir için not girin."; return; }
    const govde = { olay_no: d.karar_kaydi_taslagi.olay_no, karar: tus, onaylayan_rol: "Satınalmacı", revize_notu: not || null, yanlis_alarm: tus === "Reddet" && $("#yanlisAlarm").checked };
    $("#kararDurum").textContent = "Gönderiliyor…";
    try {
      if (DEMO) {
        const k = durum.demoKararlar.find((x) => x.olay_no === govde.olay_no);
        if (k) { k.karar = { Onayla: "Onaylandı", Reddet: "Reddedildi", "Değiştir": "Revize Edildi" }[tus]; k.yanlis_alarm_mi = govde.yanlis_alarm; k.kullanici_geri_bildirimi = not || (tus === "Onayla" ? "Onaylandı." : ""); }
      } else await api("/decision", { method: "POST", body: JSON.stringify(govde) });
      $("#kararDurum").textContent = "Kaydedildi.";
      await yenile();
    } catch (e) { $("#kararDurum").textContent = "Hata: " + e.message; }
  }

  async function epostaGonder() {
    const metin = $("#epostaMetin").value.trim();
    if (!metin) return;
    $("#epostaDurum").textContent = "Gönderiliyor…";
    try {
      if (DEMO) { $("#epostaDurum").textContent = "DEMO modu: yükleme yapılmadı."; return; }
      const r = await api("/email", { method: "POST", body: JSON.stringify({ metin }) });
      $("#epostaDurum").textContent = "Yüklendi: " + r.key + " — risk birkaç dakika içinde listede belirir.";
      $("#epostaMetin").value = "";
    } catch (e) { $("#epostaDurum").textContent = "Hata: " + e.message; }
  }

  function ciz() { ekran1(); ekran2(); ekran3(); ekran4(); }

  async function runSec(id) {
    durum.seciliRun = id;
    durum.detay = id ? await detayGetir(id) : null;
    ciz();
  }

  async function yenile() {
    try {
      const [runs, kararlar] = await Promise.all([runlariGetir(), kararlariGetir()]);
      const yeni = runs.length && durum.runs.length && runs[0].run_id !== durum.runs[0].run_id;
      durum.runs = runs; durum.kararlar = kararlar;
      if (!durum.seciliRun || yeni) {
        const oncelik = runs.find((r) => r.risk_kademesi === "Yüksek") || runs[0];
        await runSec(yeni ? runs[0].run_id : oncelik && oncelik.run_id);
      } else if (durum.seciliRun) { durum.detay = await detayGetir(durum.seciliRun); ciz(); }
      const s = new Date();
      $("#yenileme").textContent = `Son yenileme ${iki(s.getHours())}:${iki(s.getMinutes())}:${iki(s.getSeconds())}`;
    } catch (e) { $("#yenileme").textContent = "Yenileme hatası: " + e.message; }
  }

  // ---------- Olaylar ----------
  document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("aktif", x === b));
    document.querySelectorAll(".ekran").forEach((e) => e.classList.toggle("aktif", e.id === "ekran" + b.dataset.ekran));
  }));
  $("#runTablo").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-run]"); if (tr) runSec(tr.dataset.run); });
  $("#oneriKart").addEventListener("click", (e) => { const b = e.target.closest("button[data-karar]"); if (b && !b.disabled) kararGonder(b.dataset.karar); });
  $("#epostaGonder").addEventListener("click", epostaGonder);
  $("#haritaLink").href = CFG.MAP_URL || "https://dhqlkgzaubwcj.cloudfront.net";
  $("#mod").textContent = DEMO ? "DEMO (fixture)" : "Canlı";
  yenile();
  setInterval(() => { if (document.querySelector("#ekran1.aktif")) yenile(); }, CFG.REFRESH_MS || 10000);
})();
