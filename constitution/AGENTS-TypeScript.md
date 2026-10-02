# TypeScript Project Constraints

These constraints apply to TypeScript applications, libraries, services, scripts, and command-line tools. Use them together with the project's architecture, security requirements, and public contracts. Follow applicable repository instructions when they define more specific requirements. The supported compiler, runtime, and build pipeline determine which language features and operational checks apply.

## Understand the project before editing

- Inspect the working tree and target files' existing changes. Preserve user edits, unrelated files, and staging state.
- Read the relevant modules and their callers. Identify the behavior being changed, its owner, and the intended dependency direction.
- Inspect package manifests, lockfiles, workspace configuration, applicable `tsconfig` files, lint and formatting configuration, and CI scripts before choosing commands or adding dependencies.
- Confirm supported TypeScript versions and execution environments. Do not assume a particular framework, package manager, directory layout, test runner, or Node.js runtime.
- Keep changes within the requested scope and necessary dependencies. Avoid unrelated refactoring, dependency upgrades, and repository-wide formatting.

## Essential commands

Identify the package manager from the project's `packageManager` field, lockfile, and documented workflow. Read `package.json` scripts and CI configuration for the actual command names and scope. The following is an example for a pnpm project that defines these scripts; adapt it to the repository rather than assuming every command exists.

```bash
pnpm install          # Install dependencies when needed
pnpm run build        # Build the configured project or packages
pnpm run type-check   # Validate TypeScript types
pnpm run lint         # Run the configured lint checks
pnpm run test-unit    # Run unit tests
pnpm run test-e2e     # Run end-to-end tests when relevant
```

- Use the chosen package manager consistently and preserve the lockfile. For reproducible CI installs, use its supported lockfile-enforcing mode, such as `pnpm install --frozen-lockfile` or `npm ci`, as appropriate to the project.
- With npm or Yarn, use the equivalent install and script commands. Script names such as `typecheck`, `check`, or `test` may differ; use the actual definitions instead of adding aliases solely to match this example.
- In a workspace, use its documented package-selection commands to check the affected packages and relevant dependents. A root script does not necessarily run checks for every package.
- Install dependencies only when required. Select type checks, lint, builds, and tests according to the change; end-to-end tests may require fixtures, services, or a specific environment.
- Do not run scripts that publish, deploy, or modify external data as routine verification without authorization for those actions.

## Compiler configuration and tooling

- Use the repository's installed compiler and documented scripts. Keep editor, CI, and build configuration aligned; do not depend on a globally installed compiler or silently download another toolchain.
- Enable `strict` for new projects unless a documented toolchain or interoperability constraint prevents it. In existing projects, preserve the configured checks and scope stricter settings as an explicit migration rather than an incidental change.
- Evaluate `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` against the project's contracts and migration cost. They are additional checks, not implied by `strict`.
- Choose `target`, `lib`, `module`, and `moduleResolution` to match the actual runtime and build pipeline. Type declarations for an API do not provide that API or a polyfill at runtime.
- Do not weaken compiler or lint rules, exclude affected source files, or introduce broad ambient declarations merely to make a change pass checks. Keep justified exceptions narrow and explain their reason and removal condition where temporary.
- Treat formatting and import ordering as project configuration. Do not impose universal quote, semicolon, naming-prefix, or line-length rules.

## Types, inference, and contracts

- Prefer inference for straightforward local values. Declare types explicitly where they define public contracts, constrain inference, or make a complex boundary easier to understand.
- Give exported functions and methods explicit return types when they form a supported module or library contract. Keep parameters and returned values independent of incidental implementation details.
- Model actual valid states. Use discriminated unions when variants have different required data; avoid collections of optional fields or boolean flags that admit invalid combinations.
- Distinguish absent properties, `undefined`, `null`, and empty values according to the contract, especially for updates and serialization. Do not use truthiness checks when `0`, `false`, or an empty string is valid.
- Check collection lookups and indexed access when absence is possible, even if the current compiler settings do not report it. Do not assume an array is nonempty or every dictionary key exists.
- Use `type` and `interface` according to the semantics needed and existing conventions. Declaration merging, unions, mapped types, and extension requirements matter more than a universal preference for either keyword.
- Introduce generics to express a real relationship between values or contracts. Avoid unused type parameters and elaborate conditional types when a direct type would express the requirement clearly.
- Use `readonly` and readonly collections when callers should not mutate data through an interface. They do not freeze objects at runtime or guarantee deep immutability; protect shared data through actual ownership or copying where required.
- Keep type-level machinery understandable and economical. Do not trade maintainable contracts and reasonable compiler performance for clever abstractions.

## Unknown values, narrowing, and assertions

- Use `unknown` for values whose shape has not been established, including unvalidated input and caught errors. Narrow or validate before use.
- Do not use `any` to bypass a known contract or resolve an ordinary type error. If an untyped dependency requires it, isolate it at the adapter boundary, document the limitation, and expose a checked contract to consumers.
- Prefer control-flow narrowing and checked conversion over type assertions. An assertion changes the compiler's view; it does not validate or convert a runtime value.
- Use assertions and non-null assertions only when an invariant is established and remains valid at the use site. Do not use double assertions through `unknown` or `any` to disguise incompatible models.
- A custom type predicate or assertion function must verify the properties it promises. Do not declare a guard trustworthy merely because its signature satisfies the compiler.
- When the supported compiler provides `satisfies`, use it where checking a value against a contract while retaining its inferred type is useful. Use `as const` when literal preservation or readonly inference expresses the intended contract.
- Handle all variants of a closed union. Use an exhaustiveness check where omission would be a defect; still validate unknown external variants at the runtime boundary.
- Avoid `@ts-ignore` and file-wide suppression. When a suppression is necessary, prefer a narrowly scoped `@ts-expect-error` with a reason; negative type tests should identify the contract they are verifying.

## Runtime validation and model boundaries

- TypeScript types are erased at runtime. Validate external data at its trust boundary before treating it as an application model, including network payloads, parsed JSON, persisted data, environment variables, and messages as applicable.
- Reuse existing validation libraries or boundary utilities before adding another solution. Validate the fields and invariants required by the current contract without building speculative validation infrastructure.
- Keep protocol, domain, persistence, and view models distinct where their responsibilities differ. Convert deliberately at boundaries instead of casting one representation into another.
- When a schema is the authoritative contract, derive types from it if the existing tooling supports that workflow. Avoid separately maintained declarations that can disagree with runtime validation.
- Make serialization explicit for values such as dates, large integers, maps, and optional fields. A successful type check does not prove a value can be encoded or round-tripped by the chosen protocol.
- Validation does not establish authorization. Apply the project's identity, access-control, and data-isolation rules independently of client-supplied types or identifiers.

## Modules, imports, and dependencies

- Organize modules around coherent responsibilities and explicit dependencies. Keep business rules independent of framework and infrastructure details where the project's architecture requires it.
- Use `import type` and `export type` for type-only dependencies when supported by the configured toolchain. Do not expect a type-only import to execute module initialization.
- Respect the actual ESM or CommonJS contract, package exports, and runtime import resolution. A TypeScript path alias alone does not configure runtime resolution.
- Keep environment-specific APIs behind appropriate boundaries. Do not leak server-only modules, credentials, or Node.js APIs into browser bundles.
- Avoid dependency cycles and import-time side effects that make initialization order or resource ownership implicit. Use deliberate entry points for initialization when required.
- Search existing modules and installed dependencies before adding another abstraction or package. Review compatibility, maintenance, security, bundle or startup cost, and required type declarations.
- Publish only intended exports. Do not expose internal dependency types accidentally or rely on another package's unsupported internal paths.
- For published libraries, verify declaration output, exports, and supported consumer environments. Do not assume a successful workspace build proves the installed package works.

## Errors, promises, and resource ownership

- Follow the existing error contract. Preserve useful operation context and the underlying cause where supported; do not swallow failures or return success after a required operation fails.
- Narrow caught values before reading error properties. JavaScript can throw values other than `Error`; normalize at a boundary when consumers require a stable error representation.
- Await, return, or explicitly supervise every promise. Prefixing a promise with `void` does not handle rejection; intentional background work needs an owner and failure policy.
- Do not pass an asynchronous callback to an API that ignores its returned promise unless completion and rejection are supervised separately. For example, `forEach` does not await an asynchronous callback.
- Define whether work should be sequential or concurrent from its dependencies and side effects. Bound concurrency for potentially large inputs; do not create unbounded work simply because `Promise.all` is available.
- Propagate cancellation through APIs that support it. State intentional background lifetimes, and clean up resources on completion, failure, and cancellation as applicable.
- Check assumptions about shared mutable state across `await` boundaries. Prevent stale responses, duplicate submissions, or competing updates when the actual interaction or use case permits them.
- Assign ownership for timers, subscriptions, listeners, streams, files, and connections. Make cleanup reliable, using the runtime's supported mechanisms and existing project patterns.
- For retries and side effects, define limits, stopping conditions, idempotency, and partial-failure behavior according to the operation's contract.
- Follow project logging conventions and protect sensitive data. Do not ban or introduce a logging API universally; libraries and applications may have different diagnostic contracts.

## Tests and verification

- Run relevant existing tests first. Add or extend tests when changed behavior or an identified regression lacks coverage, using the repository's existing infrastructure.
- Test observable behavior and relevant failures rather than mirroring implementation details. Use type-level tests when a public type contract is itself part of the changed behavior.
- Type checking, linting, tests, and builds verify different properties. Run the applicable checks for the affected scope; a transpilation-only build does not replace type checking.
- Use project scripts and applicable `tsconfig` files for type checks. Where no wrapper exists, use the installed compiler with the correct project configuration; passing individual source files can bypass that configuration.
- Verify runtime integration, bundling, or consumer compatibility when the change depends on them. Report supported environments that could not be checked.
- Keep asynchronous tests deterministic through observable events, controlled clocks, or existing synchronization tools. Ensure cleanup and avoid arbitrary sleeps or unbounded waits.
- Do not leave focused tests or disable existing tests to obtain a passing result. Explain any necessary, explicitly scoped test exclusion.
- For changes limited to UI presentation, use relevant type checks, builds, and browser verification rather than adding snapshots of implementation structure by default.
- Documentation-only changes require content and formatting checks; do not run unrelated application tests solely because a file changed.

## Generated code, compatibility, and completion

- Change authoritative schemas or generator inputs and regenerate through the established workflow. Do not edit generated declarations or artifacts as though they were handwritten source.
- Evaluate compatibility for public APIs, exported types, serialized formats, CLI arguments, and supported runtimes. A type-only change can still break consumers.
- Follow the repository's actual release and versioning process. Changesets, public npm access, and a particular package layout are project choices, not universal TypeScript requirements.
- Document non-obvious contracts, ownership, and compatibility decisions. Keep comments accurate and temporary workarounds traceable with a removal condition.
- Review the final diff for unrelated edits, unintended generated changes, and accidental configuration or dependency changes.
- Report what changed, which checks actually ran, and any remaining verification gaps. Do not create commits or perform destructive Git operations without explicit authorization.

<!-- REFERENCE:START -->

- [Vercel agent guidelines](https://raw.githubusercontent.com/vercel/vercel/refs/heads/main/AGENTS.md) — reference for organizing repository instructions; Vercel-specific commands, release rules, and runtime APIs are not adopted.
- [TypeScript configuration reference](https://www.typescriptlang.org/tsconfig/) — compiler settings and their individual semantics.
- [TypeScript narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) — control-flow analysis, type guards, and discriminated unions.

<!-- REFERENCE:END -->
