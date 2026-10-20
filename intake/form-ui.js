/* Form rendering and data collection for the offline intake pages. No network, no storage. */
(function () {
  "use strict";
  var schema = JSON.parse(document.getElementById("schema").textContent);
  var form = document.getElementById("intake");
  var NUMERIC = { integer: true, number: true };

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function visible(f) { return f.variants.indexOf(VARIANT) >= 0; }
  function label(f) { return f.label_zh + " / " + f.label_en; }
  function exampleText(f) {
    var ex = f.example;
    if (ex === undefined || ex === "") return "";
    return "例 / e.g. " + (Array.isArray(ex) ? ex.join(", ") : String(ex));
  }

  function input(f, name) {
    if (f.type === "enum") {
      var s = el("select", { name: name });
      s.appendChild(el("option", { value: "" }, "--"));
      f.options.forEach(function (o) { s.appendChild(el("option", { value: o.value }, o.zh + " / " + o.en)); });
      return s;
    }
    if (f.type === "multi_enum") {
      var d = el("div", { "class": "opts", "data-name": name });
      f.options.forEach(function (o) {
        var l = el("label");
        var c = el("input", { type: "checkbox", value: o.value });
        l.appendChild(c);
        l.appendChild(document.createTextNode(" " + o.zh + " / " + o.en));
        d.appendChild(l);
      });
      return d;
    }
    if (f.type === "lines") return el("textarea", { name: name, rows: "4" });
    return el("input", { type: "text", name: name });
  }

  function renderSection(sec) {
    var fs = el("fieldset", { "data-section": sec.key });
    fs.appendChild(el("legend", {}, sec.title_zh + " / " + sec.title_en));
    sec.fields.filter(visible).forEach(function (f) {
      if (f.type === "properties") { fs.appendChild(renderProps(f)); return; }
      var w = el("div", { "class": "f" });
      var l = el("label", { "class": "t" }, label(f) + " ");
      l.appendChild(el("span", { "class": f.required ? "req" : "ex" }, f.required ? "*必填/required" : "选填/optional"));
      w.appendChild(l);
      w.appendChild(input(f, sec.key + "." + f.key));
      w.appendChild(el("div", { "class": "ex" }, exampleText(f)));
      fs.appendChild(w);
    });
    return fs;
  }

  function renderProps(f) {
    var cols = f.columns.filter(visible);
    var w = el("div", { "class": "f" });
    w.appendChild(el("label", { "class": "t" }, label(f) + " *"));
    var t = el("table", { id: "props" });
    var hr = el("tr");
    cols.forEach(function (c) { hr.appendChild(el("th", { title: exampleText(c) }, c.label_zh + (c.required ? "*" : ""))); });
    hr.appendChild(el("th", {}, ""));
    t.appendChild(hr);
    w.appendChild(t);
    var add = el("button", { type: "button" }, "+ 添加属性 / Add property");
    add.onclick = function () { addRow(cols, {}); };
    w.appendChild(add);
    return w;
  }

  function addRow(cols, values) {
    var t = document.getElementById("props");
    var tr = el("tr", { "class": "prop" });
    cols.forEach(function (c) {
      var td = el("td");
      var i = input(c, c.key);
      i.setAttribute("data-col", c.key);
      if (values[c.key] !== undefined && values[c.key] !== null) i.value = String(values[c.key]);
      td.appendChild(i);
      tr.appendChild(td);
    });
    var del = el("button", { type: "button" }, "x");
    del.onclick = function () { tr.parentNode.removeChild(tr); };
    var td2 = el("td"); td2.appendChild(del); tr.appendChild(td2);
    t.appendChild(tr);
  }

  function toValue(f, raw) {
    if (NUMERIC[f.type]) {
      var s = raw.trim();
      if (s === "") return undefined;
      return /^-?[0-9]+(\.[0-9]+)?$/.test(s) ? parseFloat(s) : raw;
    }
    if (f.type === "lines") return raw.replace(/\r\n/g, "\n").split("\n").filter(function (x) { return x.trim() !== ""; });
    return raw === "" ? undefined : raw;
  }

  function collect() {
    var data = { schema_version: schema.schema_version, variant: VARIANT };
    schema.sections.forEach(function (sec) {
      var out = {};
      sec.fields.filter(visible).forEach(function (f) {
        var name = sec.key + "." + f.key;
        if (f.type === "properties") {
          var cols = f.columns.filter(visible);
          out[f.key] = Array.prototype.map.call(document.querySelectorAll("tr.prop"), function (tr) {
            var p = {};
            cols.forEach(function (c) {
              var v = toValue(c, tr.querySelector('[data-col="' + c.key + '"]').value);
              if (v !== undefined) p[c.key] = v;
            });
            return p;
          });
        } else if (f.type === "multi_enum") {
          var box = form.querySelector('[data-name="' + name + '"]');
          var v = Array.prototype.filter.call(box.querySelectorAll("input"), function (c) { return c.checked; })
            .map(function (c) { return c.value; });
          if (v.length) out[f.key] = v;
        } else {
          var val = toValue(f, form.querySelector('[name="' + name + '"]').value);
          if (val !== undefined) out[f.key] = val;
        }
      });
      data[sec.key] = out;
    });
    return data;
  }

  function load(data) {
    schema.sections.forEach(function (sec) {
      var src = (data && data[sec.key]) || {};
      sec.fields.filter(visible).forEach(function (f) {
        var name = sec.key + "." + f.key, v = src[f.key];
        if (f.type === "properties") {
          Array.prototype.forEach.call(document.querySelectorAll("tr.prop"), function (tr) { tr.parentNode.removeChild(tr); });
          (Array.isArray(v) ? v : []).forEach(function (p) { addRow(f.columns.filter(visible), p || {}); });
        } else if (f.type === "multi_enum") {
          var box = form.querySelector('[data-name="' + name + '"]');
          Array.prototype.forEach.call(box.querySelectorAll("input"), function (c) {
            c.checked = Array.isArray(v) && v.indexOf(c.value) >= 0;
          });
        } else {
          var i = form.querySelector('[name="' + name + '"]');
          i.value = v === undefined || v === null ? "" : (Array.isArray(v) ? v.join("\n") : String(v));
        }
      });
    });
  }

  schema.sections.forEach(function (sec) { form.appendChild(renderSection(sec)); });
  addRow(schema.sections[2].fields[0].columns.filter(visible), {});

  var out = document.getElementById("out"), status = document.getElementById("status");
  document.getElementById("gen").onclick = function () {
    var data = collect();
    out.value = PrdIntakeCompiler.compilePrompt(data, schema);
    var n = PrdIntakeCompiler.findPending(data, schema).length;
    status.textContent = n ? ("待确认项 " + n + " 条：提示词为 CLARIFY_ONLY 模式，AI 只会列出问题，不会生成交付物。 / " + n +
      " pending item(s): prompt is CLARIFY_ONLY.") : "无待确认项：提示词为 GENERATE 模式。 / No pending items: GENERATE mode.";
  };
  document.getElementById("copy").onclick = function () { out.select(); document.execCommand("copy"); };
  document.getElementById("export").onclick = function () {
    var blob = new Blob([JSON.stringify(collect(), null, 2) + "\n"], { type: "application/json" });
    var a = el("a", { href: URL.createObjectURL(blob), download: "intake." + VARIANT + ".json" });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };
  document.getElementById("import").onchange = function (ev) {
    var file = ev.target.files[0];
    if (!file) return;
    var r = new FileReader();
    r.onload = function () { try { load(JSON.parse(r.result)); status.textContent = "已导入 / Imported"; }
      catch (e) { status.textContent = "JSON 无法解析 / Invalid JSON"; } };
    r.readAsText(file);
  };
})();
