# Git basics for this repo

You and your son are sharing one repo, working straight on `main`, no
branches. That keeps things simple: the whole workflow is _pull, edit,
add, commit, push_, repeated.

Think of a **commit** as a saved snapshot of the whole project at a point
in time — closer to a checkpoint than a diff, though it stores only what
changed since the last one. **Push** and **pull** are how that snapshot
history gets copied to and from GitHub, which is really just a shared
server holding a copy of the repo.

## The essential loop

Every session, in this order:

1. **`git pull`** — get any changes your son has pushed since you last
   looked, before you start editing. Do this first, every time, even if
   you're fairly sure nothing changed.

2. Edit `dxwatch.py` (or whatever file) as normal, in your regular editor.

3. **`git status`** — see what you touched. Worth running often; it costs
   nothing and tells you exactly where you stand.

   ```
   git status
   ```

4. **`git add <file>`** — stage the file(s) you want in the next commit.
   **`git add *`** — (Optional) shortcut that stages all files.

   ```
   git add dxwatch.py
   ```

   Staging is git's own concept — think of it as a holding area you build
   up before you commit, so a commit can bundle exactly the files you
   mean it to, not just "everything that changed."

5. **`git commit -m "message"`** — take the snapshot. The message should
   say _why_, briefly — "add band filter to spot output" is more useful
   later than "changes."

   ```
   git commit -m "add band filter to spot output"
   ```

6. **`git push`** — send your commit(s) up to GitHub so your son can pull
   them.
   ```
   git push
   ```

That's the whole cycle. If you're the only one editing in a sitting, you
can skip straight to step 2 having already pulled at the start.

## A few more you'll want

- **`git diff`** — see exactly what changed, line by line, before you
  stage it. Good habit before every `git add`.

  ```
  git diff
  ```

- **`git log`** — see the commit history (who changed what, and the
  messages left behind).

  ```
  git log --oneline
  ```

- **`git checkout -- <file>`** — throw away _uncommitted_ edits to a
  file and revert it to the last commit. Useful if you've made a mess
  and want to start that file over. There's no undo past this, so check
  `git diff` first if you're not sure.
  ```
  git checkout -- dxwatch.py
  ```

## If `git pull` complains about a conflict

This means you and your son edited the same lines since the last pull.
Git will mark the conflicting spot in the file with `<<<<<<<`, `=======`,
and `>>>>>>>` markers. Don't panic and don't guess — stop, and either
sort it out together or ask for help resolving it. It's a normal,
recoverable situation, not a sign anything is broken.

## Further reading

For anything beyond this — branches, undoing a bad commit, and the rest
of git's much larger toolbox — the "Git Basics" chapter of the free
_Pro Git_ book is the standard reference:
https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository
