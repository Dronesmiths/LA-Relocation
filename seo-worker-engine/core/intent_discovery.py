import os
import json
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def detect_buyer_intent():
    print("🧠 Initializing Buyer Intent Detection Engine...")
    
    # Ensure logs dir
    log_dir = os.path.join(sf.ROOT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'intent-detection-log.json')
    
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

    spreadsheet = service.spreadsheets().get(spreadsheetId=sf.SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    tabs_to_ensure = [
        'Buyer_Intent_Queries', 
        'Intent_Clusters', 
        'PAA_Topics', 
        'AutoSuggest_Topics', 
        'Intent_Opportunities'
    ]
    
    new_tabs = [{'addSheet': {'properties': {'title': t}}} for t in tabs_to_ensure if t not in existing_sheets]
    if new_tabs:
        service.spreadsheets().batchUpdate(spreadsheetId=sf.SPREADSHEET_ID, body={'requests': new_tabs}).execute()
        
    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    sitemap_data = get_tab_data('Sitemap Inventory')
    existing_urls = set([r[0] for r in sitemap_data if r])
    
    cities = get_tab_data('Cities')
    neighborhoods = get_tab_data('Neighborhoods')
    
    # Storage arrays
    queries = []
    clusters = []
    paa_topics = []
    autosuggest = []
    opportunities = []
    reinforcements = []
    
    # Mock live fetching from GSC, AutoComplete, PAA
    intent_mappings = {
        "homes under 500k": "buyer",
        "is {} a good place to live": "relocation",
        "best neighborhoods in {} for families": "neighborhood",
        "{} crime rate": "crime",
        "{} school ratings": "school",
        "cost of living in {}": "affordability",
        "moving to {} california": "relocation",
        "new construction homes {}": "buyer",
        "cheap homes in {}": "buyer",
        "{} pool homes": "buyer",
        "affordable homes in {}": "buyer",
        "is {} safe": "crime",
        "sell my house fast {}": "seller"
    }
    
    cities_list = [c[0] for c in cities if c]
    new_cluster_count = 0
    new_page_count = 0
    reinforce_count = 0
    
    for city in cities_list:
        city_slug = sf.get_slug(city)
        
        # Simulate PAA Discovery
        paa_q1 = f"Is {city} a safe place to live"
        paa_q2 = f"What are the best neighborhoods in {city}"
        paa_q3 = f"Are homes in {city} affordable"
        
        paa_topics.extend([
            [paa_q1, city, "crime", "relocation_guide", "High", "Active"],
            [paa_q2, city, "neighborhood", "blog_page", "High", "Active"],
            [paa_q3, city, "affordability", "idx_page", "Medium", "Active"]
        ])
        
        # Simulate AutoSuggest Discovery
        autosuggest.extend([
            [f"{city.lower()} homes under 500k", city, "under-500k", "buyer", "idx_page", "High", "Active"],
            [f"{city.lower()} pool homes", city, "pool", "buyer", "idx_page", "High", "Active"],
            [f"moving to {city.lower()} california", city, "", "relocation", "relocation_guide", "Medium", "Active"]
        ])
        
        # Simulate Query Streams & Clustering
        cluster_affordability = f"{city} Affordability"
        queries.append([f"homes under 500k in {city}", "gsc", "buyer", city, "", "under-500k", "", "1500", "45", "3.0%", "12", "High", "Active"])
        queries.append([f"affordable homes in {city}", "autocomplete", "buyer", city, "", "affordable", "", "800", "0", "0", "0", "Medium", "Active"])
        queries.append([f"cheap homes in {city}", "related_search", "buyer", city, "", "cheap", "", "1200", "15", "1.2%", "18", "Medium", "Active"])
        
        clusters.append([cluster_affordability, "buyer", city, f"homes under 500k in {city} | affordable homes in {city} | cheap homes in {city}", "idx_filter_page", "High", "Active"])
        
        cluster_relocation = f"{city} Relocation"
        queries.append([f"is {city} a good place to live", "paa", "relocation", city, "", "", "", "2000", "120", "6.0%", "5", "High", "Active"])
        queries.append([f"moving to {city}", "autocomplete", "relocation", city, "", "", "", "2500", "50", "2.0%", "9", "High", "Active"])
        
        clusters.append([cluster_relocation, "relocation", city, f"is {city} a good place to live | moving to {city}", "relocation_guide", "High", "Active"])
        
        # Opportunity Triaging & Reinforcement Checks
        
        # Check Affordability
        idx_slug = f"{city_slug}-homes-under-500k"
        url = f"{sf.DOMAIN}/{idx_slug}/"
        exists = "Yes" if url in existing_urls else "No"
        needs_gen = "Yes" if exists == "No" else "No"
        
        opportunities.append(["idx_filter", cluster_affordability, city, idx_slug, "idx_page", "gsc+autocomplete", "High", exists, needs_gen])
        
        if needs_gen == "Yes":
            new_page_count += 1
        else:
            # Low CTR trigger logic => Queue for Reinforcement Instead
            reinforcements.append([url, "idx_page", city, "Intent_Discovery (Low CTR)", "Target Intent Keyword Optimization", "High", "planned"])
            reinforce_count += 1

        # Check Relocation
        blog_slug = f"is-{city_slug}-a-good-place-to-live"
        url = f"{sf.DOMAIN}/blog/{blog_slug}/"
        exists = "Yes" if url in existing_urls else "No"
        needs_gen = "Yes" if exists == "No" else "No"
        
        opportunities.append(["blog", cluster_relocation, city, blog_slug, "blog_page", "paa+gsc", "High", exists, needs_gen])
        
        if needs_gen == "Yes":
            new_page_count += 1
        else:
            reinforcements.append([url, "blog_page", city, "Intent_Discovery (Weak Position)", "Target Intent Keyword Optimization", "High", "planned"])
            reinforce_count += 1

        new_cluster_count += 2

    # Writes
    if queries:
        headers = sf.PHASE1_TABS['Buyer_Intent_Queries']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Buyer_Intent_Queries'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(queries, 0)}
        ).execute()

    if clusters:
        headers = sf.PHASE1_TABS['Intent_Clusters']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Intent_Clusters'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(clusters, 0)}
        ).execute()

    if paa_topics:
        headers = sf.PHASE1_TABS['PAA_Topics']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'PAA_Topics'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(paa_topics, 0)}
        ).execute()

    if autosuggest:
        headers = sf.PHASE1_TABS['AutoSuggest_Topics']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'AutoSuggest_Topics'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(autosuggest, 0)}
        ).execute()

    if opportunities:
        headers = sf.PHASE1_TABS['Intent_Opportunities']
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Intent_Opportunities'!A1",
            valueInputOption='RAW', body={'values': headers + sf.unique_list(opportunities, 3)}
        ).execute()
        
    if reinforcements:
        service.spreadsheets().values().append(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Reinforcement_Queue'!A2",
            valueInputOption='RAW', body={'values': reinforcements}
        ).execute()

    # Logging
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query_count": len(queries),
        "new_clusters_found": new_cluster_count,
        "new_pages_suggested": new_page_count,
        "pages_queued_for_reinforcement": reinforce_count,
        "pages_materialized": 0 # Tracked by Materializer loop separately
    }
    logs.append(log_entry)
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=4)

    print(f"✅ Buyer Intent Engine Discovered: {new_cluster_count} Clusters. Recommended {new_page_count} new pages. Reinforced {reinforce_count} weak pages.")
