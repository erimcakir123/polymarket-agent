"""Basketball data layer — NBA + WNBA için çift-kaynak veri pipeline'ı.

Tennis Sackmann pattern'inin basket muadili. Birincil: nba_api.
Yedek: ESPN scoreboard JSON. Sağlık takibi data_source_health.py'da.
Schema drift Pydantic ile fail-fast (schemas.py).
"""
