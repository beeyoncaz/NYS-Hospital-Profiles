import csv
import re

# Read the NY hospitals file to get the list and order
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

def normalize(text):
    text = re.sub(r'[^\w\s]', '', text.upper())
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone)
    return digits[-10:] if len(digits) >= 10 else digits

def normalize_address(address):
    norm = normalize(address)
    replacements = {
        'STREET': 'ST', 'AVENUE': 'AVE', 'ROAD': 'RD', 'DRIVE': 'DR',
        'BOULEVARD': 'BLVD', 'LANE': 'LN', 'COURT': 'CT', 'PLACE': 'PL',
        'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W',
        'PARKWAY': 'PKWY', 'HIGHWAY': 'HWY', 'CIRCLE': 'CIR'
    }
    for long_form, short_form in replacements.items():
        norm = norm.replace(long_form, short_form)
    return norm

def extract_street_name(address):
    norm = normalize_address(address)
    street_only = re.sub(r'^\d+\s*', '', norm)
    return street_only

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
        
        if ny_phone_norm and nat_phone_norm and ny_phone_norm == nat_phone_norm:
            score += 15
        elif ny_phone_norm and nat_phone_norm and len(ny_phone_norm) >= 7 and len(nat_phone_norm) >= 7:
            if ny_phone_norm[-7:] == nat_phone_norm[-7:]:
                score += 10
        
        if ny_name_norm == nat_name_norm:
            score += 10
        elif ny_name_norm in nat_name_norm or nat_name_norm in ny_name_norm:
            score += 5
        else:
            ny_words = set(ny_name_norm.split())
            nat_words = set(nat_name_norm.split())
            common_words = ny_words & nat_words
            if len(common_words) >= 2:
                score += 4
            elif len(common_words) >= 1 and ('HOSPITAL' not in common_words and 'MEDICAL' not in common_words and 'CENTER' not in common_words):
                score += 2
        
        if ny_address_norm == nat_address_norm:
            score += 10
        elif ny_street_name and nat_street_name and ny_street_name == nat_street_name:
            score += 7
        elif ny_address_norm in nat_address_norm or nat_address_norm in ny_address_norm:
            score += 5
        
        if ny_city_norm == nat_city_norm:
            score += 5
        
        if ny_street_name and nat_street_name and ny_street_name == nat_street_name and ny_city_norm == nat_city_norm:
            score += 3
        
        if score >= 8 and score > best_score:
            best_score = score
            best_match = nat_name
    
    return best_match, best_score

# Read the new national CSV and filter rows
national_data = {}
filtered_rows = []

with open('data/HCAHPS-Hospital.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    
    for row in reader:
        # Only keep NY state hospitals
        if row['State'] != 'NY':
            continue
        
        measure_id = row['HCAHPS Measure ID']
        
        # Keep only star ratings OR first instance (typically _A_P or _Y_P)
        if measure_id.endswith('_STAR_RATING') or \
           measure_id.endswith('_A_P') or \
           measure_id.endswith('_Y_P') or \
           measure_id.endswith('_PY') or \
           measure_id.endswith('_9_10') or \
           (measure_id.endswith('_A') and not measure_id.endswith('_SA')) or \
           measure_id.endswith('_LINEAR_SCORE') or \
           measure_id == 'H_STAR_RATING':
            
            facility_name = row['Facility Name']
            
            # Track facility info for matching
            if facility_name not in national_data:
                national_data[facility_name] = {
                    'address': row['Address'],
                    'city': row['City/Town'],
                    'phone': row['Telephone Number']
                }
            
            filtered_rows.append(row)

print(f"Filtered to {len(filtered_rows)} rows from original data")

# Add new column to fieldnames
fieldnames_with_flag = ['In 219 List'] + list(fieldnames)

# Build the output
matched_rows = []
not_found_rows = []
matched_facilities = set()

# Go through NY hospitals in order
for ny_hospital in ny_hospitals:
    match, score = find_match(ny_hospital, national_data)
    
    if match:
        for row in filtered_rows:
            if row['Facility Name'] == match:
                row_with_flag = {'In 219 List': 'YES'}
                row_with_flag.update(row)
                matched_rows.append(row_with_flag)
        matched_facilities.add(match)
        print(f"✓ Matched (score {score}): {ny_hospital['name']} → {match}")
    else:
        empty_row = {'In 219 List': 'YES (NOT IN NATIONAL DATA)'}
        for field in fieldnames:
            empty_row[field] = ''
        empty_row['Facility Name'] = ny_hospital['name']
        empty_row['Address'] = ny_hospital['address']
        empty_row['City/Town'] = ny_hospital['city']
        empty_row['State'] = 'NY'
        empty_row['Telephone Number'] = ny_hospital['phone']
        not_found_rows.append(empty_row)
        print(f"✗ Not found: {ny_hospital['name']}")

# Collect additional hospitals
additional_rows = []
print("\n--- Additional hospitals ---")
added_facilities = set()
for row in filtered_rows:
    facility_name = row['Facility Name']
    if facility_name not in matched_facilities:
        row_with_flag = {'In 219 List': 'NO'}
        row_with_flag.update(row)
        additional_rows.append(row_with_flag)
        if facility_name not in added_facilities:
            print(f"+ Added: {facility_name}")
            added_facilities.add(facility_name)

# Sort
not_found_rows.sort(key=lambda x: x['Facility Name'])
additional_rows.sort(key=lambda x: x['Facility Name'])

# Combine
output_rows = matched_rows + not_found_rows + additional_rows

# Write output
with open('collected-data/nys_hcahps.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames_with_flag)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\n{'='*60}")
print(f"Successfully created nys_hcahps.csv")
print(f"Total rows: {len(output_rows)}")
print(f"Matched hospitals from 219 list: {len(matched_facilities)}")
print(f"Not found from 219 list: {len(not_found_rows)}")
print(f"Additional hospitals: {len(added_facilities)}")