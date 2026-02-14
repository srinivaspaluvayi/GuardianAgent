"""Redis Streams helpers (XADD, XREADGROUP, XACK)."""
import json
from typing import Any, Dict, List, Tuple

import redis


class RedisStreams:
    def __init__(self, url: str):
        self.r = redis.Redis.from_url(url, decode_responses=True)

    def xadd(self, stream: str, obj: Dict[str, Any]) -> str:
        return self.r.xadd(stream, {"json": json.dumps(obj)})

    def ensure_group(self, stream: str, group: str) -> None:
        try:
            self.r.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def xreadgroup(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> List[Tuple[str, List[Tuple[str, Dict[str, str]]]]]:
        return self.r.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )

    def xack(self, stream: str, group: str, msg_id: str) -> None:
        self.r.xack(stream, group, msg_id)
