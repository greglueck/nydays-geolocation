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
  [--email <email>] [--limit <number>] [--delete-changed] [--delete-missing]
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

When you run "annotate.py" a second (or subsequent) time, it may identify old
entries from `<annotated-file>` that are no longer in the new `<raw-file>` or
old entries from `<annotated-file>` that have changed in the new `<raw-file>`.
This can happen if Google decides to delete or change some historical data from
your timeline.  In this case you can use either the `--delete-changed` or
`--delete-missing` options.  The `--delete-changed` option removes all entries
from `<annotated-file>` that are different in `<raw-file>`.  As a result, those
entries from `<raw-file>` are annotated and added to `<annotated-file>` thus
replacing the previous annotated entries.  The `--delete-missing` option
removes entries from `<annotated-file>` that are missing in `<raw-file>`.  As a
result, those entries are removed from your geolocation history.

The `--geocoder` option allows you to select a reverse geocoding service to
translate the latitude / longitude coordinates to a US state.  The default
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
that are less accurate.  The default setting shows only the entries that are
very accurate (an accuracy value of 800 or less).  Specify a larger value to
display more entries or specify `--accuracy 0` to disable the filter and
display all entries.

### check.py

This utility assumes you care about the number of days spent in NY state, and
it assumes you have maintained an Excel spreadsheet recording this data.  The
utility compares information from the spreadsheet with the location data and
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
whether these days were spent in NY: an empty value indicates the days were
not in NY whereas any other values indicates that days were spent in NY.
The spreadsheet data ends when a row has a blank entry in either column 1 or
column 3.  The script ignores the contents of the other columns (2, 4, and any
columns after 5).

### archive.py

This utility archives the location data for a particular year or for a range
of years.  Usage is like:

```
$ python archive.py -r <raw-file> -a <annotated-file> \
  [-y <year> | -b <begin> -e <end>] \
  -n <name> -o <output-directory>
```

The `<raw-file>` and `<annotated-file>` specify the pathnames to the raw and
annotated JSON files.  The year(s) to archive can either be specifed as a
single `<year>` or as a range `<begin>` and `<end>`.  These values are
numbers, for example `-b 2020 -e 2022` archives the location data coresponding
to the days in years 2020 - 2022 (inclusive).

The `<name>` is used to create the name of the output files, which are written
to the `<output-directory>`.  Two output files are written, one for the raw
JSON data and one for the annotated data, which have the following names:

* `<output-directory>`/geo-location-`<name>`-`<year>`-annotated.json
* `<output-directory>`/geo-location-`<name>`-`<year>`-raw.json

or:

* `<output-directory>`/geo-location-`<name>`-`<begin>`-`<end>`-annotated.json
* `<output-directory>`/geo-location-`<name>`-`<begin>`-`<end>`-raw.json

The archived files have the same format as the input raw and annotated files,
so all the utility scripts can also be run on these archived files.


## Formats of the raw and annotated JSON files

The raw and annotated JSON files have similar formats.  The raw file looks
like this:

```
{
  "locations": [{
    "latitudeE7": <integer>,
    "longitudeE7": <integer>,
    "accuracy": <integer>,
    "timestamp": <string>
    /* other entries */
  },
  ...
  ]
}
```

The annotated file adds "geocoder" and "state" fields:

```
{
  "geocoder": <string>,
  "locations": [{
    "latitudeE7": <integer>,
    "longitudeE7": <integer>,
    "accuracy": <integer>,
    "timestamp": <string>,
    "state": <string>
  },
  ...
  ]
}
```

The meaning of each field is as follows:

* `"geocoder"`: A string telling the geocoding service that was used to reverse
  geocode the location data in the annotated JSON file.  Possible values are:

  - `"local"`: The Python package "reverse_geocoder", which runs locally.
  - `"osm"`: The Nominatim web service from openstreetmap.org.

* `"locations"`: Google location history periodically records an entry telling
  the location of your mobile device.  These entries are sorted by increasing
  timestamp.

* `"latitudeE7"`: An integer telling the latitude of the location.  The value
  is the latitude multiplied by 1E7.

* `"longitudeE7"`: An integer telling the longitude of the location.  The value
 is the longitude multiplied by 1E7.

* `"accuracy"`: The approximate accuracy of the location in meters.  A smaller
  value indicates higher accuracy.

* `"timestamp"`: The time at which the entry was recorded, a string in
  [ISO-8601][1] format.

* `"state"`: A string telling the US state that contains this location entry.
  The values follow the 2-letter [USPS abbreviations][2] for the 50 US states
  plus the District of Columbia.  The value "EX" indicates a location that is
  outside of the US.

The `"latitudeE7"`, `"longitudeE7"`, `"accuracy"`, and `"timestamp"` fields
come directly from the raw Google takeout data, which is documented more fully
[here][3].

[1]: <https://en.wikipedia.org/wiki/ISO_8601>
[2]: <https://about.usps.com/who-we-are/postal-history/state-abbreviations.htm>
[3]: <https://locationhistoryformat.com/reference/records/>


## Development Utilities

The project also contains the files `test-states.py` and `states.csv` which
are useful for testing new geolocation services.  The CSV file contains a list
of all the US states and territories along with a latitude / longitude
coordinate that is inside each one.  The `test-states.py` utility reads this
CSV file and can be modified to pass each coordinate to a new geolocation
service to see what is returned.
