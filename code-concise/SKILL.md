---
name: code-concise
description: This skill provides automated code review and optimization guidance based on Robert C. Martin's "Clean Code" principles. Apply this skill when reviewing code, identifying issues, detecting optimization opportunities, or providing specific refactoring recommendations. Uses progressive disclosure to minimize token consumption while ensuring comprehensive analysis.
---

# Clean Code Review & Optimization Skill

This skill provides **automated code review and intelligent optimization recommendations** based on "Clean Code" principles. It focuses on **detecting issues, identifying optimization opportunities, and providing actionable refactoring suggestions**.

## When to Use This Skill

Apply this skill when:
- **Reviewing code** and need automatic issue detection
- **Analyzing code quality** and identifying potential problems
- **Providing code improvement suggestions** with specific recommendations
- **Performing code audits** with actionable feedback
- **Optimizing existing code** with intelligent refactoring recommendations
- **Mentoring developers** with concrete code examples

## Progressive Disclosure Approach

To minimize token consumption while ensuring comprehensive analysis, this skill uses a **layered, progressive disclosure strategy**:

### Phase 1: Quick Scan (Initial Analysis)
- Scan code for obvious violations
- Identify top 3-5 critical issues
- Provide brief summary with severity indicators
- Output: High-level overview with critical issues highlighted

### Phase 2: Detailed Review (On Request)
- Expand on specific issues from Phase 1
- Provide code examples (before/after)
- Explain why each issue matters
- Suggest specific fixes
- Output: Detailed analysis with actionable recommendations

### Phase 3: Optimization Suggestions (On Request)
- Identify performance improvements
- Suggest architectural refactoring
- Recommend design pattern applications
- Provide complete refactoring code
- Output: Comprehensive optimization plan

**Usage Pattern:**
```
User: Review this code
→ Phase 1 output (quick scan)

User: Tell me more about issue #2
→ Phase 2 output (detailed analysis of issue #2)

User: Show me how to fix issues #1, #3, and #5
→ Phase 3 output (complete refactoring suggestions)
```

## Core Functions

### 1. Automatic Issue Detection
Automatically identify code violations across multiple categories:
- Naming conventions
- Function complexity
- Code duplication
- Error handling
- Code structure
- Test coverage

### 2. Intelligent Optimization Recognition
Detect opportunities for improvement:
- Performance bottlenecks
- Design pattern applications
- Code simplification opportunities
- Maintainability improvements
- Security concerns

### 3. Actionable Recommendations
Provide specific, implementable suggestions:
- Code refactoring examples (before → after)
- Priority rankings (Critical, High, Medium, Low)
- Effort estimates (Quick fix, Moderate, Major)
- Risk assessments for changes

---

## Issue Detection Rules

### Priority Levels

**CRITICAL** - Must fix immediately:
- Security vulnerabilities
- Data loss risks
- Performance disasters
- Logic errors
- Null pointer exceptions

**HIGH** - Should fix soon:
- Code duplication > 10 lines
- Functions > 50 lines
- Cyclomatic complexity > 10
- Magic numbers
- Missing error handling

**MEDIUM** - Should fix eventually:
- Non-meaningful names
- Inconsistent naming
- Unclear intent
- Missing documentation
- Overly complex logic

**LOW** - Nice to have:
- Formatting issues
- Minor style violations
- Minor naming improvements

---

## Category 1: Naming Issues

### 1.1 Non-Intention-Revealing Names
**Pattern:** Variables/functions with generic or unclear names

**Detection:**
- Variables: `d`, `temp`, `data`, `value`, `var1`, `x`, `y`
- Functions: `do()`, `run()`, `process()`, `handle()`

**Fix:** Use descriptive names

**Before:**
```javascript
function process(d, a) {
  return d * a;
}
```

**After:**
```javascript
function calculateTotalCost(days, dailyRate) {
  return days * dailyRate;
}
```

### 1.2 Misleading Names
**Pattern:** Names that don't match their purpose

**Detection:**
- `list` when it's not a list type
- `get()` when it modifies data
- `isX()` when it returns non-boolean

**Fix:** Align names with actual behavior

### 1.3 Noise Words
**Pattern:** Unnecessary prefixes/suffixes

**Detection:**
- `nameString`, `dataMap`, `valueInt`
- `theUser`, `aCustomer`
- `variable` in variable name

**Fix:** Remove noise

**Before:**
```javascript
const userNameString = "John";
const userDataMap = { age: 30 };
```

**After:**
```javascript
const userName = "John";
const userData = { age: 30 };
```

---

## Category 2: Function Issues

### 2.1 Too Long
**Pattern:** Functions exceeding 20-30 lines

**Detection:**
- Line count > 20 (WARNING)
- Line count > 50 (HIGH)

**Fix:** Extract smaller functions

**Before:**
```javascript
function processOrder(order) {
  // validate
  if (!order.customerId) return;
  if (!order.items || order.items.length === 0) return;
  // calculate
  let total = 0;
  for (let item of order.items) {
    if (!item.price) continue;
    total += item.price * item.quantity;
  }
  // apply discount
  if (total > 1000) total *= 0.9;
  // save
  const record = {
    orderId: order.id,
    total: total,
    date: new Date()
  };
  database.save(record);
  // notify
  email.send(order.customerEmail, "Order processed");
}
```

**After:**
```javascript
function processOrder(order) {
  validateOrder(order);
  const total = calculateOrderTotal(order);
  const discountedTotal = applyDiscount(total);
  const record = createOrderRecord(order, discountedTotal);
  saveOrder(record);
  notifyCustomer(order);
}
```

### 2.2 Too Many Parameters
**Pattern:** Functions with 4+ parameters

**Detection:**
- Parameter count > 3 (WARNING)
- Parameter count > 5 (HIGH)

**Fix:** Use parameter objects

**Before:**
```javascript
function createUser(firstName, lastName, email, age, address, city, zip) {
  // ...
}
```

**After:**
```javascript
function createUser(userDetails) {
  // userDetails = { firstName, lastName, email, age, address, city, zip }
}
```

### 2.3 Flag Arguments
**Pattern:** Boolean parameters that change behavior

**Detection:**
- Boolean parameter in non-predicate function

**Fix:** Create separate functions

**Before:**
```javascript
function render(isPreview) {
  if (isPreview) {
    // preview logic
  } else {
    // production logic
  }
}
```

**After:**
```javascript
function renderPreview() { /* ... */ }
function renderForProduction() { /* ... */ }
```

### 2.4 Side Effects
**Pattern:** Functions that both return values and modify state

**Detection:**
- Return value present + modifies global/static variables
- Return value present + writes to database/file

**Fix:** Separate concerns

**Before:**
```javascript
function checkPassword(username, password) {
  this.session.initialize();  // side effect
  return this.userRepository.authenticate(username, password);
}
```

**After:**
```javascript
function checkPassword(username, password) {
  return this.userRepository.authenticate(username, password);
}

function initializeSession(user) {
  this.session.initialize(user);
}
```

---

## Category 3: Code Duplication

### 3.1 Duplicate Code Blocks
**Pattern:** Same code appearing 3+ times

**Detection:**
- Identify code blocks with >10 identical lines
- Same logic with different values

**Fix:** Extract to function

**Before:**
```javascript
function calculateTax(state, amount) {
  if (state === 'CA') return amount * 0.0725;
  if (state === 'NY') return amount * 0.08875;
  if (state === 'TX') return amount * 0.0625;
}
```

**After:**
```javascript
function calculateTax(state, amount) {
  const taxRates = {
    'CA': 0.0725,
    'NY': 0.08875,
    'TX': 0.0625
  };
  return amount * (taxRates[state] || 0);
}
```

### 3.2 Duplicate Logic
**Pattern:** Similar logic with slight variations

**Fix:** Use parameterization

---

## Category 4: Error Handling

### 4.1 Ignoring Errors
**Pattern:** Empty catch blocks or error suppression

**Detection:**
- `catch(e) {}`
- `try { ... } catch(e) { return null; }`

**Fix:** Proper error handling

**Before:**
```javascript
try {
  saveData(data);
} catch (e) {
  // ignore
}
```

**After:**
```javascript
try {
  saveData(data);
} catch (e) {
  logger.error("Failed to save data", e);
  throw new DataPersistenceError("Could not save data", e);
}
```

### 4.2 Returning Null
**Pattern:** Functions that return null to indicate absence

**Detection:**
- Return statement with null in non-optional context

**Fix:** Use Optional/Maybe pattern or throw exception

**Before:**
```javascript
function getUser(id) {
  const user = database.find(id);
  return user || null;  // forces null check by caller
}
```

**After:**
```javascript
function getUser(id) {
  const user = database.find(id);
  if (!user) {
    throw new UserNotFoundError(id);
  }
  return user;
}
```

### 4.3 Magic Error Codes
**Pattern:** Returning numeric error codes

**Detection:**
- Return of negative numbers or error constants

**Fix:** Use exceptions

**Before:**
```javascript
function connectToDatabase(config) {
  if (!config.host) return -1;
  if (!config.port) return -2;
  // ... connect logic
  return 0;  // success
}
```

**After:**
```javascript
function connectToDatabase(config) {
  if (!config.host) {
    throw new ConfigurationError("Host is required");
  }
  if (!config.port) {
    throw new ConfigurationError("Port is required");
  }
  // ... connect logic
}
```

---

## Category 5: Code Structure

### 5.1 Deep Nesting
**Pattern:** More than 3 levels of indentation

**Detection:**
- Nesting level > 3

**Fix:** Use guard clauses and early returns

**Before:**
```javascript
function processOrder(order) {
  if (order) {
    if (order.items) {
      if (order.items.length > 0) {
        for (let item of order.items) {
          if (item.price) {
            // process item
          }
        }
      }
    }
  }
}
```

**After:**
```javascript
function processOrder(order) {
  if (!order || !order.items || order.items.length === 0) {
    return;
  }

  for (let item of order.items) {
    processItem(item);
  }
}

function processItem(item) {
  if (item.price) {
    // process item
  }
}
```

### 5.2 God Functions
**Pattern:** Functions that do too many things

**Detection:**
- Function calls > 5 different types of operations
- Mixes database, UI, business logic, logging

**Fix:** Separate concerns

### 5.3 Magic Numbers
**Pattern:** Numeric literals without explanation

**Detection:**
- Numbers not 0, 1, -1, 2
- Numbers not in named constants

**Fix:** Use named constants

**Before:**
```javascript
if (user.age >= 65 && user.yearsEmployed >= 10) {
  pension = salary * 0.8;
}
```

**After:**
```javascript
const RETIREMENT_AGE = 65;
const FULL_PENSION_YEARS = 10;
const FULL_PENSION_RATE = 0.8;

if (user.age >= RETIREMENT_AGE && user.yearsEmployed >= FULL_PENSION_YEARS) {
  pension = salary * FULL_PENSION_RATE;
}
```

---

## Category 6: Comments

### 6.1 Redundant Comments
**Pattern:** Comments that repeat code

**Detection:**
- Comment that restates code in natural language

**Fix:** Remove comment or improve code

**Before:**
```javascript
// Increment the counter
count++;
// Return true if the user is active
return user.isActive();
```

**After:**
```javascript
count++;
return user.isActive();
```

### 6.2 Outdated Comments
**Pattern:** Comments that don't match current code

**Detection:**
- Comment describes different behavior than code

**Fix:** Update or remove comment

### 6.3 Commented-Out Code
**Pattern:** Code blocks that are commented out

**Detection:**
- Large blocks of commented code (>5 lines)

**Fix:** Delete (version control remembers it)

---

## Category 7: Class Design

### 7.1 Large Classes
**Pattern:** Classes > 200 lines

**Detection:**
- Line count > 200 (WARNING)
- Line count > 500 (HIGH)

**Fix:** Split into multiple classes

### 7.2 Too Many Responsibilities
**Pattern:** Class methods don't share common theme

**Detection:**
- Methods unrelated by noun
- Mixes database, UI, business logic

**Fix:** Apply Single Responsibility Principle

**Before:**
```javascript
class Employee {
  calculatePay() { ... }
  saveToDatabase() { ... }
  sendEmail() { ... }
  generateReport() { ... }
}
```

**After:**
```javascript
class Employee {
  calculatePay() { ... }
}

class EmployeeRepository {
  save(employee) { ... }
}

class EmailService {
  send(employee, message) { ... }
}

class ReportGenerator {
  generate(employee) { ... }
}
```

### 7.3 Violating Law of Demeter
**Pattern:** Chaining method calls across objects

**Detection:**
- `a.getB().getC().doSomething()`

**Fix:** Encapsulate intermediate access

**Before:**
```javascript
const capital = customer.getAddress().getCity().getState().getCapital();
```

**After:**
```javascript
const capital = customer.getCapital();
```

---

## Optimization Recommendations

### Performance Optimizations

1. **Cache expensive operations**
```javascript
// Bad
for (let i = 0; i < items.length; i++) {
  const expensive = calculateExpensive(items[i].id);
  // use expensive
}

// Good
const cache = new Map();
function getCachedExpensive(id) {
  if (!cache.has(id)) {
    cache.set(id, calculateExpensive(id));
  }
  return cache.get(id);
}
```

2. **Use appropriate data structures**
```javascript
// Bad: Linear search in array
const found = users.find(u => u.id === targetId);

// Good: Constant-time lookup
const userMap = new Map(users.map(u => [u.id, u]));
const found = userMap.get(targetId);
```

### Maintainability Improvements

1. **Extract repeated logic**
2. **Use design patterns appropriately**
3. **Reduce coupling between modules**
4. **Increase cohesion within modules**

---

## Interactive Review Workflow

When reviewing code, follow this pattern:

### Step 1: Initial Assessment (Phase 1)
```
📊 CODE REVIEW SUMMARY

File: example.js
Lines: 150
Severity Distribution: 2 Critical, 3 High, 4 Medium, 2 Low

🔴 CRITICAL ISSUES (2):
1. [Line 45] Potential null pointer exception
2. [Line 78] SQL injection vulnerability

🟡 HIGH PRIORITY (3):
3. [Line 23] Function too long (67 lines)
4. [Line 56] Duplicate code block (15 lines)
5. [Line 102] Magic number: 0.0725

Request: "Tell me more about issue #1-3" for details
```

### Step 2: Detailed Analysis (Phase 2)
```
📋 ISSUE #1: Null Pointer Exception
Location: example.js:45
Severity: 🔴 Critical

Problem:
The function `getUserData()` may return null, but the code
assumes it always returns an object.

Code:
```javascript
const user = getUserData(userId);
const name = user.name;  // ⚠️ Potential null pointer
```

Impact:
- Runtime error when user doesn't exist
- Application crash
- Poor user experience

Recommended Fix:
```javascript
const user = getUserData(userId);
if (!user) {
  throw new UserNotFoundError(userId);
}
const name = user.name;
```

Effort: Quick fix (2 minutes)
Risk: Low
```

### Step 3: Complete Refactoring (Phase 3)
```
🔧 REFACTORING PLAN

Issue #3: Function Too Long

Current Implementation:
[Show current code]

Refactored Solution:
```javascript
function processOrder(order) {
  validateOrder(order);
  const pricing = calculatePricing(order);
  const discounted = applyDiscount(pricing);
  const record = saveOrderRecord(order, discounted);
  notifyCustomer(order, record);
  return record;
}

function validateOrder(order) { /* ... */ }
function calculatePricing(order) { /* ... */ }
function applyDiscount(pricing) { /* ... */ }
function saveOrderRecord(order, pricing) { /* ... */ }
function notifyCustomer(order, record) { /* ... */ }
```

Benefits:
✓ Each function has single responsibility
✓ Easier to test
✓ Easier to maintain
✓ Reduced cognitive complexity
✓ Better code reusability

Estimated Effort: 30 minutes
Risk: Low (same behavior, better structure)
```

---

## Quick Reference: Common Violations

| Violation | Pattern | Priority | Quick Fix |
|-----------|---------|----------|-----------|
| Generic variable name | `d`, `temp`, `data` | Medium | Use descriptive name |
| Long function | >20 lines | High | Extract smaller functions |
| Many parameters | >3 params | High | Use parameter object |
| Deep nesting | >3 levels | Medium | Use guard clauses |
| Duplicate code | >10 lines repeated | High | Extract to function |
| Magic number | Unexplained number | Medium | Use named constant |
| Null return | Returns null | Critical | Use exception/Optional |
| Empty catch | `catch(e) {}` | High | Handle properly |
| Large class | >200 lines | Medium | Split classes |
| God object | Many responsibilities | High | Apply SRP |

---

## Implementation Tips

### For Code Reviewers
1. **Start with Phase 1** - Provide quick overview
2. **Wait for user request** before diving deep
3. **Prioritize by severity** - Focus on critical issues first
4. **Provide context** - Explain why each issue matters
5. **Be constructive** - Offer actionable solutions

### For Users
1. **Review Phase 1 summary** to understand overall code health
2. **Request details** only for issues you want to address
3. **Ask for refactoring** when ready to implement fixes
4. **Prioritize** based on severity and effort
5. **Test thoroughly** after applying changes

### Optimization Workflow
```
1. Quick Scan → Identify top issues
2. Deep Dive → Understand specific problems
3. Refactor → Apply optimized solutions
4. Validate → Test changes
5. Iterate → Review again if needed
```

---

## Token-Efficient Response Patterns

### Pattern 1: Quick Review
```
🔴 CRITICAL: [issue] at line [X]
🟡 HIGH: [issue] at line [X]
🟢 MEDIUM: [issue] at line [X]
Ask for details on issues #[1-N]
```

### Pattern 2: Single Issue Detail
```
❌ ISSUE #[N]: [Name]
📍 Line [X]
🔴 Priority
⚠️ Impact: [1-2 sentences]
✅ Fix: [code snippet]
⏱️ Effort: [time]
```

### Pattern 3: Refactoring Block
```
🔧 Refactoring for issue #[N]:
Before: [brief description]
After: [code block]
Benefits: ✓ ✓ ✓
```

---

## Best Practices

### Do ✅
- Prioritize by severity
- Provide actionable fixes
- Show before/after code
- Estimate effort and risk
- Be specific about line numbers
- Focus on the most impactful issues

### Don't ❌
- Overwhelm with too many issues at once
- Provide theoretical advice without code examples
- Ignore context and project constraints
- Suggest massive rewrites
- Be pedantic about minor style issues
- Repeat information unnecessarily

---

## Additional Resources

### References Directory
Place supplementary materials in `references/`:
- Language-specific style guides
- Framework-specific best practices
- Pattern libraries
- Example code before/after

### Notes
- This skill is designed for **interactive code review**
- **Progressive disclosure** reduces token usage
- Focus on **actionable, high-impact improvements**
- Balance between **comprehensive analysis** and **efficiency**
