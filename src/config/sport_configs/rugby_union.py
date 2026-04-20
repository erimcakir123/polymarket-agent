"""Rugby Union sport config (SPEC-015)."""

RUGBY_UNION_CONFIG: dict = {
    "regulation_minutes": 80,
    "stoppage_buffer": 3,

    "score_exit_first_half_lock": 50,
    "score_exit_blowout_minute": 50,
    "score_exit_blowout_deficit": 14,
    "score_exit_late_minute": 70,
    "score_exit_late_deficit": 7,

    "draw_protect_until": 70,
    "knockout_auto_exit_draw": True,

    "excluded_competitions": [
        "International Friendly",
        "Preseason",
        "Test",
    ],
}
