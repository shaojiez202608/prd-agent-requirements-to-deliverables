/*
 * Drive a built intake form in jsdom the way a user would: fill every field from an intake JSON,
 * click "Generate", and print the prompt text from the output box.
 *
 * jsdom is not a project dependency. Install it in a scratch folder outside the repo and point NODE_PATH at it:
 *   (cd /tmp/jsdom && npm init -y && npm install jsdom@24)
 *   NODE_PATH=/tmp/jsdom/node_modules node scripts/form_smoke_test.js intake/pm.html sample-data/smart-plug.pm.intake.json
 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const [htmlPath, intakePath] = process.argv.slice(2);
const intake = JSON.parse(fs.readFileSync(intakePath, "utf8"));
const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), { runScripts: "dangerously" });
const w = dom.window, d = w.document;
const schema = JSON.parse(d.getElementById("schema").textContent);
const variant = d.documentElement.innerHTML.match(/var VARIANT = "(\w+)"/)[1];
const visible = (f) => f.variants.indexOf(variant) >= 0;

for (const sec of schema.sections) {
  const src = intake[sec.key] || {};
  for (const f of sec.fields.filter(visible)) {
    const name = `${sec.key}.${f.key}`, v = src[f.key];
    if (f.type === "properties") {
      const rows = Array.isArray(v) ? v : [];
      const addBtn = Array.from(d.querySelectorAll("button")).find((b) => b.textContent.includes("Add property"));
      while (d.querySelectorAll("tr.prop").length < rows.length) addBtn.click();
      d.querySelectorAll("tr.prop").forEach((tr, i) => {
        for (const c of f.columns.filter(visible)) {
          const val = rows[i] ? rows[i][c.key] : undefined;
          tr.querySelector(`[data-col="${c.key}"]`).value = val === undefined ? "" : String(val);
        }
      });
    } else if (f.type === "multi_enum") {
      d.querySelector(`[data-name="${name}"]`).querySelectorAll("input").forEach((c) => {
        c.checked = Array.isArray(v) && v.includes(c.value);
      });
    } else {
      d.querySelector(`[name="${name}"]`).value = v === undefined ? "" : (Array.isArray(v) ? v.join("\n") : String(v));
    }
  }
}
d.getElementById("gen").click();
process.stdout.write(d.getElementById("out").value);
process.stderr.write(d.getElementById("status").textContent + "\n");
