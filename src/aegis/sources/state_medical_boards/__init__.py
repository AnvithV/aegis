"""State medical board disciplinary action ingestion."""

from __future__ import annotations

from aegis.sources.state_medical_boards.california import CaliforniaMBC
from aegis.sources.state_medical_boards.florida import FloridaDOH
from aegis.sources.state_medical_boards.illinois import IllinoisIDFPR
from aegis.sources.state_medical_boards.massachusetts import MassachusettsBORM
from aegis.sources.state_medical_boards.michigan import MichiganLARA
from aegis.sources.state_medical_boards.new_jersey import NewJerseyDCA
from aegis.sources.state_medical_boards.new_york import NewYorkOPMC
from aegis.sources.state_medical_boards.ohio import OhioSMBO
from aegis.sources.state_medical_boards.pennsylvania import PennsylvaniaPSMB
from aegis.sources.state_medical_boards.texas import TexasTMB

__all__ = [
    "CaliforniaMBC",
    "FloridaDOH",
    "IllinoisIDFPR",
    "MassachusettsBORM",
    "MichiganLARA",
    "NewJerseyDCA",
    "NewYorkOPMC",
    "OhioSMBO",
    "PennsylvaniaPSMB",
    "TexasTMB",
]
