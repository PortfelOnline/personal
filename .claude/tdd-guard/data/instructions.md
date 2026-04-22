# TDD Guard Custom Instructions

## Batch test writing: allow up to 5 tests at once

When writing NEW test files (not modifying existing ones), allow adding up to **5 tests at once** in a single file creation. This is acceptable when:
- The tests cover a single cohesive unit (one function, one module)
- All tests in the batch are related to the same feature
- No implementation code exists yet (pure TDD — tests first)

Do NOT block a Write operation that creates a test file with 5 or fewer `it(...)` or `test(...)` calls across one or more `describe` blocks, as long as the file contains only test code and no implementation.

## Batch scripts

Batch processing scripts in `scripts/` directory that orchestrate calls to existing tested modules do NOT require their own unit tests before creation. The underlying modules (imageGen, wordpress, llm) are already tested. Allow creating `scripts/batch-*.ts` files without requiring tests first.
