# Utility to convert an old format annotated file into the new format.
# The old format looked like this:
#
#   {
#     "geocoder": <string>,
#     "days": {
#       "<date>": {
#         "<timestamp>": {
#           "latitudeE7": <integer>,
#           "longitudeE7": <integer>,
#           "accuracy": <integer>,
#           "state": <string>
#         },
#         ...
#       },
#       ...
#     }
#   }
#
# Where "days" is a dictionary whose keys are dates in "YYYY-MM-DD" format,
# where the date represents a day in the US/Eastern timezone.  Each value in
# this dictionary is another dictionary, whose keys are timestamps in ISO 8601
# format representing a UTC time.  The timestamps always represent times within
# the parent's date.
#
# The values in this inner dictionary are the same as the "locations" entries
# from Google takeout.

import argparse
import datetime
import json

args = None

def main():
  parse_args()
  old_annotated = read_old_annotated_file(args.annotated)

  locations = []
  for day, day_entry in old_annotated['days'].items():
    for ts, ts_entry in day_entry.items():
      ts_as_datetime = datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone.utc)
      ts_as_string = ts_as_datetime.isoformat()
      if ts_as_string.endswith('000+00:00'):
        ts_as_string = ts_as_string[0:-9] + 'Z'
      elif ts_as_string.endswith('+00:00'):
        ts_as_string = ts_as_string[0:-6] + 'Z'
      else:
        print(f'ERROR: Unexpected timestamp format: "{ts_as_string}".')
      ts_entry['timestamp'] = ts_as_string
      locations.append(ts_entry)

  new_annotated = {
    'geocoder': old_annotated['geocoder'],
    'locations': locations
  }

  try:
    with open(args.output, 'w') as f:
      json.dump(new_annotated, f, sort_keys=True, indent=2)
  except IOError:
    print(f'ERROR: Unable to write annotated file "{args.output}".')


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Convert old annotated file to new format.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Old annotated JSON file.')
  parser.add_argument('-o', '--output', required=True,
      help='New annotated JSON file.')
  args = parser.parse_args()


def read_old_annotated_file(name):
  """Read the old-format annotated file (if it exists), and return its data."""
  try:
    with open(name) as f:
      converted = json.load(f)
  except IOError:
    converted = {'days': {}}

  # The JSON file stores the dictionary keys as strings.  Convert the date
  # keys into "date" objects and the timestamp keys into "datetime" objects.
  days = {}
  for day_conv, day_entry_conv in converted['days'].items():
    day = datetime.date.fromisoformat(day_conv)
    day_entry = {}
    days[day] = day_entry
    for ts_conv, entry in day_entry_conv.items():
      ts = int(ts_conv)
      day_entry[ts] = entry
  converted['days'] = days
  return converted


if __name__=="__main__":
  main()
