# GHL Website Content Generation

## Purpose

Generate all 410 custom values for a client's GHL website from onboarding inputs (transcript, form, GBP data, existing site content, notes). Content must be cohesive across the entire site - every H1 must relate to its H2s and Ps, and pages must support each other in the silo structure.

---

## Inputs Required

### Always Required
1. **GBP Categories & Services** - Primary category, secondary categories (up to 3), full services list
2. **Business Basics** - Name, city, service area
3. **Some Form of Context** - Can be any of the following:
   - Full onboarding call transcript
   - Your speech-to-text summary of the call
   - Notes/bullet points about the business
   - Existing site content to reference

### Optional (Enhances Quality)
- **Existing Site Content** - For tone matching and unique details
- **Onboarding Form** - Structured data (years in business, certifications, etc.)
- **Special Notes** - Neighborhood info, seasonal considerations, specific instructions

### Input Reality
The amount of detail varies per client. Sometimes you have a full transcript with rich detail. Sometimes you have bullet points. The system handles both - but missing info triggers the **Confirmation Step** (see below).

---

## Site Architecture (The Silo Structure)

```
HOMEPAGE (Primary Category + City)
├── CATEGORY 01 PAGE (Secondary Category 1 + City)
│   ├── Service 01 Page (Service + City)
│   ├── Service 02 Page
│   └── ... up to Service 13
├── CATEGORY 02 PAGE (Secondary Category 2 + City)
│   ├── Service 01 Page
│   └── ...
├── CATEGORY 03 PAGE (Secondary Category 3 + City)
│   ├── Service 01 Page
│   └── ...
├── ABOUT PAGE
└── CONTACT PAGE
```

**Key Principle:** Each page has ONE clear purpose and ONE primary keyword. Pages support each other through internal linking and consistent messaging.

---

## Keyword Targeting Formulas

| Page Type | Must Contain | Natural Phrasing OK |
|-----------|-------------|---------------------|
| Homepage | Primary Category + City | Yes - make it read naturally |
| Category | Secondary Category + City | Yes |
| Service | Service Name + City | Yes |

### H1 Examples (Natural Phrasing)

**Good H1s:**
- "Landscaper services for all of Lake Charles needs" (Primary: Landscaper, City: Lake Charles)
- "Your trusted Houston plumber for over 20 years" (Primary: Plumber, City: Houston)
- "Professional HVAC services in Dallas and surrounding areas" (Primary: HVAC, City: Dallas)

**Avoid:**
- "Plumber Houston" (too robotic, doesn't read well)
- "Lake Charles Landscaper" (stilted)

**Rule:** Both the primary category and city must appear in the H1, but the phrasing should sound like something a real business would say.

---

## Content Specifications by Page Type

### HOMEPAGE (22 fields)

**Target:** 1,200-1,800 words total across all sections
**Focus:** Primary category + mention all secondary categories + preview key services

| Field | Formula/Rule |
|-------|--------------|
| `home_h1` | Must contain primary category + city, phrased naturally (see H1 examples above) |
| `home_hero_p` | 2-3 sentences. Hook addressing main pain point + what you do + city |
| `home_why_h3` | Small label like "Why Choose Us" or "Our Approach" |
| `home_why_h2` | Trust-building statement, can include city |
| `home_why_p` | 3-4 sentences on differentiators from transcript |
| `home_why_b1_title` | Benefit 1 (short, 3-5 words) |
| `home_why_b1_p` | 1-2 sentences expanding benefit 1 |
| `home_why_b2_title` | Benefit 2 |
| `home_why_b2_p` | 1-2 sentences expanding benefit 2 |
| `home_why_b3_title` | Benefit 3 |
| `home_why_b3_p` | 1-2 sentences expanding benefit 3 |
| `home_services_h3` | Label like "Our Services" or "What We Do" |
| `home_services_p` | Overview paragraph mentioning all 3 categories naturally |
| `home_projects_h3` | Label like "Our Work" or "Recent Projects" |
| `home_projects_h2` | Statement about quality/results |
| `home_contact_h2` | CTA headline (action-oriented) |
| `home_contact_p` | 1-2 sentences encouraging contact |
| `home_testimonials_h3` | Label like "What Our Customers Say" |
| `home_testimonials_p` | Brief intro to testimonials section |
| `footer_about_p` | 2-3 sentence company summary for footer |

---

### CATEGORY PAGE (34 fields each, x3 = 102 fields)

**Target:** 900-1,300 words total
**Focus:** Secondary category + preview all services under it

| Field | Formula/Rule |
|-------|--------------|
| `cat_0X_name` | Category display name (e.g., "Water Heater Services") |
| `cat_0X_home_blurb` | 2-3 sentences for homepage preview of this category |
| `cat_0X_h1` | Must contain secondary category + city, phrased naturally |
| `cat_0X_subhead` | Supporting statement expanding on H1, includes city naturally |
| `cat_0X_valueprop_h3` | Small label for value prop section |
| `cat_0X_valueprop_p` | 2-3 sentences on why choose this category of services |
| `cat_0X_cta_h3` | Bottom CTA label |
| `cat_0X_cta_h2` | Bottom CTA headline |
| `cat_0X_svc_XX_name` | Service display name (exact service name) |
| `cat_0X_svc_XX_preview` | 2-3 sentence preview of service for category page grid |

**Note:** Services inherit `valueprop` and `cta` from their parent category.

---

### SERVICE PAGE (7 fields each, x39 = 273 fields)

**Target:** ~400 words per page
**Focus:** Single service + city, conversion-focused

| Field | Formula/Rule |
|-------|--------------|
| `cat_0X_svc_XX_h1` | Must contain service name + city, phrased naturally |
| `cat_0X_svc_XX_subhead` | Expand on H1, address primary pain point |
| `cat_0X_svc_XX_h2` | Main benefit or "Why [Service]?" |
| `cat_0X_svc_XX_h3_1` | First subtopic (problem or process step) |
| `cat_0X_svc_XX_p1` | 3-4 sentences expanding h3_1 |
| `cat_0X_svc_XX_h3_2` | Second subtopic (solution or benefit) |
| `cat_0X_svc_XX_p2` | 3-4 sentences expanding h3_2 |

---

### ABOUT PAGE (12 fields)

| Field | Formula/Rule |
|-------|--------------|
| `about_hero_subhead` | `[Primary Category] experts in [City]` or similar |
| `about_h2` | Trust-building headline about company |
| `about_p1` | Company story paragraph 1 (founding, experience) |
| `about_p2` | Company story paragraph 2 (approach, values) |
| `about_mission_h2` | Mission/values headline |
| `about_mission_p` | Mission statement paragraph |
| `about_value_1` | Core value 1 (short phrase) |
| `about_value_2` | Core value 2 |
| `about_value_3` | Core value 3 |
| `about_team_p` | Paragraph about team expertise |
| `about_cta_h2` | CTA headline |
| `about_cta_p` | CTA supporting text |

---

### CONTACT PAGE (1 field)

| Field | Formula/Rule |
|-------|--------------|
| `contact_p` | 1-2 sentences encouraging contact, mentions responsiveness |

---

## Writing Guidelines

### Voice & Tone
- **5th-grade reading level** - short, clear sentences
- **Conversational but structured** - sounds like a real local expert
- **Helpful, not salesy** - give value, not just pitches
- **Based on transcript** - match the owner's actual way of speaking

### Content Structure Pattern
1. **Hook** - Address the pain point immediately
2. **Preview** - What this page covers
3. **Body** - Helpful info mixed with service descriptions
4. **Local signals** - Neighborhoods, landmarks, seasonal issues
5. **CTA** - Clear next step

### Keyword Integration
- Target keyword in: H1, first paragraph, naturally throughout
- **1-2% keyword density** for primary keyword
- Use semantic variations naturally
- H2s should be exact-match for services/categories

### Local SEO Signals (weave throughout)
- Neighborhood names
- Local landmarks
- Service area mentions
- Seasonal/weather-related issues
- Community involvement references

---

## WORDS TO NEVER USE

These words trigger AI-detection and sound generic. Never use them:

embark, look no further, navigating, picture this, top-notch, unleash, unlock, unveil, we've got you covered, transition, transitioning, crucial, delve, daunting, deep dive, dive in, realm, ensure, in conclusion, in summary, optimal, assessing, firstly, strive, striving, furthermore, moreover, comprehensive, we know, we understand, testament, captivating, eager, refreshing, edge of my seat, breath of fresh air, to consider, it is important to consider, there are a few considerations, it's essential to, vital, it's important to note, it should be noted, to sum up, secondly, lastly, in terms of, with regard to, it's worth mentioning, it's interesting to note, significantly, notably, essentially, as such, therefore, thus, interestingly, in essence, noteworthy, bear in mind, it's crucial to note, one might argue, it's widely acknowledged, predominantly, from this perspective, in this context, this demonstrates, arguably, it's common knowledge, undoubtedly, this raises the question, in a nutshell, unveiled

---

## Content Cohesion Rules

### Cross-Page Consistency
1. **Same terminology** - If transcript says "water heater" not "hot water heater", use that everywhere
2. **Same differentiators** - If "family-owned since 1985" is mentioned, reference it on multiple pages
3. **Same tone** - Casual transcript = casual content throughout
4. **Logical flow** - Homepage previews categories → Category pages expand → Service pages go deep

### Parent-Child Relationships
- Category `valueprop` and `cta` fields are inherited by all services under that category
- Service `preview` on category page should tease what's on the full service page
- Homepage `home_blurb` for each category should align with category page content

### Internal Linking Language
- Service previews should naturally lead to "Learn more about [service_name]"
- Category overviews should reference "our [category_name] services"

---

## Generation Process

### Step 1: Extract from Inputs

From whatever context is provided, extract:

- Business name, city, service area
- Primary category, secondary categories, all services
- Key differentiators (years in business, family-owned, certifications, etc.)
- Owner's voice/tone
- Any specific neighborhoods or local references
- Seasonal considerations

### Step 2: Confirmation Step (REQUIRED - happens in chat)

Before generating content, review what you have and what's missing. Present to the user:

```
## Ready to Generate - Confirmation Needed

**What I have:**
- Business: [name]
- Location: [city]
- Primary Category: [x]
- Secondary Categories: [x, y, z]
- Services: [list]
- Differentiators found: [years in business, family-owned, etc.]
- Tone: [casual/professional/etc.]

**What I'm missing (please fill in):**
1. [Specific question about missing info]
2. [Another question]
3. ...

**Or confirm:** If the above looks correct and you're OK with me filling gaps creatively, say "go ahead."
```

**Common gaps to ask about:**

| If Missing | Ask |
|------------|-----|
| Years in business | "How long has the business been operating?" |
| Key differentiator | "What makes this business different from competitors?" |
| Service area details | "Any specific neighborhoods or areas to mention?" |
| Certifications/licenses | "Any certifications, licenses, or credentials to highlight?" |
| Team info | "Owner-operated? Small team? Any team details for About page?" |
| Seasonal considerations | "Any seasonal services or busy periods to mention?" |

**Rule:** Don't generate all 410 fields until the user confirms or answers the questions.

### Step 3: Build the Framework

- Assign services to categories (max 13 per category)
- Create keyword targets for each page
- Identify 3 core differentiators/benefits

### Step 4: Generate Homepage First
- Sets the tone for entire site
- Establishes the differentiators
- Previews all categories

### Step 5: Generate Categories (in order)

- Expand on homepage preview
- Create service previews that tease full pages

### Step 6: Generate Service Pages

- Go deep on single topic
- Reference parent category naturally
- Include local signals

### Step 7: Generate About & Contact

- Align with established tone
- Reinforce differentiators

### Step 8: Cohesion Check
- Read through all H1s - do they form logical hierarchy?
- Read through all CTAs - are they consistent?
- Check terminology consistency
- Verify no banned words used

---

## Output Format

Generate JSON with all 410 fields:

```json
{
  "home_h1": "...",
  "home_hero_p": "...",
  ...
  "cat_01_name": "...",
  "cat_01_svc_01_h1": "...",
  ...
  "about_hero_subhead": "...",
  ...
  "contact_p": "..."
}
```

---

## Execution Script

`execution/generate_ghl_website_content.py` (to be created)

Inputs: Transcript file, form data, GBP data
Output: JSON file with all 410 custom values
API: Uses Claude API for generation with this directive as system prompt

---

## Related Files

- `resources/ghl_custom_values_final.txt` - Complete field list with `{{ custom_values.xxx }}` format
- `resources/ghl_auto_website_material/ghl_content_seo_course/` - Source training material
- `execution/test_ghl_custom_values.py` - API validation script
- `directives/ghl_automated_onboarding_concept.md` - Overall automation concept
