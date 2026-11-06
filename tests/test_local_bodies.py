from app.services import local_bodies as lb


def test_get_and_row_ids():
    body = lb.get(0)
    assert set(body) == {"name", "type", "block"}
    assert lb.row_id(3) == "lb_3"
    assert lb.index_for_row("lb_3") == 3
    assert lb.index_for_row("nope") is None


def test_indexes_filter_by_type_and_block():
    muni = lb.indexes(lb.MUNICIPALITY)
    assert muni and all(lb.get(i)["type"] == lb.MUNICIPALITY for i in muni)
    for i in lb.indexes(lb.VILLAGE, "Gudalur"):
        assert lb.get(i)["block"] == "Gudalur"


def test_blocks_only_those_present():
    for b in lb.blocks(lb.VILLAGE):
        assert b in lb.BLOCK_ROW_IDS
    assert lb.blocks("unknown") == []


def test_needs_block_matches_cap():
    for t in lb.TYPE_ORDER:
        assert lb.needs_block(t) == (len(lb.indexes(t)) > lb.MAX_ROWS)


def test_page_short_list_has_no_next():
    taken, nxt = lb.page(lb.MUNICIPALITY)
    assert nxt is None
    assert taken == lb.indexes(lb.MUNICIPALITY)


def test_page_paginates_and_covers_everything(monkeypatch):
    bodies = tuple((f"B{i}", "x", "") for i in range(25))
    monkeypatch.setattr(lb, "BODIES", bodies)
    seen, offset = [], 0
    while True:
        taken, nxt = lb.page("x", "", offset)
        assert len(taken) <= lb.MAX_ROWS
        seen += taken
        if nxt is None:
            break
        assert len(taken) == lb.MAX_ROWS - 1
        offset = nxt
    assert seen == list(range(25))
