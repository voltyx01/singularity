# Requests to the orchestrator (symbols / classes needed from shared code)

Workers must not edit shared code. Append one line per need:

`- [agent/task] symbol -> where it is needed -> what it must do`

- [gemini-1/T001] Registry.type(Foo.class) -> Bar.<init> -> register Foo so Bar can create it
