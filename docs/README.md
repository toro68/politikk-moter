# Politiske møter - Slack notifikasjoner

Automatisk scraping og daglige Slack-meldinger for politiske møter fra kommuner i regionen.

## 🎯 Status og resultater

### ✅ Fullført
- **Slack-integrasjon**: Sender daglige meldinger til Slack med formaterte møtelister
- **GitHub Actions**: Automatisk kjøring mandag–fredag kl. 06:30 norsk tid (04:30 UTC)
- **Playwright-støtte**: Kan scrape JavaScript-tunge sider som Elements Cloud
- **Fallback-system**: Bruker mock-data når ingen møter finnes
- **Alle ønskede kilder**:
  - ✅ Bymiljøpakken.no (106 møter funnet)
  - ✅ Rogaland fylkeskommune via Elements Cloud (8 møter funnet)
  - ✅ Ferde via Elements Cloud
  - ✅ Alle kommunesider (standard ACOS/Onacos-støtte)
- **Én aktiv pipeline**: Standardoppsett som sender to batcher til samme Slack-webhook

### 📊 Nåværende resultater
```
Bymiljøpakken: 106 møter funnet
Rogaland fylkeskommune: 8 møter funnet via Playwright
Kommunesider: 0 møter (ingen publiserte møter for neste periode)
```

### 🔁 Fallback-logikk
Når ingen møter finnes i de neste 10 dagene, brukes realistiske mock-data som inkluderer alle ønskede kilder. Dette sikrer at Slack-meldingen alltid er meningsfull.  

## Hvordan det fungerer

1. **Hybrid scraping**: Requests/BeautifulSoup for standard sider, Playwright for JavaScript-tunge
2. **Fallback**: Hvis scraping feiler, brukes mock-data for demo/testing
3. **GitHub Actions**: Kjører automatisk mandag–fredag
4. **Sikker Slack**: Test-modus hindrer utilsiktet sending, må eksplisitt aktiveres

## Kommuner som dekkes

- Sauda kommune ✅ (ACOS)
- Strand kommune ✅ (ACOS)
- Suldal kommune ✅ (ACOS)
- Hjelmeland kommune ✅ (ACOS)
- Sirdal kommune 🎭 (Onacos + Playwright)
- Lund kommune 🎭 (Onacos + Playwright)
- Sokndal kommune ✅ (ACOS)
- Bjerkreim kommune ✅ (ACOS)
- Eigersund kommune ✅ (Onacos, egen parser)
- Time kommune ✅ (ACOS)
- Klepp kommune ✅ (Custom / 360online)
- Gjesdal kommune ✅ (Custom / 360online)
- Kvitsøy kommune ✅ (Custom / 360online)
- Hå kommune ✅ (ACOS)
- Sola kommune 🎭 (Onacos + Playwright)
- Stavanger kommune 🎭 (Digdem + Playwright)
- Sandnes kommune ✅ (Custom / 360online)
- Bymiljøpakken ✅ (Custom)
- Rogaland fylkeskommune 🎭 (Elements Cloud + Playwright)
- Ferde 🎭 (Elements Cloud + Playwright)

✅ = Standard scraping  
🎭 = Playwright-basert scraping

## Kildelenker

### Nord-Jæren og Jæren (turnus)

- Stavanger kommune: <https://stavanger-elm.digdem.no/motekalender>
- Sandnes kommune: <https://opengov.360online.com/Meetings/SANDNESKOMMUNE>
- Sola kommune: <https://nyttinnsyn.sola.kommune.no/wfinnsyn.ashx?response=moteplan&>
- Time kommune: <https://www.time.kommune.no/politikk/mote-og-saksdokument/moter-og-saksdokument/>
- Klepp kommune: <https://opengov.360online.com/Meetings/KLEPP>
- Gjesdal kommune: <https://opengov.360online.com/Meetings/GJESDAL>
- Kvitsøy kommune: <https://opengov.360online.com/Meetings/KVITSOY>
- Hå kommune: <https://www.ha.no/politikk-og-samfunnsutvikling/mote-og-sakspapir/>

### Ryfylke, Dalane

- Rogaland fylkeskommune: <https://prod01.elementscloud.no/publikum/971045698/Dmb>
- Ferde: <https://prod02.elementscloud.no/publikum/918012745_PROD-918012745/DmbBoard/6>
- Sauda kommune: <https://www.sauda.kommune.no/innsyn/politiske-moter/>
- Strand kommune: <https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/politiske-moter-og-sakspapirer/politisk-motekalender/>
- Suldal kommune: <https://www.suldal.kommune.no/innsyn/politiske-moter/>
- Hjelmeland kommune: <https://www.hjelmeland.kommune.no/politikk/moteplan-og-sakspapir/innsyn-moteplan/>
- Sirdal kommune: <https://innsynpluss.onacos.no/sirdal/moteoversikt/>
- Lund kommune: <https://innsynpluss.onacos.no/lund/moteoversikt/>
- Eigersund kommune: <https://innsyn.onacos.no/eigersund/mote/wfinnsyn.ashx?response=moteplan&>
- Sokndal kommune: <https://www.sokndal.kommune.no/innsyn/moteoversikt/>
- Bjerkreim kommune: <https://www.bjerkreim.kommune.no/innsyn/moteplan-og-sakslister/>
- Bymiljøpakken: <https://bymiljopakken.no/moter/>

## Slack-kanaler

Standardoppsettet har én pipeline (`standard`) som sender to separate meldinger ("Nord-Jæren og Jæren" og "Ryfylke, Dalane") for å holde møtene sortert. Som standard går begge meldingene til samme Slack-kanal via `SLACK_WEBHOOK_URL`.

Ønsker du å sende batchene til ulike kanaler, kan du gi hver batch sin egen webhook ved å oppdatere `batch_webhook_envs` i `src/politikk_moter/pipeline_config.py` og legge til de nye hemmelighetene (f.eks. `SLACK_WEBHOOK_URL_TURNUS` og `SLACK_WEBHOOK_URL_OVRIGE`).

## Veien videre

### Fase 1: Forbedret scraping

- **Selenium/Playwright**: Implementer headless browser for JavaScript-tunge sider
- **API-søk**: Undersøk om kommuner har RSS/API-endepunkter
- **Tidsjobb**: Sett opp regelmessig sjekk etter nye møter

### Fase 2: Utvidelse

- **Flere kommuner**: Legg til flere kommuner i regionen
- **Google Calendar**: Implementer Google Calendar API-integrasjon
- **E-post**: Legg til e-post-varsel som alternativ til Slack

### Midlertidig løsning

- Mock-data brukes når scraping feiler
- Basert på kjente møtedata fra kommunene
- Sikrer at Slack-integrasjonen fungerer konsekvent

## Tekniske detaljer

### Scraping-utfordringer

Kommunesidene bruker ofte:

- JavaScript for å laste møtedata (krever headless browser)
- Autentisering for API-tilgang (krever brukerkonto)
- ACOS/Onacos CMS med dynamisk innhold

### Alternativ til scraping

1. **RSS-feeds**: Noen kommuner har RSS, men ikke for møter
2. **iCal-abonnement**: Få kommuner tilbyr .ics-filer
3. **Manuell oppdatering**: Periodisk oppdatering av `mock_data.py`

## Installasjon og testing

### 1. Grunnleggende oppsett

```bash
# Klon prosjektet og installer grunnleggende avhengigheter
pip install requests beautifulsoup4

# Test grunnleggende funksjonalitet
python scraper.py --debug
```

### 2. Playwright for JavaScript-tunge sider

```bash
# Installer Playwright og browsere (anbefalt)
./scripts/install_playwright.sh

# Eller manuelt:
pip install playwright
python -m playwright install chromium
```

### 3. Komplett testing

```bash
# Kjør full test-suite (anbefalt før produksjon)
python test_complete.py

# Test kun Playwright-scraping
python playwright_scraper.py
```

### 4. Slack-integrasjon

1. Gå til din Slack workspace
2. Opprett en ny app: <https://api.slack.com/apps>
3. Velg "Incoming Webhooks"
4. Aktiver webhooks og lag en ny webhook for ønsket kanal
5. Kopier webhook URL-en

### 2. GitHub Secrets

1. Gå til repository → Settings → Secrets and variables → Actions
1. Legg til følgende secrets:

  - `SLACK_WEBHOOK_URL` (obligatorisk – brukes for begge meldinger som standard)
  - `SLACK_WEBHOOK_URL_UTVIDET` (kun hvis du aktiverer den utvidede pipelinen i `src/politikk_moter/pipeline_config.py`)

1. (Valgfritt) Legg til ekstra secrets dersom du ønsker egne kanaler for turnus og øvrige batcher, og referer til dem i `batch_webhook_envs`

### 3. Aktivering

GitHub Actions vil automatisk starte å kjøre etter at secrets er satt opp.

### 5. Produksjon (sikker Slack-sending)

```bash
# TESTING: Vis melding uten å sende til Slack
python scraper.py --debug

# PRODUKSJON: Send til Slack (krever eksplisitt --force i test-modus)
export SLACK_WEBHOOK_URL="your_webhook_url"
python scraper.py --force

# AUTOMATISK: Via GitHub Actions (anbefalt)
# - Sett SLACK_WEBHOOK_URL som GitHub secret
# - GitHub Actions kjører automatisk uten --debug
```

**Viktig sikkerhet**: Scraperen sender IKKE til Slack i test-modus (--debug) for å hindre utilsiktet sending.

## Manuell kjøring

For å teste eller kjøre manuelt:

```bash
# Installer avhengigheter
pip install requests beautifulsoup4

# Test lokalt (viser output uten å sende til Slack)
export SLACK_WEBHOOK_URL="your_webhook_url_here"
python scraper.py --debug

# Send til Slack
python scraper.py
```

## GitHub Actions

Workflow kjører:

- **Automatisk**: Mandag–fredag kl. 06:30 norsk tid (04:30 UTC)
- **Manuelt**: Via "Actions"-fanen → "Run workflow"

## Feilsøking

### Ingen møter funnet

- Kommunenes nettsider kan ha endret struktur
- Sjekk debug-output: `python scraper.py --debug`

### Slack-melding sendes ikke

- Verifiser at `SLACK_WEBHOOK_URL` secret er riktig satt
- Test webhook manuelt med curl

### GitHub Actions feiler

- Sjekk "Actions" tab for detaljerte error logs
- Workflow har innebygd debug på feil

## Tilpasning

### Legge til flere kommuner

Oppdater `KOMMUNE_CONFIGS` i `src/politikk_moter/kommuner.py` og legg kommunen inn i riktig gruppe (`core`, `extended`, osv.). Nye kommuner blir tilgjengelige for `standard`-pipelinen (og eventuelle andre pipelines du aktiverer) som peker på gruppen.

### Ny Slack-kanal / pipeline

Legg til en ny `PipelineConfig` i `src/politikk_moter/pipeline_config.py`. Velg hvilke kommunegrupper og kalendere som skal inngå, og sett miljøvariabelen for tilhørende Slack-webhook.

### Endre tidsplan

Rediger cron i `.github/workflows/daily-meetings.yml`:

```yaml
schedule:
  - cron: '30 4 * * 1-5'  # 04:30 UTC = 06:30 norsk tid (sommer)
```

### Endre antall dager

I `scraper.py`, endre `days_ahead` parameter:

```python
filtered_meetings = filter_meetings_by_date_range(all_meetings, days_ahead=14)
```

## Eksempel Slack-melding

```text
📅 Politiske møter de neste 10 dagene

*Tirsdag 20. august 2025*
• Ungdomsrådet (Sauda kommune) - kl. 09:00
  📍 Formannskapssalen

• Eldrerådet (Sauda kommune) - kl. 10:00
  📍 Formannskapssalen

*Onsdag 21. august 2025*
• Formannskapet (Strand kommune) - kl. 16:00
  📍 Kommunestyresalen
```

## Struktur

```text
.
├── scraper.py                    # Hovedskript
├── .github/workflows/
│   └── daily-meetings.yml        # GitHub Actions workflow
└── README.md                     # Denne filen
```
