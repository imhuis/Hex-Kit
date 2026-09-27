# Golang Profile

Applies to Go modules and packages independently of any web framework. Use the applicable shared layer spec for architecture and contracts; this profile supplies Go-specific semantics and idioms.

## Topic

[Go Idioms and Pitfalls](./idioms-and-pitfalls.md): small interfaces, typed nil, error wrapping, slice aliasing, loop variables, context, synchronization, and SQL rows.

## Pre-Development Checklist

- Inspect go.mod, any workspace/toolchain configuration, and the actual build environment. The effective language version matters as well as the installed compiler.
- Identify error contracts, slice ownership, goroutine lifetime, and context propagation touched by the change.
- Do not import Java-style service/interface hierarchies or select a Go web framework through this profile.

## Quality Check

Use the project's existing formatting, vet, and package-test commands. For changed concurrent behavior, run the relevant race-enabled tests when the platform supports them; a clean race run covers only exercised execution paths. Do not make every task run a repository-wide race suite.

All documentation must be written in English. Return to [Technology Profiles](../index.md).
