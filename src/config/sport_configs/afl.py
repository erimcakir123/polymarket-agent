"""AFL sport config (SPEC-015) — draws nadir ama 3-way structure."""

AFL_CONFIG: dict = {
    "regulation_minutes": 80,
    "stoppage_buffer": 4,

    "score_exit_first_half_lock": 60,
    "score_exit_blowout_minute": 60,
    "score_exit_blowout_deficit": 30,
    "score_exit_late_minute": 75,
    "score_exit_late_deficit": 15,

    "draw_protect_until": 70,
    "knockout_auto_exit_draw": True,

    "excluded_competitions": ["Preseason"],
}
