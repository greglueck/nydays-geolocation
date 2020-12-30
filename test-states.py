import openpyxl
import reverse_geocoder as rg
import time


def main():
  # This CSV file contains one latitude / longitude coordinate in each US
  # state and territory.
  states = []
  coords = []
  with open('states.csv') as f:
    for line in f:
      (state, abbrev, lat, lon) = line.split(',', 3)
      states.append(abbrev)
      coords.append((lat, lon))

  # Call the reverse-geocoder service on each coordinate to see what it
  # returns.
  reverse = rg.search(coords)

  # Print the mapping from the state name returned by the reverse geocoding
  # service to the 2-letter USPS state abbreviation.  The printed output can
  # be cut-and-pasted as Python source to initialize a dictionary that
  # performs this mapping.
  for state, rec in zip(states, reverse):
    geoCountry = rec['cc']
    geoState = rec['admin1']
    if geoCountry == 'US':
      print(f"'{geoState}': '{state}',")

if __name__=="__main__":
  main()
