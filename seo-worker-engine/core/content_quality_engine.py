import os
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def score_content_quality():
    print("⚖️ Initializing Content Quality Scoring Engine...")
    
    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    # Mock scanning generated pages
    pages_to_score = [
        ("best-neighborhoods-palmdale", 85),
        ("homes-under-500k-lancaster", 92),
        ("thin-page-example", 60), 
        ("market-update-march", 78)
    ]
    
    revisions = []
    
    for slug, raw_score in pages_to_score:
        if raw_score < 75:
            print(f"   ⚠️ Thin content detected: {slug} (Score: {raw_score}) -> Queueing for revision")
            revisions.append([slug, str(raw_score), "Low word count, sparse internal links", "Yes"])
        else:
            print(f"   ✅ Quality pass: {slug} (Score: {raw_score})")

    # Update Google Sheet if there's any revision needed
    if revisions:
        headers = sf.PHASE1_TABS.get('Content_Revision_Queue', [['Slug', 'Score', 'Issues', 'Revisions_Needed']])
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Content_Revision_Queue'!A1", valueInputOption='RAW', body={'values': headers + revisions}).execute()

    print("🏁 Quality Scoring Complete. Thin pages routed to revision queue.")
