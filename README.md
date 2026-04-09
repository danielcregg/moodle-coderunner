<h1 align="center">CodeRunner Skill</h1>

<p align="center">
  <strong>AI skill for generating validated Moodle CodeRunner programming questions</strong>
</p>

<p align="center">
  <a href="https://github.com/danielcregg/moodle-coderunner/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-4.0.0-green.svg" alt="Version 4.0.0">
  <img src="https://img.shields.io/badge/Questions%20Validated-300-brightgreen.svg" alt="300 Questions Validated">
  <img src="https://img.shields.io/badge/Pass%20Rate-100%25-brightgreen.svg" alt="100% Pass Rate">
  <img src="https://img.shields.io/badge/Claude%20Code-blueviolet.svg" alt="Claude Code">
  <img src="https://img.shields.io/badge/ChatGPT%20GPT-Compatible-blue.svg" alt="ChatGPT Compatible">
  <img src="https://img.shields.io/badge/Moodle-4.x%20Compatible-orange.svg" alt="Moodle 4.x">
  <img src="https://img.shields.io/badge/CodeRunner-4.x-red.svg" alt="CodeRunner 4.x">
</p>

<p align="center">
  Generate auto-graded programming questions for Moodle's <a href="https://coderunner.org.nz/">CodeRunner</a> plugin. Every question is compiled and tested on a <a href="https://github.com/trampgeek/jobe">Jobe</a> server before delivery. Supports Java, Python, C, C++, and Node.js across 10 question types.
</p>

<p align="center">
  <strong>Battle-tested:</strong> 300 questions generated and validated with a 100% pass rate.
</p>

---

## Quick Start

```bash
# Claude Code CLI
mkdir -p ~/.claude/skills
git clone https://github.com/danielcregg/moodle-coderunner.git ~/.claude/skills/moodle-coderunner

# Use it
/moodle-coderunner
Generate 5 Java CodeRunner questions on arrays for first-year students
```

For **Claude Desktop**: Settings > Skills > Upload `SKILL.md`.

---

## What It Does

Generates complete, import-ready Moodle XML with:

| Component | Purpose |
|-----------|---------|
| Question text | Clear instructions with examples and penalty regime |
| Answer preload | Compilable skeleton code for students |
| Model solution | Complete correct answer (hidden) |
| Visible test(s) | Students see expected input/output |
| Hidden test(s) | Prevents hard-coding, tests edge cases |
| General feedback | Explanation shown after quiz closes |
| **Jobe validation** | Every question compiled and tested before delivery |

---

## What Makes v4.0 Different

Previous versions generated questions but couldn't verify they actually worked. v4.0 introduces:

1. **Jobe server validation** — every question is compiled and executed against test cases before delivery
2. **23 battle-tested rules** — derived from analysing 370+ questions across 7 AI models
3. **Self-healing loop** — if validation fails, the AI fixes the question and retries
4. **10 question types** — function, class, method, and program types for all languages
5. **Advanced features** — partial credit, precheck, give-up, conditional display, time/memory limits

### Model Comparison (why rules matter)

We tested the same 12 questions across 7 models. The skill rules are the difference:

| Model | Size | Pass Rate |
|-------|------|-----------|
| **Claude (with skill)** | Cloud | **100%** |
| **GPT-5.4 (with rules)** | Cloud | **100%** |
| z.ai GLM-5.1 | Cloud | 17% |
| Gemma 4 E4B | 4B | 16% |
| Gemma 4 26B | 26B MoE | 0% |
| DeepSeek Coder V2 | 16B MoE | 0% |
| Qwen 3 8B | 8B | 0% |

Open-source models (7-26B) cannot reliably generate CodeRunner XML even with templates. The rules are necessary but only effective with frontier models.

---

## Supported Languages & Types

| Language | Types | Reliability |
|----------|-------|-------------|
| **Java** | `java_class`, `java_method`, `java_program` | HIGH / HIGH / LOW |
| **Python** | `python3`, `python3_w_input` | HIGH / MEDIUM |
| **C** | `c_function`, `c_program` | HIGH / MEDIUM |
| **C++** | `cpp_function`, `cpp_program` | MEDIUM / MEDIUM |
| **Node.js** | `nodejs` | HIGH |

Reliability reflects first-attempt pass rates. LOW types (java_program) have known EOF pitfalls but the skill's rules handle them.

---

## Key Rules (from 300 validated questions)

The skill contains 23 rules. Here are the most critical:

| # | Rule | Prevents |
|---|------|----------|
| 1 | Java Scanner: always `hasNext()` before reads | NoSuchElementException (30% of Java failures) |
| 2 | Python stdin: use `sys.stdin.read()` not `input()` | EOFError on empty input |
| 3 | C/C++: Jobe uses `-Werror` (all warnings fatal) | Compilation failures |
| 4 | C++: `size_t` not `int` for `.size()` loops | `-Werror=sign-compare` |
| 5 | C/C++: `#include` in `<answer>`, not just test code | `-Werror=implicit-function-declaration` |
| 6 | Array printing: `if(i) printf(" ")` pattern | Trailing space output mismatch |
| 7 | No exact floating-point comparisons | Rounding differences |
| 8 | Trace every test case mentally | Wrong expected output (20% of failures) |

See `SKILL.md` Section 2 for the complete per-language rule tables.

---

## Advanced Features

The skill supports all major CodeRunner options:

| Feature | XML Tag | Effect |
|---------|---------|--------|
| Partial credit | `<allornothing>0</allornothing>` | Weighted marks per test |
| Precheck | `<precheck>1</precheck>` | Students can test before submitting |
| Give up | `<giveupallowed>1</giveupallowed>` | Students can reveal answer |
| Time limit | `<cputimelimitsecs>2</cputimelimitsecs>` | Enforce CPU time limit |
| Memory limit | `<memlimitmb>64</memlimitmb>` | Enforce memory limit |
| Progressive tests | `hiderestiffail="1"` | Hide remaining tests on failure |
| Conditional display | `HIDE_IF_FAIL`, `HIDE_IF_SUCCEED` | Show/hide based on result |

---

## Validation Script

The repo includes `validate_coderunner.py` — a standalone Python script (stdlib only) that validates CodeRunner XML against a Jobe server:

```bash
python3 validate_coderunner.py questions.xml --jobe-url http://your-jobe-server:4000
```

- Parses Moodle XML, constructs full source per question type
- Submits to Jobe for compilation and execution
- Compares actual output against expected
- Reports PASS/FAIL with error details (COMPILE_ERROR, WRONG_OUTPUT, RUNTIME_ERROR)
- Supports all 10 question types
- No pip dependencies required

---

## Examples

### Java OOP questions
```
/moodle-coderunner
Create 5 Java java_class questions on encapsulation (getters, setters, constructors)
for first-year students. All-or-nothing grading.
```

### Python function questions
```
/moodle-coderunner
Generate 8 Python CodeRunner questions on list manipulation and string methods.
Mix of easy, medium, and hard difficulty. Validate on Jobe.
```

### Advanced features
```
/moodle-coderunner
Create 3 C function questions with partial credit (weighted marks),
precheck enabled, and a 2-second CPU time limit. Include edge case tests.
```

---

## Installation

### Claude Code (CLI)

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/danielcregg/moodle-coderunner.git ~/.claude/skills/moodle-coderunner
```

### Claude Desktop

1. Download `SKILL.md` from this repo
2. Open Claude Desktop > Settings > Skills > Upload skill
3. Drag and drop `SKILL.md`

### ChatGPT Custom GPT

See the [ChatGPT setup guide](https://github.com/danielcregg/moodle-coderunner-ai/tree/main/chatgpt) in the companion repo for instructions on creating a GPT with Jobe validation via Actions.

---

## File Structure

```
moodle-coderunner/
  SKILL.md                  # The AI skill (v4.0 — 23 rules, 10 sections)
  validate_coderunner.py    # Standalone Jobe validation script
  README.md                 # This file
  LICENSE                   # MIT
```

---

## Compatibility

| Platform | Supported | How |
|----------|:---------:|-----|
| Claude Code (CLI) | Yes | Install as skill, invoke with `/moodle-coderunner` |
| Claude Desktop | Yes | Upload `SKILL.md` via Settings > Skills |
| ChatGPT (Custom GPT) | Yes | Use `SKILL.md` as GPT instructions + Jobe Action |
| Moodle 4.x + CodeRunner 4.x | Yes | Import generated XML via Question bank |
| Moodle 3.x + CodeRunner 3.x | Yes | Import generated XML via Question bank |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **4.0.0** | 2026-04-07 | Complete rewrite. Jobe validation loop. 23 rules from 300+ validated questions. Per-language rule tables. Model comparison data. Validation script. Advanced features support (partial credit, precheck, give-up, time/memory limits). Optimised for AI consumption (341 lines, tables over prose). |
| 3.x | 2026-04-07 | Internal iterations. Stress-tested across 10 question types. Discovered stdin newline, -Werror, trailing space, and #include placement rules. |
| 2.0.0 | 2026-03-24 | Added Python support, full CodeRunner type list, review document workflow. Published to GitHub. |
| 1.0 | 2025-11-09 | Initial skill for Java CodeRunner questions. Critical `<name>` tag fix. |

---

## Related Projects

| Project | Purpose |
|---------|---------|
| [coderunner-question-forge](https://github.com/danielcregg/coderunner-question-forge) | Web app for generating and validating CodeRunner question banks |
| [moodle-coderunner-ai](https://github.com/danielcregg/moodle-coderunner-ai) | AI tutor that gives feedback on student CodeRunner submissions |
| [moodle-mcq](https://github.com/danielcregg/moodle-mcq) | Claude skill for generating Moodle MCQ questions (GIFT/XML) |

---

## License

[MIT](LICENSE)
