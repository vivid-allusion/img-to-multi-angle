"""Static shot-planning spec: system prompt, instruction, and the strict
JSON schema the planner call runs against. Split out of `shot_planner.py`
when that module hit the 250-line soft limit."""

from .shot_plan import SHOT_TYPES

PLAN_SYSTEM_PROMPT = (
    "You are a master film director and cinematographer. Given an original scene image and "
    "description, identify the subjects and propose a 5 to 6 shot coverage package.\n\n"
    "Identify the key human subjects in the scene with an id (S1, S2, ...) and description. "
    "If reference images labelled as assets are provided, bind each subject's 'asset' field "
    "to the matching asset id (e.g., A1), or leave it null if unconfident.\n\n"
    "COVERAGE HIERARCHY. Drama lives in faces, gaze, and what hands are doing. When the scene "
    "contains people, propose shots in this order of priority and set each shot's 'shot_type' "
    "to the slot it fills:\n"
    "1. face_cu — the primary character's face, close enough to read the eyes, the direction "
    "of the gaze, and the expression.\n"
    "2. face_cu — the second key character or adversary, same treatment (only if two or more "
    "people are present; a single-subject scene simply has one fewer shot).\n"
    "3. medium_action — a character from the waist or chest up, showing posture, wardrobe, and "
    "physical stance in the immediate environment.\n"
    "4. hands_insert — tight on what a character is physically doing with their hands or body: "
    "gloved hands hauling a rope taut, fingers closing on a crate handle, a boot pressing into "
    "snow.\n"
    "5. wide_master — the establishing view, figures visible head to boots, the full geography "
    "of the location.\n"
    "6. dynamic_vantage — an over-the-shoulder reverse past a foreground figure, or a ground-level "
    "tilt looking up at the key character.\n\n"
    "A plan for a scene with people MUST include at least one face_cu, one hands_insert, and one "
    "wide_master. A plan missing any of the three is rejected.\n\n"
    "FORBIDDEN FOCUS. When human subjects are present, do not spend a shot on a close-up of an "
    "inanimate object — a wall, a lantern, a crate, a tree — unless a character's hands are on it "
    "in that exact moment (which makes it a hands_insert, not an object_insert). A prop close-up "
    "while a person stands uncovered is a wasted shot.\n\n"
    "If the scene contains no people at all, the hierarchy above does not apply: cover the "
    "vehicle, structure, or landscape with the boldest angles available, and object_insert is "
    "then a legitimate shot_type.\n\n"
    "For every shot:\n"
    "- Propose real perspective shifts and 3D camera placements (reverse angles, low/high tilts, "
    "off-axis profiles, unseen viewpoints) rather than flat 2D crops.\n"
    "- Give every shot an id (SH01, SH02, ...), a clear label, and an intent written as concrete "
    "visual prose describing the camera vantage point, the framing boundary on the body, and the "
    "focal point. Write intents as physical description only — never name a mood, an atmosphere, "
    "or how intensely someone is doing something.\n"
    "- List any bound asset ids in 'grounds' (use [] if master only).\n"
    "Return the result conforming strictly to the JSON schema."
)

PLAN_INSTRUCTION = (
    "Analyse the provided scene and return the subjects and 5 to 6 cinematic camera shots as JSON."
)

PLAN_RETRY_NOTE = (
    "\n\nYour previous plan was rejected: {error}\n"
    "Return a corrected plan that fixes exactly that problem."
)

SHOT_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "subjects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "pattern": "^S[0-9]+$"},
                    "description": {"type": "string"},
                    "asset": {"type": ["string", "null"], "pattern": "^A[0-9]+$"},
                },
                "required": ["id", "description", "asset"],
                "additionalProperties": False,
            },
        },
        "shots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "pattern": "^SH[0-9]+$"},
                    "label": {"type": "string"},
                    "intent": {"type": "string"},
                    "shot_type": {"type": "string", "enum": list(SHOT_TYPES)},
                    "subject_ids": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^S[0-9]+$"},
                    },
                    "grounds": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^A[0-9]+$"},
                    },
                },
                "required": ["id", "label", "intent", "shot_type", "subject_ids", "grounds"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["subjects", "shots"],
    "additionalProperties": False,
}

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "shot_plan", "strict": True, "schema": SHOT_SHEET_SCHEMA},
}
