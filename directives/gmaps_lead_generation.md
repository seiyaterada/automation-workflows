# Google Maps Lead Generation Pipeline

## Goal
Scrape businesses from Google Maps, enrich each with deep contact extraction from their websites using Claude AI, and save to a Google Sheet with automatic deduplication.

## Architecture

### Layer 1: Google Maps Scraping
- Uses Apify's `compass/crawler-google-places` actor
- Accepts dynamic search queries (e.g., "plumbers in Austin TX")
- Returns structured business data: name, address, phone, website, rating, reviews, place_id, google_maps_url

### Layer 2: Website Contact Extraction
For each business with a website:
1. HTTP fetch the main page (using httpx)
2. Convert HTML to markdown (using html2text)
3. Find and fetch up to 5 additional pages matching contact patterns
4. Search DuckDuckGo for `"{business name} owner email contact"`
5. Combine all content and send to Claude 3.5 Haiku for structured extraction

### Layer 3: Claude Extraction Schema
Claude extracts this JSON structure:
- emails, phone_numbers, addresses
- social_media (facebook, twitter, linkedin, instagram, youtube, tiktok)
- owner_info (name, title, email, phone, linkedin)
- team_members (array of contacts)
- business_hours
- additional_contacts

### Layer 4: Google Sheets Integration
- Uses gspread with OAuth credentials
- Appends to existing sheet via --sheet-url
- Implements deduplication using lead_id (MD5 hash of name|address)
- Tracks metadata: scraped_at, search_query, pages_scraped, search_enriched, enrichment_status

## Setup

### Prerequisites
1. **Apify API Token**: Sign up at https://apify.com and get your API token
2. **Anthropic API Key**: Sign up at https://anthropic.com and get your API key
3. **Google Cloud Service Account**: 
   - Create a project at https://console.cloud.google.com
   - Enable Google Sheets API and Google Drive API
   - Create a service account and download credentials.json
4. **Google Sheet**: Create a blank sheet and share it with your service account email (found in credentials.json as `client_email`)

### Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install apify-client python-dotenv httpx html2text anthropic beautifulsoup4 gspread google-auth
```

### Configuration
Create `.env` file with:
```
APIFY_API_TOKEN=your_token_here
ANTHROPIC_API_KEY=your_key_here
```

Place `credentials.json` in the project root.

## Usage

### Basic Usage
```bash
python3 execution/gmaps_lead_pipeline.py --search "plumbers in Austin TX" --limit 10 \
  --sheet-url "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
```

### Arguments
- `--search`: Search query (required)
- `--limit`: Number of results to scrape (default: 10)
- `--sheet-url`: Google Sheet URL (required)
- `--email`: Email to share new sheet with (optional, if creating new sheet)

### Standalone Scripts
```bash
# Test Google Maps scraper
python3 execution/scrape_google_maps.py --search "roofers in Austin TX" --limit 3

# Test website contact extractor
python3 execution/extract_website_contacts.py --url "https://example.com" --name "Business Name"
```

## Output Schema (36 columns)
lead_id, scraped_at, search_query, business_name, category, address, city, state, zip_code, country, phone, website, google_maps_url, place_id, rating, review_count, price_level, emails, additional_phones, business_hours, facebook, twitter, linkedin, instagram, youtube, tiktok, owner_name, owner_title, owner_email, owner_phone, owner_linkedin, team_contacts, additional_contact_methods, pages_scraped, search_enriched, enrichment_status

## Error Handling & Edge Cases

### Known Issues
1. **403/503 Errors**: ~10-15% of sites return these errors. The pipeline handles gracefully and saves the lead with GMaps data only.
2. **Facebook URLs**: Always return 400 errors. These are skipped in web search results.
3. **Broken DNS**: Some sites have DNS issues. These are caught and marked as errors.
4. **Claude Response Format**: Sometimes returns dicts instead of strings for fields like business_hours. A stringify_value() helper could be added if needed.
5. **Service Account Quota**: Service accounts have no storage. Always use an existing sheet shared with the service account.

### Performance
- Uses ThreadPoolExecutor with 3 workers for parallel website enrichment
- Limits contact pages to 5 max per site
- Truncates content to 50K chars before sending to Claude
- DuckDuckGo HTML search is free and doesn't block

## Cost Estimates
- Apify: ~$0.01-0.02 per business
- Claude Haiku: ~$0.002 per extraction
- Everything else: Free
- **Total: ~$0.015-0.025 per lead**

## Troubleshooting

### "APIFY_API_TOKEN not found"
Ensure `.env` file exists with the token.

### "credentials.json not found"
Place the Google Cloud service account credentials in the project root.

### "The caller does not have permission"
Share the Google Sheet with the service account email found in credentials.json.

### "The user's Drive storage quota has been exceeded"
Service accounts have no storage. Use --sheet-url with an existing sheet shared with the service account.

## Success Criteria
✅ Pipeline runs without errors
✅ Leads appear in Google Sheet with populated contact fields
✅ Running the same command again shows "Skipping duplicate" messages
✅ Deduplication works based on lead_id (MD5 of name|address)
