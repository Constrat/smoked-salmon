from copy import deepcopy

from salmon import cfg
from salmon.common import apply_mixed_case_title
from salmon.tagger.metadata import apply_metadata_capitalization


def test_apply_mixed_case_title_follows_common_rules():
    assert apply_mixed_case_title("love is in the air") == "Love Is in the Air"
    assert apply_mixed_case_title("rock 'n' roll") == "Rock 'n' Roll"
    assert apply_mixed_case_title("you are but a draft") == "You Are But a Draft"
    assert apply_mixed_case_title("i don't know what it is but i like it") == "I Don't Know What It Is but I Like It"
    assert apply_mixed_case_title("the go-gos") == "The Go-Gos"


def test_apply_metadata_capitalization_respects_toggles(monkeypatch):
    metadata = {
        "title": "this is as good as it gets",
        "artists": [("nick cave and the bad seeds", "main")],
        "tracks": {
            "1": {
                "1": {
                    "title": "life is but a dream",
                    "artists": [("elvis costello and the attractions", "main")],
                }
            }
        },
    }

    monkeypatch.setattr(cfg.metadata.capitalization, "album", True)
    monkeypatch.setattr(cfg.metadata.capitalization, "artists", False)
    monkeypatch.setattr(cfg.metadata.capitalization, "tracks", True)

    formatted = apply_metadata_capitalization(deepcopy(metadata))

    assert formatted["title"] == "This Is as Good as It Gets"
    assert formatted["artists"][0][0] == "nick cave and the bad seeds"
    assert formatted["tracks"]["1"]["1"]["title"] == "Life Is But a Dream"
    assert formatted["tracks"]["1"]["1"]["artists"][0][0] == "elvis costello and the attractions"


def test_apply_metadata_capitalization_can_format_artists(monkeypatch):
    metadata = {
        "title": "in a safe place",
        "artists": [("nick cave and the bad seeds", "main")],
        "tracks": {
            "1": {
                "1": {
                    "title": "rattle and hum",
                    "artists": [("elvis costello and the attractions", "main")],
                }
            }
        },
    }

    monkeypatch.setattr(cfg.metadata.capitalization, "album", False)
    monkeypatch.setattr(cfg.metadata.capitalization, "artists", True)
    monkeypatch.setattr(cfg.metadata.capitalization, "tracks", False)

    formatted = apply_metadata_capitalization(deepcopy(metadata))

    assert formatted["title"] == "in a safe place"
    assert formatted["artists"][0][0] == "Nick Cave and the Bad Seeds"
    assert formatted["tracks"]["1"]["1"]["title"] == "rattle and hum"
    assert formatted["tracks"]["1"]["1"]["artists"][0][0] == "Elvis Costello and the Attractions"
