import { chromium } from "playwright";
import process from "node:process";

const [, , sourceUrl, outputPath] = process.argv;

if (!sourceUrl || !outputPath) {
  console.error("Usage: node scripts/render_pdf.mjs <sourceUrl> <outputPath>");
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.goto(sourceUrl, { waitUntil: "networkidle" });
await page.pdf({
  path: outputPath,
  format: "A4",
  printBackground: true,
  margin: {
    top: "14mm",
    right: "10mm",
    bottom: "14mm",
    left: "10mm",
  },
});
await browser.close();
console.log(outputPath);
