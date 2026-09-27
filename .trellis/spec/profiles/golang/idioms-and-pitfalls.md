# Go Idioms and Pitfalls

## Interfaces and Errors

Prefer small interfaces at the consumer that needs the behavior. Returning a concrete type is fine; do not add an interface to every struct or mirror Java class hierarchies. Use normal error returns for expected operational failure rather than panic/recover control flow.

An interface is nil only when both its dynamic type and value are absent. A nil `*MyError` returned as `error` is a non-nil interface. Return literal `nil` on success, and inspect interface contracts rather than adding reflection-based nil checks everywhere. [Go FAQ on nil errors](https://go.dev/doc/faq#nil_error).

```go
func load() error {
    var err *MyError
    // Returning err here would produce a non-nil error interface.
    if err != nil {
        return err
    }
    return nil
}
```

The fragment assumes a project-defined `MyError` implementing `error`; it illustrates interface conversion, not a complete program.

Add context with `fmt.Errorf("load item: %w", err)` when callers should retain access to the cause. Use `errors.Is`/`errors.As` to inspect wrapped errors instead of message matching or direct type assertions. Wrapping exposes an inspectable error chain, so avoid unintentionally making an internal dependency's error part of a public contract. [errors package](https://pkg.go.dev/errors).

## Slices and Loop Variables

| Trigger | Trap | Recommended handling |
| --- | --- | --- |
| Assigning or subslicing a slice | Slice headers can share the same backing array | Copy elements when independent ownership is required; copying is still shallow for reference-containing elements |
| Appending to a shared slice | Whether append reuses storage depends on capacity | Keep the returned slice and do not base correctness on assumed reallocation |
| Retaining a tiny part of a large buffer | The backing array can stay reachable | Copy the retained portion when long-lived retention matters |

See [Go slices: usage and internals](https://go.dev/blog/slices-intro).

With Go 1.22 language semantics, variables declared by a loop are per-iteration; closures do not have the old shared-loop-variable behavior. Pre-existing variables assigned with `=` remain shared. Check the module/file's effective language version before adding or removing legacy `v := v` workarounds. This change does not make a ranged value an alias of the original slice element: use an index when the intention is to update that element. [Go 1.22 language changes](https://go.dev/doc/go1.22#language).

## Context and Goroutines

Pass `context.Context` explicitly, normally as the first parameter. Derive timeouts from the caller and call the returned cancel function. Do not replace an active request context with `context.Background()` merely to bypass cancellation, or use context values as optional function parameters. Cancellation signals intent; goroutines must observe it and exit. [context package](https://pkg.go.dev/context).

For each spawned goroutine, identify its stopping condition and result/error consumer. A blocked send needs an appropriate receiver or cancellation path. Channel closure belongs to the owner that can guarantee no further sends, not an arbitrary receiver. Do not use channels where an ordinary synchronous call is sufficient.

Do not copy a struct containing a used mutex or WaitGroup. Use pointer receivers where such state belongs to a type. For the established `WaitGroup.Add`/`Done` pattern, register work before launching it, then defer `Done` inside the goroutine; placing `Add` inside can race with `Wait`. Do not introduce newer synchronization APIs without checking the target Go version. [sync package](https://pkg.go.dev/sync).

## Standard-Library Resource Traps

After a successful `database/sql` query, arrange `rows.Close()`, handle `Scan` errors, and check `rows.Err()` after iteration. A false `Next()` can mean an iteration failure, not just end-of-data. With `QueryRow`, errors such as `sql.ErrNoRows` are reported by `Scan`; handle them there. [Querying for data](https://go.dev/doc/database/querying).

For repeated resource acquisition in a long-running function, remember that `defer` runs at function return, not at the end of a loop iteration. Use a small function scope or explicit closure when each iteration must release its resource promptly.

## Review Prompts

Check applicable typed-nil returns, inspectable error chains, slice aliases, language-version assumptions, goroutine termination, and deferred cleanup. General retry, API, and transaction design remain in shared specs.
