# CLAUDE.md

Guidance for Claude when working in this repository.

## What this project is

`dxwatch.py` is a live "who's on" monitor for a DX Cluster node (amateur
radio spotting network). It opens one TCP connection to a cluster node,
logs in with a callsign, and concurrently:

1. reads the live spot stream to track **active spotters**, and
2. polls `sh/users` on a timer to track **connected users**.

Full protocol and design rationale is written up in the module docstring
at the top of `dxwatch.py` — read that first, it's the source of truth.

## Who maintains this

The primary maintainer is the user's father: an experienced programmer in
**C and Smalltalk**, new to Python and to the GitHub/pip toolchain
specifically — not new to programming. Calibrate accordingly:

- Don't over-explain programming concepts (loops, objects, callbacks) —
  he knows these cold in other languages.
- Do bridge unfamiliar **Python-specific** idioms to something in C or
  Smalltalk when introducing them (e.g. `asyncio`'s event loop ≈ a
  hand-rolled `select()` loop in C, or Smalltalk's green `Process`
  scheduling — see the docstring for the pattern to follow).
- Avoid assuming familiarity with the Python packaging ecosystem (pip,
  venvs, `requirements.txt`). He shouldn't need any of it for this project.

## Hard constraints — do not casually violate

- **Single file.** `dxwatch.py` is meant to stay one self-contained file
  he can save anywhere and run. Don't split it into a package or add a
  `src/` layout without an explicit reason and his buy-in.
- **Standard library only.** No third-party dependencies, no `pip install`,
  no virtual environment. This is deliberate — it removes the entire
  Python tooling learning curve for someone who just wants to run a
  script. If a feature seems to need a PyPI package, look for a stdlib
  way first and flag the tradeoff before reaching for one.
- **No `telnetlib`.** It was deprecated and removed in Python 3.13. The
  script talks to the node over a raw socket via `asyncio.open_connection`
  instead — keep it that way. (`telnetlib3` would be the async drop-in
  *if* IAC negotiation ever became necessary, but it hasn't.)
- **Python 3.8+ compatibility.** Don't rely on syntax newer than that
  without checking it's actually needed.

## Architecture notes

- `Monitor` holds all session state as plain instance variables
  (`recent_spotters`, `user_lines`, `logged_in`, `capturing_users`).
  This is intentional and safe *because* asyncio is cooperative — state
  is only ever touched between `await` points, so there are no locks and
  no races. Don't add threading or multiprocessing; it would break this
  invariant for no benefit.
- `reader_loop` (passive, reads the spot firehose) and `users_loop`
  (active, polls `sh/users` on `USERS_EVERY`) run concurrently via
  `asyncio.gather`. Any new concurrent job should follow the same shape:
  a coroutine method on `Monitor`, added to the `gather` call in `run()`.
- `main()` owns reconnect-with-backoff. Any change to connection handling
  should preserve that — nodes drop connections, and the script should
  never require a manual restart for that reason alone.
- The five constants at the top (`CALLSIGN`, `HOST`, `PORTS`,
  `USERS_EVERY`, `SPOTTER_TTL`) are the intended configuration surface.
  Prefer adding new user-facing knobs there over inventing a config file
  or CLI flags, to keep the "just run it" story intact.

## Known rough edge

`CALL_RE` (the heuristic for pulling callsigns out of `sh/users` replies)
is deliberately loose because DXSpider and AR-Cluster format that reply
differently. If tightening it, verify against real output from the
configured node (default: W1NR, `dx.w1nr.net`) rather than assumptions —
the spot-line parser (`SPOT_RE`) is solid and doesn't need this treatment.

## Testing changes

There's no test suite. The working pattern established so far is
interactive, REPL-based verification — the same evaluate-and-inspect
rhythm as a Smalltalk workspace, which is deliberately how this project
introduces him to Python:

```
python3 -i dxwatch.py   # or: import dxwatch, from a plain REPL
>>> dxwatch.band_for(14025.0)   # example, once band filtering exists
```

This only works because network startup is gated behind
`if __name__ == "__main__":` — preserve that guard so importing the module
never launches the live connection.

## Style conventions already established

- Comments should teach, not just describe — especially anywhere a
  Python idiom shows up that a C/Smalltalk reader wouldn't have met
  before (e.g. the `None` sentinel and `is`, tuple unpacking in a
  `for` loop, chained comparisons, set literals). One line bridging it
  to something he already knows is the target, not a paragraph.
- Prefer small, separable edits over clever one-liners when extending
  behavior (e.g. a prospective filter feature was deliberately shaped as
  switch → lookup → gate, three separate steps) — the decomposition
  itself is often the more valuable thing to hand him.
- Node/protocol facts belong in the module docstring, not scattered in
  comments — keep it as the single source of truth it currently is.
