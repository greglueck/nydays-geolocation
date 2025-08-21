import argparse
import datetime
import dateutil.parser
import pathlib
import pytz
import sys
import util

args = None

def main():
  parse_args()

  # Read the raw timeline data files and get the subset of entries in each that
  # provide location data for the reqested tax years.  Ignore files that do not
  # contain any data in these years.
  raw_archives = []
  for raw_name in args.raw:
    raw = util.read_json_file(raw_name)
    archive = get_archived(raw)
    if archive:
      raw_archives.append(archive)
  if not raw_archives:
    print(f'ERROR: No raw timeline data in specified tax year(s).')
    sys.exit(1)

  # Read the annotated data file and get the subset of entries that provide
  # location data for the requested tax years.
  annotated = util.read_json_file(args.annotated)
  annotated_archive = get_archived(annotated)
  if not annotated_archive:
    print(f'ERROR: No annotated timeline data in specified tax year(s).')
    sys.exit(1)

  # Write the subsetted data as the archive files.
  write_output(raw_archives, annotated_archive)


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Create archives of the raw and annotated files for one or more tax years.',
      epilog='Must supply either --year or both --begin and --end')
  parser.add_argument('-r', '--raw', required=True, action='append',
      help='Raw Google timeline JSON file (may be repeated).')
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


def get_archived(records):
  """
  Return a subset of the timeline records whose time range falls within the
  requested tax year(s).  This works for either the raw or annotated JSON files.
  """
  archived = []
  eastern = pytz.timezone('US/Eastern')
  beginPeriod = datetime.datetime(args.begin, 1, 1, tzinfo=eastern)
  endPeriod = datetime.datetime(args.end+1, 1, 1, tzinfo=eastern)

  for rec in records:
    if 'startTime' in rec and 'endTime' in rec:
      start = dateutil.parser.isoparse(rec['startTime']).astimezone(eastern)
      end = dateutil.parser.isoparse(rec['endTime']).astimezone(eastern)

      # To be conservative, assume that midnight between December 31 and
      # January 1 is part of both years.  A point in NY on exactly midnight
      # will count as residency in NY for both days.
      if end >= beginPeriod and start <= endPeriod:
        archived.append(rec)
  return archived


def write_output(raws, annotated):
  """Write the subsetted raw and annotated data as the archive files."""

  # Get the path to the output directory and create the string we will use
  # to represent the year(s) in the output files.
  out_path = pathlib.Path(args.output)
  if args.begin == args.end:
    year = f'{args.begin}'
  else:
    year = f'{args.begin}-{args.end}'

  # Check that that annotated archive file doesn't already exist.
  # We don't want to ovewrite an existing file.
  err = False
  annotated_name = f'geo-location-{args.name}-{year}-annotated.json'
  annotated_path = pathlib.Path(args.output, annotated_name)
  if annotated_path.exists():
    print(f'ERROR: Output file already exists "{annotated_path}".')
    err = True

  # Check that the raw archive files don't already exist.
  if len(raws) == 1:
    raw_name = f'geo-location-{args.name}-{year}-raw.json'
    raw_path = pathlib.Path(args.output, raw_name)
    if raw_path.exists():
      print(f'ERROR: Output file already exists "{raw_path}".')
      err = True
  else:
    for i in range(1, len(raws)+1):
      raw_name = f'geo-location-{args.name}-{year}-raw-{i}.json'
      raw_path = pathlib.Path(args.output, raw_name)
      if raw_path.exists():
        print(f'ERROR: Output file already exists "{raw_path}".')
        err = True

  if err:
    sys.exit(1)

  # Create the output directory if it doesn't already exist.
  try:
    out_path.mkdir(parents=True, exist_ok=True)
  except IOError:
    print(f'ERROR: Unable to create output directory "{out_path}".')
    sys.exit(1)

  # Write the archive files.
  util.write_json_file(annotated, annotated_path)
  if len(raws) == 1:
    raw_name = f'geo-location-{args.name}-{year}-raw.json'
    raw_path = pathlib.Path(args.output, raw_name)
    util.write_json_file(raws[0], raw_path)
  else:
    i = 1
    for raw in raws:
      raw_name = f'geo-location-{args.name}-{year}-raw-{i}.json'
      raw_path = pathlib.Path(args.output, raw_name)
      util.write_json_file(raw, raw_path)
      i += 1


if __name__=="__main__":
  main()
