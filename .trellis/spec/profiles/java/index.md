# Java Profile

Applies to Java source regardless of framework. Read the relevant shared layer spec first; add the [Spring profile](../spring/index.md) only when Spring is actually used. This is a reusable baseline, not a claim that this repository contains a Java application.

## Topic

[Java Idioms and Pitfalls](./idioms-and-pitfalls.md): value equality, decimal arithmetic, records, collections, streams, resources, and interruption.

## Pre-Development Checklist

- Confirm the compiler release/toolchain and deployment JDK; the developer's installed JDK alone is not the compatibility target.
- Check whether the changed types rely on identity, mutable collections, generated record methods, or framework serialization/proxy behavior.
- Read only the relevant sections. Examples using records require Java 16 or later; this profile does not require a version upgrade or preview features.

## Quality Check

Verify applicable value, mutation, resource, and interruption semantics using existing project checks. Do not add a new abstraction or test suite merely because a topic appears here.

All documentation must be written in English. Return to [Technology Profiles](../index.md).
