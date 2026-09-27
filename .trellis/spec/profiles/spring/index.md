# Spring Profile

Applies to code using Spring Framework or Spring Boot. Compose it with the [Java profile](../java/index.md) for Java modules and the relevant shared layer specs. This profile does not prescribe Spring Boot, an ORM, or a web stack where one is not already used.

## Topic

[Spring Idioms and Pitfalls](./idioms-and-pitfalls.md): managed beans, proxy interception, transaction rollback, asynchronous execution, and MVC validation.

## Pre-Development Checklist

- Confirm Spring Framework/Boot versions, enabled infrastructure, and whether the application uses MVC or WebFlux.
- For annotated behavior, identify the managed bean, actual caller, proxy mode, and relevant executor or transaction manager.
- Read only applicable sections. Imperative thread-bound transactions and MVC validation must not be applied unchanged to reactive code.

## Quality Check

For changed proxy-driven behavior, use relevant existing tests that obtain the bean through the application context. A test using `new Service(...)` can verify ordinary logic but cannot prove Spring advice runs. Check the actual failure or rollback outcome, not just annotation presence. No new test framework is required.

All documentation must be written in English. Return to [Technology Profiles](../index.md).
