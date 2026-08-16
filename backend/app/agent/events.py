import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class PublicRunEvent:
    run_id: str
    event_type: str
    sequence: int
    payload: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_sse(self) -> str:
        data = json.dumps(self.as_dict(), separators=(",", ":"), ensure_ascii=False)
        return f"event: {self.event_type}\ndata: {data}\n\n"
