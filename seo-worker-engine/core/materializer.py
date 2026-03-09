import os
import json
import time
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def materialize_pages():
    print("🏗️ Starting Automated Materialization Engine...")
    
    # Ensure logs dir
    log_dir = os.path.join(sf.ROOT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'materialization-log.json')
    
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except:
            pass
            
    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    try:
        queue_data = service.spreadsheets().values().get(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Reinforcement_Queue'!A2:Z").execute().get('values', [])
    except:
        print("❌ Could not access Reinforcement_Queue")
        return
        
    updated_queue = []
    materialized_count = 0
    skipped_count = 0
    
    now = datetime.now()
    
    for row in queue_data:
        # [URL, Page_Type, City, Data_Source_Trigger, Reason, Priority, Status]
        if len(row) < 7:
            row.extend([""] * (7 - len(row)))
            
        url, p_type, city, trigger, reason, priority, status = row[:7]
        
        if status == "materialized":
            updated_queue.append(row)
            continue
            
        # Parse Local Path
        rel_path = url.replace(sf.DOMAIN, '').strip('/')
        if not rel_path:
            local_path = os.path.join(sf.ROOT_DIR, 'index.html')
        else:
            local_path = os.path.join(sf.ROOT_DIR, rel_path, 'index.html')
            
        # 24 hour modification check
        if os.path.exists(local_path):
            mtime = os.path.getmtime(local_path)
            last_mod = datetime.fromtimestamp(mtime)
            if now - last_mod < timedelta(hours=24):
                print(f"⏭️ Skipping {url} - Materialized < 24 hours ago.")
                skipped_count += 1
                row[6] = "materialized"
                updated_queue.append(row)
                continue
                
        # Template Identification
        template_name = "city_page.html"
        p_lower = p_type.lower() if p_type else ""
        if "neighborhood" in p_lower:
            template_name = "neighborhood_page.html"
        elif "idx" in p_lower:
            template_name = "idx_page.html"
        elif "blog" in p_lower:
            template_name = "blog_page.html"
        elif "relocation" in p_lower:
            template_name = "relocation_page.html"
            
        template_path = os.path.join(sf.ENGINE_ROOT, 'core', 'templates', template_name)
        if not os.path.exists(template_path):
            print(f"⚠️ Template missing: {template_name}")
            row[6] = "failed"
            updated_queue.append(row)
            continue
            
        # Assemble blocks
        ctx = sf.get_city_data_context(city)
        with open(template_path, 'r') as f:
            content = f.read()
            
        content = content.replace('{{LOCATION}}', city)
        content = content.replace('{{TITLE}}', f"{city} {p_type}")
        
        content = content.replace('{{market_block}}', sf.render_market_snippet(ctx.get('market')))
        content = content.replace('{{crime_block}}', sf.render_crime_snippet(ctx.get('crime')))
        content = content.replace('{{school_block}}', sf.render_school_snippet(ctx.get('schools')))
        content = content.replace('{{commute_block}}', sf.render_commute_snippet(ctx.get('commute')))
        content = content.replace('{{amenities_block}}', sf.render_amenities_snippet(ctx.get('amenities')))
        content = content.replace('{{demographic_block}}', sf.render_demographics_snippet(ctx.get('demographics')))
        
        # Write Output
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'w') as f:
            f.write(content)
            
        print(f"✅ Materialized {url} via {template_name}")
        materialized_count += 1
        
        logs.append({
            "timestamp": now.isoformat(),
            "page": url,
            "trigger": trigger,
            "data_source": "Google Sheets Matrix",
            "success": "success"
        })
        
        row[6] = "materialized"
        updated_queue.append(row)
        
    if updated_queue:
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Reinforcement_Queue'!A2",
            valueInputOption='RAW', body={'values': updated_queue}
        ).execute()
        
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=4)
        
    print(f"🏁 Materialization Complete. {materialized_count} built, {skipped_count} skipped.")
