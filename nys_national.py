import csv
import re

# Read the NY hospitals file to get the order and names
ny_hospitals = []
with open('collected-data/ny_hospitals.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ny_hospitals.append({
            'name': row['Hospital Name'],
            'address': row['Street Address'],
            'city': row.get('City, State, ZIP', '').split(',')[0].strip() if row.get('City, State, ZIP') else '',
            'phone': row.get('Phone', '')
        })

# Read the large national CSV file
national_data = {}
with open('data/Unplanned_Hospital_Visits-Hospital.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        # Only keep NY state hospitals
        if row['State'] == 'NY':
            facility_name = row['Facility Name']
            # Store all rows for this facility (there might be multiple rows per hospital)
            if facility_name not in national_data:
                national_data[facility_name] = {
                    'rows': [],
                    'address': row['Address'],
                    'city': row['City/Town'],
                    'phone': row.get('Telephone Number', '')
                }
            national_data[facility_name]['rows'].append(row)

# Add new column to fieldnames
fieldnames_with_flag = ['In 219 List'] + list(fieldnames)

# Function to normalize strings for comparison
def normalize(text):
    # Remove punctuation, extra spaces, convert to uppercase
    text = re.sub(r'[^\w\s]', '', text.upper())
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Function to normalize phone number (extract just digits)
def normalize_phone(phone):
    # Extract only digits
    digits = re.sub(r'\D', '', phone)
    # Return last 10 digits (remove country code if present)
    return digits[-10:] if len(digits) >= 10 else digits

# Function to extract street name (without number)
def extract_street_name(address):
    norm = normalize_address(address)
    # Remove leading numbers
    street_only = re.sub(r'^\d+\s*', '', norm)
    return street_only

# Function to normalize address
def normalize_address(address):
    norm = normalize(address)
    # Replace common abbreviations
    replacements = {
        'STREET': 'ST', 'AVENUE': 'AVE', 'ROAD': 'RD', 'DRIVE': 'DR',
        'BOULEVARD': 'BLVD', 'LANE': 'LN', 'COURT': 'CT', 'PLACE': 'PL',
        'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W',
        'PARKWAY': 'PKWY', 'HIGHWAY': 'HWY', 'CIRCLE': 'CIR'
    }
    for long_form, short_form in replacements.items():
        norm = norm.replace(long_form, short_form)
    return norm

# Function to find best match between hospitals
def find_match(ny_hospital, national_data):
    ny_name_norm = normalize(ny_hospital['name'])
    ny_address_norm = normalize_address(ny_hospital['address'])
    ny_street_name = extract_street_name(ny_hospital['address'])
    ny_city_norm = normalize(ny_hospital['city'])
    ny_phone_norm = normalize_phone(ny_hospital['phone'])
    
    best_match = None
    best_score = 0
    
    for nat_name, nat_info in national_data.items():
        nat_name_norm = normalize(nat_name)
        nat_address_norm = normalize_address(nat_info['address'])
        nat_street_name = extract_street_name(nat_info['address'])
        nat_city_norm = normalize(nat_info['city'])
        nat_phone_norm = normalize_phone(nat_info['phone'])
        
        score = 0
        
        # Check phone number match - this is very reliable!
        if ny_phone_norm and nat_phone_norm and ny_phone_norm == nat_phone_norm:
            score += 15  # Phone match is strong evidence
        elif ny_phone_norm and nat_phone_norm and len(ny_phone_norm) >= 7 and len(nat_phone_norm) >= 7:
            # Check if last 7 digits match (area code might differ)
            if ny_phone_norm[-7:] == nat_phone_norm[-7:]:
                score += 10
        
        # Check name match
        if ny_name_norm == nat_name_norm:
            score += 10  # Exact name match
        elif ny_name_norm in nat_name_norm or nat_name_norm in ny_name_norm:
            score += 5  # Partial name match
        else:
            # Check for key words in hospital name (handles abbreviations like SJRH)
            ny_words = set(ny_name_norm.split())
            nat_words = set(nat_name_norm.split())
            common_words = ny_words & nat_words
            # If they share significant words, give partial credit
            if len(common_words) >= 2:
                score += 4
            elif len(common_words) >= 1 and ('HOSPITAL' in common_words or 'MEDICAL' in common_words or 'CENTER' in common_words):
                # Don't count generic words alone
                pass
            elif len(common_words) >= 1:
                score += 2
        
        # Check address match
        if ny_address_norm == nat_address_norm:
            score += 10  # Exact address match
        elif ny_street_name and nat_street_name and ny_street_name == nat_street_name:
            score += 7  # Same street name (different numbers OK)
        elif ny_address_norm in nat_address_norm or nat_address_norm in ny_address_norm:
            score += 5  # Partial address match
        
        # Check city match
        if ny_city_norm == nat_city_norm:
            score += 5  # City match
        
        # If we have street name + city match, that's pretty strong even without name match
        if ny_street_name and nat_street_name and ny_street_name == nat_street_name and ny_city_norm == nat_city_norm:
            score += 3  # Bonus for street + city combo
        
        # If we have at least a reasonable match, consider it
        if score >= 8 and score > best_score:
            best_score = score
            best_match = nat_name
    
    return best_match, best_score

# Build the output
matched_rows = []
not_found_rows = []
matched_facilities = set()

# First, go through NY hospitals in order
for ny_hospital in ny_hospitals:
    match, score = find_match(ny_hospital, national_data)
    
    if match:
        # Add all rows for this hospital
        for row in national_data[match]['rows']:
            row_with_flag = {'In 219 List': 'YES'}
            row_with_flag.update(row)
            matched_rows.append(row_with_flag)
        matched_facilities.add(match)
        print(f"✓ Matched (score {score}): {ny_hospital['name']} → {match}")
    else:
        # Add an empty row with just the hospital info to show the gap
        empty_row = {'In 219 List': 'YES (NOT IN NATIONAL DATA)'}
        for field in fieldnames:
            empty_row[field] = ''
        empty_row['Facility Name'] = ny_hospital['name']
        empty_row['Address'] = ny_hospital['address']
        empty_row['City/Town'] = ny_hospital['city']
        empty_row['State'] = 'NY'
        empty_row['Telephone Number'] = ny_hospital['phone']
        not_found_rows.append(empty_row)
        print(f"✗ Not found: {ny_hospital['name']} at {ny_hospital['address']}, phone: {ny_hospital['phone']}")

# Collect additional hospitals from national data that weren't in ny_hospitals.csv
additional_rows = []
print("\n--- Additional hospitals from national data not in ny_hospitals.csv ---")
for facility_name, facility_info in national_data.items():
    if facility_name not in matched_facilities:
        for row in facility_info['rows']:
            row_with_flag = {'In 219 List': 'NO'}
            row_with_flag.update(row)
            additional_rows.append(row_with_flag)
        print(f"+ Added: {facility_name} at {facility_info['address']}")

# Sort not found rows alphabetically by facility name
not_found_rows.sort(key=lambda x: x['Facility Name'])

# Sort additional rows alphabetically by facility name
additional_rows.sort(key=lambda x: x['Facility Name'])

# Combine all rows: matched (in order) + not found (alphabetical) + additional (alphabetical)
output_rows = matched_rows + not_found_rows + additional_rows

# Write the output CSV
with open('collected-data/nys_unplannedhospitalvisits.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames_with_flag)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\n{'='*60}")
print(f"Successfully created nys_hai.csv")
print(f"Total rows: {len(output_rows)}")
print(f"Hospitals matched (in 219 list, found in national data): {len(matched_facilities)}")
print(f"Hospitals in 219 list but not found in national data: {len(not_found_rows)}")
print(f"Additional NY hospitals from national data (not in 219 list): {len(set(r['Facility Name'] for r in additional_rows))}")