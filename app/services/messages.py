# -*- coding: utf-8 -*-
"""All user-facing copy, keyed by language.

Once the user picks a language every reply comes from that language's
block, so the UI is never mixed. The only bilingual screen is the
language prompt itself, which the user sees before choosing.

WhatsApp enforces length caps on interactive fields and rejects the
whole message with a 400 (#131009) if any field is over. The caps are
counted in code points, and Tamil spends roughly twice as many code
points as it shows glyphs, so LIMITS is checked at import time.
"""

DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES = ("en", "ta")

LANGUAGE_IDS = {
    "lang_en": "en",
    "lang_ta": "ta",
}

# Free-text answers accepted instead of tapping a button.
LANGUAGE_KEYWORDS = {
    "1": "en",
    "en": "en",
    "eng": "en",
    "english": "en",
    "2": "ta",
    "ta": "ta",
    "tam": "ta",
    "tamil": "ta",
    "தமிழ": "ta",
    "தமிழ்": "ta",
}


# ----------------------------------------
# LANGUAGE PROMPT (the one bilingual screen)
# ----------------------------------------

INTRO = {
    "body": (
        "\U0001f64f Hello! I am *Thuyan*, the Solid Waste "
        "Management Bot.\n\n"
        "I take your solid waste complaints straight to the "
        "Control room.\n\n"
        "Please choose your language.\n\n"
        "─────────\n\n"
        "\U0001f64f வணக்கம்! நான் *தூயன்*, திடக்கழிவு "
        "மேலாண்மை உதவியாளர்.\n\n"
        "உங்கள் திடக்கழிவு புகார்களை நேரடியாக மாவட்ட "
        "ஆட்சியரிடம் கொண்டு சேர்க்கிறேன்.\n\n"
        "உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்."
    ),
    "buttons": [
        {"id": "lang_en", "title": "English"},
        {"id": "lang_ta", "title": "தமிழ்"},
    ],
}


# ----------------------------------------
# COMPLAINT LIST MENU
# ----------------------------------------

MENU = {
    "en": {
        "header": "Complaint Registration",
        "body": (
            "Please select your complaint from the list below."
        ),
        "footer": "Select one option",
        "button": "View complaints",
        "section": "Complaint options",
        "rows": [
            {
                "id": "complaint_1",
                "title": "Vehicle didn't come",
                "description": (
                    "Collection vehicle did not come today"
                ),
            },
            {
                "id": "complaint_2",
                "title": "Vehicle absent for days",
                "description": (
                    "Vehicle has not come for the past few days"
                ),
            },
            {
                "id": "complaint_3",
                "title": "No audio announcement",
                "description": (
                    "Audio announcement was not played"
                ),
            },
            {
                "id": "complaint_4",
                "title": "Rude worker or driver",
                "description": (
                    "Rude behaviour by a worker or driver"
                ),
            },
            {
                "id": "complaint_5",
                "title": "Dumped waste not cleared",
                "description": (
                    "Dumped near house or "
                    "street not cleared"
                ),
            },
            {
                "id": "complaint_6",
                "title": "Type your complaint",
                "description": (
                    "Describe the issue in your own words"
                ),
            },
        ],
    },
    "ta": {
        "header": "புகார் பதிவு",
        "body": (
            "கீழே உள்ள பட்டியலிலிருந்து உங்கள் "
            "புகாரைத் தேர்ந்தெடுக்கவும்."
        ),
        "footer": "ஒன்றைத் தேர்வுசெய்யவும்",
        "button": "பட்டியல்",
        "section": "புகார் வகைகள்",
        "rows": [
            {
                "id": "complaint_1",
                "title": "வண்டி வரவில்லை",
                "description": (
                    "குப்பை வண்டி இன்று வரவில்லை"
                ),
            },
            {
                "id": "complaint_2",
                "title": "பல நாட்களாக வரவில்லை",
                "description": (
                    "பல நாட்களாக குப்பை வண்டி வரவில்லை"
                ),
            },
            {
                "id": "complaint_3",
                "title": "ஒலி அறிவிப்பு இல்லை",
                "description": (
                    "வண்டியில் ஒலி அறிவிப்பு ஒலிக்கப்படவில்லை"
                ),
            },
            {
                "id": "complaint_4",
                "title": "பணியாளர் முரட்டுத்தனம்",
                "description": (
                    "பணியாளர் அல்லது ஓட்டுநர் "
                    "முரட்டுத்தனமாக நடந்தார்"
                ),
            },
            {
                "id": "complaint_5",
                "title": "குப்பை அகற்றப்படவில்லை",
                "description": (
                    "வீடு/தெரு அருகில் உள்ள குப்பை "
                    "அகற்றப்படவில்லை"
                ),
            },
            {
                "id": "complaint_6",
                "title": "புகாரை தட்டச்சு செய்க",
                "description": (
                    "உங்கள் புகாரை நீங்களே தட்டச்சு செய்யவும்"
                ),
            },
        ],
    },
}


# ----------------------------------------
# PHOTO YES/NO PROMPT
# ----------------------------------------

PHOTO_QUESTION = {
    "en": {
        "body": "Do you have a photo of the issue?",
        "buttons": [
            {"id": "photo_yes", "title": "Yes"},
            {"id": "photo_no", "title": "No"},
        ],
    },
    "ta": {
        "body": "இந்த சிக்கலின் புகைப்படம் உங்களிடம் உள்ளதா?",
        "buttons": [
            {"id": "photo_yes", "title": "ஆம்"},
            {"id": "photo_no", "title": "இல்லை"},
        ],
    },
}


# ----------------------------------------
# PLAIN TEXT REPLIES
# ----------------------------------------

TEXT = {
    "en": {
        "ask_location": (
            "Please share the location of the spot/complaint.\n\n"
            "You can type the location or share your "
            "WhatsApp location."
        ),
        "ask_custom_complaint": "Please type your complaint.",
        "ask_ward": "Please type your ward number.",
        "invalid_ward": (
            "Please send a valid ward number, for example 12."
        ),
        "ask_photo_upload": (
            "Please send the photo of the issue here. \U0001f4f7"
        ),
        "receipt_title": "✅ *Complaint registered*",
        "receipt_reference": "Reference: *{reference}*",
        "receipt_where": "{local_body}, Ward {ward}",
        "receipt_next": (
            "Sent to the officer responsible. You will get a "
            "message here once it is resolved."
        ),
        "receipt_no_officer": (
            "No officer is currently listed for this local body. "
            "The complaint has been recorded and will be assigned."
        ),
        "completed": (
            "Thank you for your response. Our team will get back "
            "to you and take the necessary action as soon as "
            "possible."
        ),
        "already_submitted": (
            "Your complaint has already been submitted. "
            "Send 'Hi' to register a new complaint."
        ),
        "invalid_option": (
            "That option is not valid. Please try again."
        ),
        "location_unreadable": (
            "I could not read the location. Please send it again."
        ),
        "photo_unreadable": (
            "I could not receive the photo. Please try again."
        ),
        "unsupported": (
            "Please use text, the available options, a location, "
            "or a photo."
        ),
        "not_asking_photo": (
            "You are not currently being asked for a photo."
        ),
        "send_hi_to_start": (
            "Please send 'Hi' to start a complaint."
        ),
        "fallback": (
            "Something went wrong. Please send 'Hi' to start again."
        ),
        "use_options": "Please use the options shown.",
    },
    "ta": {
        "ask_location": (
            "புகார் உள்ள இடத்தைப் பகிரவும்.\n\n"
            "இடத்தை தட்டச்சு செய்யலாம் அல்லது உங்கள் "
            "WhatsApp இருப்பிடத்தைப் பகிரலாம்."
        ),
        "ask_custom_complaint": (
            "உங்கள் புகாரை தட்டச்சு செய்யவும்."
        ),
        "ask_ward": (
            "உங்கள் வார்டு எண்ணைத் தட்டச்சு செய்யவும்."
        ),
        "invalid_ward": (
            "சரியான வார்டு எண்ணை அனுப்பவும், "
            "எடுத்துக்காட்டு: 12."
        ),
        "ask_photo_upload": (
            "சிக்கலின் புகைப்படத்தை இங்கே அனுப்பவும். "
            "\U0001f4f7"
        ),
        "receipt_title": "✅ *புகார் பதிவு செய்யப்பட்டது*",
        "receipt_reference": "குறிப்பு எண்: *{reference}*",
        "receipt_where": "{local_body}, வார்டு {ward}",
        "receipt_next": (
            "பொறுப்பான அலுவலருக்கு அனுப்பப்பட்டது. "
            "சரிசெய்யப்பட்டதும் இங்கே தகவல் வரும்."
        ),
        "receipt_no_officer": (
            "இந்த உள்ளாட்சிக்கு தற்போது அலுவலர் "
            "பதிவு செய்யப்படவில்லை. புகார் பதிவாகியுள்ளது, "
            "விரைவில் ஒதுக்கப்படும்."
        ),
        "completed": (
            "உங்கள் பதிலுக்கு நன்றி. எங்கள் குழு விரைவில் "
            "உங்களைத் தொடர்பு கொண்டு தேவையான நடவடிக்கை "
            "எடுக்கும்."
        ),
        "already_submitted": (
            "உங்கள் புகார் ஏற்கனவே பதிவு செய்யப்பட்டுள்ளது. "
            "புதிய புகார் பதிவு செய்ய 'Hi' என அனுப்பவும்."
        ),
        "invalid_option": (
            "அந்த விருப்பம் சரியானது அல்ல. மீண்டும் "
            "முயற்சிக்கவும்."
        ),
        "location_unreadable": (
            "இருப்பிடத்தைப் படிக்க முடியவில்லை. மீண்டும் "
            "அனுப்பவும்."
        ),
        "photo_unreadable": (
            "புகைப்படத்தைப் பெற முடியவில்லை. மீண்டும் "
            "முயற்சிக்கவும்."
        ),
        "unsupported": (
            "உரை, கொடுக்கப்பட்ட விருப்பங்கள், இருப்பிடம் "
            "அல்லது புகைப்படத்தைப் பயன்படுத்தவும்."
        ),
        "not_asking_photo": (
            "தற்போது உங்களிடம் புகைப்படம் "
            "கேட்கப்படவில்லை."
        ),
        "send_hi_to_start": (
            "புகார் பதிவு செய்ய 'Hi' என அனுப்பவும்."
        ),
        "fallback": (
            "ஏதோ தவறு நடந்தது. மீண்டும் தொடங்க 'Hi' என "
            "அனுப்பவும்."
        ),
        "use_options": (
            "காட்டப்பட்டுள்ள விருப்பங்களைப் பயன்படுத்தவும்."
        ),
    },
}


# Canonical English wording recorded against the complaint, so the
# District Collector's record reads the same whichever language the
# citizen used. Keyed by the numeric choice.
COMPLAINT_RECORD = {
    "1": "Garbage collection vehicle did not come today",
    "2": (
        "Garbage collection vehicle has not come "
        "for the past few days"
    ),
    "3": (
        "Audio announcement is not played "
        "from the garbage collection vehicle"
    ),
    "4": "Sanitary worker/vehicle driver behaved rudely",
    "5": (
        "Garbage Vulnerable Point (GVP) near "
        "my house/street has not been cleared"
    ),
    "6": "Other",
}


def normalize(language: str) -> str:
    """Turn any language value into a supported language code.

    Args:
        language: A language code, possibly empty or unknown.

    Returns:
        The same code if it is supported, otherwise DEFAULT_LANGUAGE.
    """
    if language in MENU:
        return language
    return DEFAULT_LANGUAGE


def t(language: str, key: str) -> str:
    """Look up a translated message.

    Args:
        language: The user's language code. Unsupported codes use
            DEFAULT_LANGUAGE.
        key: The message key.

    Returns:
        The text in the user's language, or in DEFAULT_LANGUAGE if that
        key has no translation.

    Raises:
        KeyError: If the key is missing from the default language too.
    """
    lang = normalize(language)
    return TEXT[lang].get(key, TEXT[DEFAULT_LANGUAGE][key])


def menu(language: str) -> dict:
    """Get the complaint menu content.

    Args:
        language: The user's language code.

    Returns:
        The menu definition for that language.
    """
    return MENU[normalize(language)]


def photo_question(language: str) -> dict:
    """Get the content of the 'do you want to add a photo' question.

    Args:
        language: The user's language code.

    Returns:
        The photo question definition for that language.
    """
    return PHOTO_QUESTION[normalize(language)]


# ----------------------------------------
# LOCAL BODY SCREENS
# ----------------------------------------

# Local body and block names stay in Latin script in both languages:
# they are official place names, so only the labels around them are
# translated.
LOCAL_BODY = {
    "en": {
        "type": {
            "header": "Local Body",
            "body": (
                "Please select the type of your local body."
            ),
            "footer": "Select one option",
            "button": "View types",
            "section": "Local body type",
            "labels": {
                "municipality": "Municipality",
                "town": "Town Panchayat",
                "village": "Village Panchayat",
            },
            "descriptions": {
                "municipality": "Urban local body",
                "town": "Town panchayat area",
                "village": "Rural village panchayat",
            },
        },
        "block": {
            "header": "Block",
            "body": "Please select your block.",
            "footer": "Select one option",
            "button": "View blocks",
            "section": "Blocks",
        },
        "body": {
            "header": "Local Body",
            "body": "Please select your local body.",
            "footer": "Select one option",
            "button": "View list",
            "section": "Local bodies",
            "more": "More options",
            "more_description": "Show the remaining names",
        },
    },
    "ta": {
        "type": {
            "header": "உள்ளாட்சி வகை",
            "body": (
                "உங்கள் உள்ளாட்சி வகையைத் "
                "தேர்ந்தெடுக்கவும்."
            ),
            "footer": "ஒன்றைத் தேர்வுசெய்யவும்",
            "button": "வகைகள்",
            "section": "உள்ளாட்சி வகை",
            "labels": {
                "municipality": "நகராட்சி",
                "town": "பேரூராட்சி",
                "village": "ஊராட்சி",
            },
            "descriptions": {
                "municipality": "நகர்ப்புற உள்ளாட்சி",
                "town": "பேரூராட்சி பகுதி",
                "village": "கிராமப்புற ஊராட்சி",
            },
        },
        "block": {
            "header": "ஒன்றியம்",
            "body": (
                "உங்கள் ஒன்றியத்தைத் தேர்ந்தெடுக்கவும்."
            ),
            "footer": "ஒன்றைத் தேர்வுசெய்யவும்",
            "button": "ஒன்றியங்கள்",
            "section": "ஒன்றியம்",
        },
        "body": {
            "header": "உள்ளாட்சி",
            "body": (
                "உங்கள் உள்ளாட்சியைத் தேர்ந்தெடுக்கவும்."
            ),
            "footer": "ஒன்றைத் தேர்வுசெய்யவும்",
            "button": "பட்டியல்",
            "section": "உள்ளாட்சிகள்",
            "more": "மேலும்",
            "more_description": "மீதமுள்ள பெயர்களைக் காட்டு",
        },
    },
}


def local_body(language: str) -> dict:
    """Get the local body, block and type screen content.

    Args:
        language: The user's language code.

    Returns:
        The local body screen definitions for that language.
    """
    return LOCAL_BODY[normalize(language)]


# ----------------------------------------
# LENGTH VALIDATION
# ----------------------------------------

LIMITS = {
    "header": 60,
    "body": 1024,
    "footer": 60,
    "button": 20,
    "section": 24,
    "row_title": 24,
    "row_description": 72,
    "reply_title": 20,
}


def _validate() -> None:
    """Check that every message fits WhatsApp's length limits.

    Raises:
        ValueError: If any text is longer than its limit in LIMITS.
    """
    problems = []

    def check(label, value, limit):
        """Record a problem if value is longer than limit.

        Args:
            label: A name for the text, used in the problem message.
            value: The text to measure.
            limit: The maximum allowed length.
        """
        if len(value) > limit:
            problems.append(
                f"{label}: {len(value)} > {limit} -> {value!r}"
            )

    check("INTRO.body", INTRO["body"], LIMITS["body"])

    for button in INTRO["buttons"]:
        check(
            f"INTRO.button[{button['id']}]",
            button["title"],
            LIMITS["reply_title"],
        )

    for lang in SUPPORTED_LANGUAGES:
        m = MENU[lang]
        check(f"{lang}.header", m["header"], LIMITS["header"])
        check(f"{lang}.body", m["body"], LIMITS["body"])
        check(f"{lang}.footer", m["footer"], LIMITS["footer"])
        check(f"{lang}.button", m["button"], LIMITS["button"])
        check(f"{lang}.section", m["section"], LIMITS["section"])

        if len(m["rows"]) > 10:
            problems.append(
                f"{lang}.rows: {len(m['rows'])} > 10"
            )

        for row in m["rows"]:
            check(
                f"{lang}.row[{row['id']}].title",
                row["title"],
                LIMITS["row_title"],
            )
            check(
                f"{lang}.row[{row['id']}].description",
                row["description"],
                LIMITS["row_description"],
            )

        p = PHOTO_QUESTION[lang]
        check(f"{lang}.photo.body", p["body"], LIMITS["body"])

        for button in p["buttons"]:
            check(
                f"{lang}.photo.button[{button['id']}]",
                button["title"],
                LIMITS["reply_title"],
            )

        lb = LOCAL_BODY[lang]

        for screen in ("type", "block", "body"):
            block = lb[screen]
            check(
                f"{lang}.lb.{screen}.header",
                block["header"],
                LIMITS["header"],
            )
            check(
                f"{lang}.lb.{screen}.body",
                block["body"],
                LIMITS["body"],
            )
            check(
                f"{lang}.lb.{screen}.footer",
                block["footer"],
                LIMITS["footer"],
            )
            check(
                f"{lang}.lb.{screen}.button",
                block["button"],
                LIMITS["button"],
            )
            check(
                f"{lang}.lb.{screen}.section",
                block["section"],
                LIMITS["section"],
            )

        for key, label in lb["type"]["labels"].items():
            check(
                f"{lang}.lb.type[{key}]",
                label,
                LIMITS["row_title"],
            )

        for key, text in lb["type"]["descriptions"].items():
            check(
                f"{lang}.lb.type.desc[{key}]",
                text,
                LIMITS["row_description"],
            )

        check(
            f"{lang}.lb.body.more",
            lb["body"]["more"],
            LIMITS["row_title"],
        )
        check(
            f"{lang}.lb.body.more_description",
            lb["body"]["more_description"],
            LIMITS["row_description"],
        )

    # Place names are shared by both languages and become row titles.
    from app.services import local_bodies

    for name, _, _ in local_bodies.BODIES:
        check(f"local body {name!r}", name, LIMITS["row_title"])

    for block in local_bodies.BLOCK_ROW_IDS:
        check(f"block {block!r}", block, LIMITS["row_title"])

    if problems:
        raise ValueError(
            "WhatsApp field length limits exceeded:\n  "
            + "\n  ".join(problems)
        )


_validate()
