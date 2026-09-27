# Technology Profiles

Profiles supplement the shared [backend](../backend/index.md), [frontend](../frontend/index.md), and [thinking guides](../guides/index.md). They contain language/framework constraints, idioms, and recurring implementation traps only. They do not duplicate architecture, API design, security policy, logging policy, or general testing rules.

| Profile | Select when | Focus |
| --- | --- | --- |
| [Java](./java/index.md) | The changed module uses Java | Value semantics, collections, resources, streams, and interruption |
| [Golang](./golang/index.md) | The changed module uses Go | Interfaces, errors, slices, context, goroutines, and standard-library resource handling |
| [Spring](./spring/index.md) | The changed code uses Spring Framework or Spring Boot | Bean management, proxies, transactions, async execution, and MVC validation |

## Selection and Composition

1. Read the applicable shared layer index first. Identify the actual language/framework versions from build files and dependencies.
2. Add only matching profiles: a Java Spring backend uses backend + java + spring; a Go backend uses backend + golang. Spring is a framework supplement, not a replacement for the language profile. A frontend does not inherit a backend language profile.
3. Read only the relevant sections of each profile. Runtime constraints apply where their trigger exists; idioms are defaults rather than mandatory abstractions.
4. If the task uses context manifests, reference these concrete files alongside the shared specs:

```jsonl
{"file":".trellis/spec/profiles/java/idioms-and-pitfalls.md","reason":"Java value and resource semantics"}
{"file":".trellis/spec/profiles/spring/idioms-and-pitfalls.md","reason":"Proxy-based transaction behavior"}
```

Selection is performed by the developer or AI; this directory introduces no configuration field or automatic stack detector. Project contracts and AGENTS.md precedence still apply. Unfilled shared templates remain gaps, not an instruction to invent project conventions in a profile.

## Contribution Rule

For each addition, state its trigger, concrete failure mode, recommended handling, and version caveat where needed. Link authoritative documentation near version-sensitive rules. Do not add backend/frontend subdirectories, prescribe a new dependency, or copy shared rules into every profile. All documentation must be written in English.
