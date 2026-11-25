# NEXUS MVP — Tasarım

Kaynak: SCOPE §3 (bileşen haritası), §4 (bulut mimarisi), §5 (kararlar). Sözleşmeler: `00_ortak_veri_semalari.md` (v1.1, D10).

## 1. Akış (SCOPE §4.1)
```
SES / UI yedek ─► S3 inbound-email/ ─► Lambda email_trigger (PII temizliği, eşleşme/yeni sinyal, idempotency)
   ─► AgentCore Runtime (src/app.py, tek paket, D2)
        Orkestratör (deterministik, LLM yok, K5)
          Signal ─► Risk(Olasılık) ∥ Impact ─► Risk(Puan,Kademe) ─► Options ─► Decision
   ─► S3 runs/ · registry/ · decisions/ ◄─ Lambda api (Function URL, x-api-key) ◄─► UI (S3 statik)
```
Destek servisleri: S3, SES, Lambda, IAM, CloudWatch. LLM: yalnızca Bedrock (`BEDROCK_MODEL_ID`), agent SDK'sı Strands.

## 2. Bileşenler
| Bileşen | Yol | Not |
|---|---|---|
| Runtime giriş | `src/app.py` | `eylem`: `SINYAL_ISLE`, `TOPLU_TARAMA`, `INSAN_KARARI` → `src/orchestrator/orchestrator.py` |
| Orkestratör | `src/orchestrator/` | Durum makinesi §4.1; `WHAT_IF` yok (D7); risk kayıt defteri D8; olay no D9 |
| Agent'lar | `src/agents/<agent>/` | `run(girdi) -> *Output`; tool'lar `tools/` (D11); sayıları yalnızca tool'lar üretir (K6) |
| Sözleşmeler | `src/contracts/schemas.py` | Pydantic v2, ortak şemadan birebir |
| Veri | `src/data_access/` | `NEXUS_INPUT_URI` (yerel / `s3://`) |
| E-posta tetik | `src/triggers/email_trigger/handler.py` | §4.4–4.5; `config/email_kaynaklari.yaml` |
| API | `src/api/handler.py` | `GET /runs`, `GET /runs/{id}`, `GET /decisions`, `POST /decision`, `POST /email`; CORS |
| UI | `ui/` | 4 ekran (§4.8), DEMO modu `ui/fixtures/`, hesap yok |
| Altyapı | `scripts/deploy_all.sh` | AWS CLI + agentcore starter toolkit, idempotent |

## 3. S3 düzeni (SCOPE §4.6)
`input/nexus_agent_input.xlsx` · `inbound-email/` (1 gün) · `signals/<SG>.json` · `runs/<run_id>/{signal,risk,impact,options,decision,summary}.json` · `registry/{risks,processed}.json` · `decisions/<Olay No>.json`.
Cevap anahtarı S3'e yüklenmez (KÇ6).

`summary.json` (orkestratör yazar, UI listesi için): `run_id, sinyal_no, durum, risk_no, risk_puani, risk_kademesi, olay_no, karar, baslangic_zamani, bitis_zamani`.

## 4. Güvenlik
- API: `x-api-key` başlığı = Lambda env `API_KEY` (hackathon düzeyi, §4.8). AgentCore'u yalnızca Lambda IAM rolüyle çağırır.
- Runtime IAM: Bedrock InvokeModel, kova okuma/yazma, CloudWatch, X-Ray.
- PII: ham MIME yalnızca `inbound-email/` (1 gün); agent'a temizlenmiş gövde gider (KÇ5). Karar kaydında rol yazılır (D16).

## 5. Kararlar
SCOPE §5'teki K1–K6, D1–D17 geçerlidir. Bu spec yeni karar eklemez.
- Uygulama notu (karar değil): `email_trigger` pandas yerine yalnızca `openpyxl` ile `Risk_Sinyalleri` sayfasını okur (Lambda paketi küçük kalır).
