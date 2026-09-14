from __future__ import annotations

from abc import ABC, abstractmethod

from ..context import BuildContext


class Source(ABC):
    """One upstream text. Subclasses parse it into the content database.

    `build` must be idempotent per fresh database and must not touch the
    network when `ctx.sample` is true (use `ctx.fixtures`).
    """

    def __init__(self, source_id: str, cfg: dict) -> None:
        self.id = source_id
        self.cfg = cfg

    @abstractmethod
    def build(self, ctx: BuildContext) -> None: ...
