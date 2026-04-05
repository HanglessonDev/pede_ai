---
name: extreme-programming
description: "Use when building software following XP principles, managing iterative development, or optimizing for sustainable delivery with high quality."
---

# Extreme Programming (XP)

Adaptation of XP principles for AI-assisted development workflow.

## Core Values

- **Communication** — Talk through decisions, use subagents for review
- **Simplicity** — YAGNI, build simplest thing that works
- **Feedback** — Test first, verify before claiming done
- **Courage** — Refactor boldly, delete dead code
- **Respect** — Leave code better than found

## When to Use

- Starting new features or tasks
- Making design decisions
- Reviewing code changes
- Refactoring or improving existing code

## The Practices

### 1. Pair Programming (Code Review em Tempo Real)

**Use subagent for review during implementation:**

```bash
# After each significant change, dispatch code-reviewer
Use superpowers:requesting-code-review
```

**Benefits:**
- Catch bugs early
- Share knowledge across codebase
- Two perspectives on decisions

**When to use:**
- After each task in implementing-plans workflow
- Before merging significant changes
- When stuck (fresh perspective)

### 2. TDD — Test-Driven Development

Already covered by `test-driven-development` skill.

**The cycle:**
1. Write failing test (RED)
2. Write minimal code to pass (GREEN)
3. Refactor (REFACTOR)

### 3. Continuous Integration

**Commit frequently, keep main passing:**

- Small, atomic commits
- Tests pass before commit
- Never break the build

**In practice:**
```bash
# Run tests before any claim of "done"
Use superpowers:verification-before-completion
```

### 4. Simple Design

**Three rules:**
1. Runs all tests
2. No duplicate code
3. Expresses intent

**YAGNI in action:**

```
❌ "We might need caching later" → build it later
✅ "Current requirement: show data" → show data
```

**Kaizen** — small improvements continuously:
- Fix small issues as encountered
- Refactor within scope
- Leave code better than found

### 5. Collective Ownership

**Anyone can improve any code:**

- No "this is my file"
- Fix issues where you see them
- Share knowledge across tasks

**In AI context:**
- Don't assume "other agent will fix"
- Fix bugs in any file
- Update outdated docs anywhere

### 6. Sustainable Pace

**Avoid over-engineering:**

- Don't build frameworks before using them
- Wait for 3+ similar cases before abstracting
- "Good enough" beats "perfect"

**Signs of violation:**
- Complexity for "future needs"
- Premature optimization
- Building generic solutions for specific problems

## XP in Your Workflow

| XP Practice | Your Workflow Integration |
|-------------|--------------------------|
| Pair Programming | Use `requesting-code-review` after each task |
| TDD | Use `test-driven-development` for features |
| CI | Run `verification-before-completion` before claim done |
| Simple Design | Use `kaizen` for incremental improvements |
| Collective Ownership | Fix issues anywhere, not just "your" files |
| Sustainable Pace | Use `writing-plans` to break into small tasks |

## Red Flags

- ❌ "I'll refactor later" — never happens
- ❌ Building for "might need" — YAGNI
- ❌ Big bang rewrites — incremental only
- ❌ Skipping tests for "speed" — technical debt
- ❌ Owning "your" code only — collective ownership

### 7. Bugs: Achei = Corrige

**Não existe "bug pré-existente":**

- Se você encontra, você corrige
- Bug = teste ausente
- Collective ownership: qualquer um corrige qualquer bug

**Fluxo:**
1. Escreva teste que reproduz o bug
2. Execute → teste falha
3. Corrija código → teste passa

**Nunca use como desculpa:**
- ❌ "é um bug pré-existente"
- ❌ "já era assim antes"
- ❌ "outro agente vai resolver"

## Related Skills

- Use superpowers:test-driven-development
- Use superpowers:requesting-code-review
- Use superpowers:verification-before-completion
- Use superpowers:kaizen