"""Static scope rubric and few-shot examples.

This module replaces the original RAG design. The app does not retrieve external
journal documents. Instead, it uses a compact, auditable scope schema that is
embedded in the prompt and mirrored by deterministic features.
"""
from __future__ import annotations

SCOPE_RUBRIC = {
    "in_scope": [
        "The main contribution concerns thermal radiation, radiative heat transfer, thermal emission, emissivity/absorptivity control, or radiation-dominated energy exchange.",
        "Relevant thermal-radiation topics include passive daytime radiative cooling, near-field thermal radiation, thermophotovoltaics, selective thermal emitters/absorbers, mid-infrared thermal photonics, blackbody/emissivity metrology, and radiative transfer in participating media when radiation is central.",
        "The paper should make a technical contribution to thermal-radiation physics, materials, devices, measurement, modeling, or engineering design.",
    ],
    "borderline": [
        "Thermal radiation appears as one component of a broader heat-transfer, energy, building, combustion, or thermal-management study, but is not clearly the central contribution.",
        "The abstract mixes radiation with convection/conduction/CFD or system optimization and does not establish why the radiation component is the novelty.",
        "The paper may be suitable for review only if the editor judges that the radiation mechanism or measurement is technically substantive.",
    ],
    "out_of_scope": [
        "Uses the word radiation in a non-thermal-radiation sense, such as radiation oncology, ionizing radiation, X-ray/gamma exposure, nuclear shielding, wireless electromagnetic exposure, or cosmic radiation.",
        "Primarily concerns generic energy forecasting, battery thermal management, CFD convection, remote sensing, or solar-power operations without a central thermal-radiation contribution.",
        "Mentions radiation only as background, boundary condition, or minor model term.",
    ],
    "insufficient_information": [
        "The title/abstract/keywords are too vague to identify the physical mechanism, method, or central contribution.",
        "The abstract makes broad claims about thermal control, energy systems, AI, or materials without specifying whether thermal radiation is central.",
        "When uncertain, the tool should flag insufficient information rather than inventing scope criteria.",
    ],
}

IN_SCOPE_TERMS = {
    "thermal radiation": 3,
    "radiative heat transfer": 3,
    "near-field thermal radiation": 5,
    "near field thermal radiation": 5,
    "near-field radiative heat transfer": 5,
    "near field radiative heat transfer": 5,
    "thermal emission": 3,
    "thermal emitter": 3,
    "selective emitter": 4,
    "selective absorber": 3,
    "emissivity": 3,
    "absorptivity": 2,
    "radiative cooling": 4,
    "passive daytime radiative cooling": 5,
    "thermophotovoltaic": 4,
    "tpv": 4,
    "blackbody": 3,
    "planck": 2,
    "fluctuational electrodynamics": 5,
    "surface phonon polariton": 4,
    "phonon polariton": 4,
    "hyperbolic metamaterial": 4,
    "nanophotonic": 3,
    "metamaterial": 2,
    "photonic crystal": 3,
    "mid-infrared": 2,
    "mid infrared": 2,
    "spectral selectivity": 3,
    "radiative transfer": 3,
    "participating media": 2,
    "vacuum gap": 2,
    "solar thermal": 2,
    "infrared thermal": 2,
}

BORDERLINE_TERMS = {
    "battery thermal management": 4,
    "thermal management": 2,
    "cfd": 3,
    "computational fluid dynamics": 3,
    "convection": 2,
    "conduction": 2,
    "heat exchanger": 2,
    "combustion": 2,
    "building envelope": 3,
    "furnace": 2,
    "solar receiver": 2,
    "electronics cooling": 3,
    "system optimization": 2,
    "thermal losses": 2,
}

OUT_OF_SCOPE_TERMS = {
    "radiation oncology": 5,
    "radiotherapy": 5,
    "tumor": 4,
    "ionizing radiation": 5,
    "gamma": 4,
    "x-ray": 4,
    "x ray": 4,
    "nuclear": 4,
    "neutron": 4,
    "shielding": 3,
    "wireless": 4,
    "5g": 4,
    "antenna": 4,
    "radiofrequency": 4,
    "cosmic radiation": 5,
    "remote sensing": 4,
    "land surface temperature": 3,
    "medical imaging": 5,
    "ct imaging": 5,
    "mri": 5,
    "uv radiation": 4,
    "skin": 3,
    "solar power forecasting": 5,
    "forecasting": 2,
    "information radiator": 5,
    "software engineering": 4,
    "dashboard": 2,
    "radiation is neglected": 5,
    "radiation is not addressed": 5,
    "thermal emission and radiative heat transfer are not addressed": 5,
}

VAGUE_TERMS = {
    "novel framework": 2,
    "new method": 1,
    "advanced materials": 1,
    "sustainable thermal control": 2,
    "next-generation": 1,
    "broad applications": 2,
    "improved performance": 1,
    "multiphysics optimization": 2,
}

FEW_SHOT_EXAMPLES = [
    {
        "title": "Near-field thermal radiation between patterned SiC membranes",
        "label": "in_scope",
        "why": "The title makes near-field thermal radiation the central mechanism.",
    },
    {
        "title": "Battery pack cooling using a CFD convection model with minor surface radiation terms",
        "label": "borderline",
        "why": "Radiation appears as a submodel inside broader battery thermal management.",
    },
    {
        "title": "Deep learning for solar power output forecasting",
        "label": "out_of_scope",
        "why": "The work is energy-related but not a thermal-radiation contribution.",
    },
    {
        "title": "Radiation oncology dose planning for lung tumors",
        "label": "out_of_scope",
        "why": "The word radiation is used in a biomedical/ionizing-radiation sense.",
    },
    {
        "title": "A new framework for thermal systems",
        "label": "insufficient_information",
        "why": "The submission is too vague to identify mechanism or scope fit.",
    },
]


def rubric_as_text() -> str:
    """Return the scope rubric in compact prompt-ready text."""
    blocks = []
    for label, rules in SCOPE_RUBRIC.items():
        joined = "\n  - ".join(rules)
        blocks.append(f"{label}:\n  - {joined}")
    return "\n\n".join(blocks)


def few_shots_as_text() -> str:
    lines = []
    for ex in FEW_SHOT_EXAMPLES:
        lines.append(f"Title: {ex['title']}\nLabel: {ex['label']}\nReason: {ex['why']}")
    return "\n\n".join(lines)
