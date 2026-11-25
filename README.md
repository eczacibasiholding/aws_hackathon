# NEXUS Supply Chain Risk Intervention System

Automated pipeline for supply chain disruption detection, risk assessment, mitigation option generation, and decision support with human approval workflow.

## Project Structure

```
nexus-hackathon/
├── src/nexus/              # Main package
│   ├── __init__.py
│   ├── agents/             # Agent modules
│   │   ├── __init__.py
│   │   ├── signal_agent.py      # Signal extraction (Agent 1)
│   │   ├── risk_agent.py        # Risk assessment (Agent 2)
│   │   ├── options_agent.py     # Option generation (Agent 3)
│   │   ├── decision_agent.py    # Decision support (Agent 4)
│   │   └── orchestrator.py      # Pipeline controller
│   ├── models.py           # Pydantic data models
│   ├── data_loader.py      # Excel parsing
│   ├── llm_client.py       # LLM integration (Bedrock/mock)
│   └── app.py              # Streamlit UI
├── data/                   # Input data
│   ├── NEXUS_Agent_Veri_Seti_TEKNIK.xlsx
│   └── NEXUS_Hackathon_Veri_Seti_AnaVeri.xlsx
├── decisions/              # JSON audit records
├── tests/                  # Test suite
│   ├── test_signal_agent.py
│   ├── test_risk_agent.py
│   ├── test_options_agent.py
│   ├── test_decision_agent.py
│   └── test_integration.py
├── pyproject.toml          # Project configuration
└── requirements.txt        # Dependencies list
```

## Dependencies

- **pandas**: Data processing
- **openpyxl**: Excel file handling
- **pydantic**: Data validation and models
- **streamlit**: Web UI
- **boto3**: AWS Bedrock LLM integration
- **pytest**: Testing framework
- **hypothesis**: Property-based testing

## Installation

```bash
pip install -r requirements.txt
```

Or using pyproject.toml:

```bash
pip install -e .
```

## Development

Run tests:
```bash
pytest
```

Run Streamlit app:
```bash
streamlit run src/nexus/app.py
```

## Architecture

The system follows a multi-agent pipeline:

1. **Signal Agent**: Extracts structured information from raw signal text
2. **Risk Agent**: Calculates probability, impact, and risk scores
3. **Options Agent**: Generates mitigation options with constraints
4. **Decision Agent**: Evaluates and ranks options using ÇKKV scoring
5. **Orchestrator**: Coordinates the pipeline and manages state

## Analysis Reference Date

D0 = 25.11.2026

## Frontend (tedarik zinciri haritası)

`frontend/` statik bir sayfa: `tedarik-zinciri.html` (MapLibre GL + deck.gl). Backend bağlı değilken DEMO verisiyle çalışır.

- Kütüphaneler ve harita verisi `frontend/vendor/` altında yerel olarak durur (maplibre-gl 5.24.0, deck.gl 9.3.5, topojson-client 3.1.0, world-atlas 2.0.2 `land-50m.json`). Etkinlik ağı unpkg.com'u engellediğinde sayfa boş kalıyordu; bu yüzden CDN kullanılmaz. `scripts/deploy_frontend.sh` HTML'de dış adresten script/stil bulursa deploy'u durdurur.
- Yerelde açmak: `cd frontend && python3 -m http.server 8000` → http://localhost:8000/tedarik-zinciri.html

### Barındırma (AWS)

| | |
|---|---|
| Hesap | 242872169400 |
| Bölge | us-east-1 |
| Servis | CloudFront `E2NQT3IFBSC7MH` → özel S3 bucket `nexus-ui-draft-242872169400` (Origin Access Control) |
| URL | **https://dhqlkgzaubwcj.cloudfront.net** |

- Bucket herkese kapalıdır; nesneleri yalnızca bu CloudFront dağıtımı okuyabilir. HTTP istekleri HTTPS'e yönlenir, HSTS ve `nosniff` gibi güvenlik başlıkları AWS'nin hazır `SecurityHeadersPolicy`'si ile eklenir.
- Eski adres http://nexus-ui-draft-242872169400.s3-website-us-east-1.amazonaws.com artık içerik sunmaz, HTTPS adresine 301 ile yönlendirir.
- İlk kurulum (bir kez, tekrar çalıştırılabilir): `./scripts/setup_frontend_infra.sh`
- Elle deploy: `./scripts/deploy_frontend.sh`
- Otomatik deploy: `main` dalına `frontend/**` değişikliği push edilince `.github/workflows/deploy-frontend.yml` çalışır. AWS'ye GitHub OIDC ile bağlanır (saklanan erişim anahtarı yok). Rol `nexus-github-frontend-deploy` yalnızca bu reponun `main` dalına güvenir ve yalnızca bu bucket'a yazabilir. GitHub bu repo için token'daki `sub` değerini ID'li gönderir (`repo:eczacibasiholding@282631194/aws_hackathon@1471609910:ref:refs/heads/main`); repo yeniden açılır ya da taşınırsa rolün güven koşulu bu değere göre güncellenmelidir.
- Dosyalar `Cache-Control: no-cache` ile yüklenir. CloudFront nesneyi en fazla 1 saniye tutar, bu yüzden deploy sonrası cache temizlemeye (invalidation) gerek yoktur.

### Frontend'i başka bir repoya bağlama

Frontend repoya bağımlı değildir; AWS tarafındaki tek repo bağı deploy rolünün güven koşuludur.

1. Yeni repoya şu dosyaları kopyala: `frontend/`, `scripts/deploy_frontend.sh`, `.github/workflows/deploy-frontend.yml`.
2. Rolün hangi repolara güveneceğini ayarla (liste mevcut listenin **yerine** geçer; deploy etmeye devam edecek tüm repoları yaz):
   ```bash
   ./scripts/connect_github_repo.sh yeni-sahip/yeni-repo                       # yalnız yeni repo
   ./scripts/connect_github_repo.sh eczacibasiholding/aws_hackathon yeni-sahip/yeni-repo   # ikisi birden
   ```
   Özel (private) repoda ID'leri okuyabilmek için `GH_TOKEN` ortam değişkeni gerekir. Varsayılan dal `main`'dir, değiştirmek için `BRANCH=...`.
3. Yeni repoda `main` dalına `frontend/` altında bir değişiklik push et; workflow aynı bucket'a ve aynı HTTPS adresine deploy eder.
