# NZ public holidays feed

New Zealand public holidays and regional anniversary days, one JSON file per year, at `{year}/NZ.json`.
For example: `https://shemrodger.github.io/nz-holidays-feed/2027/NZ.json`.
`years.json` lists the years in the feed and the latest one.

- Dates are the observed (Mondayised) dates for a Monday to Friday worker.
- The format matches the Nager.Date API: `date`, `localName`, `name`, `countryCode`, `global`, `counties`, `types`.
- Use the English `name` to tell the two Canterbury days apart: both carry the code NZ-CAN.

## How it stays current
A GitHub Actions job runs on the 1st of each month. It rebuilds this year and the next 3 years from two
open-source packages (Python `holidays` and `date-holidays`), and publishes only when:
1. both packages agree,
2. the years we checked by hand (`verified/`) come out exactly the same, and
3. every year shown on the Employment NZ page comes out exactly the same:
   https://employment.govt.nz/leave-and-holidays/public-holidays/public-holidays-and-anniversary-dates

If a check fails, nothing is published and the job opens a GitHub issue.

Years in this feed: 2026, 2027, 2028, 2029. Last checked: 2026-10-21.

No warranty. Employment NZ notes that regional dates can contain errors. Check them with the local council.
