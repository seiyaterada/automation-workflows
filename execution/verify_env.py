#!/usr/bin/env python3
"""
Verify environment variables and credentials for Upwork pipeline.
Checks: .env (APIFY_API_TOKEN, ANTHROPIC_API_KEY), credentials.json, token.json
"""

import os
import json
import sys
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def check_mark(success):
    return f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"

def warn_mark():
    return f"{YELLOW}⚠{RESET}"

def main():
    project_root = Path(__file__).parent.parent
    all_passed = True
    
    print("\n" + "="*60)
    print("Environment & Credentials Verification")
    print("="*60 + "\n")
    
    # 1. Check .env file exists
    env_path = project_root / ".env"
    print(f"1. Checking .env file...")
    if env_path.exists():
        print(f"   {check_mark(True)} .env file found")
        
        # Read .env content
        env_content = env_path.read_text()
        
        # Check for APIFY_API_TOKEN
        has_apify = "APIFY_API_TOKEN" in env_content
        if has_apify:
            # Check if it has a value (not just the key)
            for line in env_content.split('\n'):
                if line.startswith('APIFY_API_TOKEN'):
                    value = line.split('=', 1)[1].strip() if '=' in line else ''
                    has_apify = len(value) > 0
                    break
        print(f"   {check_mark(has_apify)} APIFY_API_TOKEN {'configured' if has_apify else 'missing or empty'}")
        if not has_apify:
            all_passed = False
        
        # Check for ANTHROPIC_API_KEY
        has_anthropic = "ANTHROPIC_API_KEY" in env_content
        if has_anthropic:
            for line in env_content.split('\n'):
                if line.startswith('ANTHROPIC_API_KEY'):
                    value = line.split('=', 1)[1].strip() if '=' in line else ''
                    has_anthropic = len(value) > 0
                    break
        print(f"   {check_mark(has_anthropic)} ANTHROPIC_API_KEY {'configured' if has_anthropic else 'missing or empty'}")
        if not has_anthropic:
            all_passed = False
    else:
        print(f"   {check_mark(False)} .env file not found")
        all_passed = False
    
    print()
    
    # 2. Check credentials.json
    print(f"2. Checking credentials.json...")
    creds_path = project_root / "credentials.json"
    if creds_path.exists():
        print(f"   {check_mark(True)} credentials.json found")
        try:
            with open(creds_path) as f:
                creds = json.load(f)
            
            # Check credential type: service account, installed, or web
            if creds.get("type") == "service_account":
                print(f"   {check_mark(True)} Valid service account credentials")
                client_email = creds.get("client_email", "")
                print(f"   {check_mark(True)} Service account: {client_email}")
                print(f"   {warn_mark()} Note: Service accounts have full API access, no OAuth scopes needed")
            elif "installed" in creds or "web" in creds:
                cred_type = "installed" if "installed" in creds else "web"
                print(f"   {check_mark(True)} Valid OAuth credentials (type: {cred_type})")
                cred_data = creds.get(cred_type, {})
                client_id = cred_data.get("client_id", "")[:30] + "..."
                print(f"   {check_mark(True)} Client ID: {client_id}")
            else:
                print(f"   {check_mark(False)} Invalid credentials format")
                all_passed = False
        except json.JSONDecodeError:
            print(f"   {check_mark(False)} Invalid JSON in credentials.json")
            all_passed = False
    else:
        print(f"   {check_mark(False)} credentials.json not found")
        all_passed = False
    
    print()
    
    # 3. Check token.json
    print(f"3. Checking token.json...")
    token_path = project_root / "token.json"
    if token_path.exists():
        print(f"   {check_mark(True)} token.json found")
        try:
            with open(token_path) as f:
                token = json.load(f)
            
            # Check scopes
            scopes = token.get("scopes", [])
            required_scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents"
            ]
            
            print(f"   Found scopes:")
            for scope in scopes:
                # Shorten scope for display
                short_scope = scope.replace("https://www.googleapis.com/auth/", "")
                print(f"      - {short_scope}")
            
            missing_scopes = [s for s in required_scopes if s not in scopes]
            if missing_scopes:
                print(f"   {warn_mark()} Missing required scopes:")
                for scope in missing_scopes:
                    short_scope = scope.replace("https://www.googleapis.com/auth/", "")
                    print(f"      - {short_scope}")
                print(f"   {warn_mark()} You may need to re-authenticate to add missing scopes")
            else:
                print(f"   {check_mark(True)} All required scopes present")
                
        except json.JSONDecodeError:
            print(f"   {check_mark(False)} Invalid JSON in token.json")
            all_passed = False
    else:
        print(f"   {warn_mark()} token.json not found")
        print(f"   {warn_mark()} Will be created on first run via OAuth flow")
    
    print()
    
    # 4. Check Python dependencies
    print(f"4. Checking Python dependencies...")
    required_packages = [
        ("anthropic", "anthropic"),
        ("google.oauth2", "google-auth"),
        ("google_auth_oauthlib", "google-auth-oauthlib"),
        ("googleapiclient", "google-api-python-client"),
        ("requests", "requests"),
        ("dotenv", "python-dotenv"),
    ]
    
    missing_packages = []
    for module, package in required_packages:
        try:
            __import__(module)
            print(f"   {check_mark(True)} {package}")
        except ImportError:
            print(f"   {check_mark(False)} {package} (not installed)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n   To install missing packages:")
        print(f"   pip install {' '.join(missing_packages)}")
        all_passed = False
    
    print()
    print("="*60)
    if all_passed:
        print(f"{GREEN}All checks passed! Ready to build the pipeline.{RESET}")
    else:
        print(f"{YELLOW}Some checks failed. Please fix the issues above.{RESET}")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
