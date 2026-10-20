# 05 Quick-start guide template

Template: `quick-start.template.md`. Audience: external developers. Rendered to PDF with `prd-agent render-pdf`.

Rules:
- Keep the data point table between the dp-table markers; columns Control, Identifier, ID, Access, Interaction.
- Message bodies are illustrative and vendor-neutral. Say so in the text.
- Never include credentials, endpoints or account identifiers. Point to the platform's secret store.
- The built-in PDF font covers Latin-1 only. Write this guide in English or supply a Unicode font
  (see docs/architecture.md, limitations).
- Re-render the PDF after every change to the Markdown. The PDF stores the SHA-256 of its source and the validator
  reports a stale PDF.
