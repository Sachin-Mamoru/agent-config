#!/usr/bin/env python3
"""Static checks for agent-config: skill frontmatter, names, links, profiles, scripts.

Usage: python3 scripts/validate.py

Rules follow the strictest of the configured agents: VS Code Copilot requires `name`
(== directory, lowercase/digits/hyphens, <= 64 chars) and `description` (<= 1024 chars)
and skips invalid skills silently; Claude Code treats both as optional. Problems in a skill
that some profile installs are errors; in other skills they are warnings.
Exit code 1 if any error.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = {"synced", "anthropic-skills"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

errors: list[str] = []
warnings: list[str] = []


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            fields[key] = "" if value in (">", ">-", "|", "|-") else value.strip("'\"")
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def profiled_skills() -> dict[str, list[str]]:
    used: dict[str, list[str]] = {}
    for pfile in sorted((ROOT / "profiles").glob("*.txt")):
        for raw in pfile.read_text().splitlines():
            name = raw.strip()
            if name and not name.startswith("#"):
                used.setdefault(name, []).append(pfile.stem)
    return used


def check_skills(used: dict[str, list[str]]) -> None:
    seen: dict[str, Path] = {}
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        d = skill_md.parent.name
        report = errors if d in used else warnings
        fm = parse_frontmatter(skill_md.read_text())
        if fm is None:
            report.append(f"skills/{d}: no YAML frontmatter (Copilot skips it; Claude Code guesses name/description)")
            continue
        name, desc = fm.get("name", ""), fm.get("description", "")
        if not name:
            report.append(f"skills/{d}: missing `name`")
        elif name != d:
            report.append(f"skills/{d}: name `{name}` != directory name")
        elif not NAME_RE.match(name) or len(name) > 64:
            report.append(f"skills/{d}: name must be lowercase letters/digits/hyphens, <= 64 chars")
        if name in RESERVED:
            errors.append(f"skills/{d}: `{name}` is a reserved skill name")
        if not desc:
            report.append(f"skills/{d}: missing `description`")
        elif len(desc) > 1024:
            report.append(f"skills/{d}: description is {len(desc)} chars (> 1024, Copilot rejects it)")
        if name and name in seen:
            errors.append(f"duplicate skill name `{name}`: {seen[name]} and {skill_md}")
        seen[name] = skill_md
    for name, profiles in used.items():
        if not (ROOT / "skills" / name / "SKILL.md").is_file():
            errors.append(f"profile(s) {', '.join(profiles)} list `{name}` but skills/{name}/SKILL.md doesn't exist")


def check_links() -> int:
    count = 0
    files = [*ROOT.glob("*.md"), *ROOT.glob("skills/**/*.md"), *ROOT.glob("templates/*.md"), *ROOT.glob("commands/*.md")]
    for md in files:
        text = re.sub(r"```.*?```", "", md.read_text(), flags=re.S)
        for target in LINK_RE.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            count += 1
            path = target.split("#", 1)[0]
            if path and not (md.parent / path).exists():
                errors.append(f"{md.relative_to(ROOT)}: broken relative link -> {target}")
    return count


def check_commands() -> None:
    for cmd in sorted((ROOT / "commands").glob("*.md")):
        fm = parse_frontmatter(cmd.read_text())
        if not fm or not fm.get("description"):
            errors.append(f"{cmd.relative_to(ROOT)}: missing `description` frontmatter")


def check_symlinks() -> None:
    for link in ROOT.rglob("*"):
        if ".git" in link.parts or not link.is_symlink():
            continue
        target = link.readlink()
        if target.is_absolute():
            errors.append(f"{link.relative_to(ROOT)}: absolute symlink -> {target} (use a relative target)")
        elif not link.exists():
            errors.append(f"{link.relative_to(ROOT)}: broken symlink -> {target}")


def check_scripts() -> None:
    for sh in sorted((ROOT / "scripts").glob("*.sh")):
        r = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True)
        if r.returncode:
            errors.append(f"{sh.relative_to(ROOT)}: bash syntax error: {r.stderr.strip()}")


def main() -> int:
    used = profiled_skills()
    check_skills(used)
    links = check_links()
    check_commands()
    check_symlinks()
    check_scripts()
    n_skills = len(list((ROOT / "skills").glob("*/SKILL.md")))
    print(f"checked {n_skills} skills, {len(used)} profiled, {links} relative links")
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
