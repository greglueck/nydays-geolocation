import argparse
import dateutil.parser
import pathlib
import pytz
import sys
import util

args = None

def main():
  # Parse command line arguments and read input files.
  parse_args()
  raw = util.read_json_file(args.raw)
  annotated = util.read_json_file(args.annotated)

  # Get subsets of the input data containing only the location entries that
  # are in the requested tax year.
  raw_archive = get_archived_raw(raw)
  annotated_archive = get_archived_annotated(annotated)

  # Write the subsetted data as the archive files.
  write_output(raw_archive, annotated_archive)


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Create archives of the raw and annotated files for one or more tax years.',
      epilog='Must supply either --year or both --begin and --end')
  parser.add_argument('-r', '--raw', required=True,
      help='Raw Google timeline JSON file.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Annotated JSON file.')
  parser.add_argument('-y', '--year', type=int,
      help='Tax year to archive.')
  parser.add_argument('-b', '--begin', type=int,
      help='First tax year to archive.')
  parser.add_argument('-e', '--end', type=int,
      help='Last tax year to archive.')
  parser.add_argument('-n', '--name', required=True,
      help='Name of person, used to name output file.')
  parser.add_argument('-o', '--output', required=True,
      help='Name of directory where output files are written.')
  args = parser.parse_args()
  if (args.year and args.begin) or (args.year and args.end):
    print('ERROR: --year is mutually exclusive with --begin and --end')
    sys.exit(1)
  if (args.begin and not args.end) or (args.end and not args.begin):
    print('ERROR: Must specify both --begin and --end (or specify --year)')
    sys.exit(1)
  if not args.year and not args.begin:
    print('ERROR: Must specify either --year or both --begin and --end')
    sys.exit(1)
  if args.year:
    args.begin = args.year
    args.end = args.year

def get_archived_raw(raw):
  """
  Return a subset of the raw data containing only timestamp entries that fall
  within the requested tax year.
  """
  locations = get_archived_locations(raw['locations'])
  return {'locations': locations}


def get_archived_annotated(annotated):
  """
  Return a subset of the annotated data containing only timestamp entries that
  fall within the requested tax year.
  """
  locations = get_archived_locations(annotated['locations'])
  return {
    'geocoder': annotated['geocoder'],
    'locations': locations
  }


def get_archived_locations(locations):
  """
  Return a subset of the locations data containing only timestamp entries that
  fall within the requested tax year.
  """
  archived = []
  eastern = pytz.timezone('US/Eastern')
  for entry in locations:
    ts = dateutil.parser.isoparse(entry['timestamp'])
    tsEastern = ts.astimezone(eastern)
    if (tsEastern.year >= args.begin) and (tsEastern.year <= args.end):
      archived.append(entry)
  return archived


def write_output(raw, annotated):
  """Write the subsetted raw and annotated data as the archive files."""

  # Get pathnames to the archive files.
  out_path = pathlib.Path(args.output)
  if args.begin == args.end:
    year = f'{args.begin}'
  else:
    year = f'{args.begin}-{args.end}'
  raw_name = f'geo-location-{args.name}-{year}-raw.json'
  raw_path = pathlib.Path(args.output, raw_name)
  annotated_name = f'geo-location-{args.name}-{year}-annotated.json'
  annotated_path = pathlib.Path(args.output, annotated_name)

  # Check if these archive files already exists.  We don't want to overwrite
  # existing archive data.
  err = False
  if raw_path.exists():
    print(f'ERROR: Output file already exists "{raw_path}".')
    err = True
  if annotated_path.exists():
    print(f'ERROR: Output file already exists "{annotated_path}".')
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
  util.write_json_file(raw, raw_path)
  util.write_json_file(annotated, annotated_path)


if __name__=="__main__":
  main()
