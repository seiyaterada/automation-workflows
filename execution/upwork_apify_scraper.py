#!/usr/bin/env python3
"""
Upwork Job Scraper using Apify's upwork-vibe~upwork-job-scraper actor.

Free tier only supports: limit, fromDate, toDate
All other filtering (verified payment, min spent, experience) is done post-scrape.

Usage:
    python execution/upwork_apify_scraper.py --limit 50 --days 1 --verified-payment \
        --min-spent 1000 --experience intermediate,expert -o .tmp/upwork_jobs.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_apify_token():
    """Get Apify API token from environment."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("ERROR: APIFY_API_TOKEN not found in environment")
        sys.exit(1)
    return token


def run_scraper(token: str, limit: int, from_date: str, to_date: str) -> dict:
    """
    Run the Upwork scraper actor on Apify.
    
    Args:
        token: Apify API token
        limit: Maximum number of jobs to scrape
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
    
    Returns:
        Actor run result with dataset items
    """
    actor_id = "upwork-vibe~upwork-job-scraper"
    api_url = f"https://api.apify.com/v2/acts/{actor_id}/runs"
    
    # Input for the actor (free tier filters only)
    input_data = {
        "limit": limit,
        "fromDate": from_date,
        "toDate": to_date,
    }
    
    print(f"Starting Apify actor: {actor_id}")
    print(f"  Limit: {limit}")
    print(f"  Date range: {from_date} to {to_date}")
    
    # Start the actor run
    response = requests.post(
        api_url,
        params={"token": token},
        json=input_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 201:
        print(f"ERROR: Failed to start actor run: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    run_data = response.json()["data"]
    run_id = run_data["id"]
    print(f"  Run ID: {run_id}")
    
    # Poll for completion (3s interval, 5 min timeout)
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    start_time = time.time()
    timeout = 300  # 5 minutes
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"ERROR: Actor run timed out after {timeout}s")
            sys.exit(1)
        
        status_response = requests.get(status_url, params={"token": token})
        status_data = status_response.json()["data"]
        status = status_data["status"]
        
        print(f"  Status: {status} ({int(elapsed)}s elapsed)", end="\r")
        
        if status == "SUCCEEDED":
            print(f"\n  Completed in {int(elapsed)}s")
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            print(f"\nERROR: Actor run {status}")
            sys.exit(1)
        
        time.sleep(3)
    
    # Get dataset items
    dataset_id = status_data["defaultDatasetId"]
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
    
    items_response = requests.get(dataset_url, params={"token": token})
    items = items_response.json()
    
    print(f"  Retrieved {len(items)} jobs from dataset")
    
    return items


def filter_jobs(jobs: list, args: argparse.Namespace) -> list:
    """
    Apply post-scrape filters to job list.
    
    Filters:
        --verified-payment: Only jobs with verified payment method
        --min-spent N: Minimum client total spent
        --experience: Comma-separated experience levels (entry,intermediate,expert)
    """
    filtered = jobs
    original_count = len(filtered)
    
    # Verified payment filter
    if args.verified_payment:
        filtered = [j for j in filtered if j.get("client", {}).get("paymentVerified", False)]
        print(f"  After verified payment filter: {len(filtered)}/{original_count}")
    
    # Minimum spent filter
    if args.min_spent:
        def get_spent(job):
            spent = job.get("client", {}).get("totalSpent", "0")
            # Handle "$1,234" format
            if isinstance(spent, str):
                spent = spent.replace("$", "").replace(",", "")
                try:
                    return float(spent)
                except ValueError:
                    return 0
            return float(spent) if spent else 0
        
        filtered = [j for j in filtered if get_spent(j) >= args.min_spent]
        print(f"  After min spent filter (${args.min_spent}): {len(filtered)}/{original_count}")
    
    # Experience level filter
    if args.experience:
        levels = [l.strip().lower() for l in args.experience.split(",")]
        
        def matches_experience(job):
            job_level = job.get("experienceLevel", "").lower()
            # Handle variations like "Intermediate" or "intermediate_level"
            for level in levels:
                if level in job_level.lower():
                    return True
            return False
        
        filtered = [j for j in filtered if matches_experience(j)]
        print(f"  After experience filter ({args.experience}): {len(filtered)}/{original_count}")
    
    return filtered


def format_job(job: dict) -> dict:
    """
    Format a job into a clean structure for output.
    Generates proper job URL and apply URL.
    
    Apify response structure uses:
    - uid: Job ID (numeric string)
    - budget: {fixedBudget: X, hourlyRate: {min: X, max: X}}
    - client: {name, timezone, industry, totalSpent, totalHires, hireRate, feedbackCount}
    """
    # Extract job ID - Apify uses "uid"
    job_id = job.get("uid", "") or job.get("id", "")
    
    # Build URLs using the uid
    job_url = f"https://www.upwork.com/jobs/~{job_id}" if job_id else ""
    apply_url = f"https://www.upwork.com/nx/proposals/job/~{job_id}/apply/" if job_id else ""
    
    # Extract client info
    client = job.get("client", {}) or {}
    
    # Extract budget - handle both fixedBudget and hourlyRate
    budget_data = job.get("budget", {}) or {}
    fixed_budget = budget_data.get("fixedBudget", 0) if isinstance(budget_data, dict) else 0
    hourly_rate = budget_data.get("hourlyRate", {}) if isinstance(budget_data, dict) else {}
    
    if fixed_budget and fixed_budget > 0:
        budget_str = f"${fixed_budget} (fixed)"
    elif hourly_rate and hourly_rate.get("min"):
        hr_min = hourly_rate.get("min", 0)
        hr_max = hourly_rate.get("max", 0)
        budget_str = f"${hr_min}-${hr_max}/hr"
    else:
        budget_str = "Not specified"
    
    # Extract skills - can be list of strings or list of dicts
    skills = job.get("skills", []) or []
    if isinstance(skills, list):
        if skills and isinstance(skills[0], dict):
            skills_str = ", ".join([s.get("name", str(s)) for s in skills])
        else:
            skills_str = ", ".join(str(s) for s in skills)
    else:
        skills_str = str(skills)
    
    # Extract experience level - might be in vendor object or directly
    vendor = job.get("vendor", {}) or {}
    experience_level = vendor.get("experienceLevel", "") or job.get("experienceLevel", "")
    
    # Extract duration
    duration = vendor.get("duration", "") or job.get("duration", "")
    
    # Extract category
    category = job.get("category", "") or vendor.get("category", "")
    
    # Extract connects
    connects = job.get("connects", "") or vendor.get("connects", "")
    
    return {
        "id": job_id,
        "title": job.get("title", ""),
        "description": job.get("description", ""),
        "url": job_url,
        "apply_url": apply_url,
        "budget": budget_str,
        "hourly_rate": f"${hourly_rate.get('min', 0)}-${hourly_rate.get('max', 0)}/hr" if hourly_rate else "",
        "job_type": "Fixed" if fixed_budget else "Hourly" if hourly_rate else "",
        "experience_level": experience_level,
        "duration": duration,
        "skills": skills_str,
        "category": category,
        "subcategory": job.get("subcategory", ""),
        "connects_required": connects,
        "posted_date": job.get("createdAt", "") or job.get("postedDate", ""),
        "client": {
            "name": client.get("name", ""),
            "country": client.get("country", "") or client.get("timezone", "").split("/")[0] if client.get("timezone") else "",
            "total_spent": client.get("totalSpent", 0),
            "total_hires": client.get("totalHires", 0),
            "hire_rate": client.get("hireRate", 0),
            "payment_verified": client.get("paymentVerified", False),
            "rating": client.get("rating", "") or client.get("avgRate", ""),
            "reviews_count": client.get("reviewsCount", "") or client.get("feedbackCount", ""),
        },
        "proposals": job.get("proposals", ""),
        "raw_data": job,  # Keep raw data for debugging
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Upwork jobs using Apify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scrape 50 jobs from the last day with verified payment
    python execution/upwork_apify_scraper.py --limit 50 --days 1 --verified-payment -o .tmp/jobs.json
    
    # Scrape with experience filter
    python execution/upwork_apify_scraper.py --limit 100 --days 3 --experience intermediate,expert -o .tmp/jobs.json
    
    # Scrape with minimum client spend filter
    python execution/upwork_apify_scraper.py --limit 50 --days 1 --min-spent 1000 -o .tmp/jobs.json
        """
    )
    
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of jobs to scrape (default: 50)")
    parser.add_argument("--days", type=int, default=1, help="Number of days back to search (default: 1)")
    parser.add_argument("--verified-payment", action="store_true", help="Only jobs with verified payment method")
    parser.add_argument("--min-spent", type=float, help="Minimum client total spent (USD)")
    parser.add_argument("--experience", type=str, help="Experience levels (comma-separated: entry,intermediate,expert)")
    parser.add_argument("-o", "--output", type=str, default=".tmp/upwork_jobs.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    # Calculate date range
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    
    # Get API token
    token = get_apify_token()
    
    # Run scraper
    print("\n" + "="*60)
    print("Upwork Job Scraper")
    print("="*60)
    
    jobs = run_scraper(token, args.limit, from_date, to_date)
    
    # Apply filters
    print("\nApplying filters...")
    filtered_jobs = filter_jobs(jobs, args)
    
    # Format jobs
    print("\nFormatting jobs...")
    formatted_jobs = [format_job(j) for j in filtered_jobs]
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted_jobs, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(formatted_jobs)} jobs to {output_path}")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
