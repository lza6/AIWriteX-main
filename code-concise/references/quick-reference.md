# Quick Reference for Code Review

This document provides quick lookup tables for common code violations and their fixes.

## Severity Matrix

| Category | Critical | High | Medium | Low |
|----------|----------|-------|--------|-----|
| Security | SQL injection, XSS, auth bypass | Weak encryption, insecure config | Missing HTTPS | Deprecated methods |
| Performance | O(n²) in hot path, memory leaks | N+1 queries, large loops | Unnecessary calculations | Minor optimizations |
| Maintainability | No tests, god objects | Duplicated code, long functions | Poor naming, magic numbers | Style issues |
| Reliability | Null pointer, unhandled exceptions | Race conditions, timeouts | Edge cases | Typos |
| Documentation | Critical missing docs | Public API docs missing | Internal docs | Comments |

## Common Patterns

### Naming Violations
- `d`, `x`, `y` → Use descriptive names
- `data`, `temp`, `value` → Be specific
- `flag`, `bool` → Use `isX`, `hasX`, `shouldX`
- `do()`, `process()`, `handle()` → Use action verb + object

### Function Smells
- Lines > 20 → Extract functions
- Params > 3 → Use parameter object
- Returns null → Use exception or Optional
- Changes global state → Make pure function
- Has boolean flag → Split into two functions

### Class Smells
- Lines > 200 → Split classes
- Unrelated methods → Apply SRP
- Mixed concerns → Separate layers
- God object → Break down

## Code Metrics

| Metric | Good | Warning | Bad |
|--------|-------|---------|-----|
| Function length | < 20 | 20-50 | > 50 |
| Cyclomatic complexity | < 10 | 10-20 | > 20 |
| Class length | < 200 | 200-500 | > 500 |
| Nesting depth | < 3 | 3-5 | > 5 |
| Parameter count | < 4 | 4-6 | > 6 |
| Duplicated lines | 0 | 1-10 | > 10 |

## Refactoring Techniques

1. **Extract Method**: Turn code fragment into method
2. **Extract Class**: Split class into smaller classes
3. **Inline Method**: Replace method with body
4. **Replace Temp with Query**: Use method instead of temp variable
5. **Introduce Parameter Object**: Group related parameters
6. **Replace Magic Number with Constant**: Name the number
7. **Decompose Conditional**: Split complex conditionals
8. **Consolidate Conditional**: Merge duplicate conditions
9. **Replace Conditional with Polymorphism**: Use strategy pattern
10. **Introduce Null Object**: Remove null checks

## Quick Fix Templates

### Guard Clause
```javascript
// Before
function process(data) {
  if (data) {
    if (data.isValid()) {
      // main logic
    }
  }
}

// After
function process(data) {
  if (!data || !data.isValid()) {
    return;
  }
  // main logic
}
```

### Early Return
```javascript
// Before
function calculate(data) {
  if (data.type === 'A') {
    return data.value * 2;
  } else if (data.type === 'B') {
    return data.value * 3;
  } else {
    return data.value;
  }
}

// After
function calculate(data) {
  if (data.type === 'A') return data.value * 2;
  if (data.type === 'B') return data.value * 3;
  return data.value;
}
```

### Named Constants
```javascript
// Before
const result = value * 0.0725 + 100;

// After
const TAX_RATE = 0.0725;
const BASE_FEE = 100;
const result = value * TAX_RATE + BASE_FEE;
```
