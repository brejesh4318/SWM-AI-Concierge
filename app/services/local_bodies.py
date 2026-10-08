# -*- coding: utf-8 -*-
"""The Nilgiris local bodies, and the paging needed to list them.

Source: "SWM - The Nilgiris (Responses)" form export.  Names are kept
in Latin script for both languages, because these are official place
names and transliterating them is not something to guess at.

A WhatsApp list message allows at most 10 rows in total, so the data
cannot always be shown in one go:

    municipality       5  -> one list
    town panchayat    10  -> one list (exactly at the cap)
    village panchayat 35  -> needs the block step, and Ooty (13) and
                             Kotagiri (11) still need a second page

So village panchayats are reached as type -> block -> list, and any
list longer than the cap keeps its last row for "more", which paging
below handles generically.  If the district adds local bodies later,
the extra pages appear on their own.
"""

MUNICIPALITY = "municipality"
TOWN = "town"
VILLAGE = "village"

TYPE_ORDER = (MUNICIPALITY, TOWN, VILLAGE)

TYPE_IDS = {
    "lbtype_municipality": MUNICIPALITY,
    "lbtype_town": TOWN,
    "lbtype_village": VILLAGE,
}

TYPE_ROW_IDS = {
    MUNICIPALITY: "lbtype_municipality",
    TOWN: "lbtype_town",
    VILLAGE: "lbtype_village",
}

BLOCK_IDS = {
    "lbblk_ooty": "Ooty",
    "lbblk_kotagiri": "Kotagiri",
    "lbblk_coonoor": "Coonoor",
    "lbblk_gudalur": "Gudalur",
}

BLOCK_ROW_IDS = {
    block: row_id
    for row_id, block in BLOCK_IDS.items()
}

# WhatsApp hard cap on rows in a single list message.
MAX_ROWS = 10

MORE_ID = "lbmore"


# (name, type, block)
BODIES = (
    ("Coonoor", MUNICIPALITY, "Coonoor"),
    ("Nelliyalam", MUNICIPALITY, "Gudalur"),
    ("Gudalur", MUNICIPALITY, "Gudalur"),
    ("Ooty", MUNICIPALITY, "Ooty"),
    ("Kotagiri", MUNICIPALITY, "Kotagiri"),

    ("Bikkatty", TOWN, "Ooty"),
    ("Sholur", TOWN, "Ooty"),
    ("Naduvattam", TOWN, "Ooty"),
    ("Kilkundah Town", TOWN, "Ooty"),
    ("Ketti", TOWN, "Coonoor"),
    ("Adigaratty", TOWN, "Coonoor"),
    ("Hulical", TOWN, "Coonoor"),
    ("Devarshola", TOWN, "Gudalur"),
    ("Ovalley Town", TOWN, "Gudalur"),
    ("Jegathala", TOWN, "Kotagiri"),

    ("Balacola", VILLAGE, "Ooty"),
    ("Doddabetta", VILLAGE, "Ooty"),
    ("Ebbanad", VILLAGE, "Ooty"),
    ("Hullathy", VILLAGE, "Ooty"),
    ("Ithalar", VILLAGE, "Ooty"),
    ("Kadanad", VILLAGE, "Ooty"),
    ("Kagguchi", VILLAGE, "Ooty"),
    ("Kookal", VILLAGE, "Ooty"),
    ("Kundha", VILLAGE, "Ooty"),
    ("Mulligoor", VILLAGE, "Ooty"),
    ("Nanjanad", VILLAGE, "Ooty"),
    ("Thummanatty", VILLAGE, "Ooty"),
    ("Thuneri", VILLAGE, "Ooty"),

    ("Aracode", VILLAGE, "Kotagiri"),
    ("Denad", VILLAGE, "Kotagiri"),
    ("Kadinamala", VILLAGE, "Kotagiri"),
    ("Kengarai", VILLAGE, "Kotagiri"),
    ("Kodanad", VILLAGE, "Kotagiri"),
    ("Kunjapani", VILLAGE, "Kotagiri"),
    ("Naduhatty", VILLAGE, "Kotagiri"),
    ("Nedugula", VILLAGE, "Kotagiri"),
    ("Thengumarahada", VILLAGE, "Kotagiri"),
    ("Jackanarai", VILLAGE, "Kotagiri"),
    ("Konavakarai", VILLAGE, "Kotagiri"),

    ("Bandhisholai", VILLAGE, "Coonoor"),
    ("Bearhatty", VILLAGE, "Coonoor"),
    ("Burliyar", VILLAGE, "Coonoor"),
    ("Melur", VILLAGE, "Coonoor"),
    ("Hubbathalai", VILLAGE, "Coonoor"),
    ("Yedapalli", VILLAGE, "Coonoor"),

    ("Cherangode", VILLAGE, "Gudalur"),
    ("Masinagudi", VILLAGE, "Gudalur"),
    ("Mudhumalai", VILLAGE, "Gudalur"),
    ("Nellakottai", VILLAGE, "Gudalur"),
    ("Sreemadurai", VILLAGE, "Gudalur"),
)


def row_id(index: int) -> str:
    """Build the WhatsApp list row ID for a local body.

    Args:
        index: The position of the local body in BODIES.

    Returns:
        The row ID, in the form 'lb_<index>'.
    """
    return f"lb_{index}"


ROW_IDS = {
    row_id(index): index
    for index in range(len(BODIES))
}


def get(index: int) -> dict:
    """Look up a local body by position.

    Args:
        index: The position of the local body in BODIES.

    Returns:
        A dictionary with the body's 'name', 'type' and 'block'.

    Raises:
        IndexError: If index is outside BODIES.
    """
    name, body_type, block = BODIES[index]

    return {
        "name": name,
        "type": body_type,
        "block": block,
    }


def index_for_row(row: str):
    """Convert a WhatsApp list row ID back into a local body position.

    Args:
        row: The row ID sent back by WhatsApp.

    Returns:
        The position in BODIES, or None if the ID is not a local body
        row.
    """
    return ROW_IDS.get(row)


def indexes(
    body_type: str,
    block: str = "",
) -> list:
    """Positions of the bodies of a type, optionally within a block.

    Args:
        body_type: The local body type key.
        block: Restrict the result to this block. Defaults to an empty
            string, meaning all blocks.

    Returns:
        A list of positions in BODIES, in list order.
    """

    return [
        index
        for index, (_, t, b) in enumerate(BODIES)
        if t == body_type and (not block or b == block)
    ]


def blocks(body_type: str) -> list:
    """Blocks that actually have a body of this type, in menu order.

    Args:
        body_type: The local body type key.

    Returns:
        A list of block names.
    """

    present = {
        block
        for _, t, block in BODIES
        if t == body_type
    }

    return [
        block
        for block in BLOCK_ROW_IDS
        if block in present
    ]


def needs_block(body_type: str) -> bool:
    """Say whether a type is too long for one list and needs a block step.

    Args:
        body_type: The local body type key.

    Returns:
        True if there are more bodies of this type than MAX_ROWS.
    """
    return len(indexes(body_type)) > MAX_ROWS


def page(
    body_type: str,
    block: str = "",
    offset: int = 0,
) -> tuple:
    """One screen of bodies.

    Args:
        body_type: The local body type key.
        block: Restrict the list to this block. Defaults to an empty
            string, meaning all blocks.
        offset: How many matching bodies to skip. Defaults to 0.

    Returns:
        A tuple (indexes_on_this_page, next_offset).  next_offset is
        None when this is the last page; otherwise the caller adds a
        "more" row and remembers the offset.
    """

    found = indexes(body_type, block)

    remaining = found[offset:]

    if len(remaining) <= MAX_ROWS:
        return remaining, None

    # Keep the last row free for "more".
    taken = remaining[: MAX_ROWS - 1]

    return taken, offset + len(taken)
