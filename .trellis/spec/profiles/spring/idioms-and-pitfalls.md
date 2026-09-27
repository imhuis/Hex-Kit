# Spring Idioms and Pitfalls

## Managed Beans and Injection

Prefer constructor injection for required collaborators; it exposes required dependencies without container lookup from business methods. Resolve cycles by checking responsibilities rather than automatically adding lazy injection. These are local defaults, not an instruction to rewrite unrelated beans. Spring documents the available mechanisms in [Dependency Injection](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html).

An object constructed with `new` is not automatically a managed, advised bean. Where transaction or async behavior depends on Spring, use the managed instance and ensure the relevant infrastructure is enabled. Multiple candidates or transaction managers require deliberate selection rather than relying on an accidental name match.

## Proxy-Based Advice

| Trigger | Failure mode | Handling |
| --- | --- | --- |
| A bean calls its own annotated method | In proxy mode, self-invocation bypasses advice | Put the advised operation behind a genuinely separate collaborator where appropriate, or use an explicit supported mechanism such as TransactionTemplate |
| Class-based proxy intercepts a final/private method | Such methods cannot be overridden for advice | Inspect method visibility, finality, and actual proxy strategy |
| A caller assumes a concrete proxy type | Interface-based and class-based proxies have different shapes | Depend on the intended contract and verify configured proxy mode |

Do not solve every interception problem with self-injection or `AopContext.currentProxy()`. The important question is which call actually crosses the proxy. These constraints apply to proxy mode; AspectJ weaving has different semantics. [Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html).

## Declarative Transactions

- `@Transactional` does not itself prove that a transaction starts: confirm bean management, transaction configuration, and the intercepted call.
- With the usual default rollback policy, unchecked exceptions and `Error` trigger rollback; checked exceptions do not. Inspect explicit rules and global configuration before depending on that default. Spring 6.2+ can configure an all-exceptions default.
- If a participating operation marks a transaction rollback-only, catching its exception does not restore commitability. Inspect the real completion outcome instead of returning success from the outer method.
- Treat `readOnly = true` as a transaction hint, not an authorization control or a portable guarantee that writes are rejected.

For exception policy, consult [Rolling Back a Declarative Transaction](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html). For interception and annotation attributes, consult [Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html). Match these references to the deployed framework version.

This section describes imperative transactions. Do not assume a new thread inherits the caller's transaction; reactive transaction context is a separate model. Shared specs own decisions about which writes must be atomic.

## Async Execution and Scheduling

In default proxy mode, a local call to an `@Async` method does not become asynchronous. Verify async support is enabled and identify the selected executor. A returned Future/CompletableFuture needs an error observer; exceptions from a void async method require an appropriate `AsyncUncaughtExceptionHandler` rather than an assumption that the caller receives them. [Task Execution and Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html).

Do not assume transaction, request, security, or logging context follows an executor switch automatically. Use the configured context propagation facilities where needed, and keep transaction boundaries explicit.

## MVC Validation

For Spring MVC, `@Valid` cascades validation; it is not itself a non-null constraint. Use the actual parameter constraints and nesting rules required by the input. Binding/object validation and method validation can produce different exceptions, including `MethodArgumentNotValidException` and `HandlerMethodValidationException`; do not handle just one and assume every invalid input is covered.

Spring MVC 6.1+ provides built-in method validation. A controller-level `@Validated` can select AOP-based method validation instead; when adopting the built-in mechanism, follow the version-specific migration guidance rather than stacking both approaches blindly. [MVC Validation](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-validation.html).

These exception details do not apply unchanged to WebFlux. Shared API specs still define public status codes and error bodies.

## Review Prompts

Check the managed instance, intercepted call, rollback configuration, executor, and validation mechanism involved in the change. Avoid introducing new wrapper layers solely to make an annotation appear effective.
