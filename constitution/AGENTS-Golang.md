# Go Project Constraints

These constraints apply to Go libraries, services, and command-line applications. Use them together with the project's architecture, security requirements, and public contracts. A project's actual layout and supported environments determine which operational instructions apply.

## Understand the project before editing

- Inspect the working tree and existing changes. Preserve user edits, unrelated files, and staging state.
- Read the relevant packages and their callers before choosing an implementation. Identify ownership, dependency direction, and the behavior being changed.
- Check `go.mod`, workspace configuration where present, build tags, and CI settings for the supported language version, toolchain, and execution environments.
- Keep changes within the requested scope and its necessary dependencies. Do not use the task as an opportunity for unrelated refactoring.

## Package boundaries and reuse

- Organize packages around coherent responsibilities and explicit dependencies. Follow the repository's layout rather than imposing a particular directory structure or application framework.
- Use `internal/` when Go's import restrictions match the intended visibility. A `pkg/` directory is optional and does not by itself establish a supported public API.
- Keep protocol adaptation, business rules, and external integrations distinct where the application needs those boundaries. Do not create layers that have no responsibility in the current design.
- Search existing packages and dependencies for the required capability before introducing another implementation. Reuse behavior only when its semantics and ownership fit the use case.
- Assess new dependencies for compatibility, maintenance, security, and operational cost. Do not replace a suitable maintained dependency with custom infrastructure solely to reduce dependency count.

## Naming, scope, and abstraction

- Choose names that express responsibility or meaning. Avoid generic names when a more precise domain or operation name is available.
- Keep variable lifetimes easy to follow. Local shadowing is acceptable when it is unambiguous; avoid it when it hides an error, changes the apparent owner of a resource, or causes later code to use the wrong value.
- Reuse `err` for sequential operations when each result is handled before reassignment. Use separate names when multiple failures need to remain available together.
- Add an interface when a consumer needs a behavioral contract or a dependency boundary. Prefer the smallest contract that expresses that responsibility; do not create an interface for every concrete type.
- Expand an interface only when the additional behavior belongs to the same responsibility. Inspect implementations, test doubles, and consumers, and evaluate compatibility before changing it.
- A short wrapper is justified when it owns a contract, translates a boundary, or expresses meaningful semantics. Remove wrappers that only obscure a direct call without adding such value.

## Error contracts and diagnostics

- Handle errors at the point where the caller can make a meaningful decision. Do not discard failures or report success after a required operation fails.
- Add operation context to propagated errors. Use `%w` when callers should retain access to the underlying error, and use `errors.Is` or `errors.As` when matching error identity or type.
- Keep implementation-specific errors behind the appropriate boundary when exposing them would create an unintended public contract.
- Reserve panic for conditions where normal recovery through an error result is inappropriate under the package's contract.
- Follow existing logging conventions. Record enough context to locate a failure without exposing credentials or sensitive payloads, and avoid logging the same propagated failure at every layer.

## Cancellation, concurrency, and shared data

- Propagate the caller's context through operations that support cancellation. Do not replace it with a detached context merely to keep work alive after the caller has finished.
- State any intentional background lifetime explicitly, with an owner, shutdown mechanism, and bounded resource use.
- For each goroutine, identify how it starts, how it stops, and who waits for it. Check that sends, receives, locks, and external calls can complete during cancellation and shutdown.
- Protect shared mutable data through a clear synchronization or ownership model. Document whether callers may modify slices, maps, or pointers passed across a package boundary.
- Define channel closing ownership. When closure must be distinguished from a message, check the receive result; when consuming until closure, a range loop may express the contract directly. Zero values remain valid unless the message contract excludes them.
- Avoid busy loops on closed channels. Do not close a channel while another goroutine can still send to it.
- Bound concurrent work and queued data where workload can exceed processing capacity. Make retry limits and stopping conditions explicit for operations that retry.
- For side effects, address partial completion and repeated execution according to the actual contract. Do not assume a retry is safe simply because the previous call returned an error.

## Resource ownership and files

- Assign an owner to each file, response body, connection, timer, and other resource requiring cleanup. Cover normal completion, early returns, and cancellation as applicable.
- Use `defer` when cleanup should occur at function exit. For resources created repeatedly in a long-running loop, release them within each iteration or a scoped function.
- Check close, flush, or commit errors when they determine whether the operation succeeded. Cleanup-only errors should follow the project's diagnostic policy.
- Use standard library facilities or existing project utilities for file operations. Choose permissions and temporary-file behavior according to the data and supported platforms.
- Do not infer successful persistence from a successful write alone when the operation's contract also requires flushing, closing, or another completion step.

## Reliability and performance

- Cover failure paths relevant to the requirement and existing contracts. External operations may require timeouts, cancellation, input limits, or handling of partial results; apply these according to the actual risk.
- Prefer implementations with understandable time and memory costs. Investigate a demonstrated performance problem before adding pooling, caching, or complex concurrency.
- Validate external input at its entry boundary. Preserve the application's authentication, authorization, and data-isolation rules through queries, writes, and caches where applicable.
- Keep externally consumed APIs, persisted formats, and CLI behavior compatible unless a breaking change is explicitly authorized.

## Tests and verification

- Use the repository's documented commands and existing test infrastructure. Build required fixtures or start required services only when the selected checks need them.
- Run relevant existing tests first. Add tests when a changed behavior or identified regression is not covered, with assertions on observable outcomes rather than implementation structure.
- Name tests by the behavior they verify. Add comments for non-obvious setup or contracts rather than repeating the test name.
- Coordinate asynchronous tests with observable events and synchronization. Avoid arbitrary sleeps; when time is part of the behavior, use bounded waits appropriate to the contract and execution environment.
- Ensure test resources and goroutines are cleaned up even when assertions fail. Do not let one test depend on mutable state left by another.
- Use the existing formatting, static-analysis, build, and lint checks. Where no project wrapper exists, `gofmt`, `go vet`, `go test`, and `go build` provide relevant baseline checks; select package scope and build settings to match the change.
- For concurrency changes, run relevant tests with `-race` when the toolchain and environment support it. A passing race run only covers paths exercised by those tests.
- Choose test-process timeouts and parallelism according to the suite and available resources. Do not impose a universal duration or worker count on every project.
- Verify affected supported platforms and integrations when the change depends on them. Use available CI or local environments and report any unverified targets.
- Documentation-only changes require content and formatting checks; do not run unrelated application tests solely because a file changed.

## Generated code and maintenance context

- Find the project's generation instructions before editing generated artifacts. Change the authoritative input and regenerate through the established workflow.
- Review generated output for unintended changes. Do not assume every repository uses the same generator or Make targets.
- Document exported behavior, ownership, cancellation, and concurrency constraints where callers need them. Explain non-obvious decisions near the code or link to the relevant design record.
- Keep comments accurate when behavior changes. Record temporary workarounds with their reason, impact, and removal condition rather than leaving an unexplained TODO.

## Completion

- Review the final changes for unrelated edits, obsolete comments, and accidental changes to generated files or dependency manifests.
- Report the resulting behavior, checks actually executed, and any remaining verification gaps.
- Do not create commits or perform destructive Git operations without explicit authorization.


<!-- REFERENCE:START -->

* https://github.com/microsoft/dcp/blob/main/AGENTS.md

<!-- REFERENCE:END -->