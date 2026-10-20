"""Command line entry point: ``prd-agent <command>``.

Exit codes: 0 ok, 1 check failed, 2 insufficient input (pending items), 3 usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import changes, consistency, forms, generate, intake, pdf, progress, prompt, publish


def _load(path: str):
    try:
        return intake.load_intake(Path(path))
    except (OSError, ValueError) as exc:
        print(f"error: cannot read intake {path}: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc


def cmd_check_intake(a) -> int:
    pending = intake.find_pending(_load(a.intake))
    if not pending:
        print("Intake is sufficient: 0 pending items.")
        return 0
    print(f"Pending confirmation items ({len(pending)}). Deliverables will not be generated until they are confirmed:")
    for p in pending:
        print(p.render())
    return 2


def cmd_compile_prompt(a) -> int:
    text = prompt.compile_prompt(_load(a.intake))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def cmd_generate(a) -> int:
    data = _load(a.intake)
    try:
        result = generate.generate(data, Path(a.out), log=print)
    except generate.InsufficientInput as exc:
        print(f"Not generating: {len(exc.pending)} pending confirmation item(s).")
        for p in exc.pending:
            print(p.render())
        return 2
    except (pdf.PdfTextError, OSError, KeyError) as exc:
        print(f"error: generation failed, {a.out} was not changed: {exc}", file=sys.stderr)
        return 3
    print(f"Wrote {len(result.files)} files to {a.out}")
    if not result.ok:
        print("Validation: FAIL. The files were written for inspection; see PROGRESS.md and run prd-agent validate.",
              file=sys.stderr)
        return 1
    return 0


def cmd_validate(a) -> int:
    report = consistency.check_folder(Path(a.folder), required=a.require or None)
    sys.stdout.write(report.to_json() if a.format == "json" else report.render_text())
    return 0 if report.ok else 1


def cmd_check_progress(a) -> int:
    problems = progress.check_progress(Path(a.folder))
    if not problems:
        print("Progress log: PASS (6 reports, file lists complete)")
        return 0
    print(f"Progress log: FAIL ({len(problems)} problem(s))")
    for p in problems:
        print(p.render())
    return 1


def cmd_render_pdf(a) -> int:
    src = Path(a.markdown)
    out = Path(a.out) if a.out else src.with_suffix(".pdf")
    try:
        pdf.render_markdown_pdf(src.read_text(encoding="utf-8"), out, title=src.stem)
    except pdf.PdfTextError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    print(f"Wrote {out}")
    return 0


def cmd_diff_model(a) -> int:
    old = json.loads(Path(a.old).read_text(encoding="utf-8"))
    new = json.loads(Path(a.new).read_text(encoding="utf-8"))
    found = changes.diff_models(old, new)
    sys.stdout.write(changes.render_changes(found))
    return 1 if any(c.breaking for c in found) and a.fail_on_breaking else 0


def cmd_build_forms(a) -> int:
    for p in forms.build_all(Path(a.out) if a.out else None):
        print(f"Wrote {p}")
    return 0


def cmd_publish(a) -> int:
    try:
        m = publish.publish(Path(a.folder), a.dest, a.name)
    except publish.PublishRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(f"Published {len(m['files'])} files as bundle {a.name} to {a.dest}")
    return 0


def cmd_fetch(a) -> int:
    m = publish.fetch(a.source, a.name, Path(a.out))
    print(f"Fetched and verified {len(m['files'])} files into {a.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prd-agent", description="Structured intake to consistent IoT deliverables")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("check-intake", help="list pending confirmation items (exit 2 if any)")
    s.add_argument("intake")
    s.set_defaults(fn=cmd_check_intake)

    s = sub.add_parser("compile-prompt", help="deterministic prompt text from an intake JSON")
    s.add_argument("intake")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_compile_prompt)

    s = sub.add_parser("generate", help="local reference generator (mock agent); refuses on pending items")
    s.add_argument("intake")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_generate)

    s = sub.add_parser("validate", help="cross-deliverable consistency check keyed on property ID")
    s.add_argument("folder")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s.add_argument("--require", nargs="*", help="files that must exist (default: planned files or FR-7 core files)")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("check-progress", help="verify PROGRESS.md against the files on disk")
    s.add_argument("folder")
    s.set_defaults(fn=cmd_check_progress)

    s = sub.add_parser("render-pdf", help="render quick-start.md to PDF")
    s.add_argument("markdown")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_render_pdf)

    s = sub.add_parser("diff-model", help="change log between two thing-model.json versions")
    s.add_argument("old")
    s.add_argument("new")
    s.add_argument("--fail-on-breaking", action="store_true")
    s.set_defaults(fn=cmd_diff_model)

    s = sub.add_parser("build-forms", help="rebuild intake/frontline.html and intake/pm.html")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_build_forms)

    s = sub.add_parser("publish", help="publish a validated folder to a local dir or s3://bucket/prefix")
    s.add_argument("folder")
    s.add_argument("--dest", required=True)
    s.add_argument("--name", required=True, help="bundle name, e.g. demo-smart-plug-v1")
    s.set_defaults(fn=cmd_publish)

    s = sub.add_parser("fetch", help="download a bundle and verify checksums")
    s.add_argument("source")
    s.add_argument("--name", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_fetch)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
