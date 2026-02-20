import csv
import re

# Read the NY hospitals file to get the order and names
ny_hospitals = []
seen_ny_hospitals = set()  # Track NY hospitals we've already added

with open('collected-data/ny_hospitals.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        hospital_name = row['Hospital Name']
        # Only add if we haven't seen this hospital name before
        if hospital_name not in seen_ny_hospitals:
            ny_hospitals.append({'name': hospital_name})
            seen_ny_hospitals.add(hospital_name)

# Read the large national CSV file
national_data = {}
seen_facilities = set()  # Track by facility ID to prevent duplicates

with open('data/FY_2025_HAC_Reduction_Program_Hospital.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        # Only keep NY state hospitals
        if row['State'] == 'NY':
            facility_id = row.get('Facility ID', '')
            facility_name = row['Facility Name']
            
            # Use Facility ID as the primary unique key
            # If no ID, fall back to name
            unique_key = facility_id if facility_id else facility_name
            
            # Only store first occurrence of each unique facility
            if unique_key not in seen_facilities:
                national_data[facility_name] = row
                seen_facilities.add(unique_key)

# Add new column to fieldnames
fieldnames_with_flag = ['In 219 List'] + list(fieldnames)

# Function to normalize strings for comparison
def normalize(text):
    # Remove punctuation, extra spaces, convert to uppercase
    text = re.sub(r'[^\w\s]', '', text.upper())
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Function to find best match between hospitals
def find_match(ny_hospital, national_data):
    ny_name_norm = normalize(ny_hospital['name'])
    
    best_match = None
    best_score = 0
    
    for nat_name in national_data.keys():
        nat_name_norm = normalize(nat_name)
        score = 0
        
        # Check name match
        if ny_name_norm == nat_name_norm:
            score += 10  # Exact name match
        elif ny_name_norm in nat_name_norm or nat_name_norm in ny_name_norm:
            score += 7  # Partial name match
        else:
            # Check for key words in hospital name (handles abbreviations like SJRH)
            ny_words = set(ny_name_norm.split())
            nat_words = set(nat_name_norm.split())
            common_words = ny_words & nat_words
            
            # Filter out generic words
            generic_words = {'HOSPITAL', 'MEDICAL', 'CENTER', 'HEALTH', 'SYSTEM', 'THE'}
            significant_common_words = common_words - generic_words
            
            # If they share significant words, give partial credit
            if len(significant_common_words) >= 2:
                score += 5
            elif len(significant_common_words) >= 1:
                score += 3
        
        # If we have at least a reasonable match, consider it
        if score >= 5 and score > best_score:
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
        # Add single row for this hospital
        row_with_flag = {'In 219 List': 'YES'}
        row_with_flag.update(national_data[match])
        matched_rows.append(row_with_flag)
        matched_facilities.add(match)
        print(f"✓ Matched (score {score}): {ny_hospital['name']} → {match}")
    else:
        # Add an empty row with just the hospital info to show the gap
        empty_row = {'In 219 List': 'YES (NOT IN NATIONAL DATA)'}
        for field in fieldnames:
            empty_row[field] = ''
        empty_row['Facility Name'] = ny_hospital['name']
        empty_row['State'] = 'NY'
        not_found_rows.append(empty_row)
        print(f"✗ Not found: {ny_hospital['name']}")

# Collect additional hospitals from national data that weren't in ny_hospitals.csv
additional_rows = []
print("\n--- Additional hospitals from national data not in ny_hospitals.csv ---")
for facility_name, row in national_data.items():
    if facility_name not in matched_facilities:
        row_with_flag = {'In 219 List': 'NO'}
        row_with_flag.update(row)
        additional_rows.append(row_with_flag)
        print(f"+ Added: {facility_name}")

# Sort not found rows alphabetically by facility name
not_found_rows.sort(key=lambda x: x['Facility Name'])

# Sort additional rows alphabetically by facility name
additional_rows.sort(key=lambda x: x['Facility Name'])

# Combine all rows: matched (in order) + not found (alphabetical) + additional (alphabetical)
output_rows = matched_rows + not_found_rows + additional_rows

# Write the output CSV
with open('collected-data/nys_LQTP_HACRP.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames_with_flag)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\n{'='*60}")
print(f"Successfully created nys_LQTP_HACRP.csv")
print(f"Total rows: {len(output_rows)}")
print(f"Hospitals matched (in 219 list, found in national data): {len(matched_facilities)}")
print(f"Hospitals in 219 list but not found in national data: {len(not_found_rows)}")
print(f"Additional NY hospitals from national data (not in 219 list): {len(additional_rows)}")