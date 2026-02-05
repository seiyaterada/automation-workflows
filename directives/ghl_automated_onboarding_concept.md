# GHL Automated Onboarding & Website Generation

## Concept Overview

Use Claude Code to parse onboarding call transcripts and automatically generate entire website copy, then push to GoHighLevel via API. The GHL website template uses custom value placeholders that get populated in one API call.

**Result:** Drop in a transcript, get a fully-written website.

---

## API Validation Status: ✅ CONFIRMED (2026-01-27)

| Capability | Status | Notes |
|------------|--------|-------|
| Read Custom Values | ✅ YES | `GET /locations/{id}/customValues` |
| Create Custom Values | ✅ YES | `POST /locations/{id}/customValues` |
| Update Custom Values | ✅ YES | `PUT /locations/{id}/customValues/{valueId}` (requires `name` + `value`) |

**Key Discovery:** Field names have dots removed in templates.
- Name: `home_hero_headline`
- Template: `{{ custom_values.home_hero_headline }}`

**API Key:** Use sub-account Private Integration token with all scopes.
**Test Script:** `execution/test_ghl_custom_values.py`
**Schema:** `resources/ghl_website_schema.json` (87 fields across 8 sections)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ONE-TIME SETUP                           │
├─────────────────────────────────────────────────────────────┤
│  1. Build GHL website template                              │
│  2. Insert custom value placeholders everywhere:            │
│     {{home.hero.h1}}                                        │
│     {{home.hero.subhead}}                                   │
│     {{about.story.p1}}                                      │
│     {{services.wedding.h2}}                                 │
│     ... 100+ fields                                         │
│  3. Save as snapshot                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 PER-CLIENT (Automated)                      │
├─────────────────────────────────────────────────────────────┤
│  1. Onboarding call happens                                 │
│  2. Transcript drops into automation                        │
│  3. Claude Code reads transcript, extracts:                 │
│     - Business name, location                               │
│     - Services offered                                      │
│     - Unique selling points                                 │
│     - Voice/tone/personality                                │
│     - Target customer details                               │
│     - Differentiators                                       │
│  4. Claude Code generates ALL copy as JSON                  │
│  5. API call: Update all custom values                      │
│  6. Website is DONE                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## GHL API Capabilities (Confirmed)

### What CAN Be Done via API

| Capability | API Support | Notes |
|------------|-------------|-------|
| Create sub-account | Yes | Requires Pro Plan |
| Auto-load snapshot on creation | Yes | Pass snapshot ID in payload - loads automatically |
| Contacts CRUD | Yes | Full create/update/delete, tagging, custom fields |
| Create opportunities | Yes | Pipeline, stage, value |
| Contact custom fields | Yes | Full API support |
| Update location custom values | Yes | This is how website copy gets populated |
| Trigger workflows | Yes | Via inbound webhooks |
| Social media posts | Yes | Read/write with appropriate scopes |

### Limitations

| Capability | Status | Workaround |
|------------|--------|------------|
| Opportunity custom fields | Limited | Use contact custom fields, then GHL workflow maps them |
| Create/modify workflows | Read-only | Must be in snapshot already |
| Multiple snapshots at once | One only | Can manually add more after |

### Required Scopes

For full automation, need these scopes in Private Integration:
- `locations.write` - Create sub-accounts
- `locations/customValues.write` - Update custom values (website copy)
- `contacts.write` - Create contacts
- `opportunities.write` - Create opportunities in pipeline

---

## Claude Code's Role

**Input:** Raw transcript from onboarding call

**Processing:**
1. Extract business information (name, location, services)
2. Identify unique selling points and differentiators
3. Capture voice/tone/personality markers
4. Understand target customer
5. Generate copy for every placeholder in the template

**Output:** JSON with all custom values populated

```json
{
  "home.hero.h1": "Create Memories That Last Forever",
  "home.hero.subhead": "Michigan's Most Intimate Lakeside Wedding Venue",
  "home.hero.cta": "Schedule Your Private Tour",
  "home.about.h2": "Our Story",
  "home.about.p1": "Nestled on 40 acres of pristine woodland...",
  "home.about.p2": "Owners Mike and Sarah Thompson built this venue after...",
  "services.ceremony.h2": "Ceremony Spaces",
  "services.ceremony.p1": "Choose from three stunning ceremony locations...",
  "services.reception.h2": "Reception Hall",
  "services.reception.p1": "Our grand ballroom accommodates up to 250 guests...",
  "faq.q1": "How far in advance should we book?",
  "faq.a1": "We recommend booking 12-18 months ahead...",
  "contact.cta": "Let's Start Planning Your Perfect Day"
}
```

---

## API Call Example

One call updates all custom values:

```
POST /locations/{locationId}/customValues
Authorization: Bearer {token}
Content-Type: application/json

{
  "customValues": [
    { "key": "home.hero.h1", "value": "Create Memories That Last Forever" },
    { "key": "home.hero.subhead", "value": "Michigan's Most Intimate..." },
    // ... all 100+ fields
  ]
}
```

---

## Full Onboarding Automation Flow

```
Client fills intake form
    ↓
Webhook fires to Make/n8n
    ↓
Claude Code processes form data:
    - Determines business type
    - Selects appropriate snapshot ID
    ↓
API: Create sub-account with snapshot ID
    (Snapshot auto-loads! Workflows, funnels, calendars, etc.)
    ↓
API: Update location custom values (basic info)
    ↓
Onboarding call happens (recorded)
    ↓
Transcript sent to Claude Code
    ↓
Claude Code generates all website copy as JSON
    ↓
API: Update all custom values (100+ fields)
    ↓
Website is fully written and live
    ↓
Webhook triggers welcome workflow
    ↓
Notification to team: "New client ready"
```

---

## What Still Needs a Human

- Domain connection
- Email/SMTP setup
- Stripe/payment integration
- Photo selection/upload
- Final copy review/tweaks
- Any snapshot customization beyond template

---

## Build Sequence

1. Define custom value schema (all field names)
2. Build GHL website template with placeholders
3. Create CC prompt/script that parses transcripts → outputs JSON
4. Wire up Make/n8n automation to hit API
5. Test with real transcripts, refine prompt
6. Document for VAs (what they still do manually)

---

## Key Sources

- [Create Sub-Account with Snapshot](https://help.gohighlevel.com/support/solutions/articles/155000005762-create-a-new-sub-account-using-snapshot)
- [Creating Sub-Accounts via Zapier](https://help.gohighlevel.com/support/solutions/articles/48001207048-creating-sub-accounts-using-zapier)
- [HighLevel API Documentation](https://marketplace.gohighlevel.com/docs/)
- [SaaS Configurator API](https://help.gohighlevel.com/support/solutions/articles/155000005768-public-api-endpoints-for-saas-configurator)

---

## Use Cases

### Wedding Industry (Book More Brides example)
- Venues, photographers, DJs
- Template per business type
- Voice extracted from onboarding call
- Copy tailored to their services and USPs

### Home Services
- Landscapers, pressure washers, HVAC
- Local SEO optimized copy
- Service area specific content
- Review/trust signals built in

### Any Service Business
- Same pattern applies
- One template per niche
- CC handles the intelligence
- API handles the data entry
