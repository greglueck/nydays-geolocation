# Utilities to read and write the annotated location JSON data file.
# This JSON file has the following format:
#
#   {
#     "<date>": {
#       "<timestamp>": {
#         "latitudeE7": <integer>,
#         "longitudeE7": <integer>,
#         "accuracy": <integer>,
#         "state": <string>
#       },
#       ...
#     }
#     ...
#   }
#
# For example:
#
#   {
#     "2017-02-18": {
#       "1487472687835": {
#         "latitudeE7": 407763853,
#         "longitudeE7": -739834621,
#         "accuracy": 50,
#         "state": "NY"
#       },
#       ...
#     }
#     ...
#   }
#
# The outer dictionary has keys that are dates in "YYYY-MM-DD" format, where
# the date represents a day in the US/Eastern timezone.  Each value in this
# dictionary is another dictionary, whose keys are POSIX timestamps (number of
# milliseconds since the Epoch, representing a UTC time.)  The timestamps
# always represent times within the parent's date.
#
# The values in this inner dictionare are yet another dictionary with the
# following key / value pairs, telling information about a single geolocation
# entry that corresponds to its timestamp:
#
#   latitudeE7: An integer telling the latitude of the location.  The value is
#     the latitude multiplied by 1E7.
#
#   longitudeE7: An integer telling the longitude of the location.  The value is
#     the longitude multiplied by 1E7.
#
#   accuracy: An integer telling the accuracy of the location.  This comes
#     directly from the Google timeline takeout file, and is not well
#     documented.  However, several web sites describe it as "Estimation of how
#     accurate the data is. An accuracy of less than 800 is generally
#     considered high."
#     https://towardsdatascience.com/analyzing-my-google-location-history-d3a5c56c7b70
#
#   state: A string telling the 2-letter US state abbreviation indicataing the
#     US state that contains this location.  The value "EX" indicates the
#     location is outside of the 50 US states.

import datetime
import json

def read(name):
  """Read the annotated file (if it exists), and return its data."""
  try:
    with open(name) as f:
      converted = json.load(f)
  except IOError:
    converted = {}

  # The JSON file stores the dictionary keys as strings.  Convert the date
  # keys into Data objects and the timestamp keys into integers.
  annotated = {}
  for day_conv, day_entry_conv in converted.items():
    day = datetime.date.fromisoformat(day_conv)
    day_entry = {}
    annotated[day] = day_entry
    for ts_conv, entry in day_entry_conv.items():
      ts = int(ts_conv)
      day_entry[ts] = entry
  return annotated


def write(annotated, name):
  """Write the annotated file."""

  # JSON can't represent dictionary keys that are Date objects.  Convert them
  # into string form.  Note that "json.dump()" automatically converts the
  # integer timestamps keys into strings.
  converted = {}
  for day, day_entry in annotated.items():
    day_conv = day.isoformat()
    converted[day_conv] = day_entry

  try:
    with open(name, 'w') as f:
      json.dump(converted, f, sort_keys=True, indent=2)
  except IOError:
    print(f'ERROR: Unable to write annotated file "{name}".')
