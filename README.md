# nydays-geolocation

This project contains a set of utilities that correlate geolocation data from
Google's Timeline to US states.  The intent is to use the geolocation data to
help identify days spent in NY state for tax purposes, but much of the logic
in the utilities could be used to identify days spent in any US state.

The utilities assume you have enabled Google Timeline on a mobile device and
have exported the Timeline data to a JSON file.  We refer to this downloaded
file as the "raw JSON file".  Once you have this raw JSON file, you can use
the following utilities.

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
  [--email <email>] [--limit <number>] [--use-cache <annotated-file>]
```

The `<raw-file>` is the pathname to the JSON file exported from Google
Timeline, and the `<annotated-file>` is the pathname to the annotated JSON file
which the utility either creates or updates.  The first time you run this
utility, it creates an annotated file with data from the raw file.  The
expectation is that you save the annotated file and periodically update it as
you collect more location data on your mobile device.

After your mobile device collects more location data, you can export the
Timeline data again and run the "annotate.py" utility again with the newly
exported raw JSON file.  The utilility will compare the content from
`<raw-file>` to the content from `<annotated-file>` and identify the new
location data.  The utility then annotates only this new data and updates
`<annotated-file>`.

If you get a new mobile device, you may find that the Timeline data from the new
device does not contain data collected by the old device.  In this case, you
can pass multiple `-r` options, each specifying the raw Timeline data from one
of your mobile devices.  The "annotate.py" utility will annotate data from all
raw files and create a single annotated file.  The order of the `-r` options is
important.  Raw files with older Timeline data should be specified before raw
files with newer data.

The `--geocoder` option allows you to select a reverse geocoding service to
translate the latitude / longitude coordinates to a US state.  The default
uses a service that runs locally.  This runs quickly but may be less
accurate.  The other option "osm" uses the open street map Nominatim service,
which runs remotely.  This is much slower but also more accurate.  Using the
"osm" service requires specifying your email address with `--email`, and the
service may reject requests if you exceed their terms of use.  The `--limit`
option may be useful to avoid exceeding these limits, allowing you to annotate
the `<raw-file>` piecemeal with several runs of the utility.

Because the reverse geocoding service may be slow, it helps to avoid making
redundant geocoding requests for coordinates that have been previously mapped
to a US state.  The `--use-cache` option provides a way to use the contents of
another annotated file to avoid these redundant geocoding requests.  If the
coordinates in the `<raw-file>` have already been mapped to a US state in the
`--use-cache` file, then the state from the `--use-cache` file is used instead
of making a new geocoding request.  The `--use-cache` option may be passed
multiple times if you have several other annotated files.

### visualize.py

This utility creates a spreadsheet where each row is a day and the columns
show the number of location data entries on that day broken down by each US
state.  Usage is like:

```
$ python visualize.py -a <annotated-file> -o <csv-file>
```

### check.py

This utility assumes you care about the number of days spent in NY state, and
it assumes you have maintained an Excel spreadsheet recording this data.  The
utility compares information from the spreadsheet with the location data and
flags any mismatches.  For example, if the spreadsheet records that a day was
spent outside of NY and the location data has an entry that is inside of NY on
that day, the utility will flag this as an error.

Usage is like:

```
$ python check.py -a <annotated-file> -w <workbook> -s <sheet>
```

The `workbook` specifies the pathname of the Excel workbook file, and
`<sheet>` is the name of the spreadsheet in that workbook.

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
  [-y <year> | -b <begin> -e <end>]  -n <name> -o <output-directory>
```

The `<raw-file>` and `<annotated-file>` specify the pathnames to the raw and
annotated JSON files.  The `-r` option can be repeated if there is more than
one raw timeline file.  The year(s) to archive can either be specifed as a
single `<year>` or as a range `<begin>` and `<end>`.  These values are
numbers, for example `-b 2020 -e 2022` archives the location data coresponding
to the days in years 2020 - 2022 (inclusive).

The `<name>` is used to create the name of the output files, which are written
to the `<output-directory>`.  One output file is written for the annotated data,
and one is written for each raw data file that has timestamp entries in the
specified year(s).  When there is just one raw file, the files are named like
this:

* `<output-directory>`/geo-location-`<name>`-`<year>`-annotated.json
* `<output-directory>`/geo-location-`<name>`-`<year>`-raw.json

or:

* `<output-directory>`/geo-location-`<name>`-`<begin>`-`<end>`-annotated.json
* `<output-directory>`/geo-location-`<name>`-`<begin>`-`<end>`-raw.json

When there are multiple raw files, they are named with a numeric suffix like:

* `<output-directory>`/geo-location-`<name>`-`<year>`-raw-1.json
* `<output-directory>`/geo-location-`<name>`-`<year>`-raw-2.json

The archived files have the same format as the input raw and annotated files,
so all the utility scripts can also be run on these archived files.


## Formats of the raw and annotated JSON files

The raw and annotated JSON files have similar formats.  The raw file is a list
of records (dictionaries), where each record has `"startTime"` and `"endTime"`
fields telling the time range for data in that record.  The remaining fields
depend on the type of record.  The scripts in this project only use the records
with this format:

```
{
  "startTime": "2023-01-02T18:00:00.000Z",
  "endTime": "2023-01-02T20:00:00.000Z",
  "timelinePath": [
    {
      "durationMinutesOffsetFromStartTime": "74",
      "point": "geo:40.756212,-73.967541"
    },
    ...
  ]
},
{
  "startTime": "2023-01-02T20:00:00.000Z",
  "endTime": "2023-01-02T22:00:00.000Z",
  "timelinePath": [
    {
      "durationMinutesOffsetFromStartTime": "7",
      "point": "geo:40.766989,-73.972554"
    },
    ...
  ]
},
...
```

The raw  JSON file has many of these records, sorted by their `"startTime"`.
Each record contains a list of `"timelinePath"` entries, where each of those
entries describes one geolocation point.

`"startTime"`: The starting time for geolocation points in this record.  This
field is a timestamp in [ISO-8601][1] format.

`"endTime"`: The ending time for geolocaiton points in this record.  This field
is also a timestamp in [ISO-8601][1] format.

`"timelinePath"`: A list of geolocation point records.

`"durationMinutesOffsetFromStartTime"`: The offset (in minutes) from
`"startTime"` for this geolocation point.

`"point"`: The latitude and longitude for this geolocation point.  The mobile
device was at this location at the timestamp specified by `startTime +
durationMinutesOffsetFromStartTime`.

The annotated file adds `"geocoder"` and `"state"` fields to each of the
`"timelinePath"` records like this:

```
{
  "startTime": "2023-01-02T18:00:00.000Z",
  "endTime": "2023-01-02T20:00:00.000Z",
  "timelinePath": [
    {
      "durationMinutesOffsetFromStartTime": "74",
      "point": "geo:40.756212,-73.967541",
      "geocoder": "osm",
      "state": "NY"
    },
    ...
  ]
},
...
```

`"geocoder"`: A string telling the geocoding service that was used to reverse
geocode the `"point"` coordinates.  Possible values are:

* `"local"`: The Python package "reverse_geocoder", which runs locally.
* `"osm"`: The Nominatim web service from openstreetmap.org.

`"state"`: A string telling the US state that contains the `"point"`
coordinates.  The values follow the 2-letter [USPS abbreviations][2] for the
50 US states plus the District of Columbia.  The value "EX" indicates a
location that is outside of the US.

[1]: <https://en.wikipedia.org/wiki/ISO_8601>
[2]: <https://about.usps.com/who-we-are/postal-history/state-abbreviations.htm>


## Development Utilities

The project also contains the files `test-states.py` and `states.csv` which
are useful for testing new geolocation services.  The CSV file contains a list
of all the US states and territories along with a latitude / longitude
coordinate that is inside each one.  The `test-states.py` utility reads this
CSV file and can be modified to pass each coordinate to a new geolocation
service to see what is returned.
