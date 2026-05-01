"""Load apex roster YAML files into an ApexRosterStore."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from aegis.sources.apex_rosters import ApexMembership, ApexRosterStore, ApexRosterType

logger = logging.getLogger(__name__)

_DEFAULT_ROSTER_DIR = Path("data/apex_rosters")


def load_apex_rosters(roster_dir: Path | None = None) -> ApexRosterStore:
    """Load all *.yaml files from roster_dir into an ApexRosterStore."""
    d = roster_dir or _DEFAULT_ROSTER_DIR
    store = ApexRosterStore()

    if not d.exists():
        logger.warning("Apex roster directory %s does not exist", d)
        return store

    for yaml_path in sorted(d.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not data or "members" not in data:
                logger.warning("Skipping %s: no 'members' key", yaml_path.name)
                continue

            roster_type = ApexRosterType(data["roster_type"])
            memberships: list[ApexMembership] = []
            for member in data["members"]:
                memberships.append(
                    ApexMembership(
                        roster_type=roster_type,
                        name=member["name"],
                        year=member.get("year"),
                        institution=member.get("institution"),
                        confidence=1.0,
                    )
                )
            store.add_batch(memberships)
            logger.info("Loaded %d members from %s", len(memberships), yaml_path.name)
        except Exception:
            logger.warning("Failed to load %s", yaml_path.name, exc_info=True)

    logger.info("Apex roster store: %d total members", store.count())
    return store
