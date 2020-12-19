import annotated_json
import argparse
import datetime
import json
import pytz
import reverse_geocoder as rg 
import sys


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
  # Remove entries from both "raw_mapped" and "annotated" which are deemed
  # inaccurate.  Anything left in "raw_mapped" should be added to the annotated
  # set.
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
      description='Create or update annotated geolocation file from Google timeline.')
  parser.add_argument('-r', '--raw', required=True,
      help='Raw Google timeline input JSON file.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Annotated output JSON file.')
  parser.add_argument('--accuracy', default=800, type=int,
      help='Skip raw entries whose "accuracy" is greater than this threshold.')
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
  for day_entry in annotated.values():
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
    print('ERROR: Annotated file contains timestamps that are missing from raw file:')
    for ts in missing:
      print(f'  {ts}')
  if changed:
    print('ERROR: Annotated file contains timestamp entries that are different from raw file:')
    for ts in changed:
      print(f'  {ts}')
  if missing or changed:
    sys.exit(1)


def trim(annotated, raw_mapped):
  """
  Remove entries from the raw data which already exist in the annotated data,
  so that the raw data represents only those entries that need to be added to
  the annotated set.  Also removes entries from both the annotated and raw data
  sets whose accuracy is below the threshold.
  """
  for day_entry in annotated.values():
    for ts in day_entry.keys():
      del raw_mapped[ts]
    inaccurate = [ts for ts, entry in day_entry.items()
        if entry['accuracy'] > args.accuracy]
    for ts in inaccurate: del day_entry[ts]

  inaccurate = [ts for ts, entry in raw_mapped.items()
      if entry['accuracy'] > args.accuracy]
  for ts in inaccurate: del raw_mapped[ts]


def annotate(annotated, raw_mapped):
  """
  Add entries from the raw data set to the annotated data set, using reverse
  geocoding to determine the US state that contains each coordinate.  Because
  some reverse geocoding services have a daily limit on the number of requests,
  some raw entries might not be added to the annotated set.  If this happens,
  a warning message is printed.
  """
  coords = []
  for entry in raw_mapped.values():
    lat = entry['latitudeE7'] / 1E7
    lon = entry['longitudeE7'] / 1E7
    coords.append((lat, lon))

  if coords:
    states = geomap(coords)
  else:
    states = []
  if len(states) < len(coords):
    remaining = len(coords) - len(states)
    print(f'WARNING: There are {remaining} timestamp entries not annotated yet.')

  # The annotated data is indexed by date in New York, so convert each timestamp
  # to Eastern time zone and get the date in that timezone.
  eastern = pytz.timezone('US/Eastern')
  for state, (ts, raw_entry) in zip(states, raw_mapped.items()):
    dtEastern = datetime.datetime.fromtimestamp(ts/1000, tz=eastern)
    day = dtEastern.date()
    if not day in annotated: annotated[day] = {}
    day_entry = annotated[day]
    day_entry[ts] = {
      'latitudeE7': raw_entry['latitudeE7'],
      'longitudeE7': raw_entry['longitudeE7'],
      'accuracy': raw_entry['accuracy'],
      'state': state
    }


def geomap(coords):
  """
  Use the "reverse_geocode" package to reverse geolocate each coordinate to a
  US state.  Since this package runs locally, there is no limit on the number
  of queries, so it reverse geolocates all coordinates.

  Returns a list of strings, where each string is a 2-letter US state code (or
  "EX" if a coordinate is outside of the US).
  """

  # The reverse geolocate results includes an "admin1" field which identifies
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
      print(f'ERROR: Unexpected "admin1" from geo decode: {admin1}')
      sys.exit(1)
    else:
      states.append(admin_to_state[admin1])
  return states


if __name__=="__main__": 
  main()