import json
import sys


def read_json_file(filename, default=None):
  """
  Read a JSON file and return its data.  Exit on error.
  If the file does not exist, the behavior depends on "default".  If "default"
  is None, exits with an error.  Otherwise, "default" is returned when the file
  does not exist.
  """
  try:
    with open(filename) as f:
      return json.load(f)
  except FileNotFoundError:
    if default != None:
      return default
    print(f'ERROR: File "{filename}" does not exist.')
  except OSError:
    print(f'ERROR: Unable to read file "{filename}".')
    sys.exit(1)


def write_json_file(data, filename):
  """Write a JSON file.  Exit on error."""
  try:
    with open(filename, 'w') as f:
      json.dump(data, f, sort_keys=True, indent=2)
  except OSError:
    print(f'ERROR: Unable to write file "{filename}".')
    sys.exit(1)


def is_midnight(time):
  """
  Given a datetime in NY timezone, return True if it is exactly midnight.
  """
  if time.hour == 0 and time.minute == 0 and \
     time.second == 0 and time.microsecond == 0:
    return True
  return False