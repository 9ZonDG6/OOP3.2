from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NumbersSnapshot:
    a: int
    b: int
    c: int
    minimum: int
    maximum: int
    notification_count: int


type Subscriber = Callable[[NumbersSnapshot], None]


class NumbersModel:
    MINIMUM = 0
    MAXIMUM = 100
    DEFAULT_STATE = (0, 50, 100)

    def __init__(self, *, storage_path: Path | None = None, autosave: bool = True) -> None:
        self._storage_path = storage_path or Path(__file__).resolve().parent / "state.json"
        self._autosave = autosave
        self._a, self._b, self._c = self.DEFAULT_STATE
        self._loaded = False
        self._notification_count = 0
        self._subscribers: list[Subscriber] = []

    @property
    def minimum(self) -> int:
        return self.MINIMUM

    @property
    def maximum(self) -> int:
        return self.MAXIMUM

    @property
    def notification_count(self) -> int:
        return self._notification_count

    @property
    def storage_path(self) -> Path:
        return self._storage_path

    @property
    def values(self) -> tuple[int, int, int]:
        return self._a, self._b, self._c

    @property
    def snapshot(self) -> NumbersSnapshot:
        return NumbersSnapshot(
            a=self._a,
            b=self._b,
            c=self._c,
            minimum=self.minimum,
            maximum=self.maximum,
            notification_count=self._notification_count,
        )

    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:
        self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

        return unsubscribe

    def load(self) -> None:
        loaded_state = self._read_state()
        force_notify = not self._loaded
        self._loaded = True
        self._commit(*loaded_state, persist=False, force_notify=force_notify)

    def save(self) -> None:
        payload = {"a": self._a, "b": self._b, "c": self._c}
        serialized = json.dumps(payload, indent=2)
        temporary_path = self._storage_path.with_suffix(".tmp")

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(serialized, encoding="utf-8")
            temporary_path.replace(self._storage_path)
        except OSError:
            return

    def set_a(self, value: int) -> None:
        a = self._clamp(value)
        b = max(self._b, a)
        c = max(self._c, b)
        self._commit(a, b, c)

    def set_b(self, value: int) -> None:
        b = self._clamp(value, self._a, self._c)
        self._commit(self._a, b, self._c)

    def set_c(self, value: int) -> None:
        c = self._clamp(value)
        b = min(self._b, c)
        a = min(self._a, b)
        self._commit(a, b, c)

    @classmethod
    def _clamp(cls, value: int, minimum: int | None = None, maximum: int | None = None) -> int:
        low = cls.MINIMUM if minimum is None else minimum
        high = cls.MAXIMUM if maximum is None else maximum
        return max(low, min(high, value))

    def _read_state(self) -> tuple[int, int, int]:
        if not self._storage_path.exists():
            return self.DEFAULT_STATE

        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            return self.DEFAULT_STATE

        if not isinstance(payload, dict):
            return self.DEFAULT_STATE

        default_a, default_b, default_c = self.DEFAULT_STATE
        a = self._read_int(payload, "a", default_a)
        b = self._read_int(payload, "b", default_b)
        c = self._read_int(payload, "c", default_c)
        return self._normalize_loaded_state(a, b, c)

    @staticmethod
    def _read_int(payload: dict[str, object], key: str, fallback: int) -> int:
        value = payload.get(key, fallback)
        if isinstance(value, bool) or not isinstance(value, int):
            return fallback
        return value

    def _normalize_loaded_state(self, a: int, b: int, c: int) -> tuple[int, int, int]:
        a = self._clamp(a)
        b = self._clamp(b)
        c = self._clamp(c)

        if a > c:
            c = a

        b = self._clamp(b, a, c)
        return a, b, c

    def _commit(
        self,
        a: int,
        b: int,
        c: int,
        *,
        persist: bool = True,
        force_notify: bool = False,
    ) -> None:
        new_state = (a, b, c)
        old_state = self.values

        if not force_notify and new_state == old_state:
            return

        self._a, self._b, self._c = new_state

        if persist and self._autosave and self._loaded:
            self.save()

        self._notify()

    def _notify(self) -> None:
        self._notification_count += 1
        snapshot = self.snapshot
        for subscriber in tuple(self._subscribers):
            subscriber(snapshot)
