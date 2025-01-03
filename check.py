import argparse
import datetime
import dateutil.parser
import openpyxl
import pytz
import sys
import util

args = None

def main():
  # Parse command line arguments and read input files.
  parse_args()
  annotated = util.read_json_file(args.annotated)
  ws = get_worksheet()

  # Create a dictionary from the NY Days spreadsheet, mapping each day to a
  # Boolean telling whether the day is a "NY day".
  ny_days = get_ny_days(ws)

  # Create a dictionary that maps each day to the set of states for that day.
  mapped = map_days_to_states(annotated)

  # Check the dictionary against the location data to see if any non-NY day
  # was actually spent in NY.
  check(ny_days, mapped)


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Validate the NY Days spreadsheet against the annotated '
        'location data.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Annotated JSON file.')
  parser.add_argument('-w', '--workbook', required=True,
      help='Excel workbook with NY Days spreadsheet.')
  parser.add_argument('-s', '--sheet', required=True,
      help='Name of NY Days spreadsheet within workbook.')
  args = parser.parse_args()


def get_worksheet():
  """Open the Excel workbook and return the "NY Days" worksheet."""
  try:
    wb = openpyxl.load_workbook(args.workbook)
  except IOError:
    print(f'ERROR: Unable to open Excel workbook "{args.workbook}".')
    sys.exit(1)
  if args.sheet not in wb:
    print(f'ERROR: Worksheet "{args.sheet}"" does not exist in '
      f'"{args.workbook}".')
    sys.exit(1)
  return wb[args.sheet]


def get_ny_days(ws):
  """
  Read the NY Days spreadsheet and return a dictionary where each key is a day
  from the spreadsheet and the value is a Boolean telling whether that day is
  a "NY day".
  """

  # The NY Days table starts on row 4.  Important columns are:
  #
  #   col 1: Starting date of a range (a "datetime" object)
  #   col 3: Ending date or a range (a "datetime" object)
  #   col 5: Either "x" or None, telling whether these days are NY days.
  ny_days = {}
  for row in ws.iter_rows(min_row=4, values_only=True):
    # Read cells from this row.  The table ends with a blank row.
    start = row[0]
    end = row[2]
    in_ny = row[4]
    if not start or not end: break

    # The row identifies a range of days.  Loop over all these days.
    start = start.date()
    end = end.date()
    days = (end - start).days + 1
    for day in [start + datetime.timedelta(days=x) for x in range(days)]:
      ny_days[day] = (in_ny != None)
  return ny_days


def map_days_to_states(annotated):
  """
  Create a dictionary from the annotated records.  Each key is a "date"
  object representing a day in NY timezone, and each value is a set of the
  states for that day.
  """
  mapped = {}
  eastern = pytz.timezone('US/Eastern')
  for rec in annotated:
    start = dateutil.parser.isoparse(rec['startTime'])
    startEastern = start.astimezone(eastern)

    for tlrec in rec['timelinePath']:
      # Get the date for this point.
      offset = int(tlrec['durationMinutesOffsetFromStartTime'])
      pointTime = startEastern + datetime.timedelta(minutes=offset)
      day = pointTime.date()

      if not day in mapped:
        mapped[day] = set()
      mapped[day].add(tlrec['state'])

      # Midnight is the first moment of the next day, but this might be hard
      # to explain to a tax authority.  To be conservative, treat a point at
      # exactly midnight as residency in the previous day also.
      if util.is_midnight(pointTime):
        day = day - datetime.timedelta(days=1)
        if not day in mapped:
          mapped[day] = set()
        mapped[day].add(tlrec['state'])

  return mapped


def check(ny_days, mapped):
  """
  Check the NY days spreadsheet against the location data.  Print warnings for
  any non-NY days that have no location data.  Print errors for any non-NY days
  that have locations in NY.
  """
  warn = []
  err = []
  for day, in_ny in ny_days.items():
    if in_ny: continue

    # A non-NY day with a location in NY is an error.
    # A non-NY day with no location data is a warning.
    if day in mapped:
      if 'NY' in mapped[day]:
        err.append(day)
    else:
      warn.append(day)

  if warn:
    print(f'WARNING: No location data for {len(warn)} non-NY days:')
    print_days('  ', warn)
  if err:
    print(f'ERROR: {len(err)} spreadsheet non-NY days have locations in NY:')
    print_days('  ', err)
    sys.exit(1)


def print_days(prefix, days):
  """
  Print a list of dates, where each range of consecutive dates is on its own
  line.  Each line is prefixed by the string "prefix".
  """
  i = 0
  while i < len(days):
    first_day = days[i]
    last_day = first_day
    for j in range(i+1, len(days)):
      day = days[j]
      if day != last_day + datetime.timedelta(days=1): break
      last_day = day
      i = j
    if (first_day == last_day):
      print(prefix + f'{first_day}')
    else:
      print(prefix + f'{first_day} - {last_day}')
    i += 1


if __name__=="__main__":
  main()
