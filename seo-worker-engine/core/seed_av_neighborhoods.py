import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import seo_factory as sf

def seed_av_neighborhoods():
    print("🌱 Seeding Antelope Valley Neighborhood Profile Angles...")

    creds = service_account.Credentials.from_service_account_file(
        sf.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    av_neighborhoods = [
        # Palmdale - Rancho Vista Cluster
        ["Rancho Vista", "Palmdale", "Rancho Vista Palmdale Neighborhood Guide", "overview", "Week 1"],
        ["Rancho Vista", "Palmdale", "Rancho Vista Palmdale Homes Near Schools", "family_friendly", "Week 1"],
        ["Rancho Vista", "Palmdale", "Rancho Vista Palmdale Family-Friendly Living", "family_friendly", "Week 1"],
        # Palmdale - Ana Verde Cluster
        ["Ana Verde", "Palmdale", "Ana Verde Palmdale New Construction Homes", "newer_homes", "Week 1"],
        ["Ana Verde", "Palmdale", "Ana Verde Palmdale Modern Neighborhood Overview", "overview", "Week 1"],
        ["Ana Verde", "Palmdale", "Ana Verde Palmdale Homes for Move-Up Buyers", "move_up_buyers", "Week 1"],
        # Palmdale - West Palmdale
        ["West Palmdale", "Palmdale", "West Palmdale Neighborhood Guide", "overview", "Week 1"],
        ["West Palmdale", "Palmdale", "West Palmdale Homes Under $600K", "affordability", "Week 1"],
        ["West Palmdale", "Palmdale", "West Palmdale Commuter-Friendly Areas", "commuter_friendly", "Week 1"],
        # Palmdale - East Palmdale
        ["East Palmdale", "Palmdale", "East Palmdale Affordable Housing Options", "affordability", "Week 1"],
        ["East Palmdale", "Palmdale", "East Palmdale First-Time Buyer Neighborhoods", "first_time_buyer", "Week 1"],
        ["East Palmdale", "Palmdale", "East Palmdale Homes With Larger Lots", "land_spacing", "Week 1"],
        # Palmdale - Lake Los Angeles
        ["Lake Los Angeles", "Palmdale", "Lake Los Angeles Neighborhood Guide", "overview", "Week 1"],
        ["Lake Los Angeles", "Palmdale", "Lake Los Angeles Affordable Homes", "affordability", "Week 1"],
        ["Lake Los Angeles", "Palmdale", "Lake Los Angeles Homes With Land", "land_spacing", "Week 1"],
        # Palmdale - Sun Village
        ["Sun Village", "Palmdale", "Sun Village Affordable Homes", "affordability", "Week 1"],
        ["Sun Village", "Palmdale", "Sun Village Rural Living Near Palmdale", "rural_lifestyle", "Week 1"],
        # Palmdale - Littlerock
        ["Littlerock", "Palmdale", "Littlerock Ranch-Style Living Guide", "rural_lifestyle", "Week 1"],
        ["Littlerock", "Palmdale", "Littlerock Homes With Acreage", "land_spacing", "Week 1"],

        # Lancaster - West Lancaster
        ["West Lancaster", "Lancaster", "West Lancaster Neighborhood Guide", "overview", "Week 2"],
        ["West Lancaster", "Lancaster", "West Lancaster Homes Near Parks", "parks_recreation", "Week 2"],
        ["West Lancaster", "Lancaster", "West Lancaster Family Neighborhoods", "family_friendly", "Week 2"],
        # Lancaster - East Lancaster
        ["East Lancaster", "Lancaster", "East Lancaster Affordable Homes", "affordability", "Week 2"],
        ["East Lancaster", "Lancaster", "East Lancaster First-Time Buyer Areas", "first_time_buyer", "Week 2"],
        # Lancaster - Quartz Hill Area
        ["Quartz Hill", "Lancaster", "Quartz Hill Neighborhood Guide", "overview", "Week 2"],
        ["Quartz Hill", "Lancaster", "Quartz Hill Small-Town Living", "small_town", "Week 2"],
        ["Quartz Hill", "Lancaster", "Quartz Hill Family-Friendly Communities", "family_friendly", "Week 2"],
        # Lancaster - Antelope Acres
        ["Antelope Acres", "Lancaster", "Antelope Acres Homes With Land", "land_spacing", "Week 2"],
        ["Antelope Acres", "Lancaster", "Antelope Acres Rural Living Guide", "rural_lifestyle", "Week 2"],
        # Lancaster - Del Sur
        ["Del Sur", "Lancaster", "Del Sur Lancaster Rural Property Guide", "rural_lifestyle", "Week 2"],

        # Quartz Hill
        ["Quartz Hill", "Quartz Hill", "Quartz Hill Real Estate Overview", "overview", "Week 3"],
        ["Quartz Hill", "Quartz Hill", "Quartz Hill Best Neighborhoods for Families", "family_friendly", "Week 3"],
        ["Quartz Hill", "Quartz Hill", "Quartz Hill Homes With Larger Lots", "land_spacing", "Week 3"],
        ["Quartz Hill", "Quartz Hill", "Quartz Hill Community Living Guide", "community_feel", "Week 3"],

        # Rosamond
        ["Rosamond", "Rosamond", "Rosamond Neighborhood Guide", "overview", "Week 3"],
        ["Rosamond", "Rosamond", "Rosamond Affordable Homes", "affordability", "Week 3"],
        ["Rosamond", "Rosamond", "Rosamond Homes With Land", "land_spacing", "Week 3"],
        ["Rosamond", "Rosamond", "Rosamond Rural Desert Living", "rural_lifestyle", "Week 3"],

        # Acton Area
        ["Acton", "Acton", "Acton Real Estate Guide", "overview", "Week 3"],
        ["Acton", "Acton", "Acton Horse Property Communities", "horse_property", "Week 3"],
        ["Acton", "Acton", "Acton Luxury Ranch Homes", "luxury_ranch", "Week 3"],

        # Littlerock / Pearblossom
        ["Pearblossom", "Pearblossom", "Pearblossom Highway Communities Guide", "rural_lifestyle", "Week 3"],
        ["Littlerock", "Littlerock", "Littlerock Horse Property Neighborhoods", "horse_property", "Week 3"],

        # Lifestyle / Special Property Clusters
        ["Antelope Valley", "Region", "Best Antelope Valley Neighborhoods for Families", "family_friendly", "Week 4"],
        ["Antelope Valley", "Region", "Most Affordable Neighborhoods in the Antelope Valley", "affordability", "Week 4"],
        ["Antelope Valley", "Region", "Antelope Valley Neighborhoods With Large Lots", "land_spacing", "Week 4"],
        ["Antelope Valley", "Region", "Best Commuter Neighborhoods Near Los Angeles", "commuter_friendly", "Week 4"],

        # Emerging / Future Development Areas
        ["Palmdale", "Palmdale", "New Construction Communities in Palmdale", "newer_homes", "Week 4"],
        ["Lancaster", "Lancaster", "New Housing Developments in Lancaster", "newer_homes", "Week 4"],
        ["Antelope Valley", "Region", "Growing Neighborhoods in the Antelope Valley", "growth_investment", "Week 4"]
    ]

    angles = []
    
    # Process the angles
    for hood, city, title, intent, publishing_week in av_neighborhoods:
        slug = sf.get_slug(title)
        
        # Determine intent groupings dynamically
        primary_angle = intent
        secondary_angle = "overview"
        if intent == "affordability":
            secondary_angle = "first_time_buyer"
        elif intent == "family_friendly":
            secondary_angle = "schools"
        elif intent == "land_spacing":
            secondary_angle = "rural_lifestyle"
            
        angles.append([
            hood, city, primary_angle, secondary_angle, "buyer_discovery", slug, "High", publishing_week
        ])
        
    # Push the Angles to the Sheet
    if angles:
        # We're appending a 'Publishing_Week' column just for tracking the rollout
        headers = [['Neighborhood', 'City', 'Primary_Angle', 'Secondary_Angle', 'Intent_Type', 'Slug', 'Priority', 'Publishing_Week']]
        service.spreadsheets().values().update(
            spreadsheetId=sf.SPREADSHEET_ID, range="'Neighborhood_Angles'!A1", 
            valueInputOption='RAW', body={'values': headers + angles}
        ).execute()

    print(f"✅ Successfully seeded 50 Differentiated Antelope Valley Neighborhood Angles across a 4-Week Rollout schedule.")
