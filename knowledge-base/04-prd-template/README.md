# 04 PRD template

Template: `PRD.template.md` in this folder. Placeholders `{{name}}` are filled by the reference generator; an agent
fills the same sections by hand.

Section order is fixed and follows the intake order:
1. Background and scenario, 2. Scope, 3. Hardware and device side, 4. Functional requirements (thing model, with
the control mapping table between `<!-- dp-table:begin -->` and `<!-- dp-table:end -->`), 5. Cloud panel and
application side, 6. App interaction flow, 7. Constraints and non-functional requirements, 8. Acceptance criteria,
9. Open items to confirm, 10. Deliverable index.

The PRD is the single document that later deliverables (architecture, quick-start, panel, demo) trace back to.
Anything not in the intake goes to section 9, never into the body as an assumption.
