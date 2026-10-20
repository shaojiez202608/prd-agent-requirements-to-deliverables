# Contributing

Thanks for your interest. This is a prototype; small, focused changes are easiest to review.

1. Open an issue that describes the problem or idea before large changes.
2. Keep the knowledge-base numbering: rules in the lowest fitting folder, cases only in `10-project-cases`.
3. If you change `src/prd_agent/intake.py` or `src/prd_agent/prompt.py`, make the same change in
   `intake/compiler.js`; `tests/test_js_parity.py` must pass.
4. If you change templates, the schema or `knowledge-base/00-project-rules/system-prompt.md`, regenerate the
   committed outputs:
   ```
   uv run prd-agent build-forms
   uv run prd-agent generate sample-data/smart-plug.pm.intake.json --out examples/smart-plug
   for v in pm frontline missing-fields; do
     uv run prd-agent compile-prompt sample-data/smart-plug.$v.intake.json --out examples/prompts/smart-plug.$v.prompt.txt
   done
   ```
5. Run `uv run ruff check .` and `uv run pytest` before opening a pull request.
6. Use synthetic data only. Do not add real company, customer, product, person or module names, or any credentials.
