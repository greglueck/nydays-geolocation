import annotated_json
import argparse
import datetime
import json
import pathlib
import pytz
import sys


args = None

def main():
  # Parse command line arguments and read input files.
  parse_args()
  raw = read_raw_file()
  annotated = annotated_json.read(args.annotated)

  # Get subsets of the input data containing only the location entries that
  # are in the requested tax year.
  raw_archive = get_raw_archive(raw)
  annotated_archive = get_annotated_archive(annotated)

  # Write the subsetted data as the archive files.
  write_output(raw_archive, annotated_archive)


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Create archives of the raw and annotated files for a tax year.')
  parser.add_argument('-r', '--raw', required=True,
      help='Raw Google timeline JSON file.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Annotated JSON file.')
  parser.add_argument('-y', '--year', required=True, type=int,
      help='Tax year to archive.')
  parser.add_argument('-n', '--name', required=True,
      help='Name of person, used to name output file.')
  parser.add_argument('-o', '--output', required=True,
      help='Name of directory where output files are written.')
  args = parser.parse_args()


def read_raw_file():
  """Read the Google timeline file, and return its data."""
  try:
    with open(args.raw) as f:
      return json.load(f)
  except IOError:
    print(f'ERROR: Input raw timeline file "{args.raw}" does not exist.')
    sys.exit(1)


def get_raw_archive(raw):
  """
  Return a subset of the raw data, containing only timestamp entries that fall
  within the requested tax year.
  """
  locations = []
  eastern = pytz.timezone('US/Eastern')
  for entry in raw['locations']:
    ts = int(entry['timestampMs'])
    dtEastern = datetime.datetime.fromtimestamp(ts/1000, tz=eastern)
    if dtEastern.year == args.year:
      locations.append(entry)
  return {'locations': locations}


def get_annotated_archive(annotated):
  """
  Return a subset of the annotated data, containing only days that fall within
  the requested tax year.
  """
  archive = {}
  for day, day_entry in annotated.items():
    if day.year == args.year:
      archive[day] = day_entry
  return archive


def write_output(raw, annotated):
  """Write the subsetted raw and annotated data as the archive files."""

  # Get pathnames to the archive files.
  out_path = pathlib.Path(args.output)
  raw_name = f'geo-location-{args.name}-{args.year}-raw.json'
  raw_path = pathlib.Path(args.output, raw_name)
  annotated_name = f'geo-location-{args.name}-{args.year}-annotated.json'
  annotated_path = pathlib.Path(args.output, annotated_name)

  # Check if these archive files already exists.  We don't wanto to overwrite
  # existing archive data.
  err = False
  if raw_path.exists():
    print(f'ERROR: Output file already exists "{raw_path}"')
    err = True
  if annotated_path.exists():
    print(f'ERROR: Output file already exists "{annotated_path}"')
    err = True
  if err:
    sys.exit(1)

  # Create the output directory if it doesn't already exist.
  try:
    out_path.mkdir(parents=True, exist_ok=True)
  except IOError:
    print(f'ERROR: Unable to create output directory "{out_path}".')
    sys.exit(1)

  # Write the files.
  try:
    with open(raw_path, 'w') as f:
      json.dump(raw, f, indent=2)
  except IOError:
    print(f'ERROR: Unable to write output file "{raw_path}".')
    sys.exit(1)
  annotated_json.write(annotated, str(annotated_path))


if __name__=="__main__":
  main()