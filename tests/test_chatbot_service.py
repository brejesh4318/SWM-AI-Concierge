from app.services import chatbot_service as cb
from app.services import local_bodies as lb
from app.services import messages
from app.state import conversation_manager as cm
from app.state.conversation_state import ConversationState as S

U = "9190"


def say(text):
    return cb.process_text_message(U, text)


def to_complaint_menu():
    say("hi")
    say("english")


def test_start_asks_language():
    assert say("hi") == {"type": "language_menu"}
    assert cm.get_state(U) == S.WAITING_FOR_LANGUAGE


def test_language_keyword_and_invalid():
    say("hi")
    assert say("???")["type"] == "language_menu"
    assert say("Tamil")["type"] == "complaint_menu"
    assert cm.get_language(U) == "ta"
    assert cm.get_state(U) == S.WAITING_FOR_COMPLAINT


def test_language_of_defaults_to_english():
    assert cb.language_of(U) == "en"


def test_predefined_complaint_goes_to_body_type():
    to_complaint_menu()
    assert say("1")["type"] == "local_body_type_menu"
    assert cm.get_data_value(U, "complaint_choice") == "1"
    assert (
        cm.get_data_value(U, "complaint_type")
        == messages.COMPLAINT_RECORD["1"]
    )


def test_invalid_complaint_reshows_menu():
    to_complaint_menu()
    assert say("99")["type"] == "complaint_menu"


def test_custom_complaint_flow():
    to_complaint_menu()
    assert say("6")["type"] == "text"
    assert cm.get_state(U) == S.WAITING_FOR_CUSTOM_COMPLAINT
    assert say("")["type"] == "text"
    assert say("dead dog on road")["type"] == "local_body_type_menu"
    assert cm.get_data_value(U, "custom_complaint") == "dead dog on road"


def test_match_local_body_type_variants():
    assert cb._match_local_body_type("en", "1") == lb.MUNICIPALITY
    assert cb._match_local_body_type("en", " TOWN ") == lb.TOWN
    for lang in messages.SUPPORTED_LANGUAGES:
        for key, label in messages.LOCAL_BODY[lang]["type"]["labels"].items():
            assert cb._match_local_body_type("en", label.upper()) == key
    assert cb._match_local_body_type("en", "zzz") is None


def test_body_type_selection_municipality_then_ward():
    to_complaint_menu()
    say("1")
    assert say("nonsense")["type"] == "local_body_type_menu"
    assert say("municipality")["type"] == "local_body_menu"
    assert cm.get_state(U) == S.WAITING_FOR_LOCAL_BODY
    name = lb.get(lb.indexes(lb.MUNICIPALITY)[0])["name"]
    assert say("nobody")["type"] == "local_body_menu"
    assert say(name.lower())["type"] == "text"
    assert cm.get_state(U) == S.WAITING_FOR_WARD
    assert cm.get_data_value(U, "local_body") == name


def test_village_requires_block(monkeypatch):
    monkeypatch.setattr(lb, "needs_block", lambda t: t == lb.VILLAGE)
    result = cb.select_local_body_type(U, lb.VILLAGE)
    assert result == {"type": "block_menu"}
    assert cm.get_state(U) == S.WAITING_FOR_BLOCK


def test_block_text_selection():
    cm.set_state(U, S.WAITING_FOR_BLOCK)
    cm.save_data(U, "local_body_type", lb.VILLAGE)
    block = lb.blocks(lb.VILLAGE)[0]
    assert say("junk")["type"] == "block_menu"
    assert say(block.upper())["type"] == "local_body_menu"
    assert cm.get_data_value(U, "local_body_block") == block


def test_show_more_local_bodies(monkeypatch):
    monkeypatch.setattr(
        lb, "BODIES", tuple((f"B{i}", "x", "") for i in range(25))
    )
    cm.save_data(U, "local_body_type", "x")
    cm.save_data(U, "local_body_offset", 0)
    cb.show_more_local_bodies(U)
    assert cm.get_data_value(U, "local_body_offset") == lb.MAX_ROWS - 1
    # last page: offset unchanged
    cm.save_data(U, "local_body_offset", 20)
    assert cb.show_more_local_bodies(U) == {"type": "local_body_menu"}
    assert cm.get_data_value(U, "local_body_offset") == 20


def test_local_body_context_defaults():
    assert cb.local_body_context(U) == {
        "body_type": "",
        "block": "",
        "offset": 0,
    }


def test_ward_validation_and_location():
    cm.set_state(U, S.WAITING_FOR_WARD)
    assert say("abc")["message"] == messages.t("en", "invalid_ward")
    assert say("Ward 12")["type"] == "text"
    assert cm.get_data_value(U, "ward_number") == "12"
    assert cm.get_state(U) == S.WAITING_FOR_LOCATION
    assert say("")["type"] == "text"
    assert say("Near temple")["type"] == "photo_question"
    assert cm.get_data_value(U, "location_text") == "Near temple"


def test_photo_question_branches():
    cm.set_state(U, S.ASKING_FOR_PHOTO)
    assert say("maybe")["type"] == "photo_question"
    assert say("yes")["type"] == "text"
    assert cm.get_state(U) == S.WAITING_FOR_PHOTO
    assert say("hello")["type"] == "text"  # still asks for upload
    cm.set_state(U, S.ASKING_FOR_PHOTO)
    assert say("இல்லை") == {"type": "completed"}
    assert cm.get_state(U) == S.COMPLETED


def test_completed_restart_and_already_submitted():
    cm.set_state(U, S.COMPLETED)
    cm.set_language(U, "ta")
    assert say("thanks")["message"] == messages.t("ta", "already_submitted")
    assert say("Hello")["type"] == "language_menu"
    assert cm.get_language(U) == ""


def test_location_pin():
    assert cb.process_location_message(U, "1", "2")["type"] == "text"
    cm.set_state(U, S.WAITING_FOR_LOCATION)
    assert cb.process_location_message(U, "1.5", "2.5") == {
        "type": "photo_question"
    }
    assert cm.get_data_value(U, "latitude") == "1.5"
    assert cm.get_state(U) == S.ASKING_FOR_PHOTO


def test_photo_upload():
    assert cb.process_photo_message(U, "m")["message"] == messages.t(
        "en", "not_asking_photo"
    )
    cm.set_state(U, S.WAITING_FOR_PHOTO)
    assert cb.process_photo_message(U, "path.jpg") == {"type": "completed"}
    assert cm.get_data_value(U, "photo_media_id") == "path.jpg"


def test_get_completed_complaint_strips_internal_keys():
    cm.save_data(U, "local_body_offset", 5)
    cm.save_data(U, "ward_number", "3")
    cm.set_language(U, "ta")
    out = cb.get_completed_complaint(U)
    assert "local_body_offset" not in out
    assert out["ward_number"] == "3" and out["language"] == "ta"


def test_localised_complaint():
    assert cb.localised_complaint("en", None) == ""
    assert cb.localised_complaint("en", "1") != ""
    assert cb.localised_complaint("en", "99") == ""


def test_build_receipt_with_and_without_officer():
    complaint = {
        "complaint_choice": "1",
        "complaint_type": "x",
        "local_body": "Coonoor",
        "ward_number": "4",
    }
    with_officer = cb.build_receipt("en", "NLG-2026-00001", complaint)
    assert "NLG-2026-00001" in with_officer and "Coonoor" in with_officer
    assert messages.t("en", "receipt_next") in with_officer
    without = cb.build_receipt("en", "R", complaint, has_officer=False)
    assert messages.t("en", "receipt_no_officer") in without


def test_build_receipt_custom_and_fallback():
    assert "my text" in cb.build_receipt(
        "en", "R", {"custom_complaint": "my text"}
    )
    assert "canon" in cb.build_receipt("en", "R", {"complaint_type": "canon"})
