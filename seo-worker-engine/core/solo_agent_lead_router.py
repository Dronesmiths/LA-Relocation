import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

# Mock agent config
AGENT_NAME = "Local Real Estate Expert"
AGENT_EMAIL = "agent@larelocation.com"
AGENT_PHONE = "555-0199"

def route_leads():
    print("👤 Initializing Solo Agent Lead Capture System...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    leads = []
    
    # Simulate inbound traffic generating various leads
    lead_types = [
        "buyer_inquiry", "property_showing_request", "relocation_help_request", 
        "home_value_request", "market_report_request"
    ]

    for i in range(random.randint(2, 6)):
        l_type = random.choice(lead_types)
        city = random.choice(["Palmdale", "Lancaster", "Santa Clarita", "Burbank"])
        
        url_source = f"/{sf.get_slug(city)}/"
        if l_type == "property_showing_request":
            url_source = f"/{sf.get_slug(city)}-homes-for-sale/"
        elif l_type == "relocation_help_request":
            url_source = f"/moving-to-{sf.get_slug(city)}/"
        elif l_type == "home_value_request":
            url_source = f"/what-is-my-home-worth-{sf.get_slug(city)}/"
        elif l_type == "market_report_request":
            url_source = f"/{sf.get_slug(city)}-housing-market-forecast/"

        # Send notification logic (Mocked)
        print(f"   -> 📧 Emailing {AGENT_EMAIL}: New {l_type.replace('_', ' ').title()}")
        print(f"   -> 📱 SMS to {AGENT_PHONE}: Lead captured on {url_source}")
        print(f"   -> 🪝 Webhook CRM Sync: Successful")

        leads.append([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"User_{random.randint(1000, 9999)}",
            f"user{random.randint(100,999)}@example.com",
            f"555-{random.randint(1000,9999)}",
            l_type,
            url_source,
            city,
            "Unknown",
            "Email+SMS+CRM",
            "New"
        ])

    if leads:
        headers = sf.PHASE1_TABS['Solo_Agent_Leads']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Solo_Agent_Leads'!A1", valueInputOption='RAW', body={'values': headers + leads}).execute()

    print(f"✅ Routed {len(leads)} fresh leads directly to {AGENT_NAME}.")
