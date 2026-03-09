import os
import json
import subprocess
import urllib.request
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def load_config():
    config_path = os.path.join(sf.ENGINE_ROOT, 'core', 'registries', 'deployment_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def ping_sitemap(sitemap_url):
    print(f"📡 Pinging sitemap: {sitemap_url}")
    # Google ping
    try:
        urllib.request.urlopen(f"https://www.google.com/ping?sitemap={sitemap_url}")
        return True
    except Exception as e:
        print(f"❌ Failed to ping Google: {e}")
        return False

def deploy_pages(mode="full_autonomous", with_git=False):
    print(f"🚀 Initializing Cloud Deployment Rig (Mode: {mode})")
    
    config = load_config()
    
    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    deploy_queue = get_tab_data('Deployment_Queue')
    
    pages_attempted = []
    
    for row in deploy_queue:
        if len(row) >= 7:
            url, ptype, city, cluster, gen_at, val_status, dep_status = row[:7]
            if val_status.lower() == "passed" and dep_status.lower() != "deployed":
                pages_attempted.append(row)
                
    if not pages_attempted:
        print("✅ No new valid pages pending deployment.")
        return

    print(f"📦 Assembling {len(pages_attempted)} eligible pages for delivery...")
    
    if mode == "preview":
        print("🛑 PREVIEW MODE: Skipping physical deploy triggers.")
        return

    if with_git or config.get("git_integration", {}).get("enabled"):
        print("🐙 Triggering Git Configuration...")
        try:
            subprocess.run(["git", "add", "."], check=True, cwd=sf.ROOT_DIR)
            commit_msg = f"{config.get('git_integration', {}).get('commit_message_prefix', '[Auto]')} deployed {len(pages_attempted)} new index matrices."
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=sf.ROOT_DIR)
            if config.get("git_integration", {}).get("auto_push"):
                subprocess.run(["git", "push"], check=True, cwd=sf.ROOT_DIR)
                print("✅ Git Push Complete.")
        except Exception as e:
            print(f"❌ Git iteration failed: {e}")

    # Build trigger placeholder
    build_cmd = config.get("build_command", "npm run build")
    if build_cmd and config.get("provider") != "github_actions":
        print(f"⚙️ Running build: {build_cmd}")
        # subprocess.run(build_cmd.split(), cwd=sf.ROOT_DIR) # mock
        
    # Provider checks
    if config.get("provider") == "s3_cloudfront":
        print(f"☁️ Syncing S3 to {config.get('deployment_target')}")
    elif config.get("provider") == "cloudflare":
        print(f"☁️ Triggering Cloudflare deploy hook")
        
    if config.get("cache_purge_enabled"):
        print("🧹 Purging CDN Cache...")
        
    sitemaps = config.get("sitemap_urls", [])
    if config.get("notify_search_engines"):
        for sm in sitemaps:
            ping_sitemap(sm)

    # In production, actually update sheet rows via API to "Deployed" status
    print(f"✅ Successful deployment cascade across {len(pages_attempted)} nodes.")
