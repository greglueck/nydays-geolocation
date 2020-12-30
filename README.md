# nydays-geolocation

This project contains a set of utilities that correlate geolocation data from
Google "location history" to US states.  The intent is to use the geolocation
data to help identify days spent in NY state for tax purposes, but much of the
logic in the utilities could be used to identify days spent in any US state.

The utilities assume you have enabled Google "location history" on a mobile
device and have downloaded the data in JSON format via Google takeout.  We
refer to this downloaded file as the "raw JSON file".  Once you have this raw
JSON file, you can use the following utilities.

## Utility Scripts

### annotate.py

The raw JSON file contains a series of entries where each entry contains a
timestamp and a pair of coordinates (latitude / longitude) telling the location
of your device at that time.  The "annotate.py" utility identifies the US state
containing the coordinates by using a reverse geolocation service.  There are
options to choose the geolocation service, and depending on the choice this
tool may run for a long time.  Therefore, the tool saves the results in an
output file called the "annotated JSON file", and the other utilities consume
this file.

This utility can be run like:

```
$ python annotate.py -r <raw-file> -a <annotated-file> [--geocoder <service>] \
  [--email <email>] [--limit <number>]
```

The `<raw-file>` is the pathname to the JSON file downloaded from Google
takeout, and the `<annotated-file>` is the pathname to the annotated JSON file
which the utility either creates or updates.  The first time you run this
utility, it creates an annotated file with data from the raw file.  The
expectation is that you save the annotated file and periodically update it as
you collect more location data on your mobile device.

After your mobile device collects more location data, you can download it via
Google takeout and run the "annotate.py" utility again with the newly
downloaded raw JSON file.  The utilility will compare the content from
`<raw-file>` to the content from `<annotated-file>` and identify the new
location data.  The utility then annotates only this new data and updates
`<annotated-file>`.

The `--geocoder` option allows you to select a reverse geocoding service to
translate the lattidue / longitude coordinates to a US state.  The default
uses a service that runs locally.  This runs quickly but may be less
accurate.  The other option "osm" uses the open street map Nominatim service,
which runs remotely.  This is much slower but also more accurate.  Using the
"osm" service requires specifying your email address with `--email`, and the
service may reject requests if you exceed their terms of use.  The `--limit`
option may be useful to avoid exceeding these limits, allowing you to annotate
the `<raw-file>` piecemeal with several runs of the utility.

### visualize.py

This utility creates a spreadsheet where each row is a day and the columns
show the number of location data entries on that day broken down by each US
state.  Usage is like:

```
$python visualize.py -a <annotated-file> -o <csv-file> [--accuracy <number>]
```

Each location entry in the raw data file contains an indication of the entry's
accuracy.  The `--accuracy` option allows you to filter out location entries
that are less accurate.  The default setting  shows only the entries that are
very accurate (an accuracy value of 800 or less).  Specify a larger value to
display more entries or specify `--accuracy 0` to disable the filter and
display all entries.

### check.py

This utility assumes you care about the number of days spent in NY state, and
it assume you have maintained an Excel spreadsheet recording this data.  The
utility compares information from the spreadhseet with the location data and
flags any mismatches.  For example, if the spreadsheet records that a day was
spent outside of NY and the location data has an entry that is inside of NY on
that day, the utility will flag this as an error.

Usage is like:

```
$ python check.py -a <annotated-file> -w <workbook> -s <sheet> \
  [--accuracy <number>]
```

The `workbook` specifies the pathname of the Excel workbook file, and
`<sheet>` is the name of the spreadsheet in that workbook.  The `--accuracy`
option causes the utility to ignore location entries that are less accurate.

The spreadsheet is assumed to have a specific format, where the data starts
on row 4:

| Column 1  | Column 2 | Column 3  | Column 4 | Column 5  |
| --------  | -------- | --------  | -------- | --------  |
| `<start>` |          | `<end>`   |          | `<in NY>` |
| ...       |          | ...       |          | ...       |
| `<start>` |          | `<end>`   |          | `<in NY>` |
| `<blank>` |          | `<blank>` |          |           |

The `<start>` entry in column 1 is an Excel date that indicates the start of
a range of days and `<end>` tells the end of that range, where the range
includes both `<start>` and `<end>`.  The `<in NY>` value in column 5 tells
whether these days were spent in NY: a non-empty value indicates the days were
not in NY whereas any other values indicates that days were spent in NY.
The spreadsheet data ends when a row has a blank entry in either column 1 or
column 3.  The script ignores the contents of the other columns (2, 4, and any
columns after 5).

### archive.py

This utility archives the location data for a particular year.  Usage is like:

```
$ python archive.py -r <raw-file> -a <annotated-file> -y <year> -n <name> \
  -o <output-directory>
```

The `<raw-file>` and `<annotated-file>` specify the pathnames to the raw and
annotated JSON files.  The `<year>` is a number specifying the year to
archive.  For example, specifying `2020` archives the location data
corresponding to days in the year 2020.  The `<name>` is used to create the
name of the output files, which are written to the `<output-directory>`.  Two
output files are written, one for the raw JSON data and one for the annotated
data, which have the following names:

* `<output-directory>`/geo-location-`<name>`-`<year>`-annotated.json
* `<output-directory>`/geo-location-`<name>`-`<year>`-raw.json

The archived files have the same format as the input raw and annotated files,
so all the utility scripts can also be run on these archive files.


## Development Utilities

The project also contains the files `test-states.py` and `states.csv` which
are useful for testing new geolocation services.  The CSV file contains a list
of all the US states and territories along with a lattitude / longitude
coordinate that is inside each one.  The `test-states.py` utility reads this
CSV file and can be modified to pass each coordinate to a new geolocation
service to see what is returned.
