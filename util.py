import json
import sys


def read_json_file(filename):
  """Read a JSON file and return its data.  Exit on error."""
  try:
    with open(filename) as f:
      return json.load(f)
  except IOError:
    print(f'ERROR: Unable to read file "{filename}".')
    sys.exit(1)


def write_json_file(data, filename):
  """Write a JSON file.  Exit on error."""
  try:
    with open(filename, 'w') as f:
      json.dump(data, f, sort_keys=True, indent=2)
  except IOError:
    print(f'ERROR: Unable to write file "{filename}".')
    sys.exit(1)
