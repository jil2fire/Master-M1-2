import { mkdir, copyFile, writeFile } from "node:fs/promises";

const raw = process.env.API_BASE_URL;
if (!raw) throw new Error("API_BASE_URL is required");
const url = new URL(raw);
if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) {
  throw new Error("API_BASE_URL must be HTTPS (or local HTTP)");
}
await mkdir("dist", { recursive: true });
for (const name of ["index.html", "style.css", "app.js"]) {
  await copyFile(name, `dist/${name}`);
}
await writeFile("dist/config.js", `window.APP_CONFIG = { API_BASE_URL: ${JSON.stringify(url.origin)} };\n`);
