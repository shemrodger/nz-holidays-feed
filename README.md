# NZ public holidays feed

New Zealand public holidays and regional anniversary days, one JSON file per year, at `{year}/NZ.json`.

- Dates are the observed (Mondayised) dates for a Monday to Friday worker.
- Source: Employment New Zealand, https://employment.govt.nz/leave-and-holidays/public-holidays/public-holidays-and-anniversary-dates
- Every year in this feed is checked against that page by automated tests before it is published.
- Employment New Zealand notes that regional dates can contain errors. Check them with the local council.
- The format matches the Nager.Date API (`date`, `localName`, `name`, `countryCode`, `global`, `counties`, `types`).
- Use the English `name` to tell the two Canterbury days apart: both carry the code NZ-CAN.

Years in this feed: 2026, 2027.

No warranty. Check the dates before you rely on them.
