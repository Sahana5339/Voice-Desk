import pytest

import core


# ---------------------------------------------------------------- order-id and slot filling
@pytest.mark.parametrize("slot,text,expected", [
    ("order_id", "48213", "48213"),
    ("order_id", "चार आठ दो एक तीन", "48213"),
    ("order_id", "four eight two one three", "48213"),
    ("order_id", "12", None),
    ("amount", "1200 rupees", 1200),
    ("amount", "500", 500),
])
def test_fill_slot(slot, text, expected):
    assert core.fill_slot(slot, text) == expected


@pytest.mark.parametrize("text,expected", [
    ("my order number is 48213", "48213"),
    ("my order is delayed for three days, please check 48213", "48213"),
    ("నా ఆర్డర్ రాలేదు మూడు రోజులు 48213", "48213"),
    ("48213 has not arrived, my package is delayed", "48213"),
    ("Package delayed for three days, tracking number 48213", "48213"),
    ("my order number is four eight two one three", "48213"),
    ("నా ఆర్డర్ మూడు నాలుగు ఐదు ఆరు ఏడు ఎనిమిది", "345678"),
    ("ఆర్డర్ ౪౮౨౧౩", "48213"),
])
def test_extract_order(text, expected):
    assert core.extract_order(text) == expected


# ---------------------------------------------------------------- dialogue
def test_known_order_id_is_not_asked_again():
    for i, text in enumerate(["My order has not arrived, order number is 48213",
                              "My order is delayed for three days, please check 48213"]):
        tk = core.make_ticket(text, "en-IN", i)
        assert tk["order_id"] == "48213" and core.missing_slot(tk) is None


def test_missing_order_id_is_asked():
    assert core.missing_slot(core.make_ticket("Mera order nahi aaya, bahut deri ho gayi", "hi-IN", 1)) == "order_id"


def test_override_fills_slot():
    tk = core.make_ticket("Mera order nahi aaya", "hi-IN", 1, overrides={"order_id": "48213"})
    assert core.missing_slot(tk) is None and tk["order_id"] == "48213"


def test_fraud_never_delayed_by_questions():
    tk = core.make_ticket("My account was hacked, money stolen", "en-IN", 2)
    assert core.missing_slot(tk) is None and tk["escalate"]


def test_repeat_complaint_detected_and_raised():
    first = core.make_ticket("My parcel has not arrived. Order number 48213", "en-IN", 3)
    again = core.make_ticket("My parcel still has not arrived. Order number 48213", "en-IN", 4, history=[first])
    assert again["repeat_of"] == first["id"] and again["urgency"] in ("High", "Critical")


# ---------------------------------------------------------------- reply language
@pytest.mark.parametrize("code,text,expected", [
    ("te-IN", "My order has not arrived", "en"),
    ("en-IN", "मेरा ऑर्डर नहीं आया", "hi"),
    ("te-IN", "ನನ್ನ ಆರ್ಡರ್ ಬಂದಿಲ್ಲ", "kn"),
    ("hi-IN", "Mera order nahi aaya", "hi"),
])
def test_reply_language(code, text, expected):
    assert core.reply_language(code, text) == expected


def test_questions_exist_in_all_reply_languages():
    assert all(core.followup_question(s, l) for s in core.QUESTIONS for l in ("hi", "kn", "en"))


# ---------------------------------------------------------------- privacy and record
def test_card_masked_spacing_kept():
    assert core.mask_pii("card 4111 1111 1111 1234 used") == "card XXXX-XXXX-XXXX-1234 used"


def test_phone_masked():
    out = core.mask_pii("call 9876543210")
    assert out.endswith("3210") and "98765" not in out


def test_json_record_has_next_step():
    assert "next_step" in core.to_record(core.make_ticket("Internet is not working", "en-IN", 1))


# ---------------------------------------------------------------- safety invariants
@pytest.mark.parametrize("text", [
    "My account was hacked and money was transferred without my permission",
    "The mixer grinder is giving sparks and smoke, I got an electric shock",
    "मेरे अकाउंट से बिना अनुमति पैसे कट गए, यह धोखाधड़ी है",
])
def test_fraud_and_safety_are_always_critical_and_escalated(text):
    tk = core.make_ticket(text, None, 1)
    assert tk["urgency"] == "Critical" and tk["escalate"] and tk["sla_hours"] == 1
