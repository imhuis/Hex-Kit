# Java Idioms and Pitfalls

## Values and Equality

| Trigger | Trap | Recommended handling |
| --- | --- | --- |
| Comparing strings or boxed values | `==` compares object identity; wrapper caches can make faulty comparisons appear correct | Use value equality, such as `Objects.equals`, when that is the intended contract |
| Unboxing a nullable wrapper | Implicit conversion can throw `NullPointerException` | Resolve absence before arithmetic or boolean conditions; do not choose a default that changes meaning |
| Using an object as a hash key | Mutating fields used by `equals`/`hashCode` can make lookup fail | Keep equality-relevant fields stable while the object is a key |

For `BigDecimal`, construct exact decimal input from a string or an appropriate scaled integer. `new BigDecimal(double)` retains the binary floating-point approximation; `valueOf(double)` cannot restore precision already lost upstream. `equals` includes scale, while `compareTo` compares numeric value. Use the comparison that matches the requirement; do not change key semantics casually. Division may require explicit precision and rounding. [BigDecimal reference](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html).

```java
var amount = new BigDecimal("1.00");
boolean sameValue = amount.compareTo(new BigDecimal("1.0")) == 0;
// amount.equals(new BigDecimal("1.0")) is false because the scales differ.
```

## Records and Collections

Records are shallowly immutable: a final component reference does not freeze its contents. A record containing a list may need a defensive copy when it promises snapshot semantics. Generated equality, hashing, and string output also include components; arrays do not automatically receive content-based equality. Review whether the generated behavior fits the value type. [Record reference](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Record.html).

```java
record Batch(List<String> ids) {
    Batch {
        ids = List.copyOf(ids);
    }
}
```

This intentionally rejects a null list or null elements. `List.copyOf` creates an unmodifiable list, not a deep copy of mutable elements; `List.of` also rejects nulls. Choose a mutable `ArrayList` when mutation is intended. Do not use immutable factories merely for style when their null or mutation contract differs. [List reference](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html).

## Streams and Resource Lifetime

- Stream operations are lazy until a terminal operation, and pipelines can optimize away some operations. Do not put required business effects in `peek` or rely on incidental execution of intermediate callbacks.
- A stream is consumed once; create a new stream rather than reuse it after a terminal operation.
- `Stream.toList()` returns an unmodifiable list and requires Java 16+. When a mutable result is needed, collect explicitly into an `ArrayList`; do not assume every collector returns a particular mutable implementation.
- Close I/O-backed streams such as those returned by `Files.lines` using try-with-resources. Ordinary collection streams do not require resource cleanup.

These behaviors are specified in the [Stream reference](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html). A loop is an equally valid choice when control flow is clearer.

## Interruption and Thread Choice

When catching `InterruptedException`, normally propagate it; if the method cannot, restore the flag with `Thread.currentThread().interrupt()` and leave the interrupted work. The exception clears the interrupt status, so silently catching it loses the cancellation signal. `Thread.interrupted()` also clears the current thread's status; `isInterrupted()` does not. [Thread reference](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html).

Virtual threads are a Java 21+ option, not a required executor migration. They do not increase database connection capacity or make CPU-bound work inherently faster. Check runtime-specific behavior before carrying performance assumptions across JDK versions. The same [Thread reference](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html) describes their intended use.

## Review Prompts

Check only relevant triggers: identity versus value equality, decimal scale, shallow mutability, stream ownership, and interruption. Broader concurrency policy and resource ownership remain in shared specs.
