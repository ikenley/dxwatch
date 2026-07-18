# dxwatch

A live "who's on" monitor for a DX Cluster node — amateur radio's real-time
spot network.

It answers "who's online" in both senses at once:

- **Active spotters** — operators currently posting spots, read straight off
  the live feed as they arrive.
- **Connected users** — operators currently logged in to the node, fetched
  by polling `sh/users` once a minute.

## Running it

This is **one file**, and it uses **only the Python standard library**.
There is nothing to install — no `pip`, no virtual environment, no
`requirements.txt`.

1. Make sure Python 3 is installed (3.8 or newer). Check with:
   ```
   python3 --version
   ```
2. Run it:
   ```
   python3 dxwatch.py
   ```
3. Press `Ctrl-C` to stop.

That's the whole ceremony. If Python isn't installed yet, get it from
[python.org](https://www.python.org/downloads/) or your OS's package
manager.

## Configuring it

Everything you're likely to want to change lives in five constants near the
top of `dxwatch.py`:

```python
CALLSIGN    = "AC1NY"          # the call you log in with (use YOUR own call)
HOST        = "dx.w1nr.net"    # W1NR, Marlborough MA (YCCC)
PORTS       = [7300, 23]       # try DXSpider's usual port first, then plain telnet
USERS_EVERY = 60               # seconds between "sh/users" polls
SPOTTER_TTL = 600              # a spotter counts as "active" for this many seconds
```

**Change `CALLSIGN` to your own.** Cluster etiquette is to identify as
yourself when you connect — don't log in as `AC1NY`.

## The node

Defaults to **W1NR** in Marlborough, MA — a DXSpider node run by the Yankee
Clipper Contest Club, and the closest reliable node to Worcester (no node
sits in Worcester itself). If W1NR is ever down, **K1TTT** in Peru, MA is
the western-Mass alternative — swap in its host to point there instead.

## What you'll see

A running line for every spot as it arrives:

```
14:32:07  W1ABC      spotted JA1XYZ     on   14025.0  CQ DX
```

and, once a minute, a snapshot of who's connected and who's been active:

```
==== connected users @ 14:33:00  (n=12) ====================
  W1ABC  K1XYZ  N1QRS  ...
---- active spotters, last 10 min  (n=4) --------------------
  W1ABC  W3LPL  K1TTT  ...
```

## A known rough edge

Spot lines are near-standardized across cluster software, so that parser is
solid. The `sh/users` reply is the soft spot — its column layout differs
between DXSpider and AR-Cluster, so the script extracts anything
callsign-shaped from the reply (`CALL_RE`) rather than assuming a fixed
format. It works, but once you've seen W1NR's actual `sh/users` output
you may want to tighten that pattern. That's a good first edit to make.

## License

See `LICENSE`.
