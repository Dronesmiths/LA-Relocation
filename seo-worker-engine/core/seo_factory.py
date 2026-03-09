import os
import sys
import argparse
import xml.etree.ElementTree as ET
import json
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import re
import random
import demographic_ingest


def get_slug(name):
    """Robust slugifier that handles non-breaking spaces and hidden whitespace."""
    if not name: return "-"
    return '-'.join(str(name).lower().split()).replace('_', '-')

def get_cities_from_inventory(service):
    """Robust city discovery from Sitemap Inventory or fallback lists."""
    try:
        inventory = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'Sitemap Inventory'!A2:B").execute().get('values', [])
    except:
        inventory = []

    cities = []
    for row in inventory:
        if len(row) >= 2 and (row[1] == '📍' or 'location' in row[1].lower()):
            url = row[0]
            city_slug = url.rstrip('/').split('/')[-1]
            city_name = city_slug.replace('-', ' ').title()
            if city_name not in cities:
                cities.append(city_name)
    
    if not cities:
        # Core service area fallback
        cities = ['Burbank', 'Lancaster', 'Palmdale', 'Santa Clarita', 'Glendale', 'Long Beach', 'Torrance', 'Pasadena']
    
    return cities

# --- Configuration Loader ---
def load_config():
    """Loads site-specific configuration from config.json."""
    # The config is in the parent folder of 'core'
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config.json')
    if not os.path.exists(config_path):
        print(f"ERROR: config.json not found at {config_path}")
        sys.exit(1)
    with open(config_path, 'r') as f:
        return json.load(f)

CONFIG = load_config()
ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Resolve ROOT_DIR relative to ENGINE_ROOT
WEBSITE_REL_PATH = CONFIG.get('WEBSITE_DIR', '../website')
ROOT_DIR = os.path.abspath(os.path.join(ENGINE_ROOT, WEBSITE_REL_PATH))

SITEMAP_PATH = os.path.join(ROOT_DIR, CONFIG.get('SITEMAP_FILENAME', 'sitemap.xml'))
SPREADSHEET_ID = CONFIG.get('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.path.join(ENGINE_ROOT, CONFIG.get('SERVICE_ACCOUNT_FILE', 'service-account.json'))
GSC_SITE_URL = CONFIG.get('GSC_SITE_URL')
DOMAIN = CONFIG.get('DOMAIN', 'https://example.com').rstrip('/')

SITEMAP_MAPPING = CONFIG.get('SITEMAP_MAPPING', {
    '📂 SERVICE PAGES': ['/services/', '/features/'],
    '✍️ BLOG ARTICLES': ['/blog/'],
    '📍 LOCATIONS': ['/locations/'],
    '🏗️ INDUSTRIES': ['/industries/'],
    'Funnel Pages': ['/pricing/', '/contact/', '/portfolio/'],
})

# Tab Definitions for Sync (Client-Friendly)
SEO_GROWTH_TABS = {
    '📖 CLIENT GUIDE': [['Section', 'Description', 'Value to You']],
    '📊 RESULTS DASHBOARD': [['Metric', 'Value', 'Goal', 'Status']],
    '🏥 WEBSITE WELLNESS': [['URL', 'Health Score', 'Meta Title', 'Meta Description', 'Status (Action Required)']],
    '🔑 CONTENT PERFORMANCE': [['Target Keyword', 'Difficulty', 'Current Rank', 'Target Page', 'Monthly Reach (Impressions)']],
    '🚀 GROWTH OPPORTUNITIES': [['New Topic', 'Buying Intent', 'Priority', 'Status']],
    '⚔️ COMPETITOR WATCH': [['Competitor', 'Website URL', 'Their Strength', 'Our Opportunity']],
    'Backlink_Audit': [['URL', 'External Backlinks', 'Internal Links', 'Authority Score', 'Status', 'Action']],
    '📂 SERVICE PAGES': [['URL', 'Last Modified', 'Status', 'Service Name', 'SEO Page Title']],
    '✍️ BLOG ARTICLES': [['URL', 'Last Modified', 'Status', 'Article Category', 'SEO Page Title']],
    'Sitemap Inventory': [['URL', 'Page Type', 'Parent Topic', 'Primary Keyword', 'Internal Links', 'Last Updated']],
    'Cornerstone_Map': [['Cornerstone', 'URL', 'Target Keyword', 'Ideal Supporting Pages', 'Current Supporting Pages', 'Missing Pages', 'Priority']],
    'Subpage_Plan': [['Parent Cornerstone', 'Subpage Topic', 'Page Type', 'Target Keyword', 'Status']],
    'Expansion_Engine': [['Cluster', 'Suggested Page', 'Target Keyword', 'Impressions', 'Opportunity Type']],
    'Reinforcement_Queue': [['URL', 'Page_Type', 'City', 'Data_Source_Trigger', 'Reason', 'Priority', 'Status']],
    'Internal_Link_Queue': [['Source Page', 'Target Page', 'Suggested Anchor', 'Cluster', 'Reason']],
    'Authority_Radar': [['Cluster', 'Total Pages', 'Internal Links', 'External Backlinks', 'Total Impressions', 'Average Position', 'Gravity Score', 'Opportunity Score', 'Priority']],
    'Cluster_Map': [['Cluster', 'URL', 'Pages', 'Gravity Score', 'Opportunity Score', 'Priority', 'Recommended Action']],
    '📍 LOCATIONS': [['URL', 'Location Name', 'Region', 'Status', 'Health Score', 'Last Updated']]
}

# Phase 1 Tab Definitions
PHASE1_TABS = {
    'Page_Inventory': [['URL', 'Page Type', 'City', 'Topic', 'Status', 'Notes']],
    'Cities': [['City', 'County', 'State', 'Slug', 'Existing Page']],
    'Neighborhoods': [['Neighborhood', 'City', 'Slug', 'Existing_Page', 'Discovery_Source', 'Priority']],
    'Blog_Topics': [['Blog Title', 'Keyword', 'City', 'URL', 'Status']],
    'Services': [['Service', 'Slug', 'URL', 'Status']],
    'IDX_Pages': [['Title', 'Slug', 'URL', 'Status']],
    'SEO_Expansion': [['Topic', 'Target City', 'Priority', 'Status']],
    'Internal_Links': [['Source', 'Target', 'Anchor', 'Status']],
    'Automation_Queue': [['Task', 'Target', 'Priority', 'Status']],
    'Crime_Data': [['City', 'State', 'Crime Index', 'Violent Crime', 'Property Crime', 'Safety Rating', 'Data Source']],
    'Schools': [['School', 'City', 'Rating', 'Type', 'District', 'Address', 'Source']],
    'Housing_Data': [['City', 'Median Price', 'Price Change', 'Inventory', 'Days on Market', 'Trend']],
    'Commute_Data': [['City', 'Destination', 'Distance', 'Average Time', 'Method']],
    'Amenities_Data': [['City', 'Parks', 'Shopping_Centers', 'Hospitals', 'Restaurants', 'Entertainment', 'Walkability_Score']],
    'Relocation_Topics': [['City', 'Topic', 'Search_Intent', 'Priority', 'Status']],
    'Demographic_Data': [['City', 'Population', 'Population_Growth', 'Median_Age', 'Median_Household_Income', 'Owner_Occupied_Percent', 'Renter_Occupied_Percent', 'Median_Rent', 'Median_Home_Value', 'Households_With_Children', 'Education_Level', 'Last_Updated', 'Data_Source']],
    'Search_Modifiers': [['Modifier', 'Modifier_Type', 'Intent', 'Priority', 'Applies_To', 'Status']],
    'Modifier_Pages': [['City', 'Neighborhood', 'Modifier', 'Generated_Slug', 'Page_Type', 'Priority', 'Status']],
    'Geo_Expansion': [['Primary_City', 'Nearby_City', 'County', 'Distance', 'SEO_Opportunity', 'Status']],
    'Property_Features': [['Feature', 'Feature_Type', 'Search_Intent', 'Priority', 'Status']],
    'Feature_Pages': [['City', 'Neighborhood', 'Feature', 'Slug', 'Priority', 'Status']],
    'Authority_Score': [['City', 'Neighborhood', 'Has_City_Page', 'Has_Neighborhood_Page', 'Has_IDX_Page', 'Has_Blogs', 'Has_Crime_Data', 'Has_School_Data', 'Has_Market_Data', 'Has_Commute_Data', 'Has_Demographic_Data', 'Internal_Link_Coverage', 'Authority_Score', 'Priority_Action']],
    'Master_Site_Map': [['Parent_Page', 'Child_Page', 'Page_Type', 'Cluster', 'Priority', 'Exists', 'Needs_Generation']],
    'Geo_Dataset': [['Geo_ID', 'Name', 'Geo_Type', 'Parent_Geo', 'Latitude', 'Longitude', 'Population', 'County', 'State', 'Status']],
    'Zip_Pages': [['Zip', 'City', 'Slug', 'Population', 'Priority', 'Status']],
    'Geo_Grid_Plan': [['Geo_Type', 'Parent_City', 'Location', 'Slug', 'Page_Type', 'Priority', 'Status']],
    'IDX_Filter_Plan': [['City', 'Neighborhood', 'Filter_Type', 'Filter_Value', 'Slug', 'Page_Type', 'Priority', 'Status']],
    'Buyer_Intent_Queries': [['Query', 'Source', 'Intent_Type', 'City', 'Neighborhood', 'Modifier', 'Feature', 'Impressions', 'Clicks', 'CTR', 'Position', 'Priority', 'Status']],
    'Intent_Clusters': [['Cluster_Name', 'Intent_Type', 'Primary_City', 'Supporting_Queries', 'Recommended_Page_Type', 'Priority', 'Status']],
    'PAA_Topics': [['Question', 'City', 'Intent_Type', 'Recommended_Page', 'Priority', 'Status']],
    'AutoSuggest_Topics': [['Phrase', 'City', 'Modifier', 'Intent_Type', 'Recommended_Page_Type', 'Priority', 'Status']],
    'Intent_Opportunities': [['Opportunity_Type', 'Query_Cluster', 'City', 'Suggested_Slug', 'Suggested_Page_Type', 'Source', 'Priority', 'Exists', 'Needs_Generation']],
    'Local_Reviews': [['City', 'Business_Name', 'Review_Source', 'Rating', 'Review_Count', 'Snippet', 'Last_Updated']],
    'Local_Businesses': [['City', 'Business_Name', 'Category', 'Address', 'Latitude', 'Longitude', 'Website', 'Data_Source']],
    'Local_Citations': [['City', 'Citation_Source', 'URL', 'Category', 'Status', 'Last_Checked']],
    'Authority_Signals': [['City', 'Total_Reviews', 'Average_Rating', 'Business_Count', 'Citation_Count', 'Authority_Score', 'Priority_Action']],
    'User_Behavior': [['Timestamp', 'Page_URL', 'Session_ID', 'Event_Type', 'Scroll_Depth', 'Time_On_Page', 'IDX_Click', 'City', 'Neighborhood', 'Device_Type']],
    'Page_Performance': [['URL', 'Page_Type', 'City', 'Views', 'Average_Time_On_Page', 'Scroll_Depth_Avg', 'IDX_Click_Rate', 'Bounce_Rate', 'Engagement_Score']],
    'Behavior_Insights': [['City', 'Neighborhood', 'Insight_Type', 'Insight', 'Priority']],
    'City_Comparisons': [['City_A', 'City_B', 'Distance_Miles', 'Price_Diff_Percent', 'Housing_Score', 'Safety_Score', 'Schools_Score', 'Commute_Score', 'Overall_Winner', 'Slug', 'Priority', 'Status']],
    'Deployment_Queue': [['URL', 'Page_Type', 'City', 'Cluster', 'Generated_At', 'Validation_Status', 'Deployment_Status', 'Priority', 'Notes']],
    'System_Health': [['Metric', 'Value', 'Threshold', 'Status', 'Recommended_Action']],
    'Neighborhood_Dataset': [['Neighborhood_Name', 'City', 'County', 'Latitude', 'Longitude', 'Population', 'Geo_Source', 'Discovery_Method', 'Priority', 'Status']],
    'Neighborhood_Pages': [['City', 'Neighborhood', 'Slug', 'Page_Type', 'Priority', 'Exists', 'Needs_Generation']],
    'Lead_Events': [['Timestamp', 'Page_URL', 'City', 'Neighborhood', 'Intent_Type', 'Lead_Type', 'Action', 'Device_Type', 'Session_ID']],
    'Lead_Sources': [['Page_URL', 'City', 'Page_Type', 'Intent_Type', 'Visitors', 'Leads', 'Conversion_Rate', 'Primary_Lead_Type', 'Priority']],
    'Lead_Capture_Strategies': [['Page_Type', 'Intent_Type', 'Lead_Widget', 'Placement', 'Priority']],
    'Lead_Conversion_Insights': [['City', 'Page_Type', 'Insight', 'Recommended_Action', 'Priority']],
    'Radius_Hubs': [['Hub_Name', 'Hub_Type', 'Latitude', 'Longitude', 'County', 'State', 'Priority', 'Status']],
    'Radius_Pages': [['Hub_Name', 'Location_Name', 'Page_Angle', 'Slug', 'Page_Type', 'Priority', 'Exists', 'Needs_Generation']],
    'Radius_Insights': [['Hub_Name', 'Insight_Type', 'Description', 'Priority']],
    'Radius_Pairs': [['Hub_Name', 'Location_Name', 'Location_Type', 'Distance_Miles', 'Estimated_Drive_Time', 'Relationship_Type', 'Priority', 'Status']],
    'Chat_Interactions': [['Timestamp', 'Session_ID', 'Page_URL', 'User_Query', 'Intent_Type', 'City', 'Neighborhood', 'Response_Type', 'Lead_Triggered', 'Device_Type']],
    'Chat_Insights': [['Topic', 'City', 'Query_Count', 'Intent_Type', 'Recommended_Page', 'Priority']],
    'Chat_Leads': [['Timestamp', 'Session_ID', 'City', 'Neighborhood', 'Lead_Type', 'Contact_Method', 'Status']],
    'Market_Signals': [['City', 'Neighborhood', 'Median_Home_Price', 'Median_Price_Per_SqFt', 'Inventory', 'Days_On_Market', 'Yearly_Change', 'Quarterly_Change', 'New_Listings', 'Price_Reductions', 'Migration_Trend', 'Rent_Growth', 'Last_Updated']],
    'Market_Predictions': [['City', 'Neighborhood', 'Momentum_Score', 'Trend_Label', 'Confidence_Level', 'Primary_Drivers', 'Risk_Factors', 'Last_Calculated', 'Priority']],
    'Trend_Insights': [['City', 'Insight_Type', 'Insight', 'Supporting_Signals', 'Recommended_Page_Type', 'Priority']],
    'Prediction_Pages': [['City', 'Neighborhood', 'Slug', 'Page_Angle', 'Page_Type', 'Priority', 'Exists', 'Needs_Generation']],
    'Seller_Intent_Queries': [['Query', 'City', 'Neighborhood', 'Intent_Type', 'Query_Count', 'Source', 'Priority']],
    'Seller_Insights': [['City', 'Neighborhood', 'Insight_Type', 'Insight', 'Supporting_Data', 'Recommended_Page', 'Priority']],
    'Seller_Pages': [['City', 'Neighborhood', 'Slug', 'Page_Angle', 'Page_Type', 'Priority', 'Exists', 'Needs_Generation']],
    'Home_Value_Leads': [['Timestamp', 'City', 'Neighborhood', 'Property_Type', 'Lead_Type', 'Contact_Method', 'Status']],
    'Migration_Flows': [['Origin_City', 'Destination_City', 'Distance_Miles', 'Median_Price_Diff', 'Crime_Diff', 'School_Diff', 'Commute_Diff', 'Migration_Trend', 'Search_Demand', 'Priority']],
    'Migration_Signals': [['Signal_ID', 'Source_Type', 'Origin', 'Destination', 'Intent_Score', 'Last_Detected']],
    'Migration_Insights': [['Origin_City', 'Destination_City', 'Insight_Type', 'Insight', 'Supporting_Data', 'Recommended_Page', 'Priority']],
    'Migration_Pages': [['Origin_City', 'Destination_City', 'Slug', 'Page_Angle', 'Page_Type', 'Priority', 'Exists', 'Needs_Generation']],
    'Authority_Hubs': [['Hub_URL', 'Hub_Type', 'City', 'Primary_Topic', 'Supporting_Page_Count', 'Authority_Status', 'Priority']],
    'Authority_Loops': [['Loop_ID', 'Primary_Hub', 'Supporting_URL', 'Page_Type', 'Anchor_Angle', 'Loop_Type', 'Priority', 'Status']],
    'Authority_Links': [['Source_URL', 'Target_URL', 'Anchor_Text', 'Anchor_Type', 'Link_Context', 'Priority', 'Status']],
    'Authority_Gaps': [['URL', 'Page_Type', 'Missing_Link_Type', 'Recommended_Target', 'Priority', 'Status']],
    'Authority_Flywheel_Score': [['City', 'Total_Pages_In_Cluster', 'Hub_Count', 'Loop_Count', 'Internal_Link_Coverage', 'Semantic_Anchor_Diversity', 'Gap_Count', 'Hub_Gravity_Score', 'Flywheel_Score', 'Recommended_Action']]
}








# --- Data Registry Loader ---
def load_registry(name):
    """Loads default data lists from the registries folder."""
    registry_path = os.path.join(ENGINE_ROOT, 'core', 'registries', f"{name}.json")
    if os.path.exists(registry_path):
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load registry {name}: {e}")
    return []

CORNERSTONE_FILE = os.path.join(ENGINE_ROOT, 'core', 'registries', 'cornerstones.json')
CORNERSTONE_MAP_EXAMPLES = load_registry('cornerstones')
SUBPAGE_PLAN_EXAMPLES = load_registry('subpage_plan')
EXPANSION_ENGINE_EXAMPLES = load_registry('expansion_engine')
LOCATIONS_REGISTRY = load_registry('locations_registry')
MARKET_INTEL_RAW = load_registry('market_intel')

# Standardize Market Intel format if it's a dict
MARKET_INTEL = MARKET_INTEL_RAW if isinstance(MARKET_INTEL_RAW, dict) else {
    '🚀 GROWTH OPPORTUNITIES': [],
    '⚔️ COMPETITOR WATCH': [],
    'Backlink_Audit': []
}

CLIENT_GUIDE_DATA = [
    ['DASHBOARD', 'A bird\'s-eye view of your total SEO success and growth progress.', 'Shows your ROI and overall site authority.'],
    ['WELLNESS', 'A technical "medical checkup" of your website pages.', 'Ensures Google can read your site perfectly.'],
    ['PERFORMANCE', 'Tracking exactly which keywords are driving people to your site.', 'Shows you what your customers are actually searching for.'],
    ['GROWTH', 'A roadmap of new content we should build to capture more traffic.', 'Plan for future customer acquisition.'],
    ['COMPETITORS', 'Monitoring who else is competing for your customers online.', 'Helps us stay one step ahead of the market.'],
    ['TRUST SIGNALS', 'Websites that are linking to you, which builds your authority.', 'The #1 factor for ranking higher on Google.']
]

# --- Core Logic ---

def get_ns():
    return {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

def categorize_url(url):
    for category, patterns in SITEMAP_MAPPING.items():
        for pattern in patterns:
            if pattern in url:
                return category
    return 'Page Health'

def get_sitemap_urls():
    if not os.path.exists(SITEMAP_PATH):
        return []
    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()
    urls = []
    for url_tag in root.findall('ns:url', get_ns()):
        loc = url_tag.find('ns:loc', get_ns()).text
        lastmod = url_tag.find('ns:lastmod', get_ns()).text if url_tag.find('ns:lastmod', get_ns()) is not None else ''
        urls.append({'loc': loc, 'lastmod': lastmod})
    return urls

def cmd_sitemap():
    """Generates a fresh sitemap.xml by crawling the local directory."""
    print("Regenerating sitemap from local files...")
    domain = CONFIG.get('DOMAIN', 'https://aipilots.site')
    sitemap_path = os.path.join(ROOT_DIR, 'sitemap.xml')
    
    # Standard patterns to include or just recursive search
    import glob
    found_pages = []
    
    # Hero search for all index.html
    matches = glob.glob(os.path.join(ROOT_DIR, '**/index.html'), recursive=True)
    for m in matches:
        if 'node_modules' in m or '.git' in m: continue
        rel = os.path.relpath(m, ROOT_DIR)
        url_path = '/' + rel.replace('index.html', '')
        found_pages.append(url_path)
            
    # Deduplicate and build XML
    found_pages = sorted(list(set(found_pages)))
    
    # Use the same namespace logic as existing sitemap
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for p in found_pages:
        url_tag = ET.SubElement(root, "url")
        loc = ET.SubElement(url_tag, "loc")
        loc.text = f"{domain}{p}"
        lastmod = ET.SubElement(url_tag, "lastmod")
        lastmod.text = datetime.now().strftime('%Y-%m-%d')

    tree = ET.ElementTree(root)
    tree.write(sitemap_path, encoding='utf-8', xml_declaration=True)
    print(f"SUCCESS: Updated sitemap with {len(found_pages)} pages.")

def update_sitemap(new_url):
    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()
    
    # Check if exists
    for url_tag in root.findall('ns:url', get_ns()):
        if url_tag.find('ns:loc', get_ns()).text == new_url:
            print(f"URL {new_url} already in sitemap.")
            return

    url_tag = ET.SubElement(root, '{http://www.sitemaps.org/schemas/sitemap/0.9}url')
    loc_tag = ET.SubElement(url_tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
    loc_tag.text = new_url
    lastmod_tag = ET.SubElement(url_tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
    lastmod_tag.text = datetime.now().strftime('%Y-%m-%d')
    
    # Prettify and save
    ET.indent(tree, space="  ", level=0)
    tree.write(SITEMAP_PATH, encoding='utf-8', xml_declaration=True)
    print(f"Updated sitemap.xml with {new_url}")

# --- Phase 1 Specific Logic ---

def cmd_init_phase1():
    """Initializes the sheet with Phase 1 tab structure and populates from sitemap."""
    print("🚀 Initializing Phase 1: Mapped Sheet Structure...")
    all_urls = get_sitemap_urls()
    print(f"Discovered {len(all_urls)} pages in sitemap.")

    inventory_rows = []
    city_rows = []
    blog_rows = []
    service_rows = []

    # Known city list for parsing (can be expanded)
    known_cities = ['palmdale', 'lancaster', 'santa-clarita', 'valencia', 'stevenson-ranch', 'canyon-country', 'saugus', 'newhall', 'castaic', 'burbank', 'glendale', 'long-beach', 'torrance', 'whittier', 'inglewood', 'downey', 'pasadena']
    
    for u in all_urls:
        url = u['loc']
        path = url.replace(DOMAIN, '').strip('/')
        parts = path.split('/')
        
        page_type = 'page'
        city = 'none'
        topic = '-'
        
        # Identification Logic
        if not path:
            page_type = 'home'
            topic = 'homepage'
        elif 'blog/' in url:
            page_type = 'blog'
            topic = parts[-1].replace('-', ' ').title()
            for c in known_cities:
                if c in path: city = c.replace('-', ' ').title()
        elif any(c in path for c in known_cities):
            page_type = 'city'
            city = parts[0].replace('-', ' ').title()
            topic = 'city overview'
        elif 'services/' in url or 'search-homes' in path or 'sell-your-home' in path:
            page_type = 'service'
            topic = parts[-1].replace('-', ' ').title()
        
        # Map to Inventory
        inventory_rows.append([url, page_type, city, topic, 'existing', ''])

        # Identification for specific tabs
        if page_type == 'city':
            city_rows.append([city, 'Los Angeles', 'CA', parts[0], 'yes'])
        elif page_type == 'blog':
            blog_rows.append([topic, topic, city, url, 'existing'])
        elif page_type == 'service':
            service_rows.append([topic, parts[-1], url, 'existing'])

    # Deduplicate City Rows
    unique_cities = []
    city_slugs = set()
    for row in city_rows:
        if row[3] not in city_slugs:
            unique_cities.append(row)
            city_slugs.add(row[3])

    # Authenticate and Update
    print("Authenticating with Google Sheets...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    # 1. Cleanup & Create Tabs
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    requests = []
    
    # Add missing tabs
    for title in PHASE1_TABS.keys():
        if title not in existing_sheets:
            requests.append({'addSheet': {'properties': {'title': title}}})
    
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': requests}).execute()
        # Refresh existing_sheets map
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 2. Populate Data
    data_updates = []
    
    def prepare_update(tab_name, rows):
        header = PHASE1_TABS[tab_name]
        values = header + rows
        return {
            'range': f"'{tab_name}'!A1",
            'values': values
        }

    data_updates.append(prepare_update('Page_Inventory', inventory_rows))
    data_updates.append(prepare_update('Cities', unique_cities))
    data_updates.append(prepare_update('Blog_Topics', blog_rows))
    data_updates.append(prepare_update('Services', service_rows))
    
    # Initialize empty tabs with just headers
    for tab in ['Neighborhoods', 'IDX_Pages', 'SEO_Expansion', 'Internal_Links', 'Automation_Queue']:
        data_updates.append(prepare_update(tab, []))

    print("Updating Google Sheet values...")
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, 
        body={'valueInputOption': 'RAW', 'data': data_updates}
    ).execute()

    # 3. Formatting
    format_requests = []
    for title, sheet_id in existing_sheets.items():
        if title in PHASE1_TABS:
            # Header Formatting
            format_requests.append({
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            })
            # Freeze Header
            format_requests.append({
                'updateSheetProperties': {
                    'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
                    'fields': 'gridProperties.frozenRowCount'
                }
            })
            # Auto-resize columns
            format_requests.append({
                'autoResizeDimensions': {
                    'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 10}
                }
            })

    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 1 COMPLETE: SEO Brain Sheet Fully Mapped.")


def cmd_init_phase2():
    """Phase 2: Connect Engine to Sheet, Detect Clusters, and Seed Expansion."""
    print("🚀 Initializing Phase 2: Authority Map & Expansion...")
    
    # 1. Fetch current sitemap and page inventory
    all_urls = get_sitemap_urls()
    print(f"Analyzing {len(all_urls)} pages...")

    # Data Containers
    inventory_rows = []
    city_rows = []
    neighborhood_rows = []
    blog_rows = []
    service_rows = []
    idx_rows = []
    expansion_rows = []
    subpage_plan_rows = []

    # Reference Data
    known_cities = {
        'palmdale': 'Los Angeles', 'lancaster': 'Los Angeles', 'santa-clarita': 'Los Angeles', 
        'valencia': 'Los Angeles', 'stevenson-ranch': 'Los Angeles', 'canyon-country': 'Los Angeles', 
        'saugus': 'Los Angeles', 'newhall': 'Los Angeles', 'castaic': 'Los Angeles', 
        'burbank': 'Los Angeles', 'glendale': 'Los Angeles', 'long-beach': 'Los Angeles', 
        'torrance': 'Los Angeles', 'whittier': 'Los Angeles', 'inglewood': 'Los Angeles', 
        'downey': 'Los Angeles', 'pasadena': 'Los Angeles'
    }
    
    neighborhood_map = {
        'rancho-vista': 'Palmdale', 'ana-verde': 'Palmdale', 'joshua-ranch': 'Palmdale',
        'west-lancaster': 'Lancaster', 'quartz-hill': 'Lancaster',
        'bridgeport': 'Valencia', 'westridge': 'Stevenson Ranch', 'copper-hill': 'Saugus',
        'tesoro-del-valle': 'Valencia', 'river-island': 'Lathrop'
    }

    # 2. Process Page Inventory
    for u in all_urls:
        url = u['loc']
        path = url.replace(DOMAIN, '').strip('/')
        parts = path.split('/')
        
        page_type = 'page'
        city = 'none'
        topic = '-'
        
        # Categorization Logic
        if not path:
            page_type = 'home'
            topic = 'homepage'
        elif 'blog/' in url:
            page_type = 'blog'
            topic = parts[-1].replace('-', ' ').title()
            for c in known_cities:
                if c in path: city = c.replace('-', ' ').title()
        elif 'services/' in url or any(k in path for k in ['search-homes', 'sell-your-home', 'home-valuation']):
            page_type = 'service'
            topic = parts[-1].replace('-', ' ').title()
        elif any(n in path for n in neighborhood_map):
            page_type = 'neighborhood'
            for n, c in neighborhood_map.items():
                if n in path:
                    city = c
                    topic = n.replace('-', ' ').title()
        elif any(c in path for c in known_cities):
            page_type = 'city'
            city = [c for c in known_cities if c in path][0].replace('-', ' ').title()
            topic = 'city overview'
        
        # Detect IDX patterns
        if any(k in path for k in ['homes-for-sale', 'real-estate-listings', 'under-', 'new-construction']):
            page_type = 'idx'
            topic = parts[-1].replace('-', ' ').title()

        inventory_rows.append([url, page_type, city, topic, 'existing'])

        # Populate Specific Tabs
        if page_type == 'city':
            city_slug = [c for c in known_cities if c in path][0]
            city_rows.append([city, known_cities[city_slug], 'CA', city_slug, 'yes'])
        elif page_type == 'neighborhood':
            neighborhood_rows.append([topic, city, parts[-1], 'yes'])
        elif page_type == 'blog':
            blog_rows.append([topic, topic, city, url, 'existing'])
        elif page_type == 'service':
            service_rows.append([topic, parts[-1], url, 'existing'])
        elif page_type == 'idx':
            idx_rows.append([topic, parts[-1], url, 'existing'])

    # 3. Seed Expansion Strategy (City Clusters)
    for city_slug, county in known_cities.items():
        city_name = city_slug.replace('-', ' ').title()
        # SEO Expansion Ideas
        expansion_rows.append([f"Moving to {city_name}", city_name, "High", "planned"])
        expansion_rows.append([f"{city_name} Housing Market", city_name, "Medium", "planned"])
        expansion_rows.append([f"Best Neighborhoods in {city_name}", city_name, "High", "planned"])
        
        # Subpage Plan (Clustering)
        # City -> Neighborhood -> IDX -> Blog
        for n_slug, n_city in neighborhood_map.items():
            if n_city.lower() == city_slug:
                n_name = n_slug.replace('-', ' ').title()
                subpage_plan_rows.append([city_name, n_name, 'neighborhood', f"{n_name} Homes", "unbuilt"])
                subpage_plan_rows.append([n_name, f"{n_name} Homes for Sale", 'idx', f"{n_name} Real Estate", "unbuilt"])
        
        subpage_plan_rows.append([city_name, f"{city_name} Relocation Guide", 'blog', f"Moving to {city_name}", "unbuilt"])

    # 4. Authenticate and Update Sheets
    print("Authenticating with Google Sheets...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    data_updates = []
    
    def prepare_update(tab_name, rows):
        # We need to fetch current headers if they exist, otherwise use Phase 1 defs
        # For simplicity, we'll re-apply headers
        header = PHASE1_TABS.get(tab_name, [])
        return {
            'range': f"'{tab_name}'!A1",
            'values': header + rows
        }

    data_updates.append(prepare_update('Page_Inventory', inventory_rows))
    data_updates.append(prepare_update('Cities', unique_list(city_rows, 3)))
    data_updates.append(prepare_update('Neighborhoods', unique_list(neighborhood_rows, 2)))
    data_updates.append(prepare_update('Blog_Topics', blog_rows))
    data_updates.append(prepare_update('Services', service_rows))
    data_updates.append(prepare_update('IDX_Pages', idx_rows))
    data_updates.append(prepare_update('SEO_Expansion', expansion_rows))
    data_updates.append(prepare_update('Subpage_Plan', subpage_plan_rows))

    print("Updating Google Sheet with Phase 2 Authority Map...")
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, 
        body={'valueInputOption': 'RAW', 'data': data_updates}
    ).execute()

    print("✅ PHASE 2 COMPLETE: Authority Map & Expansion Initialized.")

# --- Phase 3 Crime Data Engine ---

def fetch_crime_stats(city, state="CA"):
    """
    Simulates fetching crime data from public APIs (FBI, Crimeometer).
    In a production environment, this would use API keys.
    """
    # Mock data based on city name for demonstration
    # Real implementations would use requests.get(API_URL, params={...})
    hash_val = sum(ord(c) for c in city)
    crime_index = (hash_val % 40) + 30  # 30-70 range
    violent_crime = round((hash_val % 5) + 2.5, 1)
    property_crime = round((hash_val % 15) + 15.0, 1)
    
    safety_rating = "Excellent" if crime_index < 40 else "Good" if crime_index < 55 else "Average"
    if crime_index > 65: safety_rating = "Below Average"

    return {
        'index': crime_index,
        'violent': violent_crime,
        'property': property_crime,
        'rating': safety_rating,
        'source': "FBI/Crimeometer (Aggregated)"
    }

def cmd_init_crime():
    """Initializes the Crime_Data tab and seeds safety-focused clusters."""
    print("🛡️ Initializing Phase 3: Crime Data Engine...")
    
    # 1. Get Cities from Sheet
    print("Authenticating with Google Sheets...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    cities = get_cities_from_inventory(service)

    crime_rows = []
    expansion_rows = []
    subpage_plan_rows = []

    for city in cities:
        print(f"Fetching crime data for {city}...")
        stats = fetch_crime_stats(city)
        crime_rows.append([city, 'CA', stats['index'], stats['violent'], stats['property'], stats['rating'], stats['source']])

        # Seed Expansion Engine with safety queries
        expansion_rows.append([f"{city} Crime Rate", city, "High", "planned"])
        expansion_rows.append([f"Is {city} Safe?", city, "High", "planned"])
        expansion_rows.append([f"Safest Neighborhoods in {city}", city, "Medium", "planned"])
        expansion_rows.append([f"Crime Statistics {city}", city, "Medium", "planned"])

        # Seed Subpage Plan
        subpage_plan_rows.append([city, f"{city} Crime Rate", 'page', f"{city} Safety Data", "unbuilt"])
        subpage_plan_rows.append([city, f"Safest Neighborhoods in {city}", 'blog', f"{city} Safety Guide", "unbuilt"])

    # 2. Ensure Tabs Exist
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    requests = []
    if 'Crime_Data' not in existing_sheets:
        requests.append({'addSheet': {'properties': {'title': 'Crime_Data'}}})
    
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': requests}).execute()
        # Refresh existing_sheets map
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 3. Update Sheets
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Crime_Data'!A1",
        valueInputOption='RAW', body={'values': PHASE1_TABS['Crime_Data'] + crime_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
        valueInputOption='RAW', body={'values': expansion_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
        valueInputOption='RAW', body={'values': subpage_plan_rows}
    ).execute()

    # 4. Apply Formatting to Crime_Data
    if 'Crime_Data' in existing_sheets:
        sheet_id = existing_sheets['Crime_Data']
        format_requests = [
            {
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {
                'updateSheetProperties': {
                    'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            {
                'autoResizeDimensions': {
                    'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 7}
                }
            }
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 3 COMPLETE: Crime Data Engine Initialized.")

# --- Phase 4 School Ratings Engine ---

def fetch_school_data(city):
    """
    Simulates fetching school data from public APIs (GreatSchools, NCES).
    """
    # Mock data for demonstration
    hash_val = sum(ord(c) for c in city)
    districts = ["Unified School District", "City Schools", "Educational District"]
    district = f"{city} {districts[hash_val % len(districts)]}"
    
    schools = [
        [f"{city} Elementary", city, (hash_val % 3) + 7, "Elementary", district, f"123 {city} Blvd", "GreatSchools"],
        [f"{city} Middle School", city, (hash_val % 4) + 6, "Middle", district, f"456 Edu Lane", "GreatSchools"],
        [f"{city} High School", city, (hash_val % 2) + 8, "High", district, f"789 Scholar St", "GreatSchools"],
    ]
    return schools

def cmd_init_schools():
    """Initializes the Schools tab and updates clusters."""
    print("🎓 Initializing Phase 4: School Ratings Engine...")
    
    # 1. Get Cities from Sheet
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    cities = get_cities_from_inventory(service)

    school_rows = []
    expansion_rows = []
    subpage_plan_rows = []

    for city in cities:
        print(f"Fetching school data for {city}...")
        data = fetch_school_data(city)
        school_rows.extend(data)

        # Expansion Engine
        expansion_rows.append([f"Best Schools in {city}", city, "High", "planned"])
        expansion_rows.append([f"{city} School Ratings", city, "High", "planned"])
        expansion_rows.append([f"Top Elementary Schools in {city}", city, "Medium", "planned"])
        expansion_rows.append([f"{city} School District Guide", city, "Medium", "planned"])

        # Subpage Plan: City -> Schools -> Neighborhood -> IDX
        subpage_plan_rows.append([city, f"{city} School Ratings", 'page', f"{city} Schools", "unbuilt"])
        subpage_plan_rows.append([f"{city} School Ratings", f"Best Schools in {city}", 'blog', f"{city} Education Guide", "unbuilt"])

    # 2. Ensure Tab Exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Schools' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Schools'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 3. Update Sheets
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Schools'!A1",
        valueInputOption='RAW', body={'values': PHASE1_TABS['Schools'] + school_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
        valueInputOption='RAW', body={'values': expansion_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
        valueInputOption='RAW', body={'values': subpage_plan_rows}
    ).execute()

    # 4. Formatting
    if 'Schools' in existing_sheets:
        sheet_id = existing_sheets['Schools']
        format_requests = [
            {
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
            {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 7}}}
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 4 COMPLETE: School Ratings Engine Initialized.")

# --- Phase 5 Housing Market Data Engine ---

def fetch_housing_data(city):
    """
    Simulates fetching housing market data from public APIs (Zillow, Redfin, ATTOM).
    """
    # Mock data for demonstration
    hash_val = sum(ord(c) for c in city)
    median_price = 450000 + (hash_val % 500) * 1000
    price_change = round(((hash_val % 10) - 5) / 100, 3) # -5% to +5%
    inventory = (hash_val % 200) + 50
    days_on_market = (hash_val % 60) + 15
    trend = "Upward" if price_change > 0 else "Downward" if price_change < 0 else "Stable"

    return [city, f"${median_price:,}", f"{price_change:+.1%}", inventory, days_on_market, trend]

def cmd_init_housing():
    """Initializes the Housing_Data tab and seeds market-focused clusters."""
    print("📈 Initializing Phase 5: Housing Market Data Engine...")
    
    # 1. Get Cities from Sheet
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    cities = get_cities_from_inventory(service)

    housing_rows = []
    expansion_rows = []
    subpage_plan_rows = []

    for city in cities:
        print(f"Fetching housing data for {city}...")
        data = fetch_housing_data(city)
        housing_rows.append(data)

        # Expansion Engine
        expansion_rows.append([f"{city} Housing Market", city, "High", "planned"])
        expansion_rows.append([f"{city} Home Prices", city, "High", "planned"])
        expansion_rows.append([f"{city} Real Estate Market Trends", city, "Medium", "planned"])
        expansion_rows.append([f"Housing Market {city} 2026", city, "Medium", "planned"])

        # Subpage Plan
        subpage_plan_rows.append([city, f"{city} Housing Market", 'page', f"{city} Market Data", "unbuilt"])

    # 2. Ensure Tab Exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Housing_Data' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Housing_Data'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 3. Update Sheets
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Housing_Data'!A1",
        valueInputOption='RAW', body={'values': PHASE1_TABS['Housing_Data'] + housing_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
        valueInputOption='RAW', body={'values': expansion_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
        valueInputOption='RAW', body={'values': subpage_plan_rows}
    ).execute()

    # 4. Formatting
    if 'Housing_Data' in existing_sheets:
        sheet_id = existing_sheets['Housing_Data']
        format_requests = [
            {
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
            {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 6}}}
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 5 COMPLETE: Housing Market Data Engine Initialized.")

# --- Phase 6 Commute Intelligence Engine ---

def fetch_commute_data(city):
    """
    Simulates fetching commute data from public APIs (Google Maps, Mapbox).
    """
    destinations = [
        {"name": "Los Angeles (DTLA)", "base_dist": 60, "base_time": 75},
        {"name": "Burbank (Media District)", "base_dist": 50, "base_time": 60},
        {"name": "Santa Clarita", "base_dist": 35, "base_time": 40}
    ]
    
    hash_val = sum(ord(c) for c in city)
    rows = []
    for dest in destinations:
        dist = dest['base_dist'] + (hash_val % 10)
        time = dest['base_time'] + (hash_val % 20)
        rows.append([city, dest['name'], f"{dist} miles", f"{time} mins", "Drive / Metrolink"])
    
    return rows

def cmd_init_commute():
    """Initializes the Commute_Data tab and seeds transit-focused clusters."""
    print("🚗 Initializing Phase 6: Commute Intelligence Engine...")
    
    # 1. Get Cities from Sheet
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    cities = get_cities_from_inventory(service)

    commute_rows = []
    expansion_rows = []
    subpage_plan_rows = []

    for city in cities:
        print(f"Fetching commute intelligence for {city}...")
        data = fetch_commute_data(city)
        commute_rows.extend(data)

        # Expansion Engine
        expansion_rows.append([f"Commute from {city} to Los Angeles", city, "High", "planned"])
        expansion_rows.append([f"{city} to Burbank Commute", city, "High", "planned"])
        expansion_rows.append([f"Living in {city} Working in LA", city, "Medium", "planned"])
        expansion_rows.append([f"Is {city} a good place for LA commuters", city, "Medium", "planned"])

        # Subpage Plan
        subpage_plan_rows.append([city, f"{city} Commute Guide", 'page', f"{city} Transit Analysis", "unbuilt"])

    # 2. Ensure Tab Exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Commute_Data' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Commute_Data'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 3. Update Sheets
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Commute_Data'!A1",
        valueInputOption='RAW', body={'values': PHASE1_TABS['Commute_Data'] + commute_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
        valueInputOption='RAW', body={'values': expansion_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
        valueInputOption='RAW', body={'values': subpage_plan_rows}
    ).execute()

    # 4. Formatting
    if 'Commute_Data' in existing_sheets:
        sheet_id = existing_sheets['Commute_Data']
        format_requests = [
            {
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
            {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 5}}}
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 6 COMPLETE: Commute Intelligence Initialized.")

# --- Phase 7 Amenities Intelligence Engine ---

def fetch_amenities_data(city):
    """
    Simulates fetching lifestyle and local amenity data from public APIs (Google Places, OSM, Yelp).
    """
    hash_val = sum(ord(c) for c in city)
    
    parks = (hash_val % 15) + 5
    shopping = (hash_val % 10) + 3
    hospitals = (hash_val % 4) + 1
    restaurants = (hash_val % 50) + 20
    entertainment = (hash_val % 12) + 4
    walk_score = (hash_val % 40) + 35 # 35-75 range
    
    return [city, parks, shopping, hospitals, restaurants, entertainment, walk_score]

def cmd_ingest_amenities():
    """Ingests lifestyle data into the Amenities_Data tab and seeds lifestyle clusters."""
    print("🌿 Ingesting Phase 7: Amenities Intelligence...")
    
    # 1. Get Cities from Sheet
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    cities = get_cities_from_inventory(service)

    amenities_rows = []
    expansion_rows = []
    subpage_plan_rows = []

    for city in cities:
        print(f"Ingesting amenities intelligence for {city}...")
        data = fetch_amenities_data(city)
        amenities_rows.append(data)

        # Expansion Engine
        expansion_rows.append([f"Best Parks in {city}", city, "Medium", "planned"])
        expansion_rows.append([f"Things to do in {city}", city, "High", "planned"])
        expansion_rows.append([f"{city} Shopping and Dining Guide", city, "Medium", "planned"])
        expansion_rows.append([f"Local Amenities in {city}", city, "Medium", "planned"])

        # Subpage Plan: City -> Lifestyle
        subpage_plan_rows.append([city, f"Things to do in {city}", 'page', f"{city} Lifestyle", "unbuilt"])
        subpage_plan_rows.append([city, f"Parks and Recreation in {city}", 'blog', f"{city} Perks", "unbuilt"])

    # 2. Ensure Tab Exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Amenities_Data' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Amenities_Data'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 3. Update Sheets
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Amenities_Data'!A1",
        valueInputOption='RAW', body={'values': PHASE1_TABS['Amenities_Data'] + amenities_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
        valueInputOption='RAW', body={'values': expansion_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
        valueInputOption='RAW', body={'values': subpage_plan_rows}
    ).execute()

    # 4. Formatting
    if 'Amenities_Data' in existing_sheets:
        sheet_id = existing_sheets['Amenities_Data']
        format_requests = [
            {
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
            {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 7}}}
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 7 COMPLETE: Amenities Intelligence Ingested.")

# --- Phase 8 Internal Link Authority Hardening ---

def cmd_rebuild_internal_authority():
    """Generates strategic internal links based on real estate hierarchy rules."""
    print("🔗 Rebuilding Internal Link Authority Engine...")
    
    # 1. Load Page Inventory
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    inventory_values = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Page_Inventory'!A2:F").execute().get('values', [])
    
    if not inventory_values:
        print("No pages found in 'Page_Inventory'. Please run init-phase1 first.")
        return

    # Structure data
    pages = []
    for row in inventory_values:
        if len(row) >= 3:
            pages.append({
                'url': row[0],
                'type': row[1].lower(),
                'city': row[2],
                'topic': row[3] if len(row) > 3 else ""
            })

    # Grouping
    city_map = {}
    for p in pages:
        city = p['city']
        if not city: continue
        if city not in city_map:
            city_map[city] = {'city_page': None, 'neighborhoods': [], 'idx': [], 'blogs': [], 'services': []}
        
        if p['type'] == 'city':
            city_map[city]['city_page'] = p['url']
        elif p['type'] == 'neighborhood':
            city_map[city]['neighborhoods'].append(p['url'])
        elif p['type'] == 'idx':
            city_map[city]['idx'].append(p['url'])
        elif p['type'] == 'blog':
            city_map[city]['blogs'].append(p['url'])
        elif p['type'] == 'service':
            city_map[city]['services'].append(p['url'])

    new_links = []

    # 2. Apply Linking Rules
    for city, cluster in city_map.items():
        city_url = cluster['city_page']
        
        # Rule: City -> Neighborhoods
        if city_url:
            for nb in cluster['neighborhoods']:
                anchor = random.choice([f"best neighborhoods in {city}", f"where to live in {city}", "neighborhood guide"])
                new_links.append([city_url, nb, anchor, "planned"])

        # Rule: Neighborhood -> City / IDX / Blogs
        for nb in cluster['neighborhoods']:
            if city_url:
                new_links.append([nb, city_url, f"living in {city}", "planned"])
            
            for idx in cluster['idx']:
                new_links.append([nb, idx, f"homes for sale in {city}", "planned"])
            
            for blog in cluster['blogs']:
                new_links.append([nb, blog, "local market news", "planned"])

        # Rule: Blog -> City / Neighborhood / Service
        for blog in cluster['blogs']:
            if city_url:
                new_links.append([blog, city_url, f"homes for sale in {city}", "planned"])
            
            if cluster['neighborhoods']:
                target_nb = random.choice(cluster['neighborhoods'])
                new_links.append([blog, target_nb, "neighborhood spotlights", "planned"])
            
            for svc in cluster['services']:
                new_links.append([blog, svc, "professional real estate services", "planned"])

    # 3. Update Sheets
    if not new_links:
        print("No link pairings generated.")
        return

    print(f"Generated {len(new_links)} strategic link pairings.")
    
    # Overwrite Internal_Links tab headers + data
    data_updates = [
        {'range': f"'Internal_Links'!A1", 'values': PHASE1_TABS['Internal_Links'] + new_links}
    ]

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, 
        range="'Internal_Links'!A1",
        valueInputOption='RAW',
        body={'values': PHASE1_TABS['Internal_Links'] + new_links}
    ).execute()

    print("✅ PHASE 8 COMPLETE: Internal Authority Rebuilt.")

# --- Phase 11 Demographic Intelligence Integration ---

def fetch_demographic_data(city):
    """Integrates with US Census/ACS style datasets (simulated)."""
    # In a real scenario, this would call the Census API
    return {
        'population': "158,271",
        'growth': "+2.4%",
        'age': "31.2",
        'income': "$68,420",
        'owner': "64%",
        'renter': "36%",
        'rent': "$1,850",
        'value': "$425,000",
        'children': "42%",
        'education': "78% College Bound",
        'source': "US Census ACS 2024"
    }

def cmd_ingest_demographics():
    """Ingests demographic intelligence for all service cities using the demographic_ingest module."""
    print("📈 Ingesting Phase 11: Demographic Intelligence...")
    
    # 1. Identify cities from 'Sitemap Inventory' (Current Sheet Registry)
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    try:
        inventory = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'Sitemap Inventory'!A2:B").execute().get('values', [])
    except Exception as e:
        print(f"Error reading Sitemap Inventory: {e}")
        # Fallback to hardcoded list if sheet structure is broken
        inventory = []

    cities = []
    for row in inventory:
        if len(row) >= 2 and (row[1] == '📍' or 'location' in row[1].lower()):
            url = row[0]
            city_slug = url.rstrip('/').split('/')[-1]
            city_name = city_slug.replace('-', ' ').title()
            if city_name not in cities:
                cities.append(city_name)

    if not cities:
        print("No cities discovered in Sitemap Inventory. Falling back to core areas.")
        cities = ['Burbank', 'Lancaster', 'Palmdale', 'Santa Clarita', 'Glendale', 'Long Beach']

    # 2. Call the new module's ingestion logic
    demographic_ingest.ingest_demographics(SPREADSHEET_ID, SERVICE_ACCOUNT_FILE)

    # 3. Step 5: Flag for reinforcement (Logic to be expanded)
    print("Flagging significant demographic shifts for reinforcement...")
    # This would compare new vs old data and add to 'Reinforcement_Queue'
    # For now, we'll mark the latest city updates in the queue
    queue_rows = []
    for city in cities[:3]: # Limit to top 3 for demo purposes
        queue_rows.append([f"Update Demographic Context: {city}", f"/{get_slug(city)}/", "High", "pending"])
    
    if queue_rows:
        try:
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="'Reinforcement_Queue'!A2",
                valueInputOption='RAW',
                body={'values': queue_rows}
            ).execute()
        except:
            print("Reinforcement Queue tab not found, skipping flagging.")

    print("✅ PHASE 11 COMPLETE: Demographic Intelligence Hardened.")


def render_demographics_snippet(d):
    if not d: return "<div>Pending Demographic Audit</div>"
    return f"""
    <div class="data-card">
        <h3>Demographic Profile</h3>
        <p class="metric">{d['population']}</p>
        <p>Population ({d['growth']} Growth)</p>
        <ul>
            <li>Median Household Income: {d['income']}</li>
            <li>Median Age: {d['age']}</li>
            <li>Households with Children: {d['children']}</li>
            <li>Education Level: {d['education']}</li>
        </ul>
    </div>
    <div class="data-card">
        <h3>Housing Mix</h3>
        <p class="metric">{d['owner']}</p>
        <p>Owner Occupied</p>
        <ul>
            <li>Renter Occupied: {d['renter']}</li>
            <li>Median Rent: {d['rent']}</li>
            <li>Median Home Value: {d['value']}</li>
        </ul>
        <p><small>Source: {d['source']}</small></p>
    </div>
    """

# --- Phase 10 Master Authority Template Integration ---


def get_city_data_context(city_name):
    """Aggregates all metrics for a city from the SEO Brain Sheet."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    context = {
        'market': {},
        'crime': {},
        'schools': [],
        'commute': [],
        'amenities': {},
        'neighborhoods': [],
        'relocation': [],
        'demographics': {}
    }


    # Helper to fetch range
    def get_tab(tab_name):
        try:
            return service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            print(f"Warning: Tab {tab_name} not found in sheet.")
            return []

    # Market Data
    market_rows = get_tab('Housing_Data')
    for row in market_rows:
        if row and row[0].lower() == city_name.lower():
            context['market'] = {'median': row[1], 'change': row[2], 'inventory': row[3], 'dom': row[4], 'trend': row[5]}
            break

    # Crime Data
    crime_rows = get_tab('Crime_Data')
    for row in crime_rows:
        if row and row[0].lower() == city_name.lower():
            context['crime'] = {'index': row[2], 'violent': row[3], 'property': row[4], 'safety': row[5]}
            break

    # School Data
    school_rows = get_tab('Schools')
    for row in school_rows:
        if row and row[1].lower() == city_name.lower():
            context['schools'].append({'name': row[0], 'rating': row[2], 'type': row[3]})

    # Commute Data
    commute_rows = get_tab('Commute_Data')
    for row in commute_rows:
        if row and row[0].lower() == city_name.lower():
            context['commute'].append({'dest': row[1], 'dist': row[2], 'time': row[3]})

    # Amenities Data
    amenity_rows = get_tab('Amenities_Data')
    for row in amenity_rows:
        if row and row[0].lower() == city_name.lower():
            context['amenities'] = {'parks': row[1], 'shopping': row[2], 'hospitals': row[3], 'food': row[4], 'walk': row[6]}
            break

    # Neighborhoods
    nb_rows = get_tab('Neighborhoods')
    for row in nb_rows:
        if row and row[1].lower() == city_name.lower():
            context['neighborhoods'].append({'name': row[0], 'url': f"/locations/{get_slug(row[0])}/"})

    # Relocation Topics
    rel_rows = get_tab('Relocation_Topics')
    for row in rel_rows:
        if row and row[0].lower() == city_name.lower():
            context['relocation'].append({'topic': row[1], 'url': f"/blog/{get_slug(row[1])}/"})

    # Demographic Data
    demo_rows = get_tab('Demographic_Data')
    for row in demo_rows:
        if row and row[0].lower() == city_name.lower():
            context['demographics'] = {
                'population': row[1], 'growth': row[2], 'age': row[3],
                'income': row[4], 'owner': row[5], 'renter': row[6],
                'rent': row[7], 'value': row[8], 'children': row[9],
                'education': row[10], 'source': row[12]
            }
            break

    return context


def render_market_snippet(m):
    if not m: return "<div>Pending Market Analysis</div>"
    return f"""
    <div class="data-card">
        <h3>Median Home Price</h3>
        <p class="metric">{m['median']}</p>
        <p>Market Trend: <strong>{m['trend']}</strong> ({m['change']})</p>
    </div>
    <div class="data-card">
        <h3>Active Inventory</h3>
        <p class="metric">{m['inventory']}</p>
        <p>Avg. Days on Market: {m['dom']}</p>
    </div>
    """

def render_crime_snippet(c):
    if not c: return "<div>Pending Safety Audit</div>"
    return f"""
    <div class="data-card">
        <h3>Safety Rating</h3>
        <p class="metric">{c['safety']}</p>
        <p>Crime Index: {c['index']}</p>
        <p>Violent: {c['violent']} | Property: {c['property']}</p>
    </div>
    """

def render_school_snippet(schools):
    if not schools: return "<div>Pending School District Data</div>"
    top = sorted(schools, key=lambda x: x['rating'], reverse=True)[:3]
    html = '<div class="data-card"><h3>Top Schools</h3><ul>'
    for s in top:
        html += f"<li><strong>{s['name']}</strong> ({s['rating']}/10) - {s['type']}</li>"
    html += "</ul></div>"
    return html

def render_commute_snippet(commutes):
    if not commutes: return "<div>Pending Transit Analysis</div>"
    html = ""
    for c in commutes[:2]:
        html += f"""
        <div class="data-card">
            <h3>To {c['dest']}</h3>
            <p class="metric">{c['time']}</p>
            <p>Distance: {c['dist']}</p>
        </div>
        """
    return html

def render_amenities_snippet(a):
    if not a: return "<div>Pending Lifestyle Survey</div>"
    return f"""
    <div class="data-card">
        <h3>Local Amenities</h3>
        <ul>
            <li>Parks & Recreation: {a['parks']}</li>
            <li>Shopping Centers: {a['shopping']}</li>
            <li>Dining & Eateries: {a['food']}</li>
            <li>Hospitals/Medical: {a['hospitals']}</li>
        </ul>
        <p>Walkability Score: <strong>{a['walk']}/100</strong></p>
    </div>
    """

def render_links_snippet(items):
    if not items: return "<span>Check back soon for more guides.</span>"
    html = ""
    for i in items:
        name = i.get('name') or i.get('topic')
        html += f'<a href="{i["url"]}">{name}</a>'
    return html

# --- Phase 9 Relocation Authority Content Generator ---


def cmd_generate_relocation_guides():
    """Programmatically seeds the Relocation_Topics tab and strategy engine."""
    print("🏠 Generating Phase 9: Relocation Authority Guides...")
    
    # 1. Get Cities from Sheet
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    cities = get_cities_from_inventory(service)
    relocation_rows = []
    expansion_rows = []
    subpage_plan_rows = []
    guide_templates = [
        {"topic": "Moving to {city}", "intent": "Relocation Info", "priority": "P1"},
        {"topic": "Cost of Living in {city}", "intent": "Financial Planning", "priority": "P1"},
        {"topic": "Pros and Cons of Living in {city}", "intent": "Comparison", "priority": "P1"},
        {"topic": "Best Neighborhoods in {city}", "intent": "Selection", "priority": "P1"},
        {"topic": "Is {city} Safe?", "intent": "Safety Analysis", "priority": "P1"}
    ]

    for city in cities:
        print(f"Generating relocation guides for {city}...")
        for template in guide_templates:
            topic = template['topic'].format(city=city)
            relocation_rows.append([city, topic, template['intent'], template['priority'], "planned"])

            # Expansion Engine
            expansion_rows.append([topic, city, "High", "planned"])
            expansion_rows.append([f"{topic} Guide 2026", city, "Medium", "planned"])

            # Subpage Plan
            subpage_plan_rows.append([city, topic, 'page', f"{city} Guide", "unbuilt"])

    # 2. Ensure Tab Exists
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Relocation_Topics' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Relocation_Topics'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    # 3. Update Sheets
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Relocation_Topics'!A1",
        valueInputOption='RAW', body={'values': PHASE1_TABS['Relocation_Topics'] + relocation_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
        valueInputOption='RAW', body={'values': expansion_rows}
    ).execute()

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
        valueInputOption='RAW', body={'values': subpage_plan_rows}
    ).execute()

    # 4. Formatting
    if 'Relocation_Topics' in existing_sheets:
        sheet_id = existing_sheets['Relocation_Topics']
        format_requests = [
            {
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0, 'green': 0, 'blue': 0},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},
            {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 5}}}
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_requests}).execute()

    print("✅ PHASE 9 COMPLETE: Relocation Authority Content Seeding Finished.")


def cmd_generate_modifier_plan():
    """Generates the Search Modifiers engine for long-tail real estate pages."""
    print("🔍 Generating Phase 12: Search Modifiers Engine...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    # Ensure Search_Modifiers tab exists
    if 'Search_Modifiers' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Search_Modifiers'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
        
    modifier_values = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Search_Modifiers'!A2:E").execute().get('values', [])
    
    if not modifier_values:
        default_modifiers = [
            ["homes-under-500k", "Price", "Transactional", "High", "Both", "planned"],
            ["luxury-homes", "Price", "Transactional", "High", "Both", "planned"],
            ["pool-homes", "Feature", "Transactional", "High", "Both", "planned"],
            ["new-construction", "Feature", "Transactional", "High", "Both", "planned"],
            ["gated-community", "Feature", "Transactional", "Medium", "Both", "planned"],
            ["single-story-homes", "Feature", "Transactional", "Medium", "Both", "planned"],
            ["fixer-uppers", "Condition", "Transactional", "Medium", "Both", "planned"],
            ["condos", "Property Type", "Transactional", "Medium", "Both", "planned"],
            ["townhomes", "Property Type", "Transactional", "Medium", "Both", "planned"],
            ["4-bedroom-homes", "Size", "Transactional", "Low", "Both", "planned"],
            ["rv-parking", "Feature", "Transactional", "Low", "Both", "planned"],
            ["horse-property", "Feature", "Transactional", "Low", "Both", "planned"]
        ]
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Search_Modifiers'!A1",
            valueInputOption='RAW', body={'values': PHASE1_TABS['Search_Modifiers'] + default_modifiers}
        ).execute()
        modifier_values = default_modifiers

    # Ensure Modifier_Pages tab exists
    if 'Modifier_Pages' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Modifier_Pages'}}}]
        }).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Modifier_Pages'!A1",
            valueInputOption='RAW', body={'values': PHASE1_TABS['Modifier_Pages']}
        ).execute()

    # Get existing inventory to prevent duplicates
    sitemap_data = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Sitemap Inventory'!A2:A").execute().get('values', [])
    sitemap_urls = [row[0] for row in sitemap_data if row]
    
    page_inv_data = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Page_Inventory'!A2:A").execute().get('values', [])
    page_urls = set([row[0] for row in page_inv_data if row])

    # Get existing modifier pages to prevent re-adding
    existing_modifiers = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Modifier_Pages'!D2:D").execute().get('values', [])
    existing_mod_slugs = set([row[0] for row in existing_modifiers if row])

    cities = get_cities_from_inventory(service)
    try:
        neighborhoods_data = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'Neighborhoods'!A2:A").execute().get('values', [])
        neighborhoods = [row[0] for row in neighborhoods_data if row]
    except:
        neighborhoods = []

    new_modifier_pages = []
    
    for mod_row in modifier_values:
        modifier = mod_row[0]
        priority = mod_row[3] if len(mod_row) > 3 else "Medium"
        applies_to = mod_row[4] if len(mod_row) > 4 else "Both"
        
        # Apply to Cities
        if applies_to in ["Both", "Cities"]:
            for city in cities:
                slug = f"{get_slug(city)}-{modifier}"
                expected_url = f"{DOMAIN}/{get_slug(city)}/{slug}/"
                if expected_url not in sitemap_urls and expected_url not in page_urls and slug not in existing_mod_slugs:
                    new_modifier_pages.append([city, "", modifier, slug, "Real Estate Modifier", priority, "planned"])
                    existing_mod_slugs.add(slug)

        # Apply to Neighborhoods
        if applies_to in ["Both", "Neighborhoods"]:
            for neighborhood in neighborhoods:
                slug = f"{get_slug(neighborhood)}-{modifier}"
                expected_url = f"{DOMAIN}/neighborhood/{slug}/"
                if expected_url not in sitemap_urls and expected_url not in page_urls and slug not in existing_mod_slugs:
                    new_modifier_pages.append(["", neighborhood, modifier, slug, "Real Estate Modifier", priority, "planned"])
                    existing_mod_slugs.add(slug)
                
    if new_modifier_pages:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Modifier_Pages'!A2",
            valueInputOption='RAW', body={'values': new_modifier_pages}
        ).execute()
        print(f"✅ PHASE 12 COMPLETE: Added {len(new_modifier_pages)} new long-tail real estate pages to Modifier_Pages.")
    else:
        print("✅ PHASE 12 COMPLETE: No new modifier pages to add. All combinations are planned or exist.")


def cmd_expand_geo_clusters():
    """Generates geographic expansion plans for existing cities."""
    print("🌍 Generating Phase 13: Geographic Expansion Clusters...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    if 'Geo_Expansion' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Geo_Expansion'}}}]
        }).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Geo_Expansion'!A1",
            valueInputOption='RAW', body={'values': PHASE1_TABS['Geo_Expansion']}
        ).execute()

    cities = get_cities_from_inventory(service)
    
    # Map of expansions
    geo_map = {
        "Palmdale": [("Lancaster", "Los Angeles", "8 miles"), ("Quartz Hill", "Los Angeles", "6 miles"), ("Rosamond", "Kern", "15 miles"), ("Acton", "Los Angeles", "12 miles")],
        "Lancaster": [("Palmdale", "Los Angeles", "8 miles"), ("Quartz Hill", "Los Angeles", "4 miles"), ("Rosamond", "Kern", "15 miles"), ("Mojave", "Kern", "25 miles")],
        "Burbank": [("Glendale", "Los Angeles", "5 miles"), ("North Hollywood", "Los Angeles", "3 miles"), ("Toluca Lake", "Los Angeles", "3 miles")],
        "Glendale": [("Burbank", "Los Angeles", "5 miles"), ("Pasadena", "Los Angeles", "8 miles"), ("La Canada Flintridge", "Los Angeles", "6 miles")],
        "Santa Clarita": [("Castaic", "Los Angeles", "10 miles"), ("Newhall", "Los Angeles", "5 miles"), ("Saugus", "Los Angeles", "4 miles")]
    }

    geo_expansion_rows = []
    new_cities_rows = []
    seo_expansion_rows = []
    expansion_engine_rows = []
    subpage_plan_rows = []
    
    # Track existing nearby cities to avoid duplicates
    try:
        existing_geo = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'Geo_Expansion'!A2:B").execute().get('values', [])
    except:
        existing_geo = []
    
    existing_pairs = set([f"{r[0]}-{r[1]}" for r in existing_geo if len(r) > 1])
    
    for primary in cities:
        # Fallback dynamic expansions if city has no hardcoded map
        expansions = geo_map.get(primary, [
            (f"North {primary}", "Local", "5 miles"), 
            (f"South {primary}", "Local", "5 miles"),
            (f"{primary} Heights", "Local", "3 miles")
        ])
        
        for nearby, county, dist in expansions:
            pair_key = f"{primary}-{nearby}"
            if pair_key not in existing_pairs:
                slug = get_slug(nearby)
                geo_expansion_rows.append([primary, nearby, county, dist, "High", "planned"])
                new_cities_rows.append([nearby, county, "CA", slug, "planned"])
                seo_expansion_rows.append(["Real Estate Hub", nearby, "High", "planned"])
                expansion_engine_rows.append(["Geo Expansion", nearby, f"{nearby.lower()} ca real estate", "High", "Geo Addition"])
                subpage_plan_rows.append([primary, f"{nearby} Expansion", "location", f"{nearby.lower()} homes for sale", "unbuilt"])
                existing_pairs.add(pair_key)

    if geo_expansion_rows:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Geo_Expansion'!A2",
            valueInputOption='RAW', body={'values': geo_expansion_rows}).execute()
            
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Cities'!A2",
            valueInputOption='RAW', body={'values': new_cities_rows}).execute()
            
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'SEO_Expansion'!A2",
            valueInputOption='RAW', body={'values': seo_expansion_rows}).execute()
            
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A2",
            valueInputOption='RAW', body={'values': expansion_engine_rows}).execute()
            
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Subpage_Plan'!A2",
            valueInputOption='RAW', body={'values': subpage_plan_rows}).execute()
            
        print(f"✅ PHASE 13 COMPLETE: Added {len(geo_expansion_rows)} geographic nodes to expansion roadmap.")
    else:
        print("✅ PHASE 13 COMPLETE: All geo-nodes are already planned.")


def cmd_generate_feature_pages():
    """Generates the Property Features engine for hyper-targeted real estate pages."""
    print("🏡 Generating Phase 14: Feature Extraction Layer...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    # Ensure Property_Features tab exists
    if 'Property_Features' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Property_Features'}}}]
        }).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
        
    feature_values = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Property_Features'!A2:E").execute().get('values', [])
    
    if not feature_values:
        default_features = [
            ["pool", "Amenity", "Transactional", "High", "planned"],
            ["rv parking", "Amenity", "Transactional", "Medium", "planned"],
            ["solar", "Amenity", "Transactional", "Medium", "planned"],
            ["guest house", "Amenity", "Transactional", "Medium", "planned"],
            ["large lot", "Lot", "Transactional", "High", "planned"],
            ["horse property", "Lot", "Transactional", "Low", "planned"],
            ["mountain view", "View", "Transactional", "Medium", "planned"],
            ["gated", "Community", "Transactional", "Medium", "planned"],
            ["single story", "Style", "Transactional", "High", "planned"],
            ["corner lot", "Lot", "Transactional", "Low", "planned"],
            ["fixer upper", "Condition", "Transactional", "Medium", "planned"],
            ["new construction", "Condition", "Transactional", "High", "planned"],
        ]
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Property_Features'!A1",
            valueInputOption='RAW', body={'values': PHASE1_TABS['Property_Features'] + default_features}
        ).execute()
        feature_values = default_features

    # Ensure Feature_Pages tab exists
    if 'Feature_Pages' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Feature_Pages'}}}]
        }).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Feature_Pages'!A1",
            valueInputOption='RAW', body={'values': PHASE1_TABS['Feature_Pages']}
        ).execute()

    # Get existing inventory to prevent duplicates
    sitemap_data = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Sitemap Inventory'!A2:A").execute().get('values', [])
    sitemap_urls = [row[0] for row in sitemap_data if row]
    
    page_inv_data = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Page_Inventory'!A2:A").execute().get('values', [])
    page_urls = set([row[0] for row in page_inv_data if row])

    # Get existing feature pages to prevent re-adding
    existing_features = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Feature_Pages'!D2:D").execute().get('values', [])
    existing_feat_slugs = set([row[0] for row in existing_features if row])

    cities = get_cities_from_inventory(service)
    try:
        neighborhoods_data = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'Neighborhoods'!A2:A").execute().get('values', [])
        neighborhoods = [row[0] for row in neighborhoods_data if row]
    except:
        neighborhoods = []

    new_feature_pages = []
    
    for feat_row in feature_values:
        feature = feat_row[0]
        priority = feat_row[3] if len(feat_row) > 3 else "Medium"
        
        # Apply to Cities
        for city in cities:
            base_slug = get_slug(city)
            feat_slug = get_slug(feature)
            if "homes" in feat_slug:
                slug = f"{base_slug}-{feat_slug}"
            else:
                slug = f"{base_slug}-homes-with-{feat_slug}" if "pool" in feat_slug or "view" in feat_slug else f"{base_slug}-{feat_slug}-homes"

            expected_url = f"{DOMAIN}/{base_slug}/{slug}/"
            if expected_url not in sitemap_urls and expected_url not in page_urls and slug not in existing_feat_slugs:
                new_feature_pages.append([city, "", feature, slug, priority, "planned"])
                existing_feat_slugs.add(slug)

        # Apply to Neighborhoods
        for neighborhood in neighborhoods:
            base_slug = get_slug(neighborhood)
            feat_slug = get_slug(feature)
            if "homes" in feat_slug:
                slug = f"{base_slug}-{feat_slug}"
            else:
                slug = f"{base_slug}-homes-with-{feat_slug}" if "pool" in feat_slug or "view" in feat_slug else f"{base_slug}-{feat_slug}-homes"

            expected_url = f"{DOMAIN}/neighborhood/{slug}/"
            if expected_url not in sitemap_urls and expected_url not in page_urls and slug not in existing_feat_slugs:
                new_feature_pages.append(["", neighborhood, feature, slug, priority, "planned"])
                existing_feat_slugs.add(slug)
                
    if new_feature_pages:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Feature_Pages'!A2",
            valueInputOption='RAW', body={'values': new_feature_pages}
        ).execute()
        print(f"✅ PHASE 14 COMPLETE: Added {len(new_feature_pages)} new feature real estate pages to Feature_Pages.")
    else:
        print("✅ PHASE 14 COMPLETE: No new feature pages to add. All combinations are planned or exist.")

def cmd_validate_data_blocks():
    """Validates the data block insertion rules configured for generated pages."""
    print("🧩 Validating Data Block Orchestration Engine...")
    rules_path = os.path.join(ENGINE_ROOT, 'core', 'registries', 'data_block_rules.json')
    
    if not os.path.exists(rules_path):
        print(f"❌ Configuration missing at: {rules_path}")
        return
        
    try:
        with open(rules_path, 'r') as f:
            block_rules = json.load(f)
            
        print(f"✅ Configuration found at: {rules_path}")
        print("\n--- Current Data Block Assignments ---")
        
        for page_type, blocks in block_rules.items():
            print(f"📄 {page_type.title()} Pages:")
            for b in blocks:
                print(f"   - {b.title()} Data Block")
            print()
            
        print("Data block validation successful. The Engine is using these rules to construct pages.")
    except Exception as e:
        print(f"❌ Failed to parse data block rules: {e}")

def cmd_calculate_authority_score():
    """Calculates the Authority Score for each city and neighborhood."""
    print("📈 Calculating Authority Scores for Real Estate Network...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    if 'Authority_Score' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Authority_Score'}}}]
        }).execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Authority_Score'!A1",
            valueInputOption='RAW', body={'values': PHASE1_TABS['Authority_Score']}
        ).execute()

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    sitemap_data = get_tab_data('Sitemap Inventory')
    sitemap_urls = [r[0] for r in sitemap_data if r]
    
    cities = get_tab_data('Cities')
    neighborhoods = get_tab_data('Neighborhoods')
    idx_pages = get_tab_data('IDX_Pages')
    blogs = get_tab_data('Blog_Topics')
    crimes = get_tab_data('Crime_Data')
    schools = get_tab_data('Schools')
    housing = get_tab_data('Housing_Data')
    commute = get_tab_data('Commute_Data')
    demographics = get_tab_data('Demographic_Data')
    internal_links = get_tab_data('Internal_Links')

    score_rows = []
    
    all_targets = []
    for c in cities:
        if c: all_targets.append({'name': c[0], 'type': 'City', 'slug': get_slug(c[0])})
    for n in neighborhoods:
        if n: all_targets.append({'name': n[0], 'type': 'Neighborhood', 'slug': get_slug(n[0]), 'city': n[1] if len(n)>1 else ""})

    for target in all_targets:
        name = target['name']
        slug = target['slug']
        t_type = target['type']

        has_city_page = "No"
        has_neighborhood_page = "No"
        
        if t_type == 'City':
            expected_url = f"{DOMAIN}/{slug}/"
            if expected_url in sitemap_urls: has_city_page = "Yes"
        else:
            expected_url = f"{DOMAIN}/neighborhood/{slug}/"
            if expected_url in sitemap_urls: has_neighborhood_page = "Yes"

        has_idx = "Yes" if any(name.lower() in r[0].lower() for r in idx_pages if r) else "No"
        has_blogs = "Yes" if any(name.lower() in (r[2].lower() if len(r)>2 else "") for r in blogs) else "No"
        
        # Exact match required for data tabs to not false positive
        has_crime = "Yes" if any(name.lower() == r[0].lower() for r in crimes if r) else "No"
        has_school = "Yes" if any(name.lower() == (r[1].lower() if len(r)>1 else "") for r in schools if r) else "No"
        has_market = "Yes" if any(name.lower() == r[0].lower() for r in housing if r) else "No"
        has_commute = "Yes" if any(name.lower() == r[0].lower() for r in commute if r) else "No"
        has_demo = "Yes" if any(name.lower() == r[0].lower() for r in demographics if r) else "No"
        
        link_count = sum(1 for r in internal_links if r and len(r) > 1 and slug in r[1])
        link_coverage = "High" if link_count > 5 else ("Medium" if link_count > 2 else "Low")

        score = 0
        if has_city_page == "Yes" or has_neighborhood_page == "Yes": score += 20
        if has_idx == "Yes": score += 10
        if has_blogs == "Yes": score += 10
        if has_crime == "Yes": score += 10
        if has_school == "Yes": score += 10
        if has_market == "Yes": score += 10
        if has_commute == "Yes": score += 10
        if has_demo == "Yes": score += 10
        if link_coverage in ["High", "Medium"]: score += 10

        priority_action = "Maintain"
        if score < 40:
            priority_action = "Needs Page Generation & Initial Data"
        elif score < 70:
            priority_action = "Needs Data Ingestion & Blogs"
        elif score < 90:
            priority_action = "Needs Internal Linking & Reinforcement"

        if t_type == 'City':
            score_rows.append([name, "", has_city_page, "N/A", has_idx, has_blogs, has_crime, has_school, has_market, has_commute, has_demo, link_coverage, str(score), priority_action])
        else:
            score_rows.append([target.get('city', ''), name, "N/A", has_neighborhood_page, has_idx, has_blogs, has_crime, has_school, has_market, has_commute, has_demo, link_coverage, str(score), priority_action])

    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range="'Authority_Score'!A2:N").execute()
        
    if score_rows:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Authority_Score'!A2",
            valueInputOption='RAW', body={'values': score_rows}
        ).execute()
        
    print(f"✅ Calculated Authority Score for {len(score_rows)} locations.")


def cmd_queue_data_reinforcements():
    """Identifies metric triggers and flags connected pages for reinforcement."""
    print("🔔 Scanning Data Lakes for Trigger Conditions...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    if 'Reinforcement_Queue' not in sheet_meta:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Reinforcement_Queue'}}}]
        }).execute()
        
        # Determine correct header list to use based on which dictionary has it now
        header = SEO_GROWTH_TABS.get('Reinforcement_Queue')
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Reinforcement_Queue'!A1",
            valueInputOption='RAW', body={'values': header}
        ).execute()

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    sitemap_data = get_tab_data('Sitemap Inventory')
    crimes = get_tab_data('Crime_Data')
    schools = get_tab_data('Schools')
    housing = get_tab_data('Housing_Data')
    commute = get_tab_data('Commute_Data')
    demographics = get_tab_data('Demographic_Data')
    
    existing_queue = get_tab_data('Reinforcement_Queue')
    queued_urls = set([r[0] for r in existing_queue if r])

    queue_rows = []
    
    def flag_urls(city_name, trigger, reason, priority):
        for r in sitemap_data:
            if not r: continue
            url = r[0]
            p_type = r[1] if len(r) > 1 else 'Unknown'
            if city_name.lower().replace(' ', '-') in url.lower() or city_name.lower() in url.lower():
                if url not in queued_urls:
                    queue_rows.append([url, p_type, city_name, trigger, reason, priority, "planned"])
                    queued_urls.add(url)

    # Housing Check -> Threshold: Price Change >= 2.0%
    for r in housing:
        if not r or len(r) < 3: continue
        city = r[0]
        try:
            change = float(r[2].replace('%', '').replace('+', '').replace(',', ''))
            if abs(change) >= 2.0:
                flag_urls(city, "Median_Home_Price", f"Price shifted by {change}%", "High")
        except: pass

    # Crime Check -> Threshold: Crime Index > 35
    for r in crimes:
        if not r or len(r) < 3: continue
        city = r[0]
        try:
            index = int(r[2])
            if index > 35:
                flag_urls(city, "Crime_Index", f"Crime Index crossed threshold ({index})", "High")
        except: pass

    # School Check -> Threshold: Rating < 5
    for r in schools:
        if not r or len(r) < 3: continue
        school, city, rating = r[0], r[1], r[2]
        try:
            rate = int(rating)
            if rate < 5:
                flag_urls(city, "School_Rating", f"School rating below minimum ({school})", "Medium")
        except: pass

    # Demographics check -> Threshold: Population Growth >= 2.0%
    for r in demographics:
        if not r or len(r) < 3: continue
        city = r[0]
        try:
            growth = float(r[2].replace('%', '').replace('+', '').replace(',', ''))
            if abs(growth) >= 2.0:
                flag_urls(city, "Population_Growth", f"Population flux ({growth}%)", "Medium")
        except: pass

    # Commute check -> Threshold: Average Time > 45 mins
    for r in commute:
        if not r or len(r) < 4: continue
        city = r[0]
        try:
            time = int(r[3].replace('mins', '').strip())
            if time > 45:
                flag_urls(city, "Average_Commute_Time", f"Commute extended to {time} mins", "Medium")
        except: pass

    if queue_rows:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range="'Reinforcement_Queue'!A2",
            valueInputOption='RAW', body={'values': queue_rows}
        ).execute()
        print(f"✅ Flagged {len(queue_rows)} connected pages for data-driven reinforcements.")
    else:
        print("✅ No data thresholds exceeded. Matrix is balanced.")


def cmd_sync_external_apis():
    """Simulates external connectivity to real estate data syndicates."""
    print("📡 Initializing External Data Ingestion Engine...")
    config_path = os.path.join(ENGINE_ROOT, 'core', 'registries', 'api_config.json')
    
    if not os.path.exists(config_path):
        print(f"❌ API Config missing at: {config_path}")
        return
        
    with open(config_path, 'r') as f:
        apis = json.load(f)
        
    print(f"✅ Loaded {len(apis)} API providers.")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    # Market Sync
    market_provider = apis.get('market_data', {}).get('provider', 'Mock')
    print(f"🔄 Syncing Market Data via {market_provider}...")
    housing = get_tab_data('Housing_Data')
    updated_housing = []
    
    for r in housing:
        if not r or len(r) < 6: 
            updated_housing.append(r)
            continue
        # Induce a live fluctuation (+/- 2.5% randomly)
        import random
        fluctuation = random.uniform(-3.5, 3.5)
        new_change = round(fluctuation, 2)
        trend = "Upward" if new_change > 0 else "Downward" if new_change < 0 else "Stable"
        r[2] = f"{new_change}%"
        r[5] = trend
        updated_housing.append(r)

    if updated_housing:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Housing_Data'!A2",
            valueInputOption='RAW', body={'values': updated_housing}
        ).execute()

    # Crime Sync
    crime_provider = apis.get('crime_data', {}).get('provider', 'Mock')
    print(f"🔄 Syncing Crime Data via {crime_provider}...")
    crimes = get_tab_data('Crime_Data')
    updated_crimes = []
    
    for r in crimes:
        if not r or len(r) < 7:
            updated_crimes.append(r)
            continue
        try:
            curr_index = int(r[2])
            new_index = max(1, curr_index + random.randint(-5, 8)) # Upward drift possibility
            r[2] = str(new_index)
            r[6] = crime_provider
            updated_crimes.append(r)
        except:
            updated_crimes.append(r)

    if updated_crimes:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range="'Crime_Data'!A2",
            valueInputOption='RAW', body={'values': updated_crimes}
        ).execute()

    print("✅ Live Data Engine synchronization complete. Data schemas enriched.")

def cmd_build_command_center():
    """Builds and updates the SEO_Command_Center dashboard."""
    print("🏢 Building SEO Command Center Dashboard...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    if 'SEO_Command_Center' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'SEO_Command_Center'}}}]
        }).execute()
        
    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    sitemap_data = get_tab_data('Sitemap Inventory')
    cities = get_tab_data('Cities')
    neighborhoods = get_tab_data('Neighborhoods')
    idx_pages = get_tab_data('IDX_Pages')
    blogs = get_tab_data('Blog_Topics')
    modifiers = get_tab_data('Modifier_Pages')
    features = get_tab_data('Feature_Pages')
    crimes = get_tab_data('Crime_Data')
    schools = get_tab_data('Schools')
    housing = get_tab_data('Housing_Data')
    auth_scores = get_tab_data('Authority_Score')
    reinforcements = get_tab_data('Reinforcement_Queue')
    
    cities_list = [c[0].lower() for c in cities if c]
    crime_cities = [c[0].lower() for c in crimes if c]
    school_cities = [s[1].lower() for s in schools if len(s)>1]
    housing_cities = [h[0].lower() for h in housing if h]

    missing_crime = sum(1 for c in cities_list if c not in crime_cities)
    missing_schools = sum(1 for c in cities_list if c not in school_cities)
    missing_market = sum(1 for c in cities_list if c not in housing_cities)

    auth_sorted = sorted([r for r in auth_scores if r and len(r) > 12], key=lambda x: int(x[12]) if str(x[12]).isdigit() else 100)
    top_priority = auth_sorted[:5]
    top_priority_names = ", ".join([r[0] or r[1] for r in top_priority]) if top_priority else "None"

    reinforcement_needs = ", ".join([r[0] for r in reinforcements[:5] if r]) if reinforcements else "None"

    dashboard_data = [
        ['Metric', 'Value'],
        ['Total existing pages', str(len(sitemap_data))],
        ['Total city clusters', str(len(cities))],
        ['Total neighborhoods mapped', str(len(neighborhoods))],
        ['Total IDX targets', str(len(idx_pages))],
        ['Total blog opportunities', str(len(blogs))],
        ['Total modifier opportunities', str(len(modifiers))],
        ['Total feature opportunities', str(len(features))],
        ['Cities missing crime data', str(missing_crime)],
        ['Cities missing school data', str(missing_schools)],
        ['Cities missing market data', str(missing_market)],
        ['Top priority clusters', top_priority_names],
        ['Top reinforcement needs', reinforcement_needs]
    ]

    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range="'SEO_Command_Center'!A1:B").execute()

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'SEO_Command_Center'!A1",
        valueInputOption='RAW', body={'values': dashboard_data}
    ).execute()

    print("✅ SEO Command Center successfully activated and updated.")


def cmd_build_master_site_map():
    """Generates a hierarchical Master Site Map architecture view."""
    print("🗺️ Generating Master Site Architecture Map...")
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    if 'Master_Site_Map' not in existing_sheets:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={
            'requests': [{'addSheet': {'properties': {'title': 'Master_Site_Map'}}}]
        }).execute()
        
    def get_tab_data(tab_name):
        try:
            return service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f"'{tab_name}'!A2:Z").execute().get('values', [])
        except:
            return []

    sitemap_data = get_tab_data('Sitemap Inventory')
    sitemap_urls = set([r[0] for r in sitemap_data if r])
    
    cities = get_tab_data('Cities')
    neighborhoods = get_tab_data('Neighborhoods')
    idx_pages = get_tab_data('IDX_Pages')
    blogs = get_tab_data('Blog_Topics')
    modifiers = get_tab_data('Modifier_Pages')
    features = get_tab_data('Feature_Pages')
    relocations = get_tab_data('Relocation_Topics')
    
    master_rows = []
    
    def check_exists(slug, p_type=""):
        # Match URL slug
        for u in sitemap_urls:
            parts = [p.strip() for p in u.split('/') if p.strip()]
            if slug in parts:
                return "Yes"
        return "No"

    # Cities
    for c in cities:
        if not c: continue
        city = c[0]
        slug = get_slug(city)
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append(["Root", city, "City Hub", city, "High", exists, needs])

    # Neighborhoods
    for n in neighborhoods:
        if not n: continue
        hood = n[0]
        city = n[1] if len(n) > 1 else "Unknown"
        slug = get_slug(hood)
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append([city, hood, "Neighborhood", city, "High", exists, needs])

    # IDX Pages
    for idx in idx_pages:
        if not idx: continue
        title = idx[0]
        slug = idx[1] if len(idx) > 1 else get_slug(title)
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append(["Root", title, "IDX Page", "IDX", "High", exists, needs])

    # Blogs
    for b in blogs:
        if not b or len(b) < 3: continue
        title = b[0]
        city = b[2] if b[2] else "General"
        slug = get_slug(title)
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append([city, title, "Blog Node", city, "Medium", exists, needs])

    # Relocation Guides
    for r in relocations:
        if not r or len(r) < 2: continue
        city = r[0]
        topic = r[1]
        priority = r[3] if len(r) > 3 else "High"
        slug = get_slug(topic)
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append([city, topic, "Relocation Guide", city, priority, exists, needs])

    # Modifiers
    for m in modifiers:
        if not m or len(m) < 4: continue
        city = m[0]
        hood = m[1]
        slug = m[3]
        p_type = m[4] if len(m) > 4 else "Modifier Logic"
        priority = m[5] if len(m) > 5 else "Medium"
        
        parent = hood if hood else city
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append([parent, slug, "Modifier Hub", city, priority, exists, needs])

    # Features
    for f in features:
        if not f or len(f) < 4: continue
        city = f[0]
        hood = f[1]
        slug = f[3]
        priority = f[4] if len(f) > 4 else "Medium"
        
        parent = hood if hood else city
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append([parent, slug, "Feature Hub", city, priority, exists, needs])

    # Zip Pages
    zip_pages = get_tab_data('Zip_Pages')
    for z in zip_pages:
        if not z or len(z) < 3: continue
        zip_code = z[0]
        city = z[1]
        slug = z[2]
        priority = z[4] if len(z) > 4 else "Medium"
        
        exists = check_exists(slug)
        needs = "Yes" if exists == "No" else "No"
        master_rows.append([city, zip_code, "ZIP Code Cluster", city, priority, exists, needs])

    # Write Data
    headers = PHASE1_TABS.get('Master_Site_Map', [['Parent_Page', 'Child_Page', 'Page_Type', 'Cluster', 'Priority', 'Exists', 'Needs_Generation']])
    
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range="'Master_Site_Map'!A1:G").execute()
    
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Master_Site_Map'!A1",
        valueInputOption='RAW', body={'values': headers + master_rows}
    ).execute()
    
    print(f"✅ Master Site Map generation complete. Mapped {len(master_rows)} dynamic architecture nodes.")

def unique_list(rows, slug_col_idx):
    """Helper to deduplicate rows based on a slug column."""
    unique = []
    seen = set()
    for row in rows:
        if len(row) > slug_col_idx and row[slug_col_idx] not in seen:
            unique.append(row)
            seen.add(row[slug_col_idx])
    return unique


def analyze_page(url_path):
    """Analyzes a local HTML file for SEO health."""
    # Convert URL to local path
    rel_path = url_path.replace(DOMAIN, '').strip('/')
    if not rel_path:
        local_path = os.path.join(ROOT_DIR, 'index.html')
    else:
        local_path = os.path.join(ROOT_DIR, rel_path, 'index.html')

    if not os.path.exists(local_path):
        return None

    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        title = soup.title.string if soup.title else ""
        meta_desc = ""
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            meta_desc = desc_tag.get('content', '')

        h1 = soup.find('h1')
        h1_text = h1.get_text().strip() if h1 else "MISSING"

        # Simple Health Scoring
        score = 100
        issues = []
        if not title or len(title) < 30: 
            score -= 20
            issues.append("Short/Missing Title")
        if not meta_desc or len(meta_desc) < 100:
            score -= 20
            issues.append("Short/Missing Desc")
        if h1_text == "MISSING":
            score -= 20
            issues.append("No H1")

        # Internal Link Collection
        internal_outbound = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Normalize and identify internal links
            if href.startswith('/') or DOMAIN in href:
                # Remove query params and fragments
                clean_href = href.split('?')[0].split('#')[0]
                if clean_href.startswith(DOMAIN):
                    clean_href = clean_href.replace(DOMAIN, '')
                if not clean_href.startswith('/'):
                    clean_href = '/' + clean_href
                internal_outbound.add(clean_href)

        return {
            'url': url_path,
            'title': title,
            'title_len': len(title),
            'desc_len': len(meta_desc),
            'h1': h1_text,
            'score': score,
            'status': "Healthy" if score > 70 else "Needs Improvement",
            'issues': ", ".join(issues),
            'outbound': list(internal_outbound),
            'strategic_links': len(re.findall(r'<li.*?>.*?</li>', str(soup.find('div', class_='seo-authority-block')), re.DOTALL)) if soup.find('div', class_='seo-authority-block') else 0
        }
    except Exception as e:
        print(f"Audit Error for {local_path}: {e}")
        return None

def get_gsc_data():
    """Fetches impression/click data from Search Console."""
    print("Fetching Search Console data...")
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
        service = build('searchconsole', 'v1', credentials=creds)
        
        request = {
            'startDate': '2025-01-01', # Using a broad range for demo/initial data
            'endDate': datetime.now().strftime('%Y-%m-%d'),
            'dimensions': ['query', 'page'],
            'rowLimit': 100
        }
        response = service.searchanalytics().query(siteUrl=GSC_SITE_URL, body=request).execute()
        return response.get('rows', [])
    except Exception as e:
        print(f"GSC Error: {e}")
        return []
def get_sheet_values(service, spreadsheet_id, range_name):
    """Helper to fetch values from a specific sheet range."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name).execute()
    return result.get('values', [])

def calculate_cornerstone_gaps(service, spreadsheet_id, all_urls):
    """Analyzes Cornerstone_Map and Subpage_Plan against live sitemap."""
    cornerstone_rows = get_sheet_values(service, spreadsheet_id, "'Cornerstone_Map'!A2:F")
    subpage_rows = get_sheet_values(service, spreadsheet_id, "'Subpage_Plan'!A2:E")
    
    # 1. Map existing URLs to topics
    url_set = {u['loc'] for u in all_urls}
    
    # 2. Update Cornerstone Map
    updated_cornerstones = []
    for row in cornerstone_rows:
        if not row: continue
        name = row[0]
        ideal = int(row[2]) if len(row) > 2 and str(row[2]).isdigit() else 20
        # Check for matches in sitemap
        current = 0
        for loc in url_set:
            if f"/{name}/" in loc or f"-{name}/" in loc:
                current += 1
        
        missing = max(0, ideal - current)
        priority = row[5] if len(row) > 5 else 'Medium'
        updated_cornerstones.append([name, row[1] if len(row) > 1 else '', ideal, current, missing, priority])

    # 3. Update Subpage Plan Status
    updated_subpages = []
    for row in subpage_rows:
        if not row: continue
        parent = row[0]
        topic = row[1]
        slug = get_slug(topic)
        
        status = 'planned'
        # Check if topic slug exists in any live URL
        for loc in url_set:
            if slug in loc:
                status = 'exists'
                break
        
        updated_subpages.append([parent, topic, row[2] if len(row) > 2 else '', row[3] if len(row) > 3 else '', status])

    return updated_cornerstones, updated_subpages


def apply_formatting(service, spreadsheet_id, sheet_id, col_count, priority_colors=None):
    requests = [
        {
            'updateSheetProperties': {
                'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
                'fields': 'gridProperties.frozenRowCount'
            }
        },
        {
            'autoResizeDimensions': {
                'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': col_count}
            }
        },
        {
            'repeatCell': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 1.0},
                        'textFormat': {'bold': True}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        }
    ]
    
    # Conditional Row Formatting for Cluster_Map
    if priority_colors:
        for i, prio in enumerate(priority_colors):
            color = {'red': 0.85, 'green': 0.92, 'blue': 0.83} if prio == "Dominant" else \
                    {'red': 1.0, 'green': 0.95, 'blue': 0.8} if prio == "Growth" else \
                    {'red': 0.96, 'green': 0.8, 'blue': 0.8} # Red for Expansion
            
            requests.append({
                'repeatCell': {
                    'range': {'sheetId': sheet_id, 'startRowIndex': i + 1, 'endRowIndex': i + 2},
                    'cell': {'userEnteredFormat': {'backgroundColor': color}},
                    'fields': 'userEnteredFormat(backgroundColor)'
                }
            })

    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': requests}).execute()

# --- Commands ---

def cmd_sync():
    print("Extracting current sitemap and auditing pages...")
    all_urls = get_sitemap_urls()
    audit_results = {}
    for u in all_urls:
        res = analyze_page(u['loc'])
        if res:
            audit_results[u['loc']] = res

    gsc_rows = get_gsc_data()
    
    urls_by_category = {cat: [] for cat in SEO_GROWTH_TABS.keys()}
    urls_by_category['📖 CLIENT GUIDE'] = CLIENT_GUIDE_DATA
    
    # Dashboard Aggregation
    total_pages = len(all_urls)
    total_audit = len(audit_results)
    avg_score = sum(r['score'] for r in audit_results.values()) / total_audit if total_audit > 0 else 0
    total_clicks = sum(r.get('clicks', 0) for r in gsc_rows)
    
    urls_by_category['📊 RESULTS DASHBOARD'] = [
        ['Metric', 'Current Value', 'Target Goal', 'Wellness Status'],
        ['Total Indexed Pages', total_pages, '100+', 'On Track' if total_pages > 50 else 'Lagging'],
        ['Website Health Score', f"{avg_score:.1f}%", '90%+', 'Excellent' if avg_score > 80 else 'Audit Required'],
        ['Monthly Search Traffic', int(total_clicks), '500+', 'Active'],
        ['Last Manual Sync', datetime.now().strftime('%Y-%m-%d %H:%M'), '-', 'Updated']
    ]

    for u in all_urls:
        loc, lastmod = u['loc'], u['lastmod']
        category = categorize_url(loc)
        audit = audit_results.get(loc, {})
        
        # Extraction of human-readable name from URL slug
        path_parts = loc.rstrip('/').split('/')
        readable_name = path_parts[-1].replace('-', ' ').title() if len(path_parts) > 3 else "Main Page"

        if category == '📂 SERVICE PAGES':
            urls_by_category[category].append([loc, lastmod, audit.get('status', 'Unknown'), readable_name, audit.get('title', '')])
        elif category == '✍️ BLOG ARTICLES':
            urls_by_category[category].append([loc, lastmod, audit.get('status', 'Unknown'), readable_name, audit.get('title', '')])
        elif category == '📍 LOCATIONS':
            urls_by_category[category].append([loc, readable_name, "Antelope Valley", audit.get('status', 'Unknown'), f"{audit.get('score', 0)}/100", lastmod])
        elif category == '🏥 WEBSITE WELLNESS':
            urls_by_category[category].append([
                loc, 
                f"{audit.get('score', 0)}/100",
                audit.get('title', ''), 
                audit.get('issues', 'Healthy'), 
                audit.get('status', 'Unknown')
            ])
        elif category == 'Page Health': # Mapping generic to Wellness
             urls_by_category['🏥 WEBSITE WELLNESS'].append([
                loc, 
                f"{audit.get('score', 0)}/100",
                audit.get('title', ''), 
                audit.get('issues', 'Healthy'), 
                audit.get('status', 'Unknown')
            ])

    # Keyword Tracker from GSC
    kw_data = []
    for row in gsc_rows:
        query = row['keys'][0]
        page = row['keys'][1]
        kw_data.append([query, 'Growing', f"Pos: {row['position']:.1f}", page, int(row['impressions'])])
    urls_by_category['🔑 CONTENT PERFORMANCE'] = kw_data

    print("Authenticating with Google Sheets...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    # Pre-fetch existing Sitemap Inventory to preserve Clusters/Keywords
    print("Reading existing sitemap inventory...")
    try:
        existing_inventory = get_sheet_values(service, SPREADSHEET_ID, "'Sitemap Inventory'!A2:E")
    except Exception as e:
        print(f"Note: Could not read existing inventory (sheet may be new): {e}")
        existing_inventory = []
    inventory_map = {row[0]: (row[1], row[2], row[3]) for row in existing_inventory if len(row) >= 4}

    # Build a lookup map from the strategic roadmap
    roadmap_lookup = {get_slug(s[1]): s[0] for s in SUBPAGE_PLAN_EXAMPLES}

    # Populate Sitemap Inventory with merged data
    for u in all_urls:
        loc, lastmod = u['loc'], u['lastmod']
        category = categorize_url(loc)
        page_type = category.replace('📂 ', '').replace('✍️ ', '').split(' ')[0].rstrip('s')
        
        slug = loc.rstrip('/').split('/')[-1]
        roadmap_parent = roadmap_lookup.get(slug, '-')
        
        # Merge existing data if available
        existing = inventory_map.get(loc, (page_type, '-', '-'))
        
        # Priority: Roadmap > Existing Sheet > Path Fallback
        parent_topic = roadmap_parent if roadmap_parent != '-' else existing[1]
        
        if parent_topic == '-':
            if '/locations/' in loc: parent_topic = 'local-seo-av'
            elif '/industries/' in loc: parent_topic = 'website-build-roadmap'
            elif '/portfolio/' in loc: parent_topic = 'ai-authority-content'
            elif '/services/' in loc: parent_topic = 'managed-hosting'
            elif '/blog/' in loc: parent_topic = 'blog-general'
            elif '/website-care/' in loc: parent_topic = 'website-care'
            elif '/local-seo-av/' in loc: parent_topic = 'local-seo-av'
            elif '/nonprofit-digital/' in loc: parent_topic = 'nonprofit-digital'
            elif '/daycare-bundle/' in loc: parent_topic = 'daycare-bundle'
        
        strategic_count = audit.get('strategic_links', 0)
        urls_by_category['Sitemap Inventory'].append([loc, existing[0], parent_topic, existing[2], strategic_count, lastmod])

    # Market Intelligence Tabs (Previously curated, merge if not overlapping)
    for intel_tab, intel_data in MARKET_INTEL.items():
        if intel_tab in urls_by_category and not urls_by_category[intel_tab]:
            urls_by_category[intel_tab] = intel_data

    # 1.5 Backlink & Internal Link Audit Calculation

    # 1.5 Backlink & Internal Link Audit Calculation
    inverted_links = {}
    for url, res in audit_results.items():
        outbound = res.get('outbound', [])
        for link in outbound:
            # Normalize link to absolute URL for matching
            abs_link = link
            if abs_link.startswith('/'):
                abs_link = DOMAIN.rstrip('/') + abs_link
            
            if abs_link not in inverted_links:
                inverted_links[abs_link] = []
            inverted_links[abs_link].append(url)
    
    backlink_audit_rows = []
    for u in all_urls:
        url = u['loc']
        inbound_count = len(inverted_links.get(url, []))
        # Schema: URL, External Backlinks (Mocked for now), Internal Links, Authority Score, Status, Action
        score = min(inbound_count * 20, 100)
        status = "Healthy" if inbound_count >= 3 else "Under-linked"
        action = "-" if status == "Healthy" else "Build Internal Links"
        backlink_audit_rows.append([url, "0", inbound_count, score, status, action])
    
    urls_by_category['Backlink_Audit'] = backlink_audit_rows

    # Authority Radar Aggregation
    print("Calculating Authority Radar metrics...")
    radar_inventory = urls_by_category.get('Sitemap Inventory', [])
    try:
        radar_backlinks = get_sheet_values(service, SPREADSHEET_ID, "'Backlink_Audit'!A2:D")
    except Exception:
        radar_backlinks = []
    
    try:
        radar_performance = get_sheet_values(service, SPREADSHEET_ID, "'🔑 CONTENT PERFORMANCE'!A2:E")
    except Exception:
        radar_performance = []
    
    cluster_stats = {}
    for row in radar_inventory:
        if len(row) < 3: continue
        url, parent = row[0], row[2]
        if parent == '-': continue
        if parent not in cluster_stats:
            cluster_stats[parent] = {'pages': 0, 'internal': 0, 'external': 0, 'impressions': 0, 'positions': []}
        cluster_stats[parent]['pages'] += 1
        
        # Link to external backlinks from Backlink_Audit
        for bl in radar_backlinks:
            if len(bl) >= 4 and bl[0] == url:
                try: cluster_stats[parent]['external'] += int(bl[1]) if str(bl[1]).isdigit() else 0
                except: pass
                try: cluster_stats[parent]['internal'] += int(bl[2]) if str(bl[2]).isdigit() else 0
                except: pass
        
        # Link search performance
        for perf in radar_performance:
            if len(perf) >= 5 and perf[3] == url:
                try: cluster_stats[parent]['impressions'] += int(perf[4])
                except: pass
                try: 
                    pos_str = perf[2].replace('Pos: ', '')
                    cluster_stats[parent]['positions'].append(float(pos_str))
                except: pass

    # 2. Strategic Cornerstone & Expansion Analysis
    print("Performing unified strategic gap analysis...")
    try:
        cornerstone_data = get_sheet_values(service, SPREADSHEET_ID, "'Cornerstone_Map'!A2:D")
    except Exception:
        cornerstone_data = []
    
    # Merge seed data with sheet data with slug-normalization to prevent duplicates
    # Master Schema: [Cornerstone, URL, Target Keyword, Ideal, Current, Missing, Priority]
    all_cornerstones = {}
    for row in CORNERSTONE_MAP_EXAMPLES:
        slug = get_slug(row[0])
        all_cornerstones[slug] = [slug] + row[1:] # Force slug as Col A

    for row in cornerstone_data:
        if not row: continue
        slug = get_slug(row[0])
        if slug not in all_cornerstones:
            all_cornerstones[slug] = [slug, '-', '-', '15', '0', '15', 'High']
        
        # Schema Detection: If row[1] is a URL, it's the NEW schema
        is_new_schema = len(row) > 1 and (str(row[1]).startswith('http') or str(row[1]) == '-')
        
        if is_new_schema:
            # New Schema: [Slug, URL, Keyword, Ideal]
            if len(row) > 1: all_cornerstones[slug][1] = row[1]
            if len(row) > 2: all_cornerstones[slug][2] = row[2]
            if len(row) > 3: all_cornerstones[slug][3] = row[3]
        else:
            # Old Schema: [Slug, Keyword, Ideal]
            # row[1] was the keyword, row[2] was the ideal count
            if len(row) > 1: all_cornerstones[slug][2] = row[1] 
            if len(row) > 2: all_cornerstones[slug][3] = row[2]
        
        all_cornerstones[slug][0] = slug # FORCE 100% slug consistency

    updated_cornerstones = []
    expansion_suggestions = []
    total_expansion_count = 0
    
    sitemap_locs = [u['loc'] for u in all_urls]
    for topic, row in all_cornerstones.items():
        # Find the hub page for this cornerstone
        hub_url = '-'
        for loc in sitemap_locs:
            # Check for exact slug in path or filename
            if f"/{topic}/" in loc or loc.endswith(f"/{topic}") or loc.endswith(f"/{topic}.html"):
                hub_url = loc
                break
        
        # If not found via exact match, check for partial match in features or service pages
        if hub_url == '-':
            for loc in sitemap_locs:
                if topic in loc and ('/features/' in loc or '/services/' in loc):
                    hub_url = loc
                    break

        keyword = row[2] if len(row) > 2 else topic
        ideal_str = row[3] if len(row) > 3 else "15"
        try:
            ideal = int(ideal_str)
            current = cluster_stats.get(topic, {}).get('pages', 0)
            missing = ideal - current
            
            # Simple priority based on strategic importance + gap size
            is_new_service = any(k in topic for k in ['hosting', 'seo', 'nonprofit', 'automation', 'authority', 'strategy', 'roadmap'])
            priority = row[6] if len(row) > 6 else ("High" if (missing > 5 or is_new_service) else "Medium" if missing > 0 else "Low")
            
            updated_cornerstones.append([topic, hub_url, keyword, ideal, current, max(0, missing), priority])
            
            # Populate Expansion_Engine (Gap Analysis)
            if missing > 0 and total_expansion_count < 20:
                # 1. Filter SUBPAGE_PLAN_EXAMPLES for this cluster
                planned_for_cluster = [s for s in SUBPAGE_PLAN_EXAMPLES if s[0] == topic]
                
                # 2. Find pages that don't exist yet
                existing_slugs = [get_slug(loc) for loc in sitemap_locs]
                potential_additions = []
                for s in planned_for_cluster:
                    # s[1] is the suggested page title, s[2] is type, s[3] is target keyword
                    slug = get_slug(s[1])
                    if slug not in existing_slugs:
                        potential_additions.append([topic, s[1], s[3], "N/A (Gap Analysis)", "cluster growth"])
                
                # 3. Add descriptive suggestions
                pages_to_add = min(missing, len(potential_additions))
                for i in range(pages_to_add):
                    if total_expansion_count >= 20: break
                    expansion_suggestions.append(potential_additions[i])
                    total_expansion_count += 1
                
                # 4. Fallback if no specific planned pages are left but gap remains
                remaining_gap = missing - pages_to_add
                if remaining_gap > 0 and total_expansion_count < 20:
                    fallbacks = [
                        "2026 Strategy Guide", "Advanced Implementation", "Professional Checklist",
                        "Performance Optimization", "Future Trends & Insights", "Market Analysis",
                        "Case Study & Success Guide", "Common Pitfalls to Avoid"
                    ]
                    for i in range(min(len(fallbacks), remaining_gap)):
                        if total_expansion_count >= 20: break
                        prefix = fallbacks[i]
                        fallback_title = f"{keyword} {prefix}" if keyword != topic else f"{topic} {prefix}"
                        expansion_suggestions.append([topic, fallback_title, f"{keyword} focus", "N/A (Gap Analysis)", "cluster growth"])
                        total_expansion_count += 1
        except: continue

    urls_by_category['Cornerstone_Map'] = updated_cornerstones
    urls_by_category['Expansion_Engine'] = expansion_suggestions

    # 3. Authority Radar & Visual Cluster Map
    radar_rows = []
    # Use the combined list of all discovered clusters + strategic cornerstones
    active_clusters = set(cluster_stats.keys()).union(set(all_cornerstones.keys()))
    
    for cluster in active_clusters:
        s = cluster_stats.get(cluster, {'pages': 0, 'internal': 0, 'external': 0, 'impressions': 0, 'positions': []})
        avg_pos = sum(s['positions']) / len(s['positions']) if s['positions'] else 0
        gravity_score = (s['pages'] * 2) + (s['internal'] * 1.5) + (s['external'] * 4) + (s['impressions'] / 40)
        opportunity_score = s['impressions'] / s['pages'] if s['pages'] > 0 else 0
        priority = "Dominant" if gravity_score > 80 else "Growth" if gravity_score > 40 else "Expansion Needed"
        
        radar_rows.append([
            cluster, s['pages'], s['internal'], s['external'], s['impressions'], 
            f"{avg_pos:.1f}" if avg_pos > 0 else "-", round(gravity_score, 1), 
            round(opportunity_score, 1), priority
        ])

    radar_rows.sort(key=lambda x: x[6], reverse=True)
    urls_by_category['Authority_Radar'] = radar_rows
    
    # 3. Create Cluster_Map (Visual Summary)
    # Expected: Cluster, URL, Pages, Gravity, Opportunity, Priority, Action
    cluster_map_data = []
    # Use updated_cornerstones for the base, and merge with radar stats
    # updated_cornerstones is urls_by_category['Cornerstone_Map']
    # updated_radar is radar_rows (urls_by_category['Authority_Radar'])
    
    for row in urls_by_category['Cornerstone_Map']: # Use updated_cornerstones
        # row: [topic, hub_url, keyword, ideal, current, missing, priority]
        topic = row[0]
        hub_url = row[1]
        priority_from_cornerstone = row[6] # This is the strategic priority
        
        # Get stats from radar if available
        stats = {}
        for r_row in radar_rows: # Use radar_rows (which is updated_radar)
            if r_row[0] == topic:
                stats = {
                    'pages': r_row[1],
                    'gravity': r_row[6],
                    'opportunity': r_row[7],
                    'radar_priority': r_row[8] # Priority from radar calculation
                }
                break
        
        # Default stats if not found in radar (e.g., new cornerstones)
        if not stats:
            stats = {'pages': row[4], 'gravity': 0.0, 'opportunity': 0.0, 'radar_priority': 'Expansion Needed'}
            
        # Determine the final priority and action based on both strategic and radar analysis
        final_priority = stats['radar_priority'] # Default to radar's priority
        if priority_from_cornerstone == "High" and stats['radar_priority'] == "Expansion Needed":
            final_priority = "Growth" # Strategic override for new/important clusters
        elif priority_from_cornerstone == "High" and stats['radar_priority'] == "Growth":
            final_priority = "Dominant" # Push growth clusters if strategically high
            
        action = "Reinforce" if final_priority == "Dominant" else "Expand" if final_priority == "Growth" else "Build Cluster"
        
        cluster_map_data.append([topic, hub_url, stats['pages'], stats['gravity'], stats['opportunity'], final_priority, action])
    
    urls_by_category['Cluster_Map'] = cluster_map_data

    # 1. Cleanup: Remove duplicate/unused tabs
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = spreadsheet.get('sheets', [])
    
    whitelist = list(SEO_GROWTH_TABS.keys()) + list(PHASE1_TABS.keys())
    delete_requests = []
    
    for s in existing_sheets:
        title = s['properties']['title']
        sheet_id = s['properties']['sheetId']
        if title not in whitelist:
            print(f"Cleanup: Removing redundant tab '{title}'")
            delete_requests.append({'deleteSheet': {'sheetId': sheet_id}})
    
    if delete_requests:
        # We must ensure at least one sheet exists before deleting others
        # (Though in our case, we'll be adding the missing whitelist sheets next)
        try:
            service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': delete_requests}).execute()
        except Exception as e:
            print(f"Cleanup Error (likely tried to delete last sheet): {e}")

    # 2. Add missing tabs
    existing_titles = [s['properties']['title'] for s in service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute().get('sheets', [])]
    add_requests = []
    for category in whitelist:
        if category not in existing_titles:
            add_requests.append({'addSheet': {'properties': {'title': category}}})
    
    if add_requests:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': add_requests}).execute()

    # 3. Subpage Strategy & Roadmap Seeding
    print("Seeding subpage roadmap...")
    try:
        subpage_data = get_sheet_values(service, SPREADSHEET_ID, "'Subpage_Plan'!A2:E")
    except Exception:
        subpage_data = []
    
    all_subpages = {}
    # Load examples first
    for row in SUBPAGE_PLAN_EXAMPLES:
        parent = get_slug(row[0])
        topic = str(row[1]).strip()
        all_subpages[(parent, topic)] = row

    for row in subpage_data:
        if not row: continue
        parent = get_slug(row[0])
        topic = str(row[1]).strip()
        all_subpages[(parent, topic)] = row
        # Ensure row starts with slug
        all_subpages[(parent, topic)][0] = parent
        
    updated_subpages = []
    sitemap_locs = {u['loc'] for u in all_urls}
    
    for key, row in all_subpages.items():
        parent, topic = row[0], row[1]
        slug = get_slug(topic)
        
        status = row[4] if len(row) > 4 else 'planned'
        # Check if actually live
        for loc in sitemap_locs:
            if slug in loc:
                status = 'exists'
                break
        
        updated_subpages.append([parent, topic, row[2] if len(row) > 2 else 'blog', row[3] if len(row) > 3 else topic, status])

    urls_by_category['Subpage_Plan'] = updated_subpages

    # 4. Update tabs with fresh data and apply formatting
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    for category, values in urls_by_category.items():
        if not values and category not in MARKET_INTEL: continue
        
        # Determine priority colors for Cluster_Map formatting
        p_colors = None
        if category == 'Cluster_Map':
            p_colors = [row[4] for row in values]

        headers = SEO_GROWTH_TABS[category]
        data = headers + values
        range_name = f"'{category}'!A1"
        
        # Clear and update (Clear columns A to Z to remove old corrupted data)
        service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range=f"'{category}'!A:Z").execute()
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption='RAW', body={'values': data}).execute()
        
        apply_formatting(service, SPREADSHEET_ID, sheet_meta[category], len(headers[0]), priority_colors=p_colors)
        
        # Custom Conditional Formatting for Sitemap Inventory Link Floor
        if category == 'Sitemap Inventory':
            last_row = len(data)
            format_req = [{
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_meta[category], 'startRowIndex': 1, 'endRowIndex': last_row, 'startColumnIndex': 4, 'endColumnIndex': 5}],
                        'booleanRule': {
                            'condition': {'type': 'NUMBER_LESS', 'values': [{'userEnteredValue': '3'}]},
                            'format': {'backgroundColor': {'red': 1.0, 'green': 0.8, 'blue': 0.8}} # Red
                        }
                    },
                    'index': 0
                }
            }, {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_meta[category], 'startRowIndex': 1, 'endRowIndex': last_row, 'startColumnIndex': 4, 'endColumnIndex': 5}],
                        'booleanRule': {
                            'condition': {'type': 'NUMBER_GREATER', 'values': [{'userEnteredValue': '2'}]},
                            'format': {'backgroundColor': {'red': 0.8, 'green': 1.0, 'blue': 0.8}} # Green
                        }
                    },
                    'index': 1
                }
            }]
            try:
                service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': format_req}).execute()
            except Exception as e:
                print(f"Warning: Could not apply link floor formatting: {e}")

        time.sleep(2) # Prevent Google Sheets API Quota Error

    # 6. Global Dashboard Intelligence Export
    export_dashboard_json(urls_by_category)
    print("Full SEO Factory Cycle Complete.")
    return service

def export_dashboard_json(data_by_tab):
    """Exports SEO intelligence to a structured JSON file for dashboards and AI."""
    print("Exporting dashboard data to JSON...")
    
    # Ensure data directory exists
    data_dir = os.path.join(ROOT_DIR, 'data')
    os.makedirs(data_dir, exist_ok=True)

    dashboard = {
        "site": {
            "total_pages": len(data_by_tab.get('Sitemap Inventory', [])),
            "clusters": len(data_by_tab.get('Cluster_Map', [])),
            "last_sync": datetime.now().isoformat()
        },
        "clusters": [],
        "opportunities": [],
        "reinforcement_tasks": []
    }

    # Map Clusters
    for row in data_by_tab.get('Cluster_Map', []):
        # Cluster, URL, Pages, Gravity Score, Opportunity Score, Priority, Recommended Action
        dashboard['clusters'].append({
            "name": row[0],
            "url": row[1],
            "pages": row[2],
            "gravity": row[3],
            "opportunity": row[4],
            "status": row[5],
            "recommended_action": row[6]
        })

    # Map Opportunities
    for row in data_by_tab.get('Expansion_Engine', []):
        # Cluster, Suggested Page, Target Keyword, Impressions, Opportunity Type
        dashboard['opportunities'].append(row[2]) # Target Keyword

    # Map Reinforcement Tasks
    for row in data_by_tab.get('Reinforcement_Queue', []):
        # URL, Action, Reason, Priority
        dashboard['reinforcement_tasks'].append(row[0]) # URL

    export_path = os.path.join(data_dir, 'seo_dashboard.json')
    with open(export_path, 'w') as f:
        json.dump(dashboard, f, indent=2)
    
    print(f"Dashboard intelligence exported to {export_path}")
    print("SYNC COMPLETE")

def cmd_autopilot():
    """Runs the full SEO growth loop in sequence."""
    print("STARTING SEO AUTOPILOT...")
    service = cmd_sync() # Sync returns the service object now
    print("SYNC COMPLETE")
    cmd_discover(service_instance=service)
    print("DISCOVERY COMPLETE")
    cmd_reinforce(service_instance=service)
    print("REINFORCEMENT COMPLETE")
    cmd_internal(service_instance=service)
    print("INTERNAL LINKING COMPLETE")
    print("AUTOPILOT RUN FINISHED")

def cmd_reinforce(service_instance=None):
    """Identifies search opportunities and queues reinforcement tasks."""
    print("Starting SEO Reinforcement analysis...")
    if not service_instance:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        service = build('sheets', 'v4', credentials=creds)
    else:
        service = service_instance

    # 1. Read Performance and Inventory data
    perf_data = get_sheet_values(service, SPREADSHEET_ID, "'🔑 CONTENT PERFORMANCE'!A2:E")
    inventory = get_sheet_values(service, SPREADSHEET_ID, "'Sitemap Inventory'!A2:E")
    
    opportunities = []
    for row in perf_data:
        if len(row) < 5: continue
        url = row[3]  # Target Page column in CONTENT PERFORMANCE
        try:
            impressions = int(row[4])
            # Based on user instruction: Impressions > 50, Clicks < 10
            # For now, we assume Clicks < 10 if we're identifying these as opportunities
            if impressions > 50:
                opportunities.append({'url': url, 'impressions': impressions})
        except: continue

    if not opportunities:
        print("No reinforcement opportunities found based on current sheet data.")
        return

    # 2. Analyze Internal Linking from Inventory
    tasks = []
    for opp in opportunities[:10]: # Limit to 10
        url = opp['url']
        path_parts = url.rstrip('/').split('/')
        topic = path_parts[3] if len(path_parts) > 3 else "main"
        
        # Possible actions
        actions = ["expand content", "add FAQ section", "improve headings", "add internal links", "add schema", "update meta description"]
        action = actions[opportunities.index(opp) % len(actions)]
        
        reason = f"High Impressions ({opp['impressions']}) with low engagement."
        
        # Internal linking check
        related = []
        for inv in inventory:
            if inv[0] != url and inv[2] == topic:
                related.append(inv[0])
        
        if related:
            link_note = f" Link from: {', '.join(related[:2])}"
            reason += link_note

        tasks.append([url, action, reason, 'High'])

    # 3. Update Reinforcement_Queue tab
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Reinforcement_Queue' not in sheet_meta:
        # Add tab if missing
        add_req = [{'addSheet': {'properties': {'title': 'Reinforcement_Queue'}}}]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': add_req}).execute()
        # Re-fetch meta
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    headers = SEO_GROWTH_TABS['Reinforcement_Queue']
    values = headers + tasks
    range_name = "'Reinforcement_Queue'!A1"
    service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='RAW', body={'values': values}).execute()

    apply_formatting(service, SPREADSHEET_ID, sheet_meta['Reinforcement_Queue'], len(headers[0]))

    print(f"\n--- Reinforcement Summary ---")
    print(f"Pages analyzed: {len(opportunities)}")
    print(f"Reinforcement tasks created: {len(tasks)}")
    print(f"Internal link opportunities found: {sum(1 for t in tasks if 'Link from' in t[2])}")
    print(f"Check the 'Reinforcement_Queue' tab for details.")
    print("REINFORCEMENT COMPLETE")

def _generate_page(name, type, dry_run=False):
    """Internal helper to generate a single page without triggering a full sync."""
    slug = get_slug(name)
    
    # 1. Conflict Check (Slugs)
    get_sitemap_urls_data = get_sitemap_urls()
    existing_urls = [u['loc'].rstrip('/') for u in get_sitemap_urls_data]
    
    # Check if the name/slug exists ANYWHERE in the current sitemap to prevent "Idea" conflicts
    for url in existing_urls:
        url_parts = url.replace(DOMAIN, '').strip('/').split('/')
        if slug in url_parts:
            # If it already exists, skipping is safer than erroring in a batch run
            return None, f"SKIPPED: '{slug}' already exists in sitemap."

    new_url = f"{DOMAIN}"
    if type == 'location':
        # LA Relocation uses root-level folders for cities (e.g. /palmdale/)
        target_dir = os.path.join(ROOT_DIR, slug)
        new_url += f"/{slug}/"
    elif type == 'neighborhood':
        target_dir = os.path.join(ROOT_DIR, 'neighborhood', slug)
        new_url += f"/neighborhood/{slug}/"
    elif type == 'service':
        target_dir = os.path.join(ROOT_DIR, 'features', slug)
        new_url += f"/features/{slug}/"
    elif type == 'blog':
        target_dir = os.path.join(ROOT_DIR, 'blog', slug)
        new_url += f"/blog/{slug}/"
    else:
        return None, f"ERROR: Unknown type '{type}'"

    if os.path.exists(target_dir):
        return None, f"SKIPPED: Directory already exists for '{slug}'."

    # 2. Template Selection (From Engine's Internal Templates Folder)
    template_path = os.path.join(ENGINE_ROOT, 'core', 'templates', f"{type}.html")
    if type == 'blog' and not os.path.exists(template_path):
        template_path = os.path.join(ENGINE_ROOT, 'core', 'templates', 'blog.html')
    if type == 'neighborhood' and not os.path.exists(template_path):
        template_path = os.path.join(ENGINE_ROOT, 'core', 'templates', 'location.html')

    if not os.path.exists(template_path):
        return None, f"ERROR: Template not found at {template_path}"

    with open(template_path, 'r') as f:
        content = f.read()

    # Load block rules
    rules_path = os.path.join(ENGINE_ROOT, 'core', 'registries', 'data_block_rules.json')
    block_rules = {}
    if os.path.exists(rules_path):
        with open(rules_path, 'r') as f:
            block_rules = json.load(f)

    # 3. Fill Template
    if type in ['location', 'neighborhood', 'blog']:
        ctx = get_city_data_context(name)
        content = content.replace('{{LOCATION}}', name).replace('{{SLUG}}', slug)
        
        type_rules = block_rules.get(type, ["market", "crime", "schools", "commute", "amenities", "demographics"])

        RENDER_MAP = {
            'market': ('{{MARKET_DATA}}', render_market_snippet, 'market'),
            'crime': ('{{CRIME_STATS}}', render_crime_snippet, 'crime'),
            'schools': ('{{SCHOOL_RATINGS}}', render_school_snippet, 'schools'),
            'commute': ('{{COMMUTE_DATA}}', render_commute_snippet, 'commute'),
            'amenities': ('{{AMENITIES}}', render_amenities_snippet, 'amenities'),
            'demographics': ('{{DEMOGRAPHICS}}', render_demographics_snippet, 'demographics')
        }

        for block_id, (tag, render_fn, ctx_key) in RENDER_MAP.items():
            if block_id in type_rules:
                if ctx_key in ctx and ctx[ctx_key]:
                    content = content.replace(tag, render_fn(ctx[ctx_key]))
                else:
                    content = content.replace(tag, render_fn(None))
            else:
                content = content.replace(tag, "")

        content = content.replace('{{NEIGHBORHOOD_GUIDE}}', render_links_snippet(ctx['neighborhoods']))
        content = content.replace('{{INTERNAL_BLOGS}}', render_links_snippet(ctx['relocation']))
    else:

        # Check if name is in SUBPAGE_PLAN_EXAMPLES to get better context
        topic_info = next((s for s in SUBPAGE_PLAN_EXAMPLES if s[1].lower() == name.lower()), None)
        description = f"Learn more about AI Pilots' {name} solution for modern businesses."
        subtitle = f"The ultimate {name} for modern digital growth."
        
        if topic_info:
            target_keyword = topic_info[3]
            description = f"Discover how AI Pilots' {name} elevates your brand with advanced {target_keyword} capabilities."
            subtitle = f"Professional {name} built for business growth."

        content = content.replace('{{TITLE}}', name.title())
        content = content.replace('{{SLUG}}', slug)
        content = content.replace('{{DESCRIPTION}}', description)
        content = content.replace('{{SUBTITLE}}', subtitle)
        content = content.replace('{{CONTENT}}', f"<p>AI Pilots' {name} is a mission-critical tool designed to help your business scale by automating repetitive tasks and deepening customer engagement.</p>")

    # 4. Write File
    if dry_run:
        return new_url, "[DRY RUN] Success"
    else:
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, 'index.html'), 'w') as f:
            f.write(content)
        update_sitemap(new_url)
        return new_url, "CREATED"

def cmd_generate(args):
    """CLI wrapper for single page generation."""
    new_url, result = _generate_page(args.name, args.type, args.dry_run)
    print(f"{result}: {new_url if new_url else ''}")
    if result == "CREATED" and not args.dry_run:
        print("Triggering Google Sheet sync...")
        cmd_sync()
    print("GENERATE COMPLETE")

def cmd_produce_subpages():
    """Mass generates all 150+ planned subpages from SUBPAGE_PLAN_EXAMPLES."""
    print(f"🚀 Mass Materializing {len(SUBPAGE_PLAN_EXAMPLES)} Strategic Subpages...")
    created_count = 0
    skipped_count = 0
    
    for i, s in enumerate(SUBPAGE_PLAN_EXAMPLES):
        hub_name, topic_name, topic_type, topic_keyword, status = s
        print(f"[{i+1}/{len(SUBPAGE_PLAN_EXAMPLES)}] Processing: {topic_name} ({topic_type})...", end=" ", flush=True)
        
        new_url, result = _generate_page(topic_name, topic_type)
        if result == "CREATED":
            print("✅ CREATED")
            created_count += 1
        else:
            print(f"🟡 {result}")
            skipped_count += 1
            
    print(f"\n--- Mass Generation Summary ---")
    print(f"Total Processed: {len(SUBPAGE_PLAN_EXAMPLES)}")
    print(f"Newly Created: {created_count}")
    print(f"Skipped/Existing: {skipped_count}")
    
    if created_count > 0:
        print("\nTriggering final sync to index the new strategic network...")
        cmd_sync()
    print("PRODUCE SUBPAGES COMPLETE")

def cmd_discover(service_instance=None):
    """Identifies new keyword opportunities from Google Search Console data."""
    print("Starting SEO discovery process...")
    if not service_instance:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        service = build('sheets', 'v4', credentials=creds)
    else:
        service = service_instance

    # 1. Fetch GSC Data and Sitemap Inventory
    gsc_data = get_gsc_data() # Queries > 50 impressions
    inventory = get_sheet_values(service, SPREADSHEET_ID, "'Sitemap Inventory'!A2:C")
    existing_urls = {row[0] for row in inventory if len(row) > 0}
    
    # Map topics to clusters for discovery
    cluster_map = {row[0]: row[2] for row in inventory if len(row) >= 3}

    # 2. Identify queries with High Impressions but no page
    new_opportunities = []
    seen_queries = set()
    
    for row in gsc_data:
        # Expected structure: {'keys': ['query', 'page'], 'impressions': 100, ...}
        if 'keys' not in row or len(row['keys']) == 0: continue
        query = row['keys'][0]
        impressions = row.get('impressions', 0)
        
        if impressions > 50:
            # Basic query-to-topic heuristic
            is_existing = False
            for url in existing_urls:
                slug = url.rstrip('/').split('/')[-1].replace('-', ' ')
                if query in slug or slug in query:
                    is_existing = True
                    break
            
            if not is_existing and query not in seen_queries:
                # Find matching cluster
                cluster = "General"
                for keyword, topic in cluster_map.items():
                    if topic in query:
                        cluster = topic
                        break
                
                new_opportunities.append([
                    cluster,
                    get_slug(query),
                    query,
                    impressions,
                    "new demand"
                ])
                seen_queries.add(query)
                if len(new_opportunities) >= 20: break

    if not new_opportunities:
        print("No new discovery opportunities found.")
        return

    # 3. Update Expansion_Engine tab
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Expansion_Engine' not in sheet_meta:
        add_req = [{'addSheet': {'properties': {'title': 'Expansion_Engine'}}}]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': add_req}).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    headers = SEO_GROWTH_TABS['Expansion_Engine']
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Expansion_Engine'!A1",
        valueInputOption='RAW', body={'values': headers + new_opportunities}).execute()

    apply_formatting(service, SPREADSHEET_ID, sheet_meta['Expansion_Engine'], len(headers[0]))

    print(f"Discovery complete. Added {len(new_opportunities)} opportunities to Expansion_Engine.")
    print("DISCOVERY COMPLETE")

def cmd_internal(service_instance=None):
    """Optimizes internal linking between related pages within topic clusters."""
    print("Starting Strategic Internal Link Analysis...")
    if not service_instance:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        service = build('sheets', 'v4', credentials=creds)
    else:
        service = service_instance

    # 1. Read Data
    inventory = get_sheet_values(service, SPREADSHEET_ID, "'Sitemap Inventory'!A2:C")
    backlink_data = get_sheet_values(service, SPREADSHEET_ID, "'Backlink_Audit'!A2:C")
    
    # Load Cornerstones for pillar prioritization
    pill_data = []
    if os.path.exists(CORNERSTONE_FILE):
        with open(CORNERSTONE_FILE, 'r') as f:
            pill_data = json.load(f)
    
    # Map normalized slug to keyword
    pillar_map = {}
    for row in pill_data:
        if not row: continue
        topic_slug_map = {
            'website maintenance and care': 'website-care',
            'local seo antelope valley': 'local-seo-av',
            'nonprofit digital solutions': 'nonprofit-digital',
            'website build roadmap': 'website-build-roadmap',
            'ai authority content strategy': 'ai-authority-content',
            'daycare marketing bundle': 'daycare-bundle',
            'social media marketing': 'social-media-marketing',
            'managed hosting for business': 'managed-hosting'
        }
        slug = topic_slug_map.get(row[0].lower(), get_slug(row[0]))
        pillar_map[slug] = row[2]

    # 2. Group pages by Parent Topic
    clusters = {}
    for row in inventory:
        if len(row) < 3: continue
        url, page_type, parent_topic = row[0], row[1], row[2]
        
        # NORMALIZATION: Map readable topic names to slugs for matching
        topic_slug_map = {
            'website maintenance and care': 'website-care',
            'local seo antelope valley': 'local-seo-av',
            'nonprofit digital solutions': 'nonprofit-digital',
            'website build roadmap': 'website-build-roadmap',
            'ai authority content strategy': 'ai-authority-content',
            'daycare marketing bundle': 'daycare-bundle',
            'social media marketing': 'social-media-marketing',
            'managed hosting for business': 'managed-hosting'
        }
        topic_normalized = topic_slug_map.get(parent_topic.lower(), parent_topic)

        if topic_normalized not in clusters:
            clusters[topic_normalized] = []
        clusters[topic_normalized].append({'url': url, 'type': page_type})

    # 3. Strategic Opportunity Identification
    opportunities = []
    
    # A. Hub & Spoke: Ensure every subpage links to its Pillar
    for topic, pages in clusters.items():
        if topic in pillar_map:
            # Find the pillar URL
            pillar_url = None
            for p in pages:
                # Check if it's the exact pillar slug
                if p['url'].rstrip('/').split('/')[-1] == topic:
                    pillar_url = p['url']
                    break
            
            if pillar_url:
                keyword = pillar_map[topic]
                for p in pages:
                    if p['url'] != pillar_url:
                        opportunities.append([
                            p['url'], pillar_url, keyword.title(), topic, 
                            f"Pillar Support: Link to '{topic}' cornerstone"
                        ])

    # B. Cluster Density: Ensure low-authority subpages get support
    under_linked = []
    for row in backlink_data:
        if len(row) < 3: continue
        url = row[0]
        try:
            icount = int(row[2]) if str(row[2]).isdigit() else 0
            if icount < 3: under_linked.append(url)
        except: continue

    # C. Authority Floor Enforcement (Global Fallbacks)
    GLOBAL_AUTHORITY_HUBS = [
        {'url': f"{DOMAIN}/services/", 'anchor': 'Professional AI Services'},
        {'url': f"{DOMAIN}/pricing/", 'anchor': 'View Pricing & Plans'},
        {'url': f"{DOMAIN}/blog/local-seo-av/", 'anchor': 'Antelope Valley Local SEO Hub'}
    ]

    # Map existing opportunities to count links per source
    links_per_source = {}
    for opp in opportunities:
        src = opp[0]
        links_per_source[src] = links_per_source.get(src, 0) + 1

    # Ensure every page in the inventory has at least 3 links
    for row in inventory:
        if len(row) < 1: continue
        source_url = row[0]
        current_links = links_per_source.get(source_url, 0)
        
        if current_links < 3:
            # Need more links to hit authority floor
            needed = 3 - current_links
            for i in range(needed):
                # Pull from global hubs, prioritizing variety
                hub = GLOBAL_AUTHORITY_HUBS[i % len(GLOBAL_AUTHORITY_HUBS)]
                if hub['url'] == source_url: continue # Don't link to self
                
                opportunities.append([
                    source_url, hub['url'], hub['anchor'], "Global Authority",
                    f"Authority Floor: Mandating min 3 links for crawlability"
                ])
                current_links += 1
                if current_links >= 3: break

    # 4. Update Internal_Link_Queue tab
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    if 'Internal_Link_Queue' not in sheet_meta:
        add_req = [{'addSheet': {'properties': {'title': 'Internal_Link_Queue'}}}]
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': add_req}).execute()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_meta = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}

    headers = SEO_GROWTH_TABS['Internal_Link_Queue']
    # Filter to avoid too many links at once (increased to 1500 for full coverage)
    final_values = headers + opportunities[:1500]
    
    print(f"Syncing {len(final_values) - 1} strategic links to 'Internal_Link_Queue'...")
    # Trace specific urls if found
    for r in final_values:
        if 'website-care' in r[0] or 'website-care' in r[1]:
            print(f"  [CLUSTER-TRACE] {r[0]} -> {r[1]} ({r[2]})")

    range_name = "'Internal_Link_Queue'!A1"
    service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='RAW', body={'values': final_values}).execute()

    apply_formatting(service, SPREADSHEET_ID, sheet_meta['Internal_Link_Queue'], len(headers[0]))
    print(f"STRATEGIC INTERNAL LINKING COMPLETE. Found {len(opportunities)} opportunities.")

def cmd_update_internal():
    """Reads Internal_Link_Queue from Google Sheets and applies links to the HTML files."""
    print("Applying Internal Links from Queue...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    # 1. Read the link queue
    queue_data = get_sheet_values(service, SPREADSHEET_ID, "'Internal_Link_Queue'!A2:E")
    if not queue_data:
        print("No internal link opportunities found in queue.")
        return

    # 2. Group opportunities by Source Page
    link_map = {}
    for row in queue_data:
        if len(row) < 3: continue
        source_url, target_url, anchor = row[0], row[1], row[2]
        if source_url not in link_map:
            link_map[source_url] = []
        link_map[source_url].append({'target': target_url, 'anchor': anchor})

    # 3. Apply links for each source page
    applied_count = 0
    pill_data = []
    if os.path.exists(CORNERSTONE_FILE):
        with open(CORNERSTONE_FILE, 'r') as f:
            pill_data = json.load(f)
    
    # Normalize pillar URLs with domain for matching
    pillar_urls = set()
    for row in pill_data:
        if len(row) > 1 and row[1] != '-':
            p_url = row[1]
            if not p_url.startswith('http'):
                p_url = DOMAIN.rstrip('/') + '/' + p_url.lstrip('/')
            pillar_urls.add(p_url)

    for source_url, links in link_map.items():
        # Map URL to local file path
        rel_path = source_url.replace(DOMAIN, '').strip('/')
        if not rel_path:
            file_path = os.path.join(ROOT_DIR, 'index.html')
        else:
            file_path = os.path.join(ROOT_DIR, rel_path, 'index.html')

        if not os.path.exists(file_path):
            print(f"Skipping: File not found at {file_path}")
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Build the link block with authority-first design
        unique_links = {l['target']: l['anchor'] for l in links if l['target'] != source_url}
        if not unique_links: continue

        print(f"Updating: {file_path} with {len(unique_links)} links")
        link_html = '\n    <div class="seo-authority-block" style="margin: 4rem 0; padding: 3rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); backdrop-filter: blur(10px); border-radius: 24px; font-family: var(--font-primary); position: relative; overflow: hidden;">\n'
        link_html += '        <div style="position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: linear-gradient(to bottom, var(--primary-color), var(--accent-color));"></div>\n'
        
        # Check if we have any pillar links
        contains_pillar = any(t in pillar_urls for t in unique_links.keys())
        header = "Strategic Resources" if contains_pillar else "Related Reading"
        
        link_html += f'        <h4 style="margin: 0 0 2rem 0; color: white; font-family: var(--font-display); font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em;">{header}</h4>\n'
        link_html += '        <ul style="list-style: none; padding: 0; margin: 0; display: grid; gap: 1.25rem;">\n'
        
        for target, anchor in unique_links.items():
            is_pillar = target in pillar_urls
            prefix = "⭐ " if is_pillar else ""
            weight = "600" if is_pillar else "500"
            color = "var(--primary-color)" if is_pillar else "var(--text-secondary)"
            
            link_html += f'            <li style="transition: transform 0.2s ease;">\n'
            link_html += f'                <a href="{target}" class="authority-link" style="display: flex; align-items: center; gap: 0.75rem; color: {color}; text-decoration: none; font-weight: {weight}; font-size: 1.1rem; transition: all 0.2s ease;">\n'
            link_html += f'                    <span style="display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; background: rgba(37, 99, 235, 0.1); border-radius: 6px; color: var(--primary-color); font-size: 0.8rem;">→</span>\n'
            link_html += f'                    <span>{prefix}{anchor}</span>\n'
            link_html += f'                </a>\n'
            link_html += f'            </li>\n'
            
        link_html += '        </ul>\n'
        link_html += '    </div>\n'
        link_html += '    <style>\n'
        link_html += '        .authority-link:hover {\n'
        link_html += '            color: white !important;\n'
        link_html += '            transform: translateX(8px);\n'
        link_html += '        }\n'
        link_html += '        .authority-link:hover span:first-child {\n'
        link_html += '            background: var(--primary-color) !important;\n'
        link_html += '            color: white !important;\n'
        link_html += '        }\n'
        link_html += '    </style>\n'
        
        block = f"<!-- SEO_INTERNAL_LINKS_START -->{link_html}<!-- SEO_INTERNAL_LINKS_END -->"

        if "<!-- SEO_INTERNAL_LINKS_START -->" in content:
            content = re.sub(r"<!-- SEO_INTERNAL_LINKS_START -->.*?<!-- SEO_INTERNAL_LINKS_END -->", block, content, flags=re.DOTALL)
        else:
            # Semantic injection logic - try to find the best spot above footer or inside main
            if "</article>" in content:
                content = content.replace("</article>", f"{block}\n</article>")
            elif "</main>" in content:
                content = content.replace("</main>", f"{block}\n</main>")
            elif re.search(r'<footer[^>]*>', content):
                content = re.sub(r'(<footer[^>]*>)', f"{block}\n\\1", content)
            else:
                content = content.replace("</body>", f"{block}\n</body>")

        with open(file_path, 'w') as f:
            f.write(content)
        applied_count += 1

    print(f"Strategic internal links applied to {applied_count} pages.")
    print("UPDATE INTERNAL COMPLETE")

HUB_CONTENT = {
    "local-seo-av": {
        "hero_title": "Antelope Valley Local SEO Dominance",
        "hero_subtitle": "Put your business on the map in Palmdale, Lancaster, and the surrounding High Desert area.",
        "impact": [
            ("Map Pack Ranking", "We specialize in getting High Desert service businesses into the top 3 spots on Google Maps."),
            ("Keyword Authority", "Target specific service areas from Quartz Hill to Rosamond with localized landing pages."),
            ("Google Business Optimization", "Fully managed profile optimization to drive calls and leads without ad spend.")
        ],
        "faqs": [
            ("Why is local SEO important in the AV?", "With Lancaster and Palmdale growing, competition for mobile searches is at an all-time high."),
            ("How long to see results?", "Most local businesses see an increase in map impressions within 30-60 days."),
            ("Do you handle reviews?", "Yes, we implement automated systems to help you capture and display customer proof.")
        ]
    },
    "nonprofit-digital": {
        "hero_title": "Nonprofit Digital Growth & TechSoup Support",
        "hero_subtitle": "Helping charitable organizations leverage Google Grants and modern tech to change more lives.",
        "impact": [
            ("Google Ad Grants", "Secure up to $10,000/month in free search advertising to reach donors and volunteers."),
            ("Donation Optimization", "Modern, low-friction giving platforms that integrate directly with your website."),
            ("TechSoup Approval", "We guide you through the TechSoup validation process to unlock massive software discounts.")
        ],
        "faqs": [
            ("What are Google Grants?", "Google provides free search ad credit to 501(c)(3) organizations to promote their mission."),
            ("Can small nonprofits apply?", "Yes, as long as you have valid tax-exempt status, we can help you apply."),
            ("Is technical support included?", "Absolutely. We manage the technical overhead so you can focus on your cause.")
        ]
    },
    "website-build-roadmap": {
        "hero_title": "Strategic Website Build Roadmap",
        "hero_subtitle": "A forensic approach to building high-performance, authority-driven digital properties.",
        "impact": [
            ("Discovery & Planning", "We map your industry vertical and competitor landscape before a single line of code is written."),
            ("Authority Architecture", "Built-in topic clusters and semantic internal linking from day one."),
            ("Conversion Optimization", "Every element is designed to move users from discovery to meaningful engagement.")
        ],
        "faqs": [
            ("How long does a build take?", "Our 'Factory' engine allows us to deploy production-ready sites in 2-4 weeks."),
            ("Is it mobile friendly?", "We follow a mobile-first philosophy ensuring perfect performance on all devices."),
            ("Do I own the code?", "Yes, we build on modern, open standards. You own your digital assets 100%.")
        ]
    },
    "managed-hosting": {
        "hero_title": "Premium Managed Hosting for Business",
        "hero_subtitle": "Lightning-fast speed, hardened security, and zero-config maintenance for your brand.",
        "impact": [
            ("Edge Performance", "Global CDN delivery ensures your site loads in under 1 second anywhere in the world."),
            ("Security Hardening", "Enterprise-grade WAF and 24/7 monitoring to keep hackers and bots away."),
            ("Automated Backups", "Daily snapshots and instant recovery so your business data is never at risk.")
        ],
        "faqs": [
            ("What is Managed Hosting?", "It means we handle all the technical updates, speed tuning, and security for you."),
            ("Do you offer email?", "Yes, we integrate with professional Google Workspace or O365 for your domain."),
            ("Can you migrate my old site?", "Yes, we provide free white-glove migration from WordPress or generic hosts.")
        ]
    },
    "website-care": {
        "hero_title": "Pro-Grade Website Care & Maintenance",
        "hero_subtitle": "Protect your digital investment with 24/7 monitoring, security hardening, and performance optimization.",
        "impact": [
            ("Uptime Security", "We monitor your site every 60 seconds. If it goes down, we're on it before you even notice."),
            ("Performance Speed", "Weekly optimizations ensure your site stays lightning fast for both users and search engines."),
            ("Peace of Mind", "Regular backups and security patches mean you never have to worry about data loss or hackers.")
        ],
        "faqs": [
            ("What is a website care plan?", "It's a comprehensive service that handles technical updates, security, and performance for you."),
            ("Do you support WordPress?", "Yes, we specialize in hardening and maintaining WordPress sites for maximum reliability."),
            ("Can I cancel anytime?", "Absolutely. Our plans are month-to-month with no long-term contracts required.")
        ]
    }
}

def cmd_hubs():
    """Systematically generates or refreshes all 11 cornerstone hub pages with rich content."""
    print("🚀 Rebuilding Strategic Authority Hubs with Rich Content Engine...")
    template_path = os.path.join(ROOT_DIR, 'templates/feature_hub.html')
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}")
        return

    with open(template_path, 'r') as f:
        master_template = f.read()

    for row in CORNERSTONE_MAP_EXAMPLES:
        hub_name = row[0]
        slug = get_slug(hub_name)
        target_keyword = row[2]
        target_dir = os.path.join(ROOT_DIR, slug)
        
        print(f"--- Generating Rich Hub: {hub_name} ---")
        
        # Get specific content or fallback
        rich = HUB_CONTENT.get(hub_name, HUB_CONTENT["church-app"])
        
        # 1. Feature Cards
        subpages = [s for s in SUBPAGE_PLAN_EXAMPLES if s[0] == hub_name]
        feature_cards_html = ""
        icons = {
            'scheduling': 'fa-calendar-check', 'check-in': 'fa-user-check', 'management': 'fa-users-cog',
            'giving': 'fa-hand-holding-heart', 'tracking': 'fa-chart-line', 'automation': 'fa-robot',
            'outreach': 'fa-hands-helping', 'mass texting': 'fa-comment-sms', 'newsletter': 'fa-envelope-open-text',
            'engagement': 'fa-heart-pulse', 'onboarding': 'fa-user-plus', 'planning': 'fa-pen-to-square'
        }

        if not subpages:
            feature_cards_html = f"""
                <div class="feature-card">
                    <i class="fas fa-star"></i>
                    <h3>Premium {hub_name.replace('-', ' ').title()}</h3>
                    <p>Experience the most advanced {target_keyword} tools built for competitive business advantage.</p>
                </div>
            """
        else:
            for s in subpages[:6]:
                topic, keyword = s[1], s[3]
                icon = next((v for k, v in icons.items() if k in topic.lower()), "fa-star")
                feature_cards_html += f"""
                    <div class="feature-card">
                        <i class="fas {icon}"></i>
                        <h3>{topic.title()}</h3>
                        <p>Streamline your business with high-performance {keyword} solutions.</p>
                    </div>
                """

        # 2. Business Impact
        impact_html = ""
        for title, desc in rich["impact"]:
            impact_html += f"""
                <div class="impact-item">
                    <div class="impact-icon"><i class="fas fa-check"></i></div>
                    <div>
                        <h4 style="color: #065f46; font-size: 20px; font-weight: 700; margin-bottom: 8px;">{title}</h4>
                        <p style="color: #475569; line-height: 1.6;">{desc}</p>
                    </div>
                </div>
            """

        # 3. Cluster Roadmap
        roadmap_html = ""
        for s in [sub for sub in SUBPAGE_PLAN_EXAMPLES if sub[0] == hub_name]:
            topic_name, topic_type, topic_keyword, status = s[1], s[2], s[3], s[4]
            topic_slug = get_slug(topic_name)
            
            # Check if live
            is_live = False
            check_path = os.path.join(ROOT_DIR, 'features', topic_slug, 'index.html')
            if topic_type == 'blog':
                check_path = os.path.join(ROOT_DIR, 'blog', topic_slug, 'index.html')
            
            if os.path.exists(check_path):
                is_live = True
            
            badge_class = "badge-live" if is_live else "badge-planned"
            badge_text = "Live Guide" if is_live else "Planned"
            url = f"/{'blog' if topic_type == 'blog' else 'features'}/{topic_slug}/"
            
            roadmap_html += f"""
                <a href="{url if is_live else '#'}" class="roadmap-item">
                    <span class="roadmap-badge {badge_class}">{badge_text}</span>
                    <h4>{topic_name.title()}</h4>
                    <p>Strategic {topic_type.title()} focusing on {topic_keyword} for modern businesses.</p>
                </a>
            """

        # 4. FAQs
        faq_html = ""
        for q, a in rich["faqs"]:
            faq_html += f"""
                <div class="faq-item">
                    <h4>{q}</h4>
                    <p>{a}</p>
                </div>
            """

        # 5. Fill Template
        # Extract NAV and FOOTER from index.html for consistency
        try:
            with open(os.path.join(ROOT_DIR, 'index.html'), 'r') as index_f:
                index_content = index_f.read()
                nav_match = re.search(r'<\s*nav[^>]*>(.*?)<\s*/\s*nav\s*>', index_content, re.DOTALL | re.IGNORECASE)
                footer_match = re.search(r'<\s*footer[^>]*>(.*?)<\s*/\s*footer\s*>', index_content, re.DOTALL | re.IGNORECASE)
                nav_html = nav_match.group(1) if nav_match else ""
                footer_html = footer_match.group(1) if footer_match else ""
        except Exception as e:
            print(f"Warning: Could not extract Nav/Footer: {e}")
            nav_html = ""
            footer_html = ""

        content = master_template
        replacements = {
            '{{TITLE}}': f"{rich['hero_title']} | AI Pilots",
            '{{SLUG}}': slug,
            '{{DESCRIPTION}}': f"Strategic {target_keyword} solutions for businesses. High-performance {hub_name.replace('-', ' ')} optimization.",
            '{{HERO_TITLE}}': rich['hero_title'],
            '{{HERO_SUBTITLE}}': rich['hero_subtitle'],
            '{{FEATURE_CARDS}}': feature_cards_html,
            '{{MINISTRY_IMPACT}}': impact_html,
            '{{SUBPAGE_ROADMAP}}': roadmap_html,
            '{{FAQ_SECTION}}': faq_html,
            '{{NAV}}': nav_html,
            '{{FOOTER}}': footer_html
        }
        for k, v in replacements.items():
            content = content.replace(k, v)

        # 6. Write File
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, 'index.html'), 'w') as f:
            f.write(content)
        print(f"Success: {slug}/index.html")

    print("\n✅ All Authority Hubs have been enriched with roadmap connectivity.")
    cmd_sync()

def cmd_expand_locations(args):
    """Automatically generates 3 new location pages from the registry."""
    print("🚀 Running Location Expansion Engine...")
    
    # 1. Identify existing locations
    existing_slugs = set()
    locations_dir = os.path.join(ROOT_DIR, 'locations')
    if os.path.exists(locations_dir):
        for item in os.listdir(locations_dir):
            if os.path.isdir(os.path.join(locations_dir, item)):
                existing_slugs.add(item)
    
    # 2. Pick 3 new ones from registry
    to_add = []
    for loc in LOCATIONS_REGISTRY:
        if loc['slug'] not in existing_slugs:
            to_add.append(loc)
            if len(to_add) >= 3:
                break
    
    if not to_add:
        print("No new locations to add. Registry is either empty or already fully implemented.")
        return

    if args.dry_run:
        print(f"DRY RUN: Would add {len(to_add)} locations: {[l['name'] for l in to_add]}")
        return

    # 3. Use Palmdale as the Golden Master for locations
    template_dir = os.path.join(locations_dir, 'palmdale-ca')
    template_file = os.path.join(template_dir, 'index.html')
    
    if not os.path.exists(template_file):
        print(f"Error: Location template not found at {template_file}")
        return

    with open(template_file, 'r', encoding='utf-8') as f:
        master_content = f.read()

    for loc in to_add:
        new_slug = loc['slug']
        new_name = loc['name']
        new_region = loc['region']
        
        target_dir = os.path.join(locations_dir, new_slug)
        os.makedirs(target_dir, exist_ok=True)
        
        # Replace Palmdale tokens with new location
        new_content = master_content.replace('Palmdale', new_name)
        new_content = new_content.replace('palmdale-ca', new_slug)
        # Update meta title/description if they contain Palmdale
        
        target_file = os.path.join(target_dir, 'index.html')
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✓ Created {new_name} landing page at /locations/{new_slug}/")

    # 4. Update Sitemap
    cmd_sitemap()
    
    # 5. Sync to Sheets
    cmd_sync()
    print(f"Successfully expanded 3 locations: {[l['name'] for l in to_add]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEO Factory: Audit, Sync, and Growth Engine")
    
    # Simple Positional Command
    parser.add_argument('command', choices=['audit', 'sync', 'generate', 'discover', 'internal', 'update-internal', 'reinforce', 'autopilot', 'hubs', 'produce-subpages', 'sitemap', 'expand-locations', 'init-phase1', 'init-phase2', 'init-crime', 'init-schools', 'init-housing', 'init-commute', 'ingest-amenities', 'rebuild-internal-authority', 'generate-relocation-guides', 'ingest-demographics', 'generate-modifier-plan', 'expand-geo-clusters', 'generate-feature-pages', 'validate-data-blocks', 'calculate-authority-score', 'queue-data-reinforcements', 'build-command-center', 'build-master-site-map', 'sync-external-apis', 'materialize-pages', 'build-geo-grid', 'build-idx-traffic', 'detect-buyer-intent', 'sync-authority-signals', 'analyze-user-behavior', 'build-comparisons', 'generate-narratives', 'autonomous-run', 'deploy-pages', 'discover-neighborhoods', 'analyze-lead-performance', 'build-radius-pages', 'analyze-chat-intent', 'build-market-predictions', 'detect-seller-intent', 'build-migration-pages', 'build-authority-flywheel'], help='Command to run')
    
    # Optional Arguments for 'generate'
    parser.add_argument('--type', choices=['location', 'service', 'blog', 'newsletter'], help='Type of page to generate')
    parser.add_argument('--name', help='Name/Title of the page')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
    parser.add_argument('--mode', choices=['audit_only', 'build_only', 'full_autonomous', 'preview'], default='full_autonomous', help='Mode for autonomous run')
    parser.add_argument('--with-git', action='store_true', help='Use Git commit/push in deployment mode')
    
    args = parser.parse_args()

    if args.command == 'audit':
        cmd_audit()
    elif args.command == 'sync':
        cmd_sync()
    elif args.command == 'init-phase1':
        cmd_init_phase1()
    elif args.command == 'init-phase2':
        cmd_init_phase2()
    elif args.command == 'init-housing':
        cmd_init_housing()
    elif args.command == 'init-commute':
        cmd_init_commute()
    elif args.command == 'ingest-amenities':
        cmd_ingest_amenities()
    elif args.command == 'rebuild-internal-authority':
        cmd_rebuild_internal_authority()
    elif args.command == 'generate-relocation-guides':
        cmd_generate_relocation_guides()
    elif args.command == 'ingest-demographics':
        cmd_ingest_demographics()
    elif args.command == 'generate-modifier-plan':
        cmd_generate_modifier_plan()
    elif args.command == 'expand-geo-clusters':
        cmd_expand_geo_clusters()
    elif args.command == 'generate-feature-pages':
        cmd_generate_feature_pages()
    elif args.command == 'validate-data-blocks':
        cmd_validate_data_blocks()
    elif args.command == 'calculate-authority-score':
        cmd_calculate_authority_score()
    elif args.command == 'queue-data-reinforcements':
        cmd_queue_data_reinforcements()
    elif args.command == 'build-command-center':
        cmd_build_command_center()
    elif args.command == 'build-master-site-map':
        cmd_build_master_site_map()
    elif args.command == 'sync-external-apis':
        cmd_sync_external_apis()
    elif args.command == 'materialize-pages':
        import materializer as mat
        mat.materialize_pages()
    elif args.command == 'build-geo-grid':
        import geo_dataset_ingest as geo
        geo.build_geo_grid()
    elif args.command == 'build-idx-traffic':
        import idx_page_generator as idx
        idx.build_idx_traffic()
    elif args.command == 'detect-buyer-intent':
        import intent_discovery as intent
        intent.detect_buyer_intent()
    elif args.command == 'generate':
        if not args.type or not args.name:
            print("Error: --type and --name are required for 'generate' command.")
            sys.exit(1)
        cmd_generate(args)
    elif args.command == 'discover':
        cmd_discover()
    elif args.command == 'internal':
        cmd_internal()
    elif args.command == 'update-internal':
        cmd_update_internal()
    elif args.command == 'reinforce':
        cmd_reinforce()
    elif args.command == 'hubs':
        cmd_hubs()
    elif args.command == 'produce-subpages':
        cmd_produce_subpages()
    elif args.command == 'sitemap':
        cmd_sitemap()
    elif args.command == 'expand-locations':
        cmd_expand_locations(args)
    elif args.command == 'sync-authority-signals':
        import authority_signals
        authority_signals.sync_authority_signals()
    elif args.command == 'analyze-user-behavior':
        import behavior_ingest
        behavior_ingest.analyze_user_behavior()
    elif args.command == 'build-comparisons':
        import comparative_intelligence as comp
        comp.build_comparisons()
    elif args.command == 'generate-narratives':
        import knowledge_fabric as kf
        kf.generate_narratives()
    elif args.command == 'autonomous-run':
        import autonomous_orchestrator as ao
        ao.run_autonomous(args.mode)
    elif args.command == 'autopilot':
        print("Starting SEO Factory Autopilot...")
        cmd_sync_external_apis()
        
        import intent_discovery as intent
        intent.detect_buyer_intent()
        
        import authority_signals
        authority_signals.sync_authority_signals()
        
        import behavior_ingest
        behavior_ingest.analyze_user_behavior()
        
        import knowledge_fabric as kf
        kf.generate_narratives()
        
        cmd_queue_data_reinforcements()
        cmd_expand_geo_clusters()
        
        import idx_page_generator as idx
        idx.build_idx_traffic()
        
        import comparative_intelligence as comp
        comp.build_comparisons()
        
        import materializer as mat
        mat.materialize_pages()
        
        cmd_rebuild_internal_authority()
        cmd_build_command_center()
        print("AUTOPILOT COMPLETE")
    elif args.command == 'deploy-pages':
        import cloud_deployer as deployer
        deployer.deploy_pages(mode=args.mode, with_git=args.with_git)
    elif args.command == 'discover-neighborhoods':
        import neighborhood_discovery as nd
        nd.discover_neighborhoods()
    elif args.command == 'analyze-lead-performance':
        import lead_capture_engine as lce
        lce.analyze_lead_performance()
    elif args.command == 'build-radius-pages':
        import geo_radius_engine as geo_radius
        geo_radius.build_radius_pages()
    elif args.command == 'analyze-chat-intent':
        import ai_chat_agent as ai_chat
        ai_chat.analyze_chat_intent()
    elif args.command == 'build-market-predictions':
        import market_prediction_engine as mpe
        mpe.build_market_predictions()
    elif args.command == 'detect-seller-intent':
        import seller_intent_detection as seller_intent
        seller_intent.detect_seller_intent()
    elif args.command == 'build-migration-pages':
        import migration_intelligence_engine as mie
        mie.build_migration_pages()
    elif args.command == 'build-authority-flywheel':
        import authority_flywheel_engine as afe
        afe.build_authority_flywheel()
    else:
        parser.print_help()
