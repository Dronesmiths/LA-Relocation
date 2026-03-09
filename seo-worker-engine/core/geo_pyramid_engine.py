import os
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def build_geo_pyramid():
    print("🏛️ Constructing Geo Content Pyramid Architecture...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=sf.SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    cities = [row[0] for row in get_tab_data('Cities') if row]
    if not cities:
        cities = ["Palmdale", "Lancaster", "Santa Clarita", "Burbank", "Glendale"]
        
    hubs = []
    layers = []
    pyramid = []
    routes = []

    # Map core semantic hubs (Cities)
    for city in cities:
        c_slug = sf.get_slug(city)
        hub_url = f"/{c_slug}/"
        
        # 1. Hub Definition
        hubs.append(["Antelope Valley/LA County", city, hub_url, "High"])
        
        # 2. Layer Examples
        layer_classes = [
            ("neighborhood", "neighborhood_page", f"rancho-vista-{c_slug}"),
            ("comparison", "comparison_page", f"{c_slug}-vs-lancaster"),
            ("radius", "radius_page", f"cities-near-{c_slug}"),
            ("idx", "idx_filter_page", f"homes-under-500k-{c_slug}"),
            ("market", "market_page", f"{c_slug}-housing-market"),
            ("seller", "seller_page", f"what-is-my-home-worth-{c_slug}"),
            ("lifestyle", "topic_page", f"living-in-{c_slug}")
        ]
        
        for l_type, p_type, slug_ex in layer_classes:
            layers.append([city, l_type, p_type, slug_ex])
            
            # Map into the Pyramid (Parent-Child) Structure
            pyramid.append([city, l_type, slug_ex, hub_url, "High"])

            # Map the Bi-Directional Linking Rule for this node
            routes.append([
                f"/{slug_ex}/", hub_url, "upward_hub_reinforcement", "High"
            ])
            # E.g. Top Neighborhoods widget on city page points down
            if l_type in ["neighborhood", "idx", "market"]:
                routes.append([
                    hub_url, f"/{slug_ex}/", "downward_layer_distribution", "Medium"
                ])
                
        # Neighborhood -> IDX + Market Cross-linking
        n_slug = f"rancho-vista-{c_slug}"
        m_slug = f"{c_slug}-housing-market"
        idx_slug = f"homes-under-500k-{c_slug}"
        
        routes.append([f"/{n_slug}/", f"/{m_slug}/", "lateral_market_context", "Medium"])
        routes.append([f"/{n_slug}/", f"/{idx_slug}/", "lateral_idx_conversion", "High"])

    # PUSH TO GOOGLE SHEETS
    if hubs:
        headers = sf.PHASE1_TABS['Geo_Hubs']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Geo_Hubs'!A1", valueInputOption='RAW', body={'values': headers + hubs}).execute()

    if layers:
        headers = sf.PHASE1_TABS['Geo_Layers']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Geo_Layers'!A1", valueInputOption='RAW', body={'values': headers + layers}).execute()

    if pyramid:
        headers = sf.PHASE1_TABS['Geo_Pyramid']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Geo_Pyramid'!A1", valueInputOption='RAW', body={'values': headers + pyramid}).execute()

    if routes:
        headers = sf.PHASE1_TABS['Geo_Routing']
        service.spreadsheets().values().update(spreadsheetId=sf.SPREADSHEET_ID, range="'Geo_Routing'!A1", valueInputOption='RAW', body={'values': headers + routes}).execute()

    print(f"✅ Pyramid Architecture Established: Centralized {len(cities)} hubs with {len(pyramid)} supporting pillars.")
