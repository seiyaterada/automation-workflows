#!/usr/bin/env python3
"""
Upwork Proposal Generator using Claude Opus 4.5 with extended thinking.

Generates personalized cover letters and proposals for Upwork jobs,
creates Google Docs for each proposal, and outputs to a Google Sheet.

Usage:
    python execution/upwork_proposal_generator.py \
        --input .tmp/upwork_jobs.json \
        --workers 5 \
        -o .tmp/upwork_proposals.json
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents'
]

# Semaphore for serializing Google Doc creation (prevents SSL errors)
doc_creation_semaphore = threading.Semaphore(1)

# Cover letter template
COVER_LETTER_TEMPLATE = """Hi. I work with {paraphrase} daily & just built a {thing}. Free walkthrough: {doc_link}"""

# Proposal template
PROPOSAL_TEMPLATE = """Hey{name}.

I spent ~15 minutes putting this together for you. In short, it's how I would create your {paraphrase} end to end.

I've worked with $MM companies like Anthropic (yes—that Anthropic) and I have a lot of experience designing/building similar workflows.

Here's a step-by-step, along with my reasoning at every point:

## My proposed approach

{steps}

## What you'll get

{deliverables}

## Timeline

{timeline}"""


def get_anthropic_client():
    """Get Anthropic client with API key from environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def get_google_services():
    """Get Google API services using service account credentials."""
    creds_path = Path(__file__).parent.parent / "credentials.json"
    
    if not creds_path.exists():
        print(f"ERROR: credentials.json not found at {creds_path}")
        sys.exit(1)
    
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    
    sheets_service = build('sheets', 'v4', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return sheets_service, docs_service, drive_service


def generate_proposal_content(client: anthropic.Anthropic, job: dict) -> dict:
    """
    Generate proposal content using Claude Opus 4.5 with extended thinking.
    
    Returns dict with:
        - paraphrase: 2-4 word project description
        - thing: 2-5 word recent work description
        - steps: 4-6 numbered steps with reasoning
        - deliverables: 2-3 concrete deliverables
        - timeline: Realistic estimate
    """
    job_title = job.get("title", "")
    job_description = job.get("description", "")[:3000]  # Limit description length
    skills = job.get("skills", "")
    
    prompt = f"""Analyze this Upwork job and generate a personalized proposal.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

REQUIRED SKILLS: {skills}

Generate the following in JSON format:
{{
    "paraphrase": "2-4 word paraphrase of what this project is about (e.g., 'AI automation workflows', 'data scraping pipelines')",
    "thing": "2-5 word description of a relevant thing I recently built (e.g., 'a similar ETL pipeline', 'an AI agent system')",
    "steps": [
        {{"step": "Step description", "why": "Why this approach"}}
    ],
    "deliverables": ["Deliverable 1", "Deliverable 2", "Deliverable 3"],
    "timeline": "Realistic timeline estimate in conversational tone"
}}

IMPORTANT:
- Steps should be 4-6 items, each with specific tools mentioned (n8n, Claude API, Zapier, Make, Python, etc.)
- Deliverables should be concrete and specific to this job
- Timeline should be realistic and conversational
- Focus on AI, automation, and workflow building since that's my specialty
- Make it sound like I've actually thought about their specific problem"""

    try:
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=16000,
            thinking={
                "type": "enabled",
                "budget_tokens": 8000
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract text from response
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content = block.text
                break
        
        # Parse JSON from response
        # Try to find JSON in the response
        if "{" in text_content:
            json_start = text_content.find("{")
            json_end = text_content.rfind("}") + 1
            json_str = text_content[json_start:json_end]
            return json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")
            
    except Exception as e:
        print(f"  Error generating proposal: {e}")
        # Return default values on error
        return {
            "paraphrase": "automation workflows",
            "thing": "a similar system",
            "steps": [
                {"step": "Analyze requirements", "why": "Understand the full scope"},
                {"step": "Design solution architecture", "why": "Plan before building"},
                {"step": "Implement core functionality", "why": "Start with essentials"},
                {"step": "Test and iterate", "why": "Ensure quality"},
            ],
            "deliverables": ["Working solution", "Documentation", "Support"],
            "timeline": "1-2 weeks depending on complexity"
        }


def generate_cover_letter(content: dict, doc_link: str) -> str:
    """Generate a short cover letter (~35 words) for Upwork."""
    return COVER_LETTER_TEMPLATE.format(
        paraphrase=content.get("paraphrase", "automation workflows"),
        thing=content.get("thing", "a similar system"),
        doc_link=doc_link
    )


def generate_full_proposal(content: dict, client_name: str = "") -> str:
    """Generate the full proposal text for the Google Doc."""
    name_part = f" {client_name}" if client_name else ""
    
    # Format steps
    steps_list = content.get("steps", [])
    if isinstance(steps_list, list):
        steps_formatted = "\n\n".join([
            f"**{i+1}. {s.get('step', s) if isinstance(s, dict) else s}**\n{s.get('why', '') if isinstance(s, dict) else ''}"
            for i, s in enumerate(steps_list)
        ])
    else:
        steps_formatted = str(steps_list)
    
    # Format deliverables
    deliverables = content.get("deliverables", [])
    if isinstance(deliverables, list):
        deliverables_formatted = "\n".join([f"- {d}" for d in deliverables])
    else:
        deliverables_formatted = str(deliverables)
    
    return PROPOSAL_TEMPLATE.format(
        name=name_part,
        paraphrase=content.get("paraphrase", "automation workflows"),
        steps=steps_formatted,
        deliverables=deliverables_formatted,
        timeline=content.get("timeline", "1-2 weeks depending on complexity")
    )


def create_google_doc(docs_service, drive_service, title: str, content: str, retries: int = 4) -> str:
    """
    Create a Google Doc with the proposal content.
    Uses semaphore to serialize creation and exponential backoff for retries.
    
    Returns: URL to the created document
    """
    backoff_times = [1.5, 3, 6, 12]
    
    for attempt in range(retries):
        try:
            with doc_creation_semaphore:
                # Create the document
                doc = docs_service.documents().create(body={'title': title}).execute()
                doc_id = doc.get('documentId')
                
                # Insert content
                requests = [{
                    'insertText': {
                        'location': {'index': 1},
                        'text': content
                    }
                }]
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                
                # Make document publicly readable
                drive_service.permissions().create(
                    fileId=doc_id,
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()
                
                return f"https://docs.google.com/document/d/{doc_id}/edit"
                
        except HttpError as e:
            if attempt < retries - 1:
                wait_time = backoff_times[attempt]
                print(f"    Retry {attempt + 1}/{retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                print(f"    Failed to create doc after {retries} attempts: {e}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                wait_time = backoff_times[attempt]
                print(f"    Retry {attempt + 1}/{retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                print(f"    Failed to create doc after {retries} attempts: {e}")
                return None
    
    return None


def process_job(job: dict, anthropic_client, docs_service, drive_service, skip_docs: bool = False) -> dict:
    """Process a single job: generate proposal, create doc, format output."""
    job_title = job.get("title", "Unknown Job")
    job_id = job.get("id", "")
    
    print(f"  Processing: {job_title[:50]}...")
    
    # Generate proposal content
    content = generate_proposal_content(anthropic_client, job)
    
    # Generate full proposal text
    client_name = job.get("client", {}).get("name", "")
    full_proposal = generate_full_proposal(content, client_name)
    
    # Create Google Doc (unless skip_docs is True)
    doc_url = None
    if not skip_docs:
        doc_title = f"Proposal: {job_title[:50]}"
        doc_url = create_google_doc(docs_service, drive_service, doc_title, full_proposal)
    
    # Generate cover letter with doc link or fallback message
    if doc_url:
        cover_letter = generate_cover_letter(content, doc_url)
    else:
        # Fallback: shorter cover letter without doc link
        cover_letter = f"Hi. I work with {content.get('paraphrase', 'automation workflows')} daily & just built {content.get('thing', 'a similar system')}. Happy to share my detailed approach!"
    
    return {
        "job_id": job_id,
        "title": job_title,
        "url": job.get("url", ""),
        "apply_url": job.get("apply_url", ""),
        "budget": job.get("budget", ""),
        "experience_level": job.get("experience_level", ""),
        "skills": job.get("skills", ""),
        "category": job.get("category", ""),
        "client_country": job.get("client", {}).get("country", ""),
        "client_spent": job.get("client", {}).get("total_spent", ""),
        "client_hires": job.get("client", {}).get("total_hires", ""),
        "connects_required": job.get("connects_required", ""),
        "cover_letter": cover_letter,
        "proposal_doc": doc_url or "",
        "proposal_text": full_proposal if not doc_url else "",  # Fallback if doc failed
        "generated_at": datetime.now().isoformat(),
    }


def create_or_update_sheet(sheets_service, drive_service, data: list, sheet_id: str = None) -> str:
    """
    Create a new Google Sheet or update existing one with proposal data.
    
    Returns: URL to the sheet
    """
    headers = [
        "Title", "URL", "Budget", "Experience", "Skills", "Category",
        "Client Country", "Client Spent", "Client Hires", "Connects",
        "Apply Link", "Cover Letter", "Proposal Doc"
    ]
    
    if sheet_id:
        # Update existing sheet
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    else:
        # Create new sheet
        spreadsheet = sheets_service.spreadsheets().create(
            body={
                'properties': {'title': f'Upwork Proposals - {datetime.now().strftime("%Y-%m-%d %H:%M")}'},
                'sheets': [{'properties': {'title': 'Proposals'}}]
            }
        ).execute()
        sheet_id = spreadsheet.get('spreadsheetId')
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        
        # Make sheet publicly readable
        drive_service.permissions().create(
            fileId=sheet_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Add headers
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Proposals!A1:M1',
            valueInputOption='RAW',
            body={'values': [headers]}
        ).execute()
        
        print(f"Created new sheet: {sheet_url}")
    
    # Format data rows
    rows = []
    for item in data:
        row = [
            item.get("title", ""),
            item.get("url", ""),
            item.get("budget", ""),
            item.get("experience_level", ""),
            item.get("skills", ""),
            item.get("category", ""),
            item.get("client_country", ""),
            str(item.get("client_spent", "")),
            str(item.get("client_hires", "")),
            str(item.get("connects_required", "")),
            item.get("apply_url", ""),
            item.get("cover_letter", ""),
            item.get("proposal_doc", "") or item.get("proposal_text", "")[:500],
        ]
        rows.append(row)
    
    # Append rows to sheet
    if rows:
        sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='Proposals!A:M',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': rows}
        ).execute()
        
        print(f"Added {len(rows)} rows to sheet")
    
    return sheet_url


def main():
    parser = argparse.ArgumentParser(
        description="Generate Upwork proposals using Claude Opus 4.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate proposals for scraped jobs
    python execution/upwork_proposal_generator.py --input .tmp/upwork_jobs.json -o .tmp/proposals.json
    
    # Use existing sheet
    python execution/upwork_proposal_generator.py --input .tmp/jobs.json --sheet-id SHEET_ID -o .tmp/proposals.json
    
    # Adjust worker count
    python execution/upwork_proposal_generator.py --input .tmp/jobs.json --workers 3 -o .tmp/proposals.json
        """
    )
    
    parser.add_argument("--input", "-i", required=True, help="Input JSON file with scraped jobs")
    parser.add_argument("--output", "-o", default=".tmp/upwork_proposals.json", help="Output JSON file")
    parser.add_argument("--sheet-id", help="Existing Google Sheet ID to append to (creates new if omitted)")
    parser.add_argument("--workers", type=int, default=5, help="Number of parallel workers for LLM calls (default: 5)")
    parser.add_argument("--skip-docs", action="store_true", help="Skip Google Docs creation (embed proposals in sheet)")
    parser.add_argument("--no-sheet", action="store_true", help="Skip all Google API calls (output to JSON/CSV only)")
    
    args = parser.parse_args()
    
    # Load input jobs
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    
    print("\n" + "="*60)
    print("Upwork Proposal Generator")
    print("="*60)
    print(f"  Jobs to process: {len(jobs)}")
    print(f"  Workers: {args.workers}")
    print(f"  Skip Docs: {args.skip_docs}")
    print(f"  No Sheet: {args.no_sheet}")
    
    # Initialize clients
    print("\nInitializing services...")
    anthropic_client = get_anthropic_client()
    
    # Only initialize Google services if needed
    if not args.no_sheet:
        try:
            sheets_service, docs_service, drive_service = get_google_services()
        except Exception as e:
            print(f"WARNING: Could not initialize Google services: {e}")
            print("Falling back to --no-sheet mode")
            args.no_sheet = True
            args.skip_docs = True
            sheets_service = docs_service = drive_service = None
    else:
        sheets_service = docs_service = drive_service = None
    
    # Process jobs in parallel
    print(f"\nGenerating proposals...")
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_job, job, anthropic_client, docs_service, drive_service, args.skip_docs or args.no_sheet): job
            for job in jobs
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                print(f"  Completed {len(results)}/{len(jobs)}")
            except Exception as e:
                job = futures[future]
                print(f"  Error processing {job.get('title', 'Unknown')}: {e}")
    
    elapsed = time.time() - start_time
    print(f"\nProcessed {len(results)} jobs in {elapsed:.1f}s ({elapsed/len(results):.1f}s per job)")
    
    # Save results to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Saved results to {output_path}")
    
    # Also save as CSV for easy import to Google Sheets
    csv_path = output_path.with_suffix('.csv')
    import csv
    with open(csv_path, "w", encoding="utf-8", newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=[
                "title", "url", "budget", "experience_level", "skills", "category",
                "client_country", "client_spent", "client_hires", "connects_required",
                "apply_url", "cover_letter", "proposal_doc", "proposal_text"
            ])
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "budget": r.get("budget", ""),
                    "experience_level": r.get("experience_level", ""),
                    "skills": r.get("skills", ""),
                    "category": r.get("category", ""),
                    "client_country": r.get("client_country", ""),
                    "client_spent": r.get("client_spent", ""),
                    "client_hires": r.get("client_hires", ""),
                    "connects_required": r.get("connects_required", ""),
                    "apply_url": r.get("apply_url", ""),
                    "cover_letter": r.get("cover_letter", ""),
                    "proposal_doc": r.get("proposal_doc", ""),
                    "proposal_text": r.get("proposal_text", "")[:1000],  # Truncate for CSV
                })
    print(f"Saved CSV to {csv_path}")
    
    # Create/update Google Sheet (if not in no-sheet mode)
    if not args.no_sheet:
        print("\nCreating Google Sheet...")
        try:
            sheet_url = create_or_update_sheet(sheets_service, drive_service, results, args.sheet_id)
            print(f"Sheet URL: {sheet_url}")
        except Exception as e:
            print(f"WARNING: Could not create Google Sheet: {e}")
            print("Results saved to JSON and CSV files for manual upload")
    else:
        print("\nSkipping Google Sheet creation (--no-sheet mode)")
        print(f"Import {csv_path} to Google Sheets manually")
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

