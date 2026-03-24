<h1 align="center">Moodle CodeRunner</h1>

<p align="center">
  <strong>A Claude skill for generating Moodle CodeRunner programming questions with automated test cases</strong>
</p>

<p align="center">
  <a href="https://github.com/danielcregg/moodle-coderunner/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-2.0.0-green.svg" alt="Version 2.0.0">
  <img src="https://img.shields.io/badge/Claude%20Code-blueviolet.svg" alt="Claude Code">
  <img src="https://img.shields.io/badge/Claude%20Desktop-blueviolet.svg" alt="Claude Desktop">
  <img src="https://img.shields.io/badge/Moodle-4.x%20Compatible-orange.svg" alt="Moodle 4.x">
  <img src="https://img.shields.io/badge/CodeRunner-4.x-red.svg" alt="CodeRunner 4.x">
</p>

<p align="center">
  Generate auto-graded programming questions for Moodle's <a href="https://coderunner.org.nz/">CodeRunner</a> plugin. Produces import-ready Moodle XML with answer preloads, model solutions, visible and hidden test cases, penalty regimes, and live autocomplete editors. Supports Java, Python, C/C++, and more.
</p>

---

## Quick Start

```bash
# Claude Code
mkdir -p ~/.claude/skills
git clone https://github.com/danielcregg/moodle-coderunner.git ~/.claude/skills/moodle-coderunner

# Use
/moodle-coderunner
Generate 5 Java CodeRunner questions on arrays and loops for first-year students
```

For **Claude Desktop**: Settings > Skills > Upload skill > drag and drop `SKILL.md` or the `.zip`.

---

## What is CodeRunner?

[CodeRunner](https://coderunner.org.nz/) is a Moodle question type plugin that runs student-submitted code against automated test cases. Students write code in an in-browser editor, submit it, and get instant feedback on which tests passed or failed. It is the most widely used auto-grading plugin for programming courses on Moodle.

This skill generates the Moodle XML files that define CodeRunner questions — including the question text, skeleton code, model solution, and test cases — ready for direct import.

---

## What Gets Generated

For each question, the skill produces:

| Component | Purpose |
|-----------|---------|
| **Question text** | Clear instructions with example usage and penalty regime |
| **Answer preload** | Skeleton code students start from (compilable, with comments) |
| **Model solution** | Complete correct answer (hidden from students) |
| **Visible test(s)** | Students can see expected input/output |
| **Hidden test(s)** | Prevents hard-coding, tests edge cases |
| **General feedback** | Explanation shown after quiz closes |
| **Penalty regime** | 3 free attempts, then 10% increasing penalty |

---

## Supported Languages

| Language | CodeRunner Types | Status |
|----------|-----------------|--------|
| **Java** | `java_class`, `java_program`, `java_method` | Full support |
| **Python** | `python3`, `python3_w_input` | Full support |
| **C** | `c_function`, `c_program` | Supported |
| **C++** | `cpp_function`, `cpp_program` | Supported |
| **JavaScript** | `nodejs` | Supported |
| **SQL** | `sql` | Supported |
| **PHP** | `php` | Supported |
| **Pascal** | `pascal_function`, `pascal_program` | Supported |
| **Octave/MATLAB** | `octave_function`, `matlab_function` | Supported |

---

## Example: Java Class Question

<details>
<summary><strong>Click to expand full example</strong></summary>

**Question**: Implement getter and setter methods for a Student class.

**Answer preload** (what students see):
```java
public class Student {
    private String name;

    public Student(String name) {
        this.name = name;
    }

    // Write your getter method here


    // Write your setter method here

}
```

**Model solution** (hidden):
```java
public class Student {
    private String name;

    public Student(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
```

**Test case 1** (visible to students):
```
Student s = new Student("Alice");
System.out.println(s.getName());
s.setName("Bob");
System.out.println(s.getName());
```
Expected output: `Alice\nBob`

**Test case 2** (hidden):
```
Student s = new Student("Charlie");
System.out.println(s.getName());
s.setName("Diana");
System.out.println(s.getName());
```
Expected output: `Charlie\nDiana`

</details>

## Example: Python Function Question

<details>
<summary><strong>Click to expand full example</strong></summary>

**Question**: Write a function `square(n)` that returns the square of a number.

**Answer preload**:
```python
def square(n):
    # Write your code here
    pass
```

**Model solution**:
```python
def square(n):
    return n * n
```

**Test case 1** (visible): `print(square(5))` → `25`
**Test case 2** (hidden): `print(square(-3))` → `9`
**Test case 3** (hidden): `print(square(0))` → `0`

</details>

---

## Key Features

### All-or-Nothing vs Partial Credit

| Mode | When to Use | XML Tag |
|------|------------|---------|
| **All-or-nothing** | Methods must work together (getter + setter) | `<allornothing>1</allornothing>` |
| **Partial credit** | Tests are truly independent | `<allornothing>0</allornothing>` |

> **Java caveat**: Partial credit is unreliable in Java because if a method doesn't exist, tests won't compile. Default to all-or-nothing.

### Test Case Strategy

| Test | Visibility | Purpose |
|------|-----------|---------|
| Test 1 | Visible (`useasexample="1"`) | Shows students what's expected |
| Test 2 | Hidden (`useasexample="0"`) | Prevents hard-coding |
| Test 3+ | Hidden | Edge cases, boundary conditions |

### Moodle Import Compatibility

Built-in fixes for common import issues:

| Issue | Fix |
|-------|-----|
| `<n>` instead of `<name>` | Enforces full `<name>` tag |
| Missing penalty regime | Includes `0, 0, 0, 10, 20, ...` |
| No autocomplete | Adds `live_autocompletion: true` |
| Missing feedback | Always includes general feedback |

---

## Installation

### Claude Code (CLI)

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/danielcregg/moodle-coderunner.git ~/.claude/skills/moodle-coderunner
```

### Claude Desktop

1. Download `SKILL.md` from this repo (or download the repo as a `.zip`)
2. Open Claude Desktop > **Settings** > **Skills**
3. Click **Upload skill**
4. Drag and drop the `SKILL.md` file, or the `.zip` file

---

## Usage Examples

### Generate Java OOP questions
```
/moodle-coderunner

Create 5 Java CodeRunner questions on encapsulation (getters, setters, constructors)
for first-year students. Use java_class type with all-or-nothing grading.
```

### Generate Python function questions
```
/moodle-coderunner

Generate 8 Python CodeRunner questions on list manipulation and string methods.
Mix of introductory and intermediate difficulty.
```

### Generate from lecture content
```
/moodle-coderunner

Read my lecture slides on Java arrays and create 6 CodeRunner micro-assessments
covering: array declaration, accessing elements, iteration, and finding min/max.
```

---

## Compatibility

| Platform | Supported | How |
|----------|:---------:|-----|
| Claude Code (CLI) | Yes | Install as skill, invoke with `/moodle-coderunner` |
| Claude Desktop | Yes | Upload skill via Settings > Skills |
| Moodle 4.x + CodeRunner 4.x | Yes | Import generated XML via Question bank |
| Moodle 3.x + CodeRunner 3.x | Yes | Import generated XML via Question bank |
| Windows / macOS / Linux | Yes | All platforms supported |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **2.0.0** | 2026-03-24 | Added Python support, full CodeRunner type list, test case design guide, review document workflow. Published to GitHub. |
| 1.0 | 2025-11-09 | Initial skill for Java CodeRunner questions. Critical `<name>` tag fix. |

---

## Contributing

Contributions welcome. If you have ideas for supporting additional CodeRunner features (randomisation, custom prototypes, precheck modes), or want to add test case templates for more languages:

1. Fork this repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

## License

[MIT](LICENSE)
