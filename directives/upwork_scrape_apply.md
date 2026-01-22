# Upwork Job Scraping & Proposal Generation Pipeline

## Goal
Scrape Upwork jobs matching AI/automation keywords, generate personalized cover letters and proposals using Claude Opus 4.5, optionally create Google Docs for each proposal, and output to Google Sheets or CSV.

## Architecture

This pipeline follows the 3-layer DOE pattern:
1. **Directive** (this file): SOP documenting inputs, execution tools, output format, edge cases
2. **Execution scripts**: Deterministic Python scripts in `execution/`
3. **Orchestration**: AI agent reads directives, calls scripts, handles errors

## Execution Scripts

### 1. Upwork Scraper (`execution/upwork_apify_scraper.py`)

Uses Apify's `upwork-vibe~upwork-job-scraper` actor (free tier).

**Free tier constraints:**
- Only supports `limit`, `fromDate`, `toDate` filters
- All other filtering done post-scrape

**CLI:**
```bash
python execution/upwork_apify_scraper.py \
  --limit 50 --days 1 --verified-payment \
  --min-spent 1000 --experience intermediate,expert \
  -o .tmp/upwork_jobs.json
```

**Arguments:**
| Arg | Description |
|-----|-------------|
| `--limit N` | Max jobs to scrape (default: 50) |
| `--days N` | Days back to search (default: 1) |
| `--verified-payment` | Filter to verified payment only |
| `--min-spent N` | Min client total spent (USD) |
| `--experience` | Levels: entry,intermediate,expert |
| `-o FILE` | Output JSON file |

**Output format:**
```json
{
  "id": "job_uid",
  "title": "Job Title",
  "description": "Full description",
  "url": "https://www.upwork.com/jobs/~{id}",
  "apply_url": "https://www.upwork.com/nx/proposals/job/~{id}/apply/",
  "budget": "$500 (fixed)" or "$15-$35/hr",
  "experience_level": "Intermediate",
  "skills": "Python, Automation",
  "client": {
    "country": "United States",
    "total_spent": 50000,
    "total_hires": 25
  }
}
```

---

### 2. Proposal Generator (`execution/upwork_proposal_generator.py`)

Generates proposals using Claude Opus 4.5 with extended thinking.

**CLI:**
```bash
# With Google APIs
python execution/upwork_proposal_generator.py \
  --input .tmp/upwork_jobs.json --workers 5 -o .tmp/proposals.json

# Without Google APIs (CSV output for manual import)
python execution/upwork_proposal_generator.py \
  --input .tmp/upwork_jobs.json --workers 5 --no-sheet -o .tmp/proposals.json
```

**Arguments:**
| Arg | Description |
|-----|-------------|
| `--input FILE` | Input JSON from scraper |
| `--output FILE` | Output JSON file |
| `--workers N` | Parallel LLM calls (default: 5) |
| `--skip-docs` | Skip Google Docs creation |
| `--no-sheet` | Skip all Google APIs, output CSV |
| `--sheet-id ID` | Append to existing sheet |

**Output columns:**
Title, URL, Budget, Experience, Skills, Category, Client Country, Client Spent, Client Hires, Connects, Apply Link, Cover Letter, Proposal Doc

---

## Setup

### Environment Variables (`.env`)
```
APIFY_API_TOKEN=your_token
ANTHROPIC_API_KEY=your_key
```

### Google API (optional)
Place `credentials.json` (service account) in project root. Enable:
- Google Sheets API
- Google Docs API (if using doc generation)
- Google Drive API

### Python Dependencies
```bash
pip install anthropic google-auth google-auth-oauthlib google-api-python-client requests python-dotenv
```

---

## Usage Examples

### Full pipeline (no Google APIs)
```bash
# Step 1: Scrape jobs
python execution/upwork_apify_scraper.py --limit 20 --days 1 -o .tmp/jobs.json

# Step 2: Generate proposals (CSV output)
python execution/upwork_proposal_generator.py --input .tmp/jobs.json --workers 3 --no-sheet -o .tmp/proposals.json

# Step 3: Import .tmp/proposals.csv to Google Sheets manually
```

### With Google Sheets
```bash
# Ensure Google APIs are enabled for your service account
python execution/upwork_proposal_generator.py --input .tmp/jobs.json --workers 3 -o .tmp/proposals.json
```

---

## Performance Benchmarks

| Operation | Time |
|-----------|------|
| Scraping 50 jobs | 30-60s |
| 5 jobs with 2 workers | ~2 min |
| Opus 4.5 per call (8000 thinking tokens) | 30-60s |

---

## Edge Cases & Learnings

### Apify Actor
- Free tier has limited filtering - must filter post-scrape
- Job ID is in `uid` field, not `id`
- Budget structure: `{fixedBudget: X, hourlyRate: {min, max}}`
- Poll status every 3s, timeout after 5 min

### Google APIs
- Service account needs APIs enabled in Cloud Console
- Use `--no-sheet` flag if API access fails
- SSL errors on parallel doc creation - use semaphore

### Claude API
- Opus 4.5 model: `claude-opus-4-5-20251101`
- Extended thinking with 8000 token budget
- Parallelize with ThreadPoolExecutor (reduce workers if rate limited)

---

## Troubleshooting

### "APIFY_API_TOKEN not found"
Add token to `.env` file.

### "caller does not have permission" (Google)
1. Enable APIs in Google Cloud Console
2. Or use `--no-sheet` flag

### Rate limits on Anthropic API
Reduce `--workers` to 2-3.
