"""
Thread-safe token bucket rate limiter.

Each provider gets two buckets:
  - RPM (requests per minute): capacity = rpm, refill 1 token per (60/rpm) seconds
  - TPM (tokens per minute):   capacity = tpm // 10 (burst), refill tpm/60 per second

Usage:
    limiter = RateLimiter(rpm=60, tpm=250_000)
    limiter.acquire()               # blocks until RPM bucket allows
    limiter.acquire(tokens=1500)    # blocks until both RPM + TPM allow
"""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """A simple token bucket for rate limiting."""

    def __init__(self, capacity: float, refill_rate: float) -> None:
        """
        Args:
            capacity:     Maximum number of tokens (burst ceiling).
            refill_rate:  Tokens added per second.
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time (call with lock held)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Non-blocking acquire. Returns True if successful."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def acquire(self, tokens: float = 1.0, timeout: float = 30.0) -> bool:
        """
        Block until tokens are available or timeout is reached.

        Returns:
            True if acquired, False if timed out.
        """
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                # Calculate sleep time: how long until enough tokens accumulate
                deficit = tokens - self._tokens
                sleep_for = min(deficit / self._refill_rate, 1.0)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(sleep_for, remaining))

    @property
    def available(self) -> float:
        """Current token count (approximate, not thread-safe for display only)."""
        with self._lock:
            self._refill()
            return self._tokens

    @property
    def capacity(self) -> float:
        return self._capacity

    @property
    def refill_rate(self) -> float:
        return self._refill_rate


class RateLimiter:
    """
    Combined RPM + TPM rate limiter for a single provider.

    RPM bucket: 1 token per request, capacity = rpm.
    TPM bucket: estimated tokens per request, capacity = tpm // 10 (burst buffer).
    """

    def __init__(self, rpm: int, tpm: int) -> None:
        self._rpm = rpm
        self._tpm = tpm
        # RPM: refill 1 token per (60/rpm) seconds
        self.rpm_bucket = TokenBucket(
            capacity=float(rpm),
            refill_rate=rpm / 60.0,
        )
        # TPM: burst = tpm/10, refill = tpm/60 tokens per second
        self.tpm_bucket = TokenBucket(
            capacity=float(tpm // 10),
            refill_rate=tpm / 60.0,
        )

    def acquire(self, estimated_tokens: int = 1_000, timeout: float = 30.0) -> bool:
        """
        Acquire one RPM slot and estimated_tokens TPM slots.

        Args:
            estimated_tokens: Rough token estimate for this request.
                              Use image_size_bytes // 750 as a proxy.
            timeout:          Max seconds to wait.

        Returns:
            True if acquired within timeout, False otherwise.
        """
        start = time.monotonic()
        if not self.rpm_bucket.acquire(1.0, timeout=timeout):
            return False
        remaining_timeout = timeout - (time.monotonic() - start)
        return self.tpm_bucket.acquire(float(estimated_tokens), timeout=max(0.0, remaining_timeout))

    def status(self) -> dict[str, float]:
        """Return current bucket levels (for check-quota command)."""
        return {
            "rpm_available": self.rpm_bucket.available,
            "rpm_capacity": self.rpm_bucket.capacity,
            "tpm_available": self.tpm_bucket.available,
            "tpm_capacity": self.tpm_bucket.capacity,
        }
