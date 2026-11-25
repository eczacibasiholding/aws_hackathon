# NEXUS · 30 saniyelik lansman videosu

Hackathon sunumunu açmak için hazırlanmış, sesli, 30 saniyelik tanıtım filmi.

**Hazır dosya:** [`nexus-lansman-30sn.mp4`](nexus-lansman-30sn.mp4) (1920×1080, 30 fps, H.264 + AAC, −15 LUFS)

> Bu klasör sunum materyalidir. Ajan kodunun (`src/nexus`) parçası değildir ve ona bağımlı değildir.

## Akış

Ritim 120 BPM. Bir vuruş 0,5 sn sürer; sahne geçişleri vuruşlara denk gelir.

| Süre | Sahne | Ekranda | Ses |
|---|---|---|---|
| 0,0–4,5 | `signal` | Taşıyıcının gerçek bildirimi (SG-2611-001, 24.11 09:12) yazılarak gelir. `05-Dec-2026` kırmızıya döner: **"Kızıldeniz'de gemi 8 gün gecikti."** | saat tıkırtısı, klavye, glitch + bas vuruş |
| 4,5–10,0 | `map` | "Red Sea" kelimesinin içinden haritaya dalış. Mundra → Cidde rotası çizilir, gemi Cidde'de durur. Panelde: stok 4 Aralık'ta bitiyor, malzeme 10 Aralık'ta geliyor, 5,1 gün duruş, aksiyonsuz maliyet **2.741.018 ₺** | kalp atışı, hızlanan saat, riser, sonra sessizlik |
| 10,0–12,0 | `reveal` | **NEXUS** + "Kesintiden karara." | büyük patlama |
| 12,0–19,5 | `agents` | 5 ajan, her vuruşta biri yanar: Sinyal (8 dk), Risk (22/25 YÜKSEK), Etki (424.550 ₺/gün), Seçenek (6 strateji), Karar (510 kg). "Son söz insanda: Onayla · Reddet · Değiştir" | davul ritmi, her ajanda pop/ping |
| 19,5–23,0 | `decision` | KARAR düğümünün içinden geniş haritaya geçiş. Şanghay → İstanbul hava hattı (250 kg, 2 gün) + Esenyurt deposu (260 kg, 1 gün). **"Hat durmuyor."** | ritim, sonra 0,5 sn boşluk |
| 23,0–26,5 | `payoff` | 2.741.018 ₺ ile 109.567 ₺ karşılaştırması. **2.631.451 ₺ tasarruf**, 0 gün duruş, maliyet 25 kat düşük | whip + vuruş, sayaç inişinde ping |
| 26,5–30,0 | `endcard` | NEXUS logosu, "Kesintiden karara.", Amazon Bedrock · AgentCore · Strands Agents | trampet dolgusu → final patlaması |

Rakamların hepsi S1 senaryosundan alındı (`data/NEXUS_Hackathon_Veri_Seti_AnaVeri.xlsx`):

| Rakam | Sayfa ve satır |
|---|---|
| Sinyal metni ve saatleri | `Risk_Sinyalleri` SG-2611-001 |
| Risk 4,4 × 5 = 22 | `Risk_Skorlama` R-01 |
| Tükenme, kullanılabilir tarih, duruş, günlük duruş maliyeti | `Etki_Analizi` R-01 |
| 6 strateji, S1-HIB maliyeti ve tasarrufu | `Strateji_Karsilastirma` |

Ajan çıktısı bu değerlerden farklı çıkarsa video da güncellenmelidir.

## Yapı

```
index.html              kök kompozisyon: 7 sahne + müzik altlığı + ses efektleri
compositions/*.html     her sahne ayrı dosya (GSAP zaman çizelgesi)
assets/map/land.svg     ../frontend/vendor/land-50m.json'dan üretilen kara katmanı (Mercator)
assets/audio/bed.wav    tools/build_bed.py ile sentezlenen ritim altlığı (davul, saat, sub, patlamalar)
assets/sfx/             HyperFrames'in ses efektleri (Pixabay lisansı, CREDITS.md)
assets/fonts/           Inter + JetBrains Mono (OFL), Türkçe karakterler ve ₺ için latin-ext dahil
assets/vendor/gsap.min.js  GSAP 3.15.0 (CDN erişimi kapalı olduğu için yerel)
tools/                  harita ve ses altlığı üreticileri
```

Renkler tedarik zinciri haritasının (`frontend/tedarik-zinciri.html`) paletinden alındı.

## Yeniden üretmek

Gerekenler: Node 22+, ffmpeg, Chrome/Chromium, Python 3 + numpy.

```bash
cd launch-video
python3 tools/build_map.py ../frontend/vendor/land-50m.json assets/map/land.svg   # harita
python3 tools/build_bed.py assets/audio/bed.wav                                   # ritim altlığı
npx --yes hyperframes@0.9.94 check                                                # kontrol
npx --yes hyperframes@0.9.94 preview                                              # tarayıcıda düzenleme
npx --yes hyperframes@0.9.94 render --quality delivery --output nexus-lansman-30sn.mp4
```

- Metinler ilgili `compositions/*.html` dosyasında düz HTML olarak durur.
- Sesler `index.html`'deki `<audio>` etiketleridir (`data-start`, `data-volume`).
- `hyperframes preview` (HyperFrames Studio) içinde zaman çizelgesi sürüklenerek de düzenlenebilir.

## Lisanslar

| Bileşen | Lisans |
|---|---|
| [HyperFrames](https://github.com/heygen-com/hyperframes) | Apache-2.0 |
| Ses efektleri | Pixabay Content License (ticari kullanım serbest, atıf gerekmez) |
| Fontlar | SIL OFL 1.1 |
| GSAP | Standard "no charge" license |

Ritim altlığı bu repoda sentezlendi.

[Remotion](https://github.com/remotion-dev/remotion) bu projede kullanılmadı. Remotion'ın ücretsiz lisansı bireyleri ve en fazla 3 çalışanlı şirketleri kapsar; daha büyük kuruluşların [şirket lisansı](https://www.remotion.dev/license) alması gerekir. HyperFrames'in `/remotion-to-hyperframes` yolu, ileride Remotion kaynağı gelirse onu buraya taşımak için hazırdır.
