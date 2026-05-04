"""Soccer sport config (SPEC-015) — score exit + regulation timing + filters."""

SOCCER_CONFIG: dict = {
    "regulation_minutes": 90,
    "stoppage_buffer": 6,

    # Score exit minutes (HOME/AWAY position)
    "score_exit_first_half_lock": 65,
    "score_exit_2goal_minute": 65,
    "score_exit_1goal_minute": 75,

    # Draw position
    "draw_protect_until": 70,
    "draw_exit_after_goal": 75,
    "knockout_auto_exit_draw": True,

    "excluded_competitions": [
        "International Friendly",
        "Club Friendly",
        "Preseason",
        "Testimonial",
    ],
}
