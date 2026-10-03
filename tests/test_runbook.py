"""The runbook (public spec §14, Further Notes): `docs/operating.md`, read as the owner reads it
months later. Its first-time setup keeps the spec's dependency order, every routine procedure is
there, and what it names (the files in `deploy/`, the units, the variables, the commands) exists
under that name."""

import re
from pathlib import Path

import pytest

from chessop.cli import parse_args
from chessop.hosted import PITCH

ROOT = Path(__file__).parent.parent
RUNBOOK = ROOT / "docs" / "operating.md"
DEPLOY = ROOT / "deploy"


def runbook() -> str:
    return RUNBOOK.read_text()


def sections(text: str, level: str) -> dict[str, str]:
    """The headings of `level` (`##`, `###`) in `text`, each with its body up to the next one of
    that level or above."""
    found = list(re.finditer(rf"^{level} (.+)$", text, re.M))
    bodies = {}
    for i, heading in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        body = text[heading.end() : end]
        higher = re.search(rf"^#{{1,{len(level) - 1}}} ", body, re.M)
        bodies[heading.group(1)] = body[: higher.start()] if higher else body
    return bodies


def section(title_start: str) -> str:
    """The `##` section whose heading starts with `title_start`."""
    matches = [
        body for title, body in sections(runbook(), "##").items() if title.startswith(title_start)
    ]
    assert len(matches) == 1, title_start
    return matches[0]


# The first-time setup in the spec's order (§14), a word each step's heading carries.
FIRST_TIME = [
    "VPS",
    "DNS",
    "SSH",
    "provision.sh",
    "Scaleway",
    "age",
    "environment file",
    "GitHub",
    "first deploy",
    "GoatCounter",
    "UptimeRobot",
    "restore rehearsal",
    "load-test gate",
]


def test_the_first_time_setup_lists_every_step_in_dependency_order() -> None:
    steps = sections(section("First-time setup"), "###")
    titles = list(steps)
    assert len(titles) == len(FIRST_TIME)
    for title, word in zip(titles, FIRST_TIME, strict=True):
        assert word.lower() in title.lower(), (title, word)
    for title, body in steps.items():
        # Each step gives the commands to type or the console clicks to make.
        assert "```" in body or "→" in body, title


def test_the_dns_step_names_every_record_and_the_contact_redirect() -> None:
    dns = next(body for title, body in sections(runbook(), "###").items() if "DNS" in title)
    for record in ("www", "stats", "SPF", "DKIM", "DMARC", "contact@chessop.fr"):
        assert record in dns, record


def test_the_two_steps_before_the_first_publish_are_there() -> None:
    before = section("Before the first publish")
    assert "chessop build-snapshot" in before
    assert "git filter-repo --path token.txt --invert-paths" in before
    assert "revoke" in before.lower()


ROUTINE = [
    "Deploy",
    "Restore from a backup",
    "Rotate the mail key",
    "Answer a data request by email",
    "A data breach",
]


def test_every_routine_procedure_is_there() -> None:
    routine = sections(section("Routine"), "###")
    assert list(routine) == ROUTINE
    restore = routine["Restore from a backup"]
    assert "come back" in restore and "purges" in restore and "by hand" in restore
    breach = routine["A data breach"]
    assert "CNIL" in breach and "72 hours" in breach


def test_the_public_repository_is_described_by_the_pitch() -> None:
    assert PITCH in runbook()
    for topic in ("chess", "openings", "spaced-repetition"):
        assert f"--add-topic {topic}" in runbook()


def test_every_deploy_file_it_names_exists() -> None:
    named = set(re.findall(r"(?<![\w/-])deploy/([\w.@-]+)", runbook()))
    assert named
    for name in named:
        assert (DEPLOY / name).is_file(), name


# Units Debian ships rather than deploy/.
DEBIAN_UNITS = {"caddy.service", "ssh.service"}


def test_every_unit_it_names_is_in_deploy_or_debian() -> None:
    named = set(re.findall(r"\b([a-z][\w-]*@?[\w.-]*?\.(?:service|timer))\b", runbook()))
    assert "chessop.service" in named
    for unit in named:
        template = re.sub(r"@[^.]+\.", "@.", unit)
        assert unit in DEBIAN_UNITS or (DEPLOY / template).is_file(), unit


def test_every_variable_it_names_is_read_by_chessop_or_a_script() -> None:
    sources = "".join(
        path.read_text()
        for path in [*DEPLOY.iterdir(), *(ROOT / "src" / "chessop").glob("*.py")]
        if path.is_file()
    )
    named = set(re.findall(r"\bCHESSOP_[A-Z_]+\b", runbook()))
    assert "CHESSOP_TEM_SECRET_KEY" in named
    for variable in named:
        assert variable in sources, variable


def test_every_script_it_names_exists() -> None:
    for script in set(re.findall(r"\bscripts/([\w.-]+)", runbook())):
        assert (ROOT / "scripts" / script).is_file(), script


def test_every_chessop_command_it_runs_exists() -> None:
    commands = set(re.findall(r"\bbin/chessop ([a-z][\w-]*)|\bchessop ([a-z][\w-]*) --", runbook()))
    named = {first or second for first, second in commands}
    assert {"maintain", "stats", "serve", "build-snapshot"} <= named
    for command in named:
        with pytest.raises(SystemExit) as asked:
            parse_args([command, "--help"])
        assert asked.value.code == 0, command


# "user" only for the machine's users, never for a learner (CONTEXT.md).
MACHINE_USERS = r"(?:admin|system|default|goatcounter|chessop|image's|unprivileged)"


def test_it_speaks_the_glossary() -> None:
    text = runbook()  # "grind" in the pitch only: test_discovery reads this file too
    for found in re.finditer(r"(?<![-\w.])users?\b(?!\.)", text, re.I):  # not -user.email
        before = text[max(0, found.start() - 30) : found.start()]
        machine = re.search(rf"{MACHINE_USERS}[`*]* $", before, re.I)
        ssh_config = re.search(r"\n +$", before)  # `User <admin>` in ~/.ssh/config
        assert machine or ssh_config, before + found.group()
    for avoided in ("profile", "sync your", "import your"):
        assert avoided not in text.lower(), avoided
