const fs = require("node:fs");
const path = require("node:path");

const source = path.join(
  "data",
  "processed",
  "calendar_features_2023-01-01_2026-12-31.csv",
);
const docsDataDir = path.join("docs", "data");
const csvTarget = path.join(
  docsDataDir,
  "calendar_features_2023-01-01_2026-12-31.csv",
);
const jsTarget = path.join(docsDataDir, "calendar_features.js");

fs.mkdirSync(docsDataDir, { recursive: true });

const csv = fs.readFileSync(source, "utf8");
fs.writeFileSync(csvTarget, csv, "utf8");
fs.writeFileSync(
  jsTarget,
  `window.CALENDAR_FEATURES_CSV = ${JSON.stringify(csv)};\n`,
  "utf8",
);

console.log(`Wrote ${csvTarget}`);
console.log(`Wrote ${jsTarget}`);
