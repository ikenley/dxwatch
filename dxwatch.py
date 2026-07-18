#!/usr/bin/env python3
"""
dxwatch.py -- a live "who's on" monitor for a DX Cluster node.

WHAT IT DOES
    Opens one TCP connection to a DX Cluster node, logs in with your
    callsign, and then does two jobs at once on that single connection:

      1. Reads the live SPOT STREAM and keeps a rolling list of the
         operators who have posted a spot recently  -> "active spotters".
      2. Every 60 seconds it asks the node "sh/users" and prints the
         operators currently CONNECTED to the node -> "connected users".

    So it answers "who's online" in both senses at once.

HOW TO RUN IT
    This is ONE file and it uses ONLY the Python standard library. There is
    nothing to install -- no pip, no virtual environment, no GitHub. Once
    Python 3 is on the machine:

        python3 dxwatch.py

    Press Ctrl-C to stop.

THE NODE
    Defaults to W1NR (Marlborough, MA) -- DXSpider, run by the Yankee
    Clipper Contest Club, the closest reliable node to Worcester. Change
    HOST/PORTS below to point somewhere else.

    Login handshake (verified against W1NR, July 2026): on connect the
    node sends a short banner and then the prompt "login: " -- with NO
    trailing newline. So the prompt can never be detected by waiting for
    a complete line; login has to read raw chunks. Only after we answer
    with a callsign does the node start sending newline-terminated
    traffic (the spot stream, command replies).

A NOTE FOR A C / SMALLTALK READER
    * This is cooperative multitasking, not OS threads. asyncio runs a
      single event loop -- think of it as a select() loop in C, or as
      Smalltalk's green Processes scheduled by the VM. Nothing is preempted;
      a coroutine only ever yields the CPU at an "await". So there are no
      locks and no data races on the shared state below: between awaits, a
      coroutine runs to completion, uninterrupted.
    * "async def" defines a coroutine; "await X" is the yield point where
      control returns to the loop until X is ready. That's the only real
      Python-specific vocabulary here.
    * Indentation is the block delimiter -- there are no braces. The colon
      opens a block; the indent level closes it.
"""

import asyncio
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Settings -- ordinarily you only touch these.
# ---------------------------------------------------------------------------
CALLSIGN    = "AC1NY"          # the call you log in with (use YOUR own call)
HOST        = "dx.w1nr.net"    # W1NR, Marlborough MA (YCCC)
PORTS       = [7300, 23]       # try DXSpider's usual port first, then plain telnet
USERS_EVERY = 60               # seconds between "sh/users" polls
SPOTTER_TTL = 600              # a spotter counts as "active" for this many seconds

# ---------------------------------------------------------------------------
# Line patterns.
# ---------------------------------------------------------------------------
# A DXSpider spot looks like:
#   DX de W1ABC:     14025.0  JA1XYZ       CQ DX               1432Z
# Skimmer feeds append a marker to the spotter, e.g. "W3LPL-#".
SPOT_RE = re.compile(
    r"^DX de\s+(?P<spotter>[A-Z0-9/#@\-]+?):\s+"  # who reported it
    r"(?P<freq>[\d.]+)\s+"                        # frequency in kHz
    r"(?P<dx>[A-Z0-9/]+)\s+"                      # the station being spotted
    r"(?P<comment>.*?)\s*"                        # free-text comment (may be empty)
    r"(?P<time>\d{3,4}Z)?\s*$"                    # optional HHMMZ stamp
)

# Login prompts vary across node software; match the common ones.
LOGIN_RE = re.compile(r"login|enter your call|your call", re.IGNORECASE)

# Heuristic "this token looks like a callsign": something with a digit wedged
# between letters. This is deliberately loose because the exact column layout
# of "sh/users" differs between DXSpider and AR-Cluster. Once you see W1NR's
# actual sh/users output, you can tighten this.
CALL_RE = re.compile(r"\b[A-Z]{0,2}\d[A-Z]{1,4}\b")
NOT_CALLS = {"DE", "DX", "USERS", "NODE", "TOTAL", "MAX"}  # obvious false hits


def now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def normalize_spotter(call: str) -> str:
    """Strip a trailing skimmer marker so 'W3LPL-#' counts as 'W3LPL'."""
    return re.split(r"[-/](?:#|@)$", call)[0]


class Monitor:
    """One live session against the node. Holds all shared state as plain
    instance variables -- safe to share across the two coroutines below
    precisely because the event loop never preempts between awaits."""

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.logged_in = False
        self.capturing_users = False          # True only while a sh/users reply arrives
        self.user_lines = []                  # raw lines captured during that window
        self.recent_spotters = OrderedDict()  # callsign -> epoch seconds last seen

    async def send(self, command: str):
        self.writer.write((command + "\r\n").encode())
        await self.writer.drain()

    async def run(self):
        # Strictly sequential: finish the login handshake first, THEN start
        # the two concurrent jobs. This guarantees users_loop can never send
        # a command while the node is still sitting at its login prompt.
        await self.login()
        # asyncio.gather runs both coroutines on the one loop. If either
        # raises (e.g. the reader hits EOF), gather re-raises and we fall
        # back out to the reconnect loop in main().
        await asyncio.gather(self.reader_loop(), self.users_loop())

    # -- login handshake ----------------------------------------------------

    async def login(self):
        # The "login: " prompt has no trailing newline (see THE NODE above),
        # so readline() would block on it forever. Instead read raw chunks --
        # the same as recv() into a buffer in C -- and watch the accumulated
        # text for the prompt.
        buf = ""
        while True:
            chunk = await self.reader.read(256)
            if not chunk:                     # EOF before we even logged in
                raise ConnectionError("node closed the connection at login")
            buf += chunk.decode("utf-8", "replace")
            if LOGIN_RE.search(buf):
                await self.send(CALLSIGN)
                self.logged_in = True
                print(f"logged in as {CALLSIGN}")
                return

    # -- the two concurrent jobs -------------------------------------------

    async def reader_loop(self):
        while True:
            raw = await self.reader.readline()
            if not raw:                       # empty bytes == the node hung up
                raise ConnectionError("node closed the connection")
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            self.handle_line(line)

    async def users_loop(self):
        await asyncio.sleep(5)                # let the login settle first
        while True:
            self.user_lines = []
            self.capturing_users = True
            await self.send("sh/users")
            await asyncio.sleep(3)            # give the reply time to stream in
            self.capturing_users = False
            self.report()
            await asyncio.sleep(USERS_EVERY)

    # -- line dispatch ------------------------------------------------------

    def handle_line(self, line: str):
        m = SPOT_RE.match(line)
        if m:
            self.record_spot(m)
            return

        if self.capturing_users:
            self.user_lines.append(line)

    def record_spot(self, m):
        spotter = normalize_spotter(m.group("spotter"))
        self.recent_spotters[spotter] = time.time()
        self.recent_spotters.move_to_end(spotter)  # keep newest last
        print(
            f"{now_hms()}  {spotter:<10} spotted {m.group('dx'):<10} "
            f"on {m.group('freq'):>9}  {m.group('comment').strip()}"
        )

    # -- the periodic report -----------------------------------------------

    def report(self):
        connected = self.extract_users(self.user_lines)
        active = self.active_spotters()

        print()
        print(f"==== connected users @ {now_hms()}  (n={len(connected)}) "
              + "=" * 20)
        print("  " + "  ".join(connected) if connected else "  (none parsed)")
        print(f"---- active spotters, last {SPOTTER_TTL // 60} min  "
              f"(n={len(active)}) " + "-" * 20)
        print("  " + "  ".join(active) if active else "  (none yet)")
        print()

    def extract_users(self, lines):
        seen = OrderedDict()
        for line in lines:
            for tok in CALL_RE.findall(line):
                if tok not in NOT_CALLS:
                    seen[tok] = True
        return list(seen)

    def active_spotters(self):
        cutoff = time.time() - SPOTTER_TTL
        # prune expired, then return newest-first
        for call in [c for c, t in self.recent_spotters.items() if t < cutoff]:
            del self.recent_spotters[call]
        return list(reversed(self.recent_spotters))


async def connect():
    """Try each port in turn; return the first that answers."""
    last_error = None
    for port in PORTS:
        try:
            reader, writer = await asyncio.open_connection(HOST, port)
            print(f"connected to {HOST}:{port}")
            return reader, writer
        except OSError as e:
            print(f"  {HOST}:{port} -> {e}")
            last_error = e
    raise last_error


async def main():
    backoff = 2
    while True:
        try:
            reader, writer = await connect()
            backoff = 2                        # reset once we're in
            await Monitor(reader, writer).run()
        except asyncio.CancelledError:
            raise
        except (OSError, ConnectionError, asyncio.IncompleteReadError) as e:
            print(f"connection problem: {e}")
        print(f"reconnecting in {backoff}s ...")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)         # exponential backoff, capped at 60s


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped.")
