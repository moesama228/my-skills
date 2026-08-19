#!/usr/bin/env node

import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const [, , inputHtml, outputPdf, outlineFlag] = process.argv;

if (!inputHtml || !outputPdf) {
  console.error("Usage: render_html_to_pdf.mjs <input.html> <output.pdf> [outline]");
  process.exit(1);
}

const baseDir = process.env.MERMAID_PUPPETEER_BASE;
if (!baseDir) {
  console.error("MERMAID_PUPPETEER_BASE is required.");
  process.exit(1);
}

const requireFromBase = createRequire(new URL("./package.json", pathToFileURL(`${baseDir}/`)));
const puppeteer = requireFromBase("puppeteer");

const browser = await puppeteer.launch({
  executablePath: puppeteer.executablePath(),
  args: ["--no-sandbox"],
  headless: true,
});

try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(inputHtml).href, { waitUntil: "networkidle0" });
  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  });

  const pdfOptions = {
    path: outputPdf,
    format: "A4",
    printBackground: true,
    margin: {
      top: "16mm",
      right: "14mm",
      bottom: "16mm",
      left: "14mm",
    },
    preferCSSPageSize: true,
  };

  if (outlineFlag !== "false") {
    pdfOptions.outline = true;
  }

  await page.pdf(pdfOptions);
} finally {
  await browser.close();
}
