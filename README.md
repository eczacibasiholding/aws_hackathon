# NEXUS · Tedarik zinciri risk müdahale sistemi

Taşıyıcı e-postasından insan onayına kadar otonom çalışan çok agent'lı sistem: **Signal → Risk ∥ Impact → Options → Decision**, deterministik bir orkestratörle, Amazon Bedrock AgentCore Runtime üzerinde. Karar insandadır: sistem sipariş vermez, ERP'ye yazmaz.

| | |
|---|---|
| AWS hesap ID | **242872169400** |
| Bölge | **us-east-1** (SES, AgentCore Runtime ve model aynı bölgede) |
| Model | `BEDROCK_MODEL_ID` ortam değişkeni (F0'da `scripts/list_models.sh` ile seçilir; seçilen değer buraya yazılır) |
| Analiz tarihi (D0) | 25.11.2026 |
| Çerçeve | `.kiro/steering/SCOPE.md`, spec: `.kiro/specs/nexus-mvp/` |

## Mimari

```
Taşıyıcı e-postası ─► Amazon SES ─┐
UI "E-posta gönder (yedek)" / CLI ─┴► S3 inbound-email/ (1 gün yaşam döngüsü)
                                          │ ObjectCreated
                                          ▼
                     Lambda nexus-email-trigger  (MIME, kişisel veri temizliği, sinyal eşleştirme, idempotency)
                                          │ InvokeAgentRuntime {eylem: SINYAL_ISLE}
                                          ▼
     Bedrock AgentCore Runtime  (src/app.py — tek paket)          ──► AgentCore Observability
       Orkestratör (deterministik) → Signal → Risk ∥ Impact → Risk kademe → Options → Decision
       Her agent: Strands + Bedrock LLM; sayıları yalnızca tool'lar üretir
                                          │
                     S3 runs/<run_id>/*.json · registry/ · decisions/<Olay No>.json
                                          ▲
     UI (S3 statik web, 4 ekran) ◄──► Lambda nexus-api (Function URL, x-api-key) ──► INSAN_KARARI
```

Destek servisleri: S3, SES, Lambda, IAM, CloudWatch. LLM yalnızca Amazon Bedrock; agent SDK'sı Strands Agents.

| Yol | İçerik |
|---|---|
| `src/app.py` | AgentCore giriş noktası; `eylem`: `SINYAL_ISLE`, `TOPLU_TARAMA`, `INSAN_KARARI` |
| `src/orchestrator/` | Durum makinesi, risk kayıt defteri, S3'e yazma |
| `src/agents/{signal,risk,impact,options,decision}/` | Agent'lar ve tool'ları |
| `src/contracts/schemas.py` | Agent'lar arası Pydantic sözleşmeleri (v1.1) |
| `src/data_access/` | Girdi Excel'i (yerel yol veya `s3://`) |
| `src/triggers/email_trigger/handler.py` | E-posta tetik Lambda'sı |
| `src/api/handler.py` | UI API Lambda'sı: `GET /runs`, `GET /runs/{id}`, `GET /decisions`, `POST /decision`, `POST /email` |
| `ui/` | 4 ekranlı statik UI (Uyarı, Etki, Seçenekler, Öneri ve onay); `API_URL` boşsa `ui/fixtures/` ile DEMO modu |
| `scripts/` | `deploy_all.sh`, `list_models.sh`, `send_test_email.sh`, `demo_reset.py` |
| `infra/` | IAM politika şablonları |
| `config/` | `.env.example`, `email_kaynaklari.yaml` (gizli bilgi yok) |

S3 kovası `nexus-242872169400-us-east-1`: `input/` (girdi Excel'i, salt okunur) · `inbound-email/` · `signals/` · `runs/` · `registry/` · `decisions/`. Cevap anahtarı yalnızca `tests/fixtures/` altındadır, S3'e ve Runtime paketine girmez (`.dockerignore`).

## Kurulum (yerel)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp config/.env.example .env      # NEXUS_INPUT_URI=data/nexus_agent_input.xlsx ile yerelde çalışır
pytest -m "not llm" -q
```

UI'ı backend'siz görmek: `cd ui && python3 -m http.server 8080` → http://localhost:8080 (DEMO modu).

## Deploy (Kiro terminalinden, AWS SSO açıkken)

```bash
aws sts get-caller-identity                      # 242872169400 görünmeli
export AWS_REGION=us-east-1
./scripts/list_models.sh                         # en güçlü reasoning modelini/inference profile'ını seç
export BEDROCK_MODEL_ID=<seçilen-id>             # ör. us.anthropic.claude-...
BEDROCK_MODEL_ID=$BEDROCK_MODEL_ID ./scripts/list_models.sh   # deneme çağrısı "OK" dönmeli
./scripts/deploy_all.sh                          # kova + input + AgentCore + Lambda'lar + UI
```

`deploy_all.sh` idempotenttir; adımlar ayrı çalıştırılabilir: `STEPS="lambdas ui" ./scripts/deploy_all.sh`. Çıktılar (`AGENT_RUNTIME_ARN`, `API_URL`, `API_KEY`) `.build/deploy_state.env` dosyasına yazılır (repoya eklenmez).

Doğrulama:

```bash
source .build/deploy_state.env
agentcore invoke '{"eylem":"SINYAL_ISLE","sinyal_no":"SG-2611-001"}'
aws s3 ls s3://nexus-242872169400-us-east-1/runs/ --recursive | tail
./scripts/send_test_email.sh SG-2611-001         # otonom tetik (S3 yedek yolu)
aws logs tail /aws/lambda/nexus-email-trigger --since 10m
curl -s -H "x-api-key: $API_KEY" "$API_URL/runs" | head -c 600
```

Demo hazırlığı (D17): `python scripts/demo_reset.py --evet` — S3 durumunu temizler ve canlı demo sinyalleri (`SG-2611-001,SG-2611-002`) hariç toplu tarama çalıştırır.

SES (opsiyonel): doğrulanmış alan adı ve MX kaydı varsa alma kuralı `signals@<alan-adı>` → S3 `inbound-email/` eylemiyle kurulur. Yoksa UI'daki "E-posta gönder (yedek)" veya `send_test_email.sh` aynı akışı tetikler.

## Frontend (tedarik zinciri haritası)

`frontend/` statik bir sayfa: `tedarik-zinciri.html` (MapLibre GL + deck.gl). Backend bağlı değilken DEMO verisiyle çalışır.

- Kütüphaneler ve harita verisi `frontend/vendor/` altında yerel olarak durur (maplibre-gl 5.24.0, deck.gl 9.3.5, topojson-client 3.1.0, world-atlas 2.0.2 `land-50m.json`). Etkinlik ağı unpkg.com'u engellediğinde sayfa boş kalıyordu; bu yüzden CDN kullanılmaz. `scripts/deploy_frontend.sh` HTML'de dış adresten script/stil bulursa deploy'u durdurur.
- 4 ekranlı karar UI'ı (`ui/`) üst menüden bu haritaya bağlanır.
- Yerelde açmak: `cd frontend && python3 -m http.server 8000` → http://localhost:8000/tedarik-zinciri.html

### Barındırma (AWS)

| | |
|---|---|
| Hesap | 242872169400 |
| Bölge | us-east-1 |
| Servis | S3 statik web sitesi, bucket `nexus-ui-draft-242872169400` |
| URL | http://nexus-ui-draft-242872169400.s3-website-us-east-1.amazonaws.com |

- İlk kurulum (bir kez, tekrar çalıştırılabilir): `./scripts/setup_frontend_infra.sh`
- Elle deploy: `./scripts/deploy_frontend.sh`
- Otomatik deploy: `main` dalına `frontend/**` değişikliği push edilince `.github/workflows/deploy-frontend.yml` çalışır. AWS'ye GitHub OIDC ile bağlanır (saklanan erişim anahtarı yok). Rol `nexus-github-frontend-deploy` yalnızca bu reponun `main` dalına güvenir ve yalnızca bu bucket'a yazabilir. GitHub bu repo için token'daki `sub` değerini ID'li gönderir (`repo:eczacibasiholding@282631194/aws_hackathon@1471609910:ref:refs/heads/main`); repo yeniden açılır ya da taşınırsa rolün güven koşulu bu değere göre güncellenmelidir.
- Not: bucket herkese açık okunur ve HTTP'dir (demo için). HTTPS gerekirse önüne CloudFront konur.
