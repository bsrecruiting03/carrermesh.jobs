"""
Location Ontology Database Migration

Creates the locations and location_aliases tables for production-grade location handling.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5433/job_board")


def create_tables():
    """Create locations and location_aliases tables."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Create locations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,  -- country, state, city
            parent_id INTEGER REFERENCES locations(id),
            iso_code VARCHAR(20),
            latitude DECIMAL(10, 8),
            longitude DECIMAL(11, 8),
            job_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_locations_parent ON locations(parent_id);
        CREATE INDEX IF NOT EXISTS idx_locations_type ON locations(type);
        CREATE INDEX IF NOT EXISTS idx_locations_iso ON locations(iso_code);
    """)
    
    # Create location_aliases table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS location_aliases (
            id SERIAL PRIMARY KEY,
            location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
            alias VARCHAR(255) NOT NULL,
            language VARCHAR(10) DEFAULT 'en',
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_location_aliases_alias ON location_aliases(LOWER(alias));
        CREATE INDEX IF NOT EXISTS idx_location_aliases_location ON location_aliases(location_id);
    """)
    
    # Add location_id to jobs table if not exists
    cur.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'jobs' AND column_name = 'location_id'
            ) THEN
                ALTER TABLE jobs ADD COLUMN location_id INTEGER REFERENCES locations(id);
                CREATE INDEX idx_jobs_location_id ON jobs(location_id);
            END IF;
        END $$;
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Tables created successfully!")


def insert_countries():
    """Insert country data with aliases."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    countries = [
        # (name, iso_code, aliases with priority)
        ("USA", "US", [
            ("USA", 10), ("United States", 9), ("United States of America", 8),
            ("U.S.", 7), ("U.S.A.", 6), ("America", 5), ("US", 4)
        ]),
        ("Canada", "CA", [
            ("Canada", 10), ("CA", 5)
        ]),
        ("India", "IN", [
            ("India", 10), ("IN", 5), ("Bharat", 4)
        ]),
        ("United Kingdom", "GB", [
            ("UK", 10), ("United Kingdom", 9), ("Great Britain", 8),
            ("Britain", 7), ("England", 6), ("GB", 5)
        ]),
        ("Germany", "DE", [
            ("Germany", 10), ("DE", 5), ("Deutschland", 4)
        ]),
        ("France", "FR", [
            ("France", 10), ("FR", 5)
        ]),
        ("Australia", "AU", [
            ("Australia", 10), ("AU", 5), ("Aus", 4)
        ]),
        ("Singapore", "SG", [
            ("Singapore", 10), ("SG", 5)
        ]),
        ("Ireland", "IE", [
            ("Ireland", 10), ("IE", 5), ("Eire", 4)
        ]),
        ("Netherlands", "NL", [
            ("Netherlands", 10), ("NL", 5), ("Holland", 4)
        ]),
        ("Sweden", "SE", [
            ("Sweden", 10), ("SE", 5), ("Sverige", 4)
        ]),
        ("Japan", "JP", [
            ("Japan", 10), ("JP", 5), ("Nippon", 4)
        ]),
    ]
    
    for name, iso_code, aliases in countries:
        # Check if already exists
        cur.execute("SELECT id FROM locations WHERE iso_code = %s AND type = 'country'", (iso_code,))
        row = cur.fetchone()
        
        if row:
            location_id = row[0]
            logger.info(f"Country {name} already exists with id {location_id}")
        else:
            cur.execute("""
                INSERT INTO locations (name, type, iso_code)
                VALUES (%s, 'country', %s)
                RETURNING id
            """, (name, iso_code))
            location_id = cur.fetchone()[0]
            logger.info(f"Inserted country: {name} (id={location_id})")
        
        # Insert aliases
        for alias, priority in aliases:
            cur.execute("""
                INSERT INTO location_aliases (location_id, alias, priority)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (location_id, alias, priority))
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Countries inserted!")


def insert_us_states():
    """Insert US states with aliases."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get USA location_id
    cur.execute("SELECT id FROM locations WHERE iso_code = 'US' AND type = 'country'")
    usa_id = cur.fetchone()[0]
    
    states = [
        ("Alabama", "US-AL", "AL"),
        ("Alaska", "US-AK", "AK"),
        ("Arizona", "US-AZ", "AZ"),
        ("Arkansas", "US-AR", "AR"),
        ("California", "US-CA", "CA"),
        ("Colorado", "US-CO", "CO"),
        ("Connecticut", "US-CT", "CT"),
        ("Delaware", "US-DE", "DE"),
        ("Florida", "US-FL", "FL"),
        ("Georgia", "US-GA", "GA"),
        ("Hawaii", "US-HI", "HI"),
        ("Idaho", "US-ID", "ID"),
        ("Illinois", "US-IL", "IL"),
        ("Indiana", "US-IN", "IN"),
        ("Iowa", "US-IA", "IA"),
        ("Kansas", "US-KS", "KS"),
        ("Kentucky", "US-KY", "KY"),
        ("Louisiana", "US-LA", "LA"),
        ("Maine", "US-ME", "ME"),
        ("Maryland", "US-MD", "MD"),
        ("Massachusetts", "US-MA", "MA"),
        ("Michigan", "US-MI", "MI"),
        ("Minnesota", "US-MN", "MN"),
        ("Mississippi", "US-MS", "MS"),
        ("Missouri", "US-MO", "MO"),
        ("Montana", "US-MT", "MT"),
        ("Nebraska", "US-NE", "NE"),
        ("Nevada", "US-NV", "NV"),
        ("New Hampshire", "US-NH", "NH"),
        ("New Jersey", "US-NJ", "NJ"),
        ("New Mexico", "US-NM", "NM"),
        ("New York", "US-NY", "NY"),
        ("North Carolina", "US-NC", "NC"),
        ("North Dakota", "US-ND", "ND"),
        ("Ohio", "US-OH", "OH"),
        ("Oklahoma", "US-OK", "OK"),
        ("Oregon", "US-OR", "OR"),
        ("Pennsylvania", "US-PA", "PA"),
        ("Rhode Island", "US-RI", "RI"),
        ("South Carolina", "US-SC", "SC"),
        ("South Dakota", "US-SD", "SD"),
        ("Tennessee", "US-TN", "TN"),
        ("Texas", "US-TX", "TX"),
        ("Utah", "US-UT", "UT"),
        ("Vermont", "US-VT", "VT"),
        ("Virginia", "US-VA", "VA"),
        ("Washington", "US-WA", "WA"),
        ("West Virginia", "US-WV", "WV"),
        ("Wisconsin", "US-WI", "WI"),
        ("Wyoming", "US-WY", "WY"),
        # Territories
        ("District of Columbia", "US-DC", "DC"),
        ("Puerto Rico", "US-PR", "PR"),
        ("Guam", "US-GU", "GU"),
        ("Virgin Islands", "US-VI", "VI"),
    ]
    
    for name, iso_code, abbr in states:
        cur.execute("SELECT id FROM locations WHERE iso_code = %s AND type = 'state'", (iso_code,))
        row = cur.fetchone()
        
        if row:
            location_id = row[0]
        else:
            cur.execute("""
                INSERT INTO locations (name, type, parent_id, iso_code)
                VALUES (%s, 'state', %s, %s)
                RETURNING id
            """, (name, usa_id, iso_code))
            location_id = cur.fetchone()[0]
        
        # Insert aliases
        for alias in [name, abbr]:
            cur.execute("""
                INSERT INTO location_aliases (location_id, alias, priority)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (location_id, alias, 10 if alias == name else 5))
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Inserted {len(states)} US states!")


def insert_canada_provinces():
    """Insert Canadian provinces with aliases."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM locations WHERE iso_code = 'CA' AND type = 'country'")
    canada_id = cur.fetchone()[0]
    
    provinces = [
        ("Ontario", "CA-ON", "ON"),
        ("Quebec", "CA-QC", "QC"),
        ("British Columbia", "CA-BC", "BC"),
        ("Alberta", "CA-AB", "AB"),
        ("Manitoba", "CA-MB", "MB"),
        ("Saskatchewan", "CA-SK", "SK"),
        ("Nova Scotia", "CA-NS", "NS"),
        ("New Brunswick", "CA-NB", "NB"),
        ("Newfoundland and Labrador", "CA-NL", "NL"),
        ("Prince Edward Island", "CA-PE", "PE"),
        ("Northwest Territories", "CA-NT", "NT"),
        ("Yukon", "CA-YT", "YT"),
        ("Nunavut", "CA-NU", "NU"),
    ]
    
    for name, iso_code, abbr in provinces:
        cur.execute("SELECT id FROM locations WHERE iso_code = %s", (iso_code,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO locations (name, type, parent_id, iso_code)
                VALUES (%s, 'state', %s, %s)
                RETURNING id
            """, (name, canada_id, iso_code))
            location_id = cur.fetchone()[0]
            
            for alias in [name, abbr]:
                cur.execute("""
                    INSERT INTO location_aliases (location_id, alias, priority)
                    VALUES (%s, %s, %s)
                """, (location_id, alias, 10 if alias == name else 5))
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Inserted Canadian provinces!")


def insert_india_states():
    """Insert Indian states and territories."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM locations WHERE iso_code = 'IN' AND type = 'country'")
    india_id = cur.fetchone()[0]
    
    states = [
        ("Andhra Pradesh", "IN-AP"),
        ("Arunachal Pradesh", "IN-AR"),
        ("Assam", "IN-AS"),
        ("Bihar", "IN-BR"),
        ("Chhattisgarh", "IN-CT"),
        ("Goa", "IN-GA"),
        ("Gujarat", "IN-GJ"),
        ("Haryana", "IN-HR"),
        ("Himachal Pradesh", "IN-HP"),
        ("Jharkhand", "IN-JH"),
        ("Karnataka", "IN-KA"),
        ("Kerala", "IN-KL"),
        ("Madhya Pradesh", "IN-MP"),
        ("Maharashtra", "IN-MH"),
        ("Manipur", "IN-MN"),
        ("Meghalaya", "IN-ML"),
        ("Mizoram", "IN-MZ"),
        ("Nagaland", "IN-NL"),
        ("Odisha", "IN-OR"),
        ("Punjab", "IN-PB"),
        ("Rajasthan", "IN-RJ"),
        ("Sikkim", "IN-SK"),
        ("Tamil Nadu", "IN-TN"),
        ("Telangana", "IN-TG"),
        ("Tripura", "IN-TR"),
        ("Uttar Pradesh", "IN-UP"),
        ("Uttarakhand", "IN-UT"),
        ("West Bengal", "IN-WB"),
        # Union Territories
        ("Delhi", "IN-DL"),
        ("Chandigarh", "IN-CH"),
        ("Puducherry", "IN-PY"),
    ]
    
    for name, iso_code in states:
        cur.execute("SELECT id FROM locations WHERE iso_code = %s", (iso_code,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO locations (name, type, parent_id, iso_code)
                VALUES (%s, 'state', %s, %s)
                RETURNING id
            """, (name, india_id, iso_code))
            location_id = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO location_aliases (location_id, alias, priority)
                VALUES (%s, %s, 10)
            """, (location_id, name))
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Inserted Indian states!")


def insert_uk_regions():
    """Insert UK regions."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM locations WHERE iso_code = 'GB' AND type = 'country'")
    uk_id = cur.fetchone()[0]
    
    regions = [
        ("England", "GB-ENG"),
        ("Scotland", "GB-SCT"),
        ("Wales", "GB-WLS"),
        ("Northern Ireland", "GB-NIR"),
    ]
    
    for name, iso_code in regions:
        cur.execute("SELECT id FROM locations WHERE iso_code = %s", (iso_code,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO locations (name, type, parent_id, iso_code)
                VALUES (%s, 'state', %s, %s)
                RETURNING id
            """, (name, uk_id, iso_code))
            location_id = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO location_aliases (location_id, alias, priority)
                VALUES (%s, %s, 10)
            """, (location_id, name))
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Inserted UK regions!")


def insert_major_cities():
    """Insert major global cities with aliases and parent relationships."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cities = [
        # (city_name, parent_state/country, type, aliases)
        ("New York City", "New York", "city", ["NYC", "New York", "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]),
        ("San Francisco", "California", "city", ["SF", "San Fran", "Bay Area"]),
        ("Seattle", "Washington", "city", ["Seattle, WA"]),
        ("Austin", "Texas", "city", ["Austin, TX"]),
        ("Boston", "Massachusetts", "city", ["Boston, MA"]),
        ("Chicago", "Illinois", "city", ["Chicago, IL"]),
        ("Los Angeles", "California", "city", ["LA", "L.A.", "Los Angeles, CA"]),
        ("Atlanta", "Georgia", "city", ["Atlanta, GA"]),
        ("Denver", "Colorado", "city", ["Denver, CO"]),
        ("San Jose", "California", "city", ["San Jose, CA", "Silicon Valley"]),
        ("Toronto", "Ontario", "city", ["Toronto, ON", "GTA"]),
        ("Vancouver", "British Columbia", "city", ["Vancouver, BC"]),
        ("London", "United Kingdom", "city", ["Greater London", "London, UK"]),
        ("Berlin", "Germany", "city", ["Berlin, Germany"]),
        ("Munich", "Germany", "city", ["München", "Munich, Germany"]),
        ("Paris", "France", "city", ["Paris, France"]),
        ("Amsterdam", "Netherlands", "city", ["Amsterdam, NL"]),
        ("Singapore", "Singapore", "city", ["Singapore City", "Singapore, SG"]),
        ("Sydney", "Australia", "city", ["Sydney, AU", "Sydney, NSW"]),
        ("Melbourne", "Australia", "city", ["Melbourne, AU", "Melbourne, VIC"]),
        ("Dublin", "Ireland", "city", ["Dublin, IE"]),
        ("Stockholm", "Sweden", "city", ["Stockholm, SE"]),
        ("Tokyo", "Japan", "city", ["Tokyo, JP"]),
        ("Bangalore", "Karnataka", "city", ["Bengaluru", "Bangalore, KA"]),
        ("Mumbai", "Maharashtra", "city", ["Bombay", "Mumbai, MH"]),
        ("Hyderabad", "Telangana", "city", ["Hyderabad, TS", "Hyderabad, TG"]),
        ("Chennai", "Tamil Nadu", "city", ["Madras", "Chennai, TN"]),
        ("Pune", "Maharashtra", "city", ["Pune, MH"]),
        ("Gurgaon", "Haryana", "city", ["Gurugram", "Gurgaon, HR"]),
        ("Noida", "Uttar Pradesh", "city", ["Noida, UP"]),
    ]
    
    for city_name, parent_name, type, aliases in cities:
        # Get parent ID
        # Search state first, then country
        cur.execute("SELECT id FROM locations WHERE (name = %s or iso_code = %s) AND type IN ('state', 'country')", (parent_name, parent_name))
        parent_row = cur.fetchone()
        if not parent_row:
            logger.warning(f"Parent {parent_name} not found for city {city_name}")
            continue
        
        parent_id = parent_row[0]
        
        # Check if exists
        cur.execute("SELECT id FROM locations WHERE name = %s AND type = 'city' AND parent_id = %s", (city_name, parent_id))
        row = cur.fetchone()
        
        if row:
            location_id = row[0]
        else:
            cur.execute("""
                INSERT INTO locations (name, type, parent_id)
                VALUES (%s, 'city', %s)
                RETURNING id
            """, (city_name, parent_id))
            location_id = cur.fetchone()[0]
            logger.info(f"Inserted city: {city_name} (id={location_id})")
        
        # Insert aliases (including city name itself)
        all_aliases = set([city_name] + aliases)
        for alias in all_aliases:
            cur.execute("""
                INSERT INTO location_aliases (location_id, alias, priority)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (location_id, alias, 10 if alias == city_name else 5))
            
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Major cities inserted!")


if __name__ == "__main__":
    print("=== Location Ontology Setup ===")
    print("Step 1: Creating tables...")
    create_tables()
    
    print("Step 2: Inserting countries...")
    insert_countries()
    
    print("Step 3: Inserting US states...")
    insert_us_states()
    
    print("Step 4: Inserting Canadian provinces...")
    insert_canada_provinces()
    
    print("Step 5: Inserting Indian states...")
    insert_india_states()
    
    print("Step 6: Inserting UK regions...")
    insert_uk_regions()
    
    print("Step 7: Inserting major cities...")
    insert_major_cities()
    
    print("\n✅ Location Ontology setup complete!")
