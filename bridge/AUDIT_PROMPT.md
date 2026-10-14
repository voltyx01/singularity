# Bug audit (read-only)

The project works, but playtesting keeps finding places where the new code silently behaves differently from the original.
Your job: find more of them in YOUR SCOPE by comparing each file with its original, and write a report.
**Do not edit any source file.** The only file you write is the report.

- You **cannot run ANY shell command** except the gateway (see below): any other attempt aborts your run.
  Use only your built-in tools to list directories, search text, read files and write the report file.
- Files to audit: the directories of your scope. Originals: `<where the reference lives>`.

## Bug patterns to look for  (edit this list for your project - concrete patterns found earlier work best)
1. **Silent non-override.** A method kept its old name/signature, so it no longer overrides the framework method and is never called.
2. **Rename into recursion.** A method was renamed but its body still calls "itself" with the same arguments.
3. **Wrong constructor/super arguments.** A flag passed in the slot of a different parameter.
4. **Stub / lost logic.** A body that is empty, returns a constant, or is much shorter than the original; `TODO` markers.
5. **Inverted or changed conditions.** Flipped `!`, `<` vs `<=`, wrong constant, wrong config field.
6. **Never wired.** Something the original registered/subscribed that the new code does not.
7. **Serialisation.** Save and load use different keys; a synced field is never declared.

Ignore: pure renames that are correct, formatting, anything obviously equivalent.
Do NOT report "should check" items: every finding needs the concrete lines.

## Report
Write `bridge/REPORT/AUDIT-<unit>.md` (unit name given below). One entry per finding, most severe first:

```
### <short title>
- Pattern: <1-7>
- Port: <path>:<line>
- Ref: <path>:<line>
- What happens at runtime: <one sentence>
- Fix: <concrete change>
- Confidence: high | medium | low
```
End with a line `Files audited: N` and a list of files you could not finish. If nothing is found, say so.
