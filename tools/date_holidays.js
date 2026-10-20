// Prints NZ public holidays from the date-holidays package as JSON: {"2027": [["2027-01-01", "National", "New Year's Day"], ...]}
// Usage: node tools/date_holidays.js 2026 2027
// Only weekdays, so the dates are the observed (Mondayised) dates for a Monday to Friday worker.
const Holidays = require("date-holidays");

// date-holidays state -> our region name (the anniversary day each province observes)
const REGIONS = {
  AUK: "Auckland", WGN: "Wellington", NSN: "Nelson", TKI: "Taranaki", OTA: "Otago", STL: "Southland",
  CAN: "Canterbury", HKB: "Hawke's Bay", MBH: "Marlborough", CIT: "Chatham Islands", WTC: "Westland",
};

const weekday = (iso) => { const d = new Date(iso + "T00:00:00Z").getUTCDay(); return d >= 1 && d <= 5; };
const publicDays = (hd, year) => hd.getHolidays(year).filter((h) => h.type === "public").map((h) => [h.date.slice(0, 10), h.name]);

const out = {};
for (const year of process.argv.slice(2).map(Number)) {
  const national = publicDays(new Holidays("NZ"), year).filter(([d]) => weekday(d));
  const nationalKeys = new Set(national.map(([d, n]) => d + "|" + n));
  const rows = national.map(([d, n]) => [d, "National", n.replace(/ \(substitute day\)$/, "")]);
  for (const [state, region] of Object.entries(REGIONS)) {
    for (const [d, n] of publicDays(new Holidays("NZ", state), year)) {
      if (weekday(d) && !nationalKeys.has(d + "|" + n)) rows.push([d, region, region + " Anniversary Day"]);
    }
  }
  out[year] = rows;
}
process.stdout.write(JSON.stringify(out));
