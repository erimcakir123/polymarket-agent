"""Handball sport config (SPEC-015) — draws yaygin (~%10-15)."""

HANDBALL_CONFIG: dict = {
    "regulation_minutes": 60,
    "stoppage_buffer": 2,

    "score_exit_first_half_lock": 45,
    "score_exit_blowout_minute": 45,
    "score_exit_blowout_deficit": 8,
    "score_exit_late_minute": 55,
    "score_exit_late_deficit": 4,

    "draw_protect_until": 50,
    "draw_exit_after_goal_swing": 55,
    "knockout_auto_exit_draw": True,

    "excluded_competitions": ["Friendly", "Preseason"],
}
