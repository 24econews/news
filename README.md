# Economy Digest

Automated daily economic news digest for Argentina and Brazil. Fetches RSS feeds, filters relevant articles with Claude AI, summarizes them, and publishes Markdown digests in both the original language and English.

## What it does

1. **Ingests** RSS feeds from major financial outlets in each country
2. **Filters** articles for economic relevance using Claude (Anthropic API)
3. **Summarizes** each article into 3–5 sentences with key figures
4. **Builds** a dated Markdown digest (`digests/digest_YYYY-MM-DD.md`)
5. **Translates** the digest to English (`digest_YYYY-MM-DD.en.md`)
6. **Commits** the new files back to this repository automatically

Digests are stored in:
- `digests/` — Argentina
- `digests/brazil/` — Brazil

---

## How to add a new country

1. **Create a config file** `config_<country>.yaml` at the repo root:

   ```yaml
   country:
     slug: <country>         # lowercase, no spaces
     name: <Display Name>
     digest_header: "Economic Digest <Country>"

   digest:
     max_articles: 10
     output_dir: digests/<country>/
     db_path: economy_<country>.db

   rss_feeds:
     - name: Source Name
       url: https://example.com/feed.xml
   ```

2. **Add country settings** in `scheduler/daily_pipeline.py` inside `COUNTRY_SETTINGS`:

   ```python
   "country_slug": {
       "config_file": "config_<country>.yaml",
       "relevance_prompt": None,   # or a custom prompt string
       "summarizer_prompt": None,  # or a custom prompt string
   },
   ```

3. **Register the country** in `scheduler/run_all_countries.py`:

   ```python
   COUNTRIES = ["argentina", "brazil", "country_slug"]
   ```

4. **Add a pipeline step** in `.github/workflows/daily_digest.yml`:

   ```yaml
   - name: Run <Country> pipeline
     env:
       ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
     run: |
       echo "::group::<Country> pipeline"
       python scheduler/daily_pipeline.py --country <country_slug>
       echo "::endgroup::"
   ```

---

## GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (from console.anthropic.com) |

The `GITHUB_TOKEN` secret is provided automatically by GitHub Actions — no setup needed.

---

## How the automation works

A GitHub Actions workflow (`.github/workflows/daily_digest.yml`) runs every day at **10:00 UTC** (7:00 AM Argentina/Brazil time, UTC-3).

The workflow:
1. Checks out the repository
2. Installs Python dependencies (including `certifi` for SSL)
3. Runs the pipeline for each country sequentially
4. Commits any new digest files to the repo with a dated message
5. Pushes back to `main`

The workflow can also be triggered manually from the **Actions** tab in GitHub via the "Run workflow" button.

When running locally, the pipeline still performs the git commit/push step automatically. When running in GitHub Actions (detected via the `GITHUB_ACTIONS` environment variable), the pipeline skips its own git push and lets the workflow handle it.

---

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
python scheduler/daily_pipeline.py --country argentina
python scheduler/daily_pipeline.py --country brazil
# or run both:
python scheduler/run_all_countries.py
```
