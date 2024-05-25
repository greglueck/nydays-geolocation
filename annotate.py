import argparse
import dateutil.parser
import requests
import reverse_geocoder as rg
import sys
import time
import util

args = None

def main():
  # Parse command line arguments and read input files.
  parse_args()
  raw = util.read_json_file(args.raw)
  annotated = util.read_json_file(args.annotated)

  # Convert the raw and annotated location data into a dictionary indexed by
  # the timestamp.  We no longer need the raw data anymore, so delete it in
  # hopes of recovering the memory.
  ts_to_raw, _ = map_by_timestamp(raw['locations'])
  ts_to_annotated, ts_to_annotated_index = map_by_timestamp(annotated['locations'])
  del raw

  # Check to see if the input annotated data is still consistent with the raw
  # timeline data.  If not, either raise an error or remove the inconsistent
  # entries, depending on the command line arguments.  If inconsistent entries
  # are removed, the "ts_to_annotated_index" map is no longer accurate, so
  # delete it.
  validate(ts_to_annotated, ts_to_raw, ts_to_annotated_index, annotated)
  del ts_to_annotated_index

  # Remove entries from "ts_to_raw" which are already in the annotated set.
  trim(ts_to_annotated, ts_to_raw)

  # Reverse geocode all remaining entries from "ts_to_raw" to get the
  # containing US state, and add these to the annotated locations data set.
  # Write out the new annotated file.
  annotate(annotated, ts_to_raw)
  util.write_json_file(annotated, args.annotated)


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
  parser.add_argument('--limit', type=int,
      help='Limit reverse geocoding to to this many requests.')
  parser.add_argument('--delete-changed', action='store_true',
      help='Delete annotated entries that are changed in raw file')
  parser.add_argument('--delete-missing', action='store_true',
      help='Delete annotated entries that are missing in raw file')
  args = parser.parse_args()


def map_by_timestamp(locations):
  """
  Return two dictionaries whose keys are "datetime" objects.  The first
  dictionary maps each timestamp to the associated location data for that
  timestamp.  Entries are inserted into the dictionary in the same order as the
  entries in the location data.  The second dictionary maps each timestamp to
  the associated index in the location data list.
  """
  mapped_locations = {}
  mapped_index = {}
  for i in range(len(locations)):
    entry = locations[i]
    ts = dateutil.parser.isoparse(entry['timestamp'])
    mapped_locations[ts] = entry
    mapped_index[ts] = i
  return mapped_locations, mapped_index


def validate(ts_to_annotated, ts_to_raw, ts_to_annotated_index, annotated):
  """
  Check the annotated data to make sure it exists in the raw timeline data.
  Print a diagnostic if data is missing or if a timestamp's entry is different.
  Depending on the command line arguments, this diagnostic is either an error
  or an informational message.  If requested in the command line arguments,
  the missing / changed timestamp entries may be removed from the annotated
  set.
  """
  missing = []
  changed = []
  for ts, annotated_entry in ts_to_annotated.items():
    if ts not in ts_to_raw:
      missing.append(ts)
    else:
      raw_entry = ts_to_raw[ts]
      if (annotated_entry['latitudeE7'] != raw_entry['latitudeE7'] or
          annotated_entry['longitudeE7'] != raw_entry['longitudeE7'] or
          annotated_entry['accuracy'] != raw_entry['accuracy'] or
          annotated_entry['timestamp'] != raw_entry['timestamp']):
        changed.append(ts)

  # Diagnose an error if there are missing / changed entries and the command
  # line arguments don't ask to delete them.
  if missing and not args.delete_missing:
    print(f'ERROR: Annotated file contains {len(missing)} timestamp entries '
      'that are missing from raw file:')
    for ts in missing: print(f'  {ts}')
  if changed and not args.delete_changed:
    print(f'ERROR: Annotated file contains {len(changed)} timestamp entries '
      'that are different from raw file:')
    for ts in changed: print(f'  {ts}')
  if ((missing and not args.delete_missing) or
      (changed and not args.delete_changed)):
    sys.exit(1)

  # If there are missing / changed entries at this point, the user has asked
  # to delete them from the annotated list.  We must delete them in reverse
  # order of their index in the list since deleting an entry changes the
  # indices of the subsequent entries.
  indices = []
  if missing:
    print(f'INFO: Removing {len(missing)} annotated entries that are missing '
      'from raw file:')
    for ts in missing:
      print(f'  {ts}')
      indices.append(ts_to_annotated_index[ts])
      del ts_to_annotated[ts]
  if changed:
    print(f'INFO: Removing {len(changed)} annotated entries that are different '
      'from raw file:')
    for ts in changed:
      print(f'  {ts}')
      indices.append(ts_to_annotated_index[ts])
      del ts_to_annotated[ts]
  for i in sorted(indices, reverse=True):
    del annotated['locations'][i]


def trim(ts_to_annotated, ts_to_raw):
  """
  Remove entries from the raw data which already exist in the annotated data,
  so that the raw data represents only those entries that need to be added to
  the annotated set.
  """
  for ts in ts_to_annotated.keys():
    del ts_to_raw[ts]


def annotate(annotated, ts_to_raw):
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
  for entry in ts_to_raw.values():
    lat = entry['latitudeE7'] / 1E7
    lon = entry['longitudeE7'] / 1E7
    coords.append((lat, lon))
    if args.limit and len(coords) >= args.limit: break
  if not coords:
    return

  if len(ts_to_raw) > len(coords):
    print(f'INFO: Annotating {len(coords)} of {len(ts_to_raw)} entries.')
  else:
    print(f'INFO: Annotating {len(coords)} entries.')

  states = geocode(coords, annotated['geocoder'])
  if len(states) < len(ts_to_raw):
    remaining = len(ts_to_raw) - len(states)
    print(f'INFO: There are still {remaining} entries not annotated yet.')

  # Append entries to the "annotated" data, including the reverse geocoded
  # state.
  for state, (raw_entry) in zip(states, ts_to_raw.values()):
    entry = {
      'timestamp': raw_entry['timestamp'],
      'latitudeE7': raw_entry['latitudeE7'],
      'longitudeE7': raw_entry['longitudeE7'],
      'accuracy': raw_entry['accuracy'],
      'state': state
    }
    annotated['locations'].append(entry)


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
      pct = (completed / total) * 100
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
