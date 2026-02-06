import requests
from bs4 import BeautifulSoup
import csv

# Fetch the webpage
url = "https://profiles.health.ny.gov/directory/hospitals"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all divs with class "listing"
listings = soup.find_all('div', class_='listing')

hospitals = []

for listing in listings:
    # Get all <p> tags within this listing
    paragraphs = listing.find_all('p')
    
    if len(paragraphs) >= 4:
        # Extract data from each paragraph
        hospital_name = paragraphs[0].get_text().strip()
        street_address = paragraphs[1].get_text().strip()
        city_state_zip = paragraphs[2].get_text().strip()
        phone = paragraphs[3].get_text().replace('Tel:', '').strip()
        
        hospitals.append({
            'Hospital Name': hospital_name,
            'Street Address': street_address,
            'City, State, ZIP': city_state_zip,
            'Phone': phone
        })

# Write to CSV
output_file = 'ny_hospitals.csv'
with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Hospital Name', 'Street Address', 'City, State, ZIP', 'Phone']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for hospital in hospitals:
        writer.writerow(hospital)

print(f"Successfully exported {len(hospitals)} hospitals to {output_file}")