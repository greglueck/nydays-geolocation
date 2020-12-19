import annotated_json
import argparse

args = None

def main():
  # Parse command line arguments and open annotated file.
  parse_args()
  annotated = annotated_json.read(args.annotated)

  # Create a dictionary summarizing the number of timestamp entries in each
  # US state for each day:
  #
  # {day: {state: <count>, ...}, ...}
  summary = summarize(annotated)

  # Get a list of all the states in our summary.  These will be the columns
  # in our spreadsheet.
  states = find_states(summary)

  # Create a 2-D list for the spreadsheet and write it out.
  cells = make_spreadsheet(states, summary)
  write_csv(args.output, cells)


def parse_args():
  """Parse the command line arguments into global "args"."""
  global args
  parser = argparse.ArgumentParser(
      description='Create a CSV file showing states for each day.')
  parser.add_argument('-a', '--annotated', required=True,
      help='Annotated JSON file.')
  parser.add_argument('-o', '--output', required=True,
      help='Output CSV file.')
  args = parser.parse_args()


def summarize(annotated):
  """
  Returns a dictionary with one key for each day.  Each value is also a
  dictionary, where each key is a state and the value is the number of
  timestamp entries in that state for that day.
  """
  summary = {}
  for day, day_entry in annotated.items():
    summary[day] = {}
    for entry in day_entry.values():
      state = entry['state']
      if not state in summary[day]: summary[day][state] = 0
      summary[day][state] += 1
  return summary


def find_states(summary):
  """
  Return a list of all the states that are in the summary dictionary, sorted
  by the order in which we want them to appear in the spreadsheet.
  """
  found_ex = False
  states_dict = {}
  for day_entry in summary.values():
    for state in day_entry.keys():
      if state == 'EX': found_ex = True
      else: states_dict[state] = True
  states = sorted(states_dict.keys())
  if found_ex: states.append('EX')
  return states


def make_spreadsheet(states, summary):
  """Return a 2-D list representing the cells of the spreadsheet."""

  # The first row is a header.  Use the label "Outside US" instead of "EX".
  cells = []
  row = ['Day']
  row.extend(['Outside US' if state=='EX' else state for state in states])
  cells.append(row)

  # The remaining rows are the data for each date.  For cells that have a
  # zero count, leave the cell blank rather than setting it to "0".
  for day, day_entry in summary.items():
    row = []
    row.append(day.isoformat())
    for state in states:
      row.append(str(day_entry.get(state, '')))
    cells.append(row)
  return cells


def write_csv(name, cells):
  """Write the spreadsheet cells as a CSV text file."""
  try:
    with open(name, 'w') as f:
      for row in cells:
        line = ','.join(row)
        f.write(line + '\n')
  except IOError:
    print(f'ERROR: Unable to write CSV file "{name}".')


if __name__=="__main__":
  main()