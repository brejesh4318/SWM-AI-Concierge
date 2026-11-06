import pytest

from app.services import messages as m


def test_normalize():
    assert m.normalize("ta") == "ta"
    assert m.normalize("fr") == m.DEFAULT_LANGUAGE
    assert m.normalize("") == m.DEFAULT_LANGUAGE


def test_t_translates_and_falls_back():
    assert m.t("ta", "ask_ward") != ""
    assert m.t("zz", "ask_ward") == m.t("en", "ask_ward")


def test_t_unknown_key_raises():
    with pytest.raises(KeyError):
        m.t("en", "definitely_missing")


def test_menu_and_photo_question():
    assert m.menu("en")["rows"]
    assert m.photo_question("ta")["buttons"]


def test_language_keywords_valid():
    assert set(m.LANGUAGE_KEYWORDS.values()) <= set(m.SUPPORTED_LANGUAGES)
    assert set(m.LANGUAGE_IDS.values()) <= set(m.SUPPORTED_LANGUAGES)


def test_complaint_record_has_six_options():
    assert set(m.COMPLAINT_RECORD) == {"1", "2", "3", "4", "5", "6"}


def test_no_translation_has_keys_missing_from_english():
    for lang in m.SUPPORTED_LANGUAGES:
        assert set(m.TEXT[lang]) <= set(m.TEXT["en"])
