import os
import json
import random
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def analyze_user_behavior():
    print("🕵️ Initializing User Behavior Feedback Engine...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=sf.SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    tabs_to_ensure = [
        'User_Behavior', 
        'Page_Performance', 
        'Behavior_Insights', 
        'Behavior_Reinforcement'
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
    
    behavior = []
    performance = []
    insights = []
    reinforcements = []

    # Mock user traffic signals for all URLs
    for row in sitemap_data:
        if not row: continue
        url = row[0]
        p_type = row[1] if len(row) > 1 else "Page"
        city = "General"
        
        # Simulate local analytics
        views = random.randint(10, 5000)
        avg_time = random.randint(10, 300) # seconds
        scroll_depth = random.randint(30, 100) # percentage
        idx_clicks = random.randint(0, int(views * 0.15))
        bounce_rate = round(random.uniform(0.1, 0.9), 2)
        idx_click_rate = round(idx_clicks / views, 2)
        
        # weighted Engagement Score
        engagement_score = min(100, (avg_time / 180) * 40 + (scroll_depth / 100) * 30 + (idx_click_rate / 0.1) * 30)
        engagement_score = round(engagement_score, 1)

        performance.append([url, p_type, city, str(views), str(avg_time), f"{scroll_depth}%", f"{idx_click_rate*100}%", f"{bounce_rate*100}%", str(engagement_score)])

        # Triaging Insights & Reinforcements
        if avg_time < 30 and bounce_rate > 0.7:
            insights.append([city, "", "low_engagement", f"{url} has high bounce and low time. Needs rewrite.", "High"])
            reinforcements.append([url, p_type, "low_engagement", "Trigger narrative rewrite & CTA repositioning", "High", "Planned"])
            
        elif idx_click_rate > 0.1:
            insights.append([city, "", "high_idx_clicks", f"{url} drives strong buyer intent.", "Medium"])
            reinforcements.append([url, p_type, "high_idx_click_rate", "Boost internal linking density to IDX hub", "Medium", "Planned"])
            
        elif scroll_depth > 80:
            insights.append([city, "", "high_scroll_depth", f"Users highly engaged with bottom page sections on {url}.", "Low"])
            
    # Push to Sheets
    if performance:
        headers = sf.PHASE1_TABS['Page_Performance']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Page_Performance'!A1", valueInputOption='RAW', body={'values': headers + sf.unique_list(performance, 0)}).execute()

    if insights:
        headers = sf.PHASE1_TABS['Behavior_Insights']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Behavior_Insights'!A1", valueInputOption='RAW', body={'values': headers + insights}).execute()

    if reinforcements:
        headers = sf.PHASE1_TABS['Behavior_Reinforcement']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Behavior_Reinforcement'!A1", valueInputOption='RAW', body={'values': headers + reinforcements}).execute()

        # Route actionable reinforcements to main Reinforcement_Queue
        # format: URL, Page_Type, City, Trigger, Reason, Priority, Status
        transfer_queue = []
        for r in reinforcements:
            transfer_queue.append([r[0], r[1], "Dynamic", r[2], r[3], r[4], "Planned"])
            
        service.spreadsheets().values().append(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Reinforcement_Queue'!A2",
            valueInputOption='RAW', body={'values': transfer_queue}
        ).execute()

    print(f"✅ Behavior Engine Analysis Complete. Logged {len(insights)} Behavioral Insights. Queued {len(reinforcements)} Page Adjustments.")
