"""LIVE mod onayı — headless (sunucu) güvenli. main.py ince kalsın diye ayrı."""
from __future__ import annotations

from typing import Callable

_CONFIRM_PHRASE = "CONFIRM LIVE"
_HEADLESS_ENV_TRUE = "1"


def require_live_confirmation(
    is_tty: bool,
    env_value: str | None,
    prompt_fn: Callable[[], str] | None,
) -> None:
    """LIVE mod için onay iste. Onay yoksa SystemExit.

    - Klavye varsa (is_tty): 'CONFIRM LIVE' yazılmalı.
    - Klavye yoksa (sunucu): POLYMARKET_CONFIRM_LIVE=1 ortam değişkeni şart.
    """
    if is_tty:
        if prompt_fn is None or prompt_fn().strip() != _CONFIRM_PHRASE:
            raise SystemExit("LIVE onayı verilmedi. İptal.")
        return
    if env_value != _HEADLESS_ENV_TRUE:
        raise SystemExit(
            "Headless LIVE onayı yok. Sunucuda LIVE için POLYMARKET_CONFIRM_LIVE=1 gerekli."
        )


def confirm_live_if_needed(is_live: bool) -> None:
    """main.py'den tek satır çağrı — LIVE ise gerçek tty/env/input ile onay iste.

    main.py ince kalsın diye (ARCH Kural 5) tty/env okuma burada yapılır.
    """
    if not is_live:
        return
    import os  # noqa: PLC0415
    import sys  # noqa: PLC0415
    require_live_confirmation(
        is_tty=sys.stdin.isatty(),
        env_value=os.getenv("POLYMARKET_CONFIRM_LIVE"),
        prompt_fn=lambda: input("Type 'CONFIRM LIVE' to proceed: "),
    )
