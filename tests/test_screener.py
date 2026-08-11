import screener


def _entry(iv_hv, days_away):
    return {
        "iv_hv_ratio": iv_hv,
        "earnings": {"days_away": days_away},
    }


def test_flag_reasons_ivhv_above_threshold():
    assert screener.flag_reasons(_entry(1.6, "30d")) == ["IV/HV 1.60x"]


def test_flag_reasons_earnings_soon():
    assert "earnings in 3d" in screener.flag_reasons(_entry(1.1, "3d"))


def test_flag_reasons_no_flags():
    assert screener.flag_reasons(_entry(1.1, "30d")) == []


def test_flag_reasons_past_earnings():
    assert screener.flag_reasons(_entry(1.1, "2d ago")) == []


def test_flag_reasons_missing_values():
    assert screener.flag_reasons(_entry(None, "\u2014")) == []


def test_format_message_has_table_and_banner():
    entries = [{
        "ticker": "UUUU",
        "price": 10.74,
        "atm_iv": 0.78,
        "hist_vol": 0.57,
        "iv_hv_ratio": 1.6,
        "expiry_used": "2026-08-28",
        "strike": 10.5,
        "earnings": {
            "earnings_date": "2026-08-28",
            "days_away": "17d",
            "high_52w": "$14.20",
            "eps_est": "$0.12",
            "rev_est": "$45M",
        },
    }]
    msg = screener.format_message(entries)
    assert "ACTION ALERT" in msg
    assert "UUUU" in msg
    assert "IV/HV 1.60x" in msg
    assert msg.count("```") == 2
