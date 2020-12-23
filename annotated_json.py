# Utilities to read and write the annotated location JSON data file.
# This JSON file has the following format:
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
# For example:
#
#   {
#     "geocoder": "local",
#     "days": {
#       "2017-02-18": {
#         "1487472687835": {
#           "latitudeE7": 407763853,
#           "longitudeE7": -739834621,
#           "accuracy": 50,
#           "state": "NY"
#         },
#         ...
#       },
#       ...
#     }
#   }
#
# The top-level dictionary has two keys:
#
#   geocoder: A string telling the geocoding service that was used to reverse
#     geocode the location data.  Possible values are:
#
#       "local": The Python package "reverse_geocoder", which runs locally.
#
#       "osm": The Nominatim web service from openstreetmap.org.
#
#   days: A dictionary whose keys are dates in "YYYY-MM-DD" format, where
#     the date represents a day in the US/Eastern timezone.  Each value in
#     this dictionary is another dictionary, whose keys are POSIX timestamps
#     (number of milliseconds since the Epoch, representing a UTC time.)  The
#     timestamps always represent times within the parent's date.
#
#     The values in this inner dictionary are yet another dictionary with the
#     following key / value pairs, telling information about a single
#     geolocation entry that corresponds to its timestamp:
#
#     latitudeE7: An integer telling the latitude of the location.  The value
#       is the latitude multiplied by 1E7.
#
#     longitudeE7: An integer telling the longitude of the location.  The
#       value is the longitude multiplied by 1E7.
#
#     accuracy: An integer telling the accuracy of the location.  This comes
#       directly from the Google timeline takeout file, and is not well
#       documented.  However, several web sites describe it as "Estimation of
#       how accurate the data is. An accuracy of less than 800 is generally
#       considered high."
#       https://towardsdatascience.com/analyzing-my-google-location-history-d3a5c56c7b70
#
#     state: A string telling the US state that contains this location.  The
#       values follow the 2-letter USPS post office abbreviations
#       (https://about.usps.com/who-we-are/postal-history/state-abbreviations.htm)
#       for the 50 US states plus the District of Columbia.  The value "EX"
#       indicates a location that is outside of the US.

import datetime
import json

def read(name):
  """Read the annotated file (if it exists), and return its data."""
  try:
    with open(name) as f:
      converted = json.load(f)
  except IOError:
    converted = {'days': {}}

  # The JSON file stores the dictionary keys as strings.  Convert the date
  # keys into Data objects and the timestamp keys into integers.
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


def write(annotated, name):
  """Write the annotated file."""

  # JSON can't represent dictionary keys that are Date objects.  Convert them
  # into string form.  Note that "json.dump()" automatically converts the
  # integer timestamps keys into strings.
  converted = {
    "geocoder": annotated['geocoder'],
    "days": {}
  }
  for day, day_entry in annotated['days'].items():
    day_conv = day.isoformat()
    converted['days'][day_conv] = day_entry

  try:
    with open(name, 'w') as f:
      json.dump(converted, f, sort_keys=True, indent=2)
  except IOError:
    print(f'ERROR: Unable to write annotated file "{name}".')
