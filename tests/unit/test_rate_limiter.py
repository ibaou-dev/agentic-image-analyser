"""Unit tests for the token bucket rate limiter."""

from __future__ import annotations

import threading
import time

import pytest

from agentic_vision.rate_limiter import RateLimiter, TokenBucket


# ─── TokenBucket ─────────────────────────────────────────────────────────────
class TestTokenBucket:
    def test_starts_full(self) -> None:
        b = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert b.available == pytest.approx(10.0, abs=0.1)

    def test_try_acquire_succeeds_when_full(self) -> None:
        b = TokenBucket(capacity=5.0, refill_rate=1.0)
        assert b.try_acquire(5.0) is True

    def test_try_acquire_fails_when_empty(self) -> None:
        b = TokenBucket(capacity=5.0, refill_rate=1.0)
        b.try_acquire(5.0)  # drain
        assert b.try_acquire(1.0) is False

    def test_acquire_blocks_until_refilled(self) -> None:
        # Capacity 1, refill 10/s → 0.1s to get 1 token
        b = TokenBucket(capacity=1.0, refill_rate=10.0)
        b.try_acquire(1.0)  # drain
        start = time.monotonic()
        acquired = b.acquire(1.0, timeout=2.0)
        elapsed = time.monotonic() - start
        assert acquired is True
        assert 0.05 < elapsed < 0.5  # should take ~0.1s

    def test_acquire_timeout(self) -> None:
        # Capacity 1, refill 0.1/s — needs 10s to refill; timeout=0.1s
        b = TokenBucket(capacity=1.0, refill_rate=0.1)
        b.try_acquire(1.0)  # drain
        result = b.acquire(1.0, timeout=0.1)
        assert result is False

    def test_refill_does_not_exceed_capacity(self) -> None:
        b = TokenBucket(capacity=5.0, refill_rate=100.0)
        time.sleep(0.1)  # let it refill (already full)
        assert b.available <= 5.0 + 0.01  # float tolerance

    def test_thread_safety(self) -> None:
        """Multiple threads acquiring simultaneously should not over-drain."""
        b = TokenBucket(capacity=100.0, refill_rate=0.0)  # no refill
        successes = []

        def try_get() -> None:
            successes.append(b.try_acquire(1.0))

        threads = [threading.Thread(target=try_get) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sum(successes) == 100  # exactly capacity


# ─── RateLimiter ─────────────────────────────────────────────────────────────
class TestRateLimiter:
    def test_default_rpm_tpm(self) -> None:
        rl = RateLimiter(rpm=60, tpm=250_000)
        status = rl.status()
        assert status["rpm_capacity"] == 60.0
        assert status["tpm_capacity"] == 25_000.0  # tpm // 10

    def test_acquire_succeeds_when_fresh(self) -> None:
        rl = RateLimiter(rpm=60, tpm=250_000)
        assert rl.acquire(estimated_tokens=500, timeout=1.0) is True

    def test_acquire_fails_when_rpm_exhausted(self) -> None:
        # rpm=1 with 0 refill rate (implicitly via very slow refill)
        # Drain the RPM bucket manually
        rl = RateLimiter(rpm=1, tpm=100_000)
        rl.rpm_bucket.try_acquire(1.0)  # drain 1 slot
        result = rl.acquire(estimated_tokens=100, timeout=0.05)
        assert result is False  # can't get RPM slot fast enough

    def test_status_returns_expected_keys(self) -> None:
        rl = RateLimiter(rpm=30, tpm=100_000)
        status = rl.status()
        assert set(status.keys()) == {
            "rpm_available",
            "rpm_capacity",
            "tpm_available",
            "tpm_capacity",
        }

    def test_rpm_refill_rate(self) -> None:
        # rpm=60 means 1 req/sec; capacity=60
        rl = RateLimiter(rpm=60, tpm=250_000)
        assert rl.rpm_bucket.refill_rate == pytest.approx(1.0)  # 60/60
