import annotated_json
import argparse
import datetime
import json
import pytz
import requests
import reverse_geocoder as rg
import sys
import time


args = None

def main():
  # Parse command line arguments and read input files.
  parse_args()
  raw = read_raw_file()
  annotated = annotated_json.read(args.annotated)

  # Convert the raw timeline data into a dictionary indexed by the timestamp.
  # Since the raw timeline data is big, delete it in hopes of recovering the
  # memory.
  raw_mapped = map_by_timestamp(raw)
  del raw

  # Check to see if the input annotated data is still consistent with the raw
  # timeline data.  Raise an error if not.
  validate(annotated, raw_mapped)

  # Remove entries from "raw_mapped" which are already in the annotated set.
  trim(annotated, raw_mapped)

  # Reverse geocode all entries from "raw_mapped" to get the containing US
  # state, and add these to the annotated set.  Write out the new annotated
  # file.
  annotate(annotated, raw_mapped)
  annotated_json.write(annotated, args.annotated)


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Create or update annotated geolocation file from Google '
        'timeline.')
  parser.add_argument('-r', '--raw', required=True,
      help='Raw Google timeline input JSON file.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Annotated output JSON file.')
  parser.add_argument('--geocoder', choices=['local', 'osm'],
      help='Reverse geocoding service to use, only if annotated file does '
        'not yet exist.')
  parser.add_argument('--email',
      help='Your email address. Required when using "osm" geocoder.')
  args = parser.parse_args()


def read_raw_file():
  """Read the Google timeline file, and return its data."""
  try:
    with open(args.raw) as f:
      return json.load(f)
  except IOError:
    print(f'ERROR: Input raw timeline file "{args.raw}" does not exist.')
    sys.exit(1)


def map_by_timestamp(raw):
  """
  Translate the raw timeline data into a dictionary whose keys are integer
  timestamps.  Each dictionary entry is another dictionary with the
  coordinates.
  """
  mapped = {}
  for loc in raw['locations']:
    ts = int(loc['timestampMs'])
    mapped[ts] = {
      'latitudeE7': loc['latitudeE7'],
      'longitudeE7' : loc['longitudeE7'],
      'accuracy' : loc['accuracy']
    }
  return mapped


def validate(annotated, raw_mapped):
  """
  Check the annotated data to make sure it exists in the raw timeline data.
  Raise an error if data is missing or if a timestamp's entry is different.
  """
  missing = []
  changed = []
  for day_entry in annotated['days'].values():
    for ts, entry in day_entry.items():
      if ts not in raw_mapped:
        missing.append(ts)
      else:
        raw_entry = raw_mapped[ts]
        if (entry['latitudeE7'] != raw_entry['latitudeE7'] or
            entry['longitudeE7'] != raw_entry['longitudeE7'] or
            entry['accuracy'] != raw_entry['accuracy']):
          changed.append(ts)
  if missing:
    print('ERROR: Annotated file contains timestamps that are missing from '
      'raw file:')
    for ts in missing: print(f'  {ts}')
  if changed:
    print('ERROR: Annotated file contains timestamp entries that are different '
      'from raw file:')
    for ts in changed: print(f'  {ts}')
  if missing or changed:
    sys.exit(1)


def trim(annotated, raw_mapped):
  """
  Remove entries from the raw data which already exist in the annotated data,
  so that the raw data represents only those entries that need to be added to
  the annotated set.
  """
  for day_entry in annotated['days'].values():
    for ts in day_entry.keys():
      del raw_mapped[ts]


def annotate(annotated, raw_mapped):
  """
  Add entries from the raw data set to the annotated data set, using reverse
  geocoding to determine the US state that contains each coordinate.  Because
  some reverse geocoding services have a daily limit on the number of requests,
  some raw entries might not be added to the annotated set.  If this happens,
  an info message is printed.
  """

  # Make sure the command line doesn't request a different geocoding service
  # if the annotated file already exists.
  if 'geocoder' in annotated and args.geocoder:
    if annotated['geocoder'] != args.geocoder:
      print(f'ERROR: Annotated file already uses "{annotated["geocoder"]}", '
        'cannot specify different geocoding service on command line.')
      sys.exit(1)

  # If the annotated file doesn't exist yet, set the geocoding service
  # according to the command line.
  if 'geocoder' not in annotated:
    annotated['geocoder'] = args.geocoder or 'local'

  # Get the list of coordinates to reverse geocode.
  coords = []
  for entry in raw_mapped.values():
    lat = entry['latitudeE7'] / 1E7
    lon = entry['longitudeE7'] / 1E7
    coords.append((lat, lon))
  if not coords:
    return

  print(f'INFO: Annotating {len(coords)} entries.')
  states = geocode(coords, annotated['geocoder'])
  if len(states) < len(coords):
    remaining = len(coords) - len(states)
    print(f'INFO: There are still {remaining} entries not annotated yet.')

  # The annotated data is indexed by date in New York, so convert each timestamp
  # to Eastern time zone and get the date in that timezone.
  eastern = pytz.timezone('US/Eastern')
  for state, (ts, raw_entry) in zip(states, raw_mapped.items()):
    dtEastern = datetime.datetime.fromtimestamp(ts/1000, tz=eastern)
    day = dtEastern.date()
    if not day in annotated['days']: annotated['days'][day] = {}
    day_entry = annotated['days'][day]
    day_entry[ts] = {
      'latitudeE7': raw_entry['latitudeE7'],
      'longitudeE7': raw_entry['longitudeE7'],
      'accuracy': raw_entry['accuracy'],
      'state': state
    }


def geocode(coords, geocoder):
  """
  Reverse geocode each coordinate to a US state, using the geocoding
  service specified by "geocoder".  Returns a list of strings, where each
  string is a 2-letter US state code (or "EX" if a coordinate is outside of
  the US).  The returned list may have fewer element than "coords" if the
  geocoding service is unable to translate all the coordinates.
  """
  if geocoder == 'local': return geocode_local(coords)
  if geocoder == 'osm': return geocode_osm(coords)
  return []


def geocode_local(coords):
  """
  Use the "reverse_geocoder" package to reverse geocode each coordinate to a
  US state.  Since this package runs locally, there is no limit on the number
  of queries, so it reverse geocodes all coordinates.
  """

  # The reverse geocode results includes an "admin1" field which identifies
  # the US state.  This dictionary maps this "admin1" field to a 2-letter state
  # code.
  admin_to_state = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'Washington, D.C.': 'DC',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY'
  }

  states = []
  results = rg.search(coords, verbose=False)
  for res in results:
    cc = res['cc']
    admin1 = res['admin1']
    if cc != 'US':
      states.append('EX')
    elif admin1 not in admin_to_state:
      print(f'ERROR: Unexpected "admin1" from reverse geocode "{admin1}".')
      sys.exit(1)
    else:
      states.append(admin_to_state[admin1])
  return states


def geocode_osm(coords):
  # The Nominatim service returns a "state" field which identifies the US
  # state or territory.  This dictionary translates that field into a 2-letter
  # state code, except for territories which are translated to "EX".
  translate_state = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'District of Columbia': 'DC',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Guam': 'EX',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Northern Mariana Islands': 'EX',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Puerto Rico': 'EX',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'United States Virgin Islands': 'EX',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY'
  }

  if not args.email:
    print(f'ERROR: Must specify email adress when using "osm" geocoder.')
    sys.exit(1)

  # Each coordinate is reverse mapped by sending a REST request to the
  # openstreetmap server.  The "zoom" argument says that we only care about
  # state-level granularity.  The "email" argument is required by their usage
  # policy.
  url = 'https://nominatim.openstreetmap.org/reverse'
  req_args = {
    'format': 'json',
    'zoom': 5,
    'email': args.email
  }

  # Loop over all coordinates, reverse geocoding each one.  This may take a
  # long time if there are many coordinates.  Therefore, the strategy for
  # error handling is to print the error message and terminate the loop, but
  # return any data that was successfully geocoded.  This allows the
  # successful data to be stored in the annotated file.
  states = []
  completed = 0
  total = len(coords)
  print('INFO: You can interrupt by pressing CTRL-C.')
  try:
    for c in coords:
      # Add the coordinates to the argument list and send the request.
      req_args['lat'] = c[0]
      req_args['lon'] = c[1]
      r = requests.get(url, params=req_args)

      # If we get an error code or the response isn't JSON format,
      # something is wrong.
      if r.status_code != requests.codes.ok:
        if completed: print('')
        print(f'ERROR: Response error: {r.status_code}.')
        break
      try:
        rjson = r.json()
      except ValueError:
        if completed: print('')
        print(f'ERROR: Response not JSON.')
        break

      # If a coordinate is outside of any country (e.g. in the middle of the
      # ocean), the server seems to return an "error" field and omit the
      # "address" field.  Therefore, treat this condition as a location that
      # is outside of any US state.
      #
      # Locations in US territories set the country code to "us", but only
      # some territories return the name of the territory in the "state"
      # field.  Other territories simply omit the "state" field entirely.
      # Therefore, if the "state" field is missing, just treat this as a
      # location that is outside of any US state.
      if 'error' in rjson or 'address' not in rjson or \
          rjson['address'].get('country_code') != 'us' or \
          'state' not in rjson['address']:
        states.append('EX')
      else:
        # The "translate_state" dictionary contains all the values we expect
        # to see in the "state" field.  If we see any other value, diagnose an
        # error, so the dictionary can be updated.
        rstate = rjson['address']['state']
        if rstate not in translate_state:
          if completed: print('')
          print(f'ERROR: Unexpected "state" from reverse geocode "{rstate}".')
          break
        else:
          states.append(translate_state[rstate])

      # Print progress and wait 1 second.  The terms of use require a 1 second
      # delay between requests.
      # https://operations.osmfoundation.org/policies/nominatim/
      completed += 1
      pct = completed / total
      print(f'\rINFO: Completed {completed} annotations ({pct:.0f}%).',
        end='', flush=True)
      time.sleep(1)
    else:
      print('')
  except KeyboardInterrupt:
    if completed: print('')
    print('INFO: Interrupted from keyboard.')

  return states


if __name__=="__main__":
  main()
