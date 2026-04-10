---
name: moodle-coderunner
version: 6.0.0
description: |
  Generate Moodle CodeRunner programming questions with Jobe server validation.
  Uses minimal pipeline: AI generates code + tests, Jobe computes expected output.
  Supports Java, Python, C, C++, Node.js. Produces import-ready Moodle XML.
  Battle-tested: 1000+ questions validated with 0% failure rate.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
---

# CodeRunner Question Generator (Minimal Pipeline)

Generate Moodle CodeRunner questions. Two modes depending on your environment.

## Mode Detection

**Before doing anything else, determine your mode:**

Run this command:
```bash
echo "jobe-check"
```

- **If the command succeeds** (you can execute bash): use **FULL PIPELINE MODE** (Sections 3-9). Jobe computes all expected output via curl. This is the preferred mode.
- **If the command fails** (no bash access, e.g. Claude.ai or ChatGPT): use **FALLBACK MODE** (see box below). You must mentally trace expected output yourself.

> **FALLBACK MODE (no bash access)**
>
> When you cannot run bash commands (Claude.ai, ChatGPT, API without tools):
> 1. Generate the same JSON structure as Section 6, but you MUST include `"expected"` in each test case by carefully tracing the solution through the test code.
> 2. Trace character-by-character. Pay special attention to: trailing spaces, newlines, floating-point precision, array formatting.
> 3. Apply all per-language rules from Section 2 and auto-fix rules from Section 8 manually.
> 4. Wrap in XML using the template from Section 7.
> 5. **Add this warning to the user:** "These questions were generated WITHOUT Jobe server validation. Before using them, import into Moodle and ensure `Validate on save` is enabled (it is by default). Moodle will run the solution against all test cases on import and flag any mismatches."
> 6. All other sections (question design, type rules, XML template, checklist) still apply.

**Full Pipeline mode is strongly preferred.** It eliminates the #1 source of errors (hallucinated expected output, which causes 35% of all failures).

---

## 1. Question Type Reference

Choose the type FIRST -- it determines everything else.

| Type | Student Writes | Test Mechanism | Stdin? | Reliability |
|------|---------------|----------------|--------|-------------|
| `java_class` | A class | Test code calls methods | No | HIGH |
| `java_method` | Static method(s) ONLY | Test code calls methods | No | HIGH |
| `java_program` | Full program with `main` | Empty test, stdin input | Yes | LOW -- EOF issues |
| `python3` | Function(s) or class | Test code calls with `print()` | No | HIGH |
| `python3_w_input` | Full program | Empty test, stdin input | Yes | MEDIUM -- EOF issues |
| `c_function` | Function(s) + headers | Test code has `main()` | No | HIGH |
| `c_program` | Full program with `main` | Empty test, stdin input | Yes | MEDIUM |
| `cpp_function` | Function(s) + headers | Test code has `main()` | No | MEDIUM -- Werror |
| `cpp_program` | Full program with `main` | Empty test, stdin input | Yes | MEDIUM -- Werror |
| `nodejs` | Function(s) | Test code uses `console.log()` | No | HIGH |

**Default choice**: Prefer `java_class` > `java_method` > `java_program`. Prefer function types over program types -- they avoid stdin/EOF problems entirely.

---

## 2. Per-Language Rules

These rules are derived from 1000+ validated questions. Every rule exists because questions failed without it.

### Java

| Rule | Applies To | What To Do |
|------|-----------|------------|
| Scanner EOF guard | `java_program` | ALWAYS call `hasNextLine()`/`hasNextInt()` before EVERY `Scanner` read. #1 Java failure cause. |
| Class name | `java_program` | Class MUST be named `Answer` |
| Method-only solution | `java_method` | Solution MUST be ONLY the method(s) -- NO class wrapper, NO main(), NO import statements. The buildSource step wraps it in `public class Answer { <methods> main() { testcode } }`. Including `public class` or `main()` causes compilation errors. |
| Class qualifier in tests | `java_class` | Test code runs in a separate `__Tester__` class. Call static methods as `ClassName.method()`. Create objects as `ClassName obj = new ClassName(); obj.method()`. |

### Python

| Rule | Applies To | What To Do |
|------|-----------|------------|
| EOF guard | `python3_w_input` | Use `import sys; data = sys.stdin.read().strip()` with `if data:` guard. Never bare `input()`. |
| Function-only solution | `python3` | Solution is function/class definitions only. Test code calls them with `print()`. |

### C

| Rule | Applies To | What To Do |
|------|-----------|------------|
| `-Werror` | ALL C types | Jobe compiles with `-Werror`. ALL warnings are fatal. No unused variables, no implicit declarations. |
| `#include` in answer | `c_function` | ALL headers (`<stdio.h>`, `<ctype.h>`, `<string.h>`, `<math.h>`, `<stdlib.h>`) MUST be in the solution, not just test code. |
| `scanf` return check | `c_program` | Always: `if (scanf("%d", &n) == 1) { ... }`. Unchecked scanf on empty stdin = uninitialized variable. |
| Test code wrapper | `c_function` | Test code MUST include `#include <stdio.h>` and `int main(void) { ... return 0; }` |
| Array printing | ALL C types | Use `if (i) printf(" "); printf("%d", arr[i]);` -- NOT `printf("%d ", arr[i])` (trailing space fails). |
| Function-only solution | `c_function` | Solution is function(s) with #include headers only. NO main(). Test code provides main(). |

### C++

| Rule | Applies To | What To Do |
|------|-----------|------------|
| `-Werror` | ALL C++ types | Same as C -- all warnings fatal. |
| `size_t` for `.size()` | ALL C++ types | `for (size_t i = 0; i < vec.size(); i++)` -- `int` vs `size_t` is `-Werror=sign-compare` fatal. |
| Member init order | `cpp_function` | Declare class members in SAME order as constructor initializer list. `-Werror=reorder` is fatal. |
| `#include` in answer | `cpp_function` | Include `<vector>`, `<string>`, `<algorithm>`, `<sstream>` etc. in the solution, not just test code. |
| Test code wrapper | `cpp_function` | Test code MUST include `#include <iostream>`, `using namespace std;`, and `int main() { ... }` |
| Array printing | ALL C++ types | `if (i) cout << " "; cout << v[i];` -- no trailing space. |

### Node.js

| Rule | Applies To | What To Do |
|------|-----------|------------|
| Deterministic output | `nodejs` | Use `JSON.stringify(result)` for objects/arrays. Do NOT use `JSON.stringify(obj, replacer)`. |
| No npm packages | `nodejs` | Only Node.js built-in features. No require() of external modules. |

---

## 3. Jobe Server Configuration

### Servers

| Server | URL | Notes |
|--------|-----|-------|
| Primary | `https://jobe2.cosc.canterbury.ac.nz` | Canterbury University public Jobe. No API key needed. |
| Backup | `http://3.252.250.94` | EC2 backup with CORS proxy. |

Try the primary server first. If it fails (timeout or HTTP error), fall back to the backup.

### Language IDs for Jobe

| Question Types | Jobe `language_id` |
|----------------|-------------------|
| `python3`, `python3_w_input` | `python3` |
| `java_class`, `java_method`, `java_program` | `java` |
| `c_function`, `c_program` | `c` |
| `cpp_function`, `cpp_program` | `cpp` |
| `nodejs` | `nodejs` |

### Calling Jobe via curl

Use this exact curl pattern for every Jobe call:

```bash
curl -s -w "\n%{http_code}" \
  https://jobe2.cosc.canterbury.ac.nz/jobe/index.php/restapi/runs \
  -H "Content-Type: application/json" \
  -d '{
    "run_spec": {
      "language_id": "LANGUAGE_ID",
      "sourcecode": "FULL_SOURCE_CODE",
      "input": "STDIN_OR_EMPTY",
      "sourcefilename": "FILENAME",
      "parameters": {"cputime": 10, "memorylimit": 256000}
    }
  }'
```

**Response format:**
```json
{"outcome": 15, "cmpinfo": "", "stdout": "42\n", "stderr": ""}
```

**Outcome codes:**
- `15` = success. Use `stdout` as the expected output.
- `11` = compilation error. Read `cmpinfo` for the error.
- `12` = runtime error. Read `stderr` for the error.
- `13` = time limit exceeded.
- `17` = memory limit exceeded.
- Any other outcome = failure.

**Important:** Stdin MUST end with `\n`. If the input does not end with a newline, append one before sending.

**Important:** Expected output: strip the trailing newline from stdout before using it as expected output. CodeRunner strips trailing newlines before comparing, so the `<expected>` tag should NOT include a trailing newline.

### Escaping for curl -d

The sourcecode and input fields are inside a JSON string inside a bash command. You MUST properly escape:
- Backslashes: `\` becomes `\\`
- Double quotes: `"` becomes `\"`
- Newlines: actual newlines become `\n`
- Tabs: actual tabs become `\t`
- Dollar signs in bash: use single-quoted heredoc to avoid shell expansion

**Recommended pattern:** Write the JSON payload to a temp file, then curl with `--data @file`:

```bash
# Write payload to temp file (avoids all escaping issues)
cat > /tmp/jobe_payload.json << 'PAYLOAD'
{
  "run_spec": {
    "language_id": "python3",
    "sourcecode": "def add(a, b):\n    return a + b\n\nprint(add(2, 3))",
    "input": "",
    "sourcefilename": "test.py",
    "parameters": {"cputime": 10, "memorylimit": 256000}
  }
}
PAYLOAD

curl -s https://jobe2.cosc.canterbury.ac.nz/jobe/index.php/restapi/runs \
  -H "Content-Type: application/json" \
  --data @/tmp/jobe_payload.json
```

For complex source code (multi-line, quotes, special chars), ALWAYS use the temp file approach.

---

## 4. Building Source Code

Before calling Jobe, assemble the full source code from the solution and test code. The assembly rules depend on the question type.

### Assembly Rules by Type

#### `java_method`
Wrap the solution methods inside a class, add main() with the test code:
```java
public class Answer {
    SOLUTION_METHODS

    public static void main(String[] args) throws Exception {
        TESTCODE
    }
}
```
- Filename: `Answer.java`
- Stdin: empty

#### `java_class`
Strip `public` from the student's class declaration, append a tester class:
```java
class ClassName {
    // solution with 'public class' changed to 'class'
}

public class __Tester__ {
    public static void main(String[] args) throws Exception {
        TESTCODE
    }
}
```
- Filename: `__Tester__.java`
- Stdin: empty
- **Important:** Test code must use the class name qualifier: `ClassName.method()` or `ClassName obj = new ClassName();`

#### `java_program`
Use the solution as-is. Extract the public class name for the filename.
- Filename: `{ClassName}.java` (extracted from `public class X`, default `Answer`)
- Stdin: test input
- Test code: empty

#### `python3`
Concatenate solution and test code:
```python
SOLUTION

TESTCODE
```
- Filename: `test.py`
- Stdin: empty

#### `python3_w_input`
Use solution as-is, pass stdin separately.
- Filename: `test.py`
- Stdin: test input
- Test code: empty

#### `c_function` / `cpp_function`
Concatenate solution and test code:
```c
SOLUTION

TESTCODE
```
- Filename: `test.c` or `test.cpp`
- Stdin: empty
- **Important:** Test code must include `#include` directives and `int main()`.

#### `c_program` / `cpp_program`
Use solution as-is, pass stdin separately.
- Filename: `test.c` or `test.cpp`
- Stdin: test input
- Test code: empty

#### `nodejs`
Concatenate solution and test code:
```javascript
SOLUTION

TESTCODE
```
- Filename: `test.js`
- Stdin: empty

---

## 5. Question Design

Every question MUST include:

1. **`name`** -- `Micro-Assessment - Descriptive Title` (unique, not "Question 1")
2. **`question_text`** -- Clear HTML instructions: method names, parameter types, return types, example usage. Include penalty regime text (see below).
3. **`solution`** -- Complete, correct model solution (NEVER empty)
4. **`preload`** -- Compilable skeleton with comments (do not give away the solution structure)
5. **`feedback`** -- Explanation of correct approach (shown after quiz closes)
6. **Test cases** -- 3+ test cases: 1 visible, 2+ hidden, include edge cases
7. **Self-contained** -- never reference lectures or slides

### Penalty Regime Text (include in every question_text)
```html
<p><strong>Penalty Regime:</strong></p>
<ul>
<li>You have a total of <strong>3 attempts</strong> without any penalties.</li>
<li>Starting from the <strong>4th attempt onwards</strong>, a penalty of <strong>10%</strong> will be applied.</li>
</ul>
```

### Test Case Requirements
- Minimum 3 test cases
- First test case: visible (`useasexample="1"`, display `SHOW`)
- Remaining test cases: hidden (`useasexample="0"`, display `HIDE`)
- Each test MUST produce DIFFERENT output (prevents hard-coding)
- Include at least one edge case (empty input, zero, negative, boundary)
- For program types with stdin: include empty stdin test case
- For partial credit (`allornothing="0"`): marks MUST sum to 1.0
- Do NOT include expected output in the JSON -- Jobe will compute it

---

## 6. Workflow (Full Pipeline Mode)

This workflow assumes you passed the mode detection check and can run bash commands. If you cannot, follow Fallback Mode described at the top.

### Step 1: Gather Requirements

Ask the user for:
- **Language**: Java, Python, C, C++, Node.js (and specific type if they have a preference)
- **Topic**: What the questions should be about
- **Count**: How many questions (default: 5)
- **Difficulty**: easy / medium / hard
- **Grading mode**: all-or-nothing (default) or partial credit

### Step 2: Generate JSON for All Questions

For each question, generate a JSON object with this structure:

```json
{
  "name": "Micro-Assessment - Descriptive Title",
  "qtype": "java_class",
  "question_text": "<h4>Title</h4><p>Instructions with examples...</p><p><strong>Penalty Regime:</strong></p><ul><li>You have a total of <strong>3 attempts</strong> without any penalties.</li><li>Starting from the <strong>4th attempt onwards</strong>, a penalty of <strong>10%</strong> will be applied.</li></ul>",
  "feedback": "<p>Explanation of the correct approach.</p>",
  "solution": "complete model solution code",
  "preload": "skeleton code for students",
  "test_cases": [
    {"testcode": "System.out.println(obj.method(arg));", "stdin": "", "visible": true},
    {"testcode": "System.out.println(obj.method(arg2));", "stdin": "", "visible": false},
    {"testcode": "System.out.println(obj.method(edge));", "stdin": "", "visible": false}
  ]
}
```

**Do NOT include `expected` in test_cases.** Jobe will compute it.

For program types (java_program, python3_w_input, c_program, cpp_program):
- `testcode` is empty string `""`
- `stdin` contains the input data

### Step 3: Validate Each Test Case on Jobe

For each question, for each test case:

1. **Build the full source code** using the assembly rules from Section 4
2. **Determine the language_id** from Section 3
3. **Determine the filename** from Section 4
4. **Write the Jobe payload** to a temp file
5. **Call Jobe via curl**
6. **Check the outcome:**
   - If outcome is `15`: strip the trailing newline from `stdout` and save it as the expected output for this test case
   - If outcome is NOT `15`: the test case failed -- see Step 4

**Example -- validating a python3 question:**

```bash
# Question: def add(a, b): return a + b
# Test case: print(add(2, 3))
# Built source: "def add(a, b):\n    return a + b\n\nprint(add(2, 3))"

cat > /tmp/jobe_payload.json << 'PAYLOAD'
{
  "run_spec": {
    "language_id": "python3",
    "sourcecode": "def add(a, b):\n    return a + b\n\nprint(add(2, 3))",
    "input": "",
    "sourcefilename": "test.py",
    "parameters": {"cputime": 10, "memorylimit": 256000}
  }
}
PAYLOAD

curl -s https://jobe2.cosc.canterbury.ac.nz/jobe/index.php/restapi/runs \
  -H "Content-Type: application/json" \
  --data @/tmp/jobe_payload.json
```

Response: `{"outcome":15,"cmpinfo":"","stdout":"5\n","stderr":""}`

Expected output for this test case: `5` (stdout with trailing newline stripped).

**Example -- validating a java_class question:**

```bash
# Solution: public class Calculator { public int add(int a, int b) { return a + b; } }
# Test case: Calculator c = new Calculator(); System.out.println(c.add(2, 3));
# Built source (java_class assembly):
#   class Calculator { public int add(int a, int b) { return a + b; } }
#   public class __Tester__ {
#       public static void main(String[] args) throws Exception {
#           Calculator c = new Calculator(); System.out.println(c.add(2, 3));
#       }
#   }

cat > /tmp/jobe_payload.json << 'PAYLOAD'
{
  "run_spec": {
    "language_id": "java",
    "sourcecode": "class Calculator { public int add(int a, int b) { return a + b; } }\n\npublic class __Tester__ {\n    public static void main(String[] args) throws Exception {\n        Calculator c = new Calculator(); System.out.println(c.add(2, 3));\n    }\n}",
    "input": "",
    "sourcefilename": "__Tester__.java",
    "parameters": {"cputime": 10, "memorylimit": 256000}
  }
}
PAYLOAD

curl -s https://jobe2.cosc.canterbury.ac.nz/jobe/index.php/restapi/runs \
  -H "Content-Type: application/json" \
  --data @/tmp/jobe_payload.json
```

### Step 4: Fix and Retry on Failure

If Jobe returns a non-15 outcome for any test case:

1. Read the error from `cmpinfo` (compile errors) or `stderr` (runtime errors)
2. Diagnose the issue using the common fixes table below
3. Fix the solution or test code
4. Rebuild the source and call Jobe again
5. Repeat up to 3 times per question

If a question still fails after 3 retries, report it to the user and move on.

### Common Fixes

| Error | Fix |
|-------|-----|
| `implicit declaration` | Add missing `#include` to solution |
| `sign-compare` | Change `int i` to `size_t i` in `.size()` loops |
| `reorder` | Reorder class members to match constructor initializer list |
| `illegal start of expression` (java_method) | Solution must be raw method(s) only -- remove class wrapper, main(), imports |
| Trailing space in output | Use `if(i) printf(" ")` pattern for array printing |
| `NoSuchElementException` | Add `hasNext()` guard before Scanner read |
| `EOFError` | Use `sys.stdin.read()` instead of `input()` |
| `cannot find symbol` (java_class) | Test code must use class name qualifier: `ClassName.method()` |
| `non-static` (java_method) | Add `static` keyword to method |
| `control reaches end of non-void` | Add return statement at end of function |
| `reached end of file` / `expected }` | Count `{` and `}` -- add missing closing brace |
| `unnamed classes are a preview` | Wrap code in `public class Answer { }` |
| `ArrayIndexOutOfBounds` | Add empty array check: `if (arr.length == 0) return default;` |

### Step 5: Assemble the XML

Once ALL test cases for ALL questions have passed Jobe validation, wrap everything in the Moodle XML template from Section 7.

For each test case, the `<expected>` value is the stdout captured from Jobe (with trailing newline stripped).

### Step 6: Write and Confirm

1. Write the XML to a file named `{module}_{topic}_coderunner.xml`
2. Report to the user:
   - Number of questions generated
   - Number that passed validation
   - Any that failed and were excluded
   - The file path

---

## 7. XML Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<quiz>
  <question type="category">
    <category><text>$course$/Category Name</text></category>
  </question>

  <!-- Repeat this block for each question -->
  <question type="coderunner">
    <name><text>QUESTION_NAME</text></name>
    <questiontext format="html"><text><![CDATA[QUESTION_HTML]]></text></questiontext>
    <generalfeedback format="html"><text><![CDATA[FEEDBACK_HTML]]></text></generalfeedback>
    <defaultgrade>1</defaultgrade>
    <penalty>0</penalty>
    <hidden>0</hidden>
    <idnumber></idnumber>
    <coderunnertype>QTYPE</coderunnertype>
    <prototypetype>0</prototypetype>
    <allornothing>1</allornothing>
    <penaltyregime>0, 0, 0, 10, 20, ...</penaltyregime>
    <precheck>0</precheck>
    <hidecheck>0</hidecheck>
    <showsource>0</showsource>
    <answerboxlines>18</answerboxlines>
    <answerboxcolumns>100</answerboxcolumns>
    <answerpreload><![CDATA[PRELOAD_CODE]]></answerpreload>
    <globalextra></globalextra>
    <useace></useace>
    <resultcolumns></resultcolumns>
    <template></template>
    <iscombinatortemplate></iscombinatortemplate>
    <allowmultiplestdins></allowmultiplestdins>
    <answer><![CDATA[MODEL_SOLUTION]]></answer>
    <validateonsave>1</validateonsave>
    <testsplitterre></testsplitterre>
    <language></language>
    <acelang></acelang>
    <sandbox></sandbox>
    <grader></grader>
    <cputimelimitsecs></cputimelimitsecs>
    <memlimitmb></memlimitmb>
    <sandboxparams></sandboxparams>
    <templateparams></templateparams>
    <hoisttemplateparams>1</hoisttemplateparams>
    <extractcodefromjson>1</extractcodefromjson>
    <templateparamslang>None</templateparamslang>
    <templateparamsevalpertry>0</templateparamsevalpertry>
    <templateparamsevald>{}</templateparamsevald>
    <twigall>0</twigall>
    <uiplugin></uiplugin>
    <uiparameters><![CDATA[{"live_autocompletion": true}]]></uiparameters>
    <attachments>0</attachments>
    <attachmentsrequired>0</attachmentsrequired>
    <maxfilesize>10240</maxfilesize>
    <filenamesregex></filenamesregex>
    <filenamesexplain></filenamesexplain>
    <displayfeedback>1</displayfeedback>
    <giveupallowed>0</giveupallowed>
    <prototypeextra></prototypeextra>
    <testcases>
      <!-- Repeat for each test case -->
      <testcase testtype="0" useasexample="USE_AS_EXAMPLE" hiderestiffail="0" mark="MARK_VALUE">
        <testcode><text>TESTCODE</text></testcode>
        <stdin><text>STDIN</text></stdin>
        <expected><text>EXPECTED_FROM_JOBE</text></expected>
        <extra><text></text></extra>
        <display><text>DISPLAY_VALUE</text></display>
      </testcase>
    </testcases>
  </question>
</quiz>
```

### Field Values per Test Case

| Field | Visible test (first) | Hidden test (remaining) |
|-------|---------------------|------------------------|
| `useasexample` | `1` | `0` |
| `display` | `SHOW` | `HIDE` |
| `mark` | `1.0000000` (all-or-nothing) | `1.0000000` (all-or-nothing) |

For partial credit: distribute marks so they sum to 1.0 (e.g., 4 tests = `0.2500000` each).

### Optional Feature Tags

| Feature | Tag | Values | Effect |
|---------|-----|--------|--------|
| Precheck | `<precheck>1</precheck>` | 0/1 | Students can test before submitting |
| Give up | `<giveupallowed>1</giveupallowed>` | 0/1 | Students can reveal model answer |
| CPU limit | `<cputimelimitsecs>5</cputimelimitsecs>` | seconds | Enforce time limit |
| Memory limit | `<memlimitmb>64</memlimitmb>` | MB | Enforce memory limit |

---

## 8. Auto-Fix Rules to Apply Before Jobe

Before sending code to Jobe, apply these fixes to the solution and test code. These catch the most common AI generation mistakes.

### Solution Fixes

| # | Fix | Applies To | What To Do |
|---|-----|-----------|------------|
| 1 | Strip class/main/imports | `java_method` | Remove any `public class` wrapper, `main()` method, and `import` statements. java_method solutions must be bare static methods only. |
| 2 | Wrap in public class | `java_class` | If solution has no `class` keyword, wrap in `public class Answer { ... }` |
| 3 | Rename class to Answer | `java_program` | If solution has a class not named `Answer`, rename it |
| 4 | Add Scanner hasNext guards | `java_program` | Wrap `scanner.nextInt()` with `scanner.hasNextInt() ? scanner.nextInt() : 0` and `scanner.nextLine()` with `scanner.hasNextLine() ? scanner.nextLine() : ""` |
| 5 | Remove accidental main() | `c_function`, `cpp_function` | Strip `int main(...)` block from function-type solutions |
| 6 | Add missing main() | `c_program`, `cpp_program` | Append `int main(void) { return 0; }` if no main() exists |
| 7 | Auto-close braces | `java_*`, `c_*`, `cpp_*`, `nodejs` | Count `{` vs `}` and append missing closing braces |
| 8 | Wrap input() in try/except | `python3_w_input` | If solution uses bare `input()` without `sys.stdin` or `try`, wrap in `try: ... except EOFError: pass` |
| 9 | Add missing C headers | `c_function`, `c_program` | Detect function usage and add missing `#include`: stdio.h, string.h, stdlib.h, math.h, ctype.h, limits.h |
| 10 | Add missing C++ headers | `cpp_function`, `cpp_program` | Detect usage and add: iostream, vector, string, algorithm, map, set, stack, queue, sstream |
| 11 | Fix int to size_t | `cpp_function`, `cpp_program` | Rewrite `for (int i = 0; i < v.size()` to `for (size_t i = 0; i < v.size()` |
| 12 | Cast to size_t | `cpp_function`, `cpp_program` | Rewrite `if (x < v.size()` to `if ((size_t)x < v.size()` |

### Test Code Fixes

| # | Fix | Applies To | What To Do |
|---|-----|-----------|------------|
| 1 | Wrap C test code | `c_function` | If test code lacks `int main`, wrap with `#include <stdio.h>` + `int main(void) { ... return 0; }` |
| 2 | Wrap C++ test code | `cpp_function` | If test code lacks `int main`, wrap with `#include <iostream>` + `using namespace std;` + `int main() { ... }` |
| 3 | Fix unmatched parens | All types | If closing parens exceed opening parens, trim trailing `)` |

Apply these fixes programmatically before building the source and calling Jobe.

---

## 9. Complete Worked Example

Here is a complete end-to-end example generating one Python question.

### 9a. Generate JSON

```json
{
  "name": "Micro-Assessment - Sum of Even Numbers",
  "qtype": "python3",
  "question_text": "<h4>Sum of Even Numbers</h4><p>Write a function <code>sum_evens(nums)</code> that takes a list of integers and returns the sum of all even numbers in the list.</p><h5>Example</h5><pre>sum_evens([1, 2, 3, 4, 5, 6]) -> 12</pre><p><strong>Penalty Regime:</strong></p><ul><li>You have a total of <strong>3 attempts</strong> without any penalties.</li><li>Starting from the <strong>4th attempt onwards</strong>, a penalty of <strong>10%</strong> will be applied.</li></ul>",
  "feedback": "<p>Use a list comprehension or loop to filter even numbers (n % 2 == 0) and sum them. The built-in <code>sum()</code> function works well with a generator expression.</p>",
  "solution": "def sum_evens(nums):\n    return sum(n for n in nums if n % 2 == 0)",
  "preload": "def sum_evens(nums):\n    # Write your code here\n    pass",
  "test_cases": [
    {"testcode": "print(sum_evens([1, 2, 3, 4, 5, 6]))", "stdin": "", "visible": true},
    {"testcode": "print(sum_evens([]))", "stdin": "", "visible": false},
    {"testcode": "print(sum_evens([1, 3, 5]))", "stdin": "", "visible": false},
    {"testcode": "print(sum_evens([-2, -1, 0, 1, 2]))", "stdin": "", "visible": false}
  ]
}
```

### 9b. Validate Test Case 1 on Jobe

Build source (python3 = solution + "\n\n" + testcode):
```
def sum_evens(nums):
    return sum(n for n in nums if n % 2 == 0)

print(sum_evens([1, 2, 3, 4, 5, 6]))
```

```bash
cat > /tmp/jobe_payload.json << 'PAYLOAD'
{
  "run_spec": {
    "language_id": "python3",
    "sourcecode": "def sum_evens(nums):\n    return sum(n for n in nums if n % 2 == 0)\n\nprint(sum_evens([1, 2, 3, 4, 5, 6]))",
    "input": "",
    "sourcefilename": "test.py",
    "parameters": {"cputime": 10, "memorylimit": 256000}
  }
}
PAYLOAD

curl -s https://jobe2.cosc.canterbury.ac.nz/jobe/index.php/restapi/runs \
  -H "Content-Type: application/json" \
  --data @/tmp/jobe_payload.json
```

Result: `{"outcome":15,"stdout":"12\n",...}` -- expected output: `12`

### 9c. Repeat for All Test Cases

- Test 2: `sum_evens([])` -- stdout `0\n` -- expected: `0`
- Test 3: `sum_evens([1, 3, 5])` -- stdout `0\n` -- expected: `0`
- Test 4: `sum_evens([-2, -1, 0, 1, 2])` -- stdout `0\n` -- expected: `0`

### 9d. Wrap in XML

Fill in the XML template from Section 7:
- `QUESTION_NAME` = `Micro-Assessment - Sum of Even Numbers`
- `QTYPE` = `python3`
- `QUESTION_HTML` = the question_text HTML
- `FEEDBACK_HTML` = the feedback HTML
- `MODEL_SOLUTION` = the solution code
- `PRELOAD_CODE` = the preload code
- For each test case: fill `TESTCODE`, `STDIN`, `EXPECTED_FROM_JOBE`, `USE_AS_EXAMPLE`, `DISPLAY_VALUE`

---

## 10. Final Checklist

Before delivery, every question must satisfy:

- [ ] `<name>` tag uses descriptive title starting with `Micro-Assessment -`
- [ ] Correct `<coderunnertype>` for the task
- [ ] `<answer>` contains complete, compilable model solution
- [ ] `<answer>` for java_method is raw method(s) only (no class wrapper)
- [ ] `<answerpreload>` provides compilable skeleton
- [ ] `<generalfeedback>` explains correct approach
- [ ] `<validateonsave>1</validateonsave>`
- [ ] `<penaltyregime>0, 0, 0, 10, 20, ...</penaltyregime>`
- [ ] Penalty regime text in `<questiontext>`
- [ ] Self-contained (no lecture references)
- [ ] 3+ test cases: 1 visible, 2+ hidden, edge cases included
- [ ] Each test produces different output
- [ ] No floating-point exact comparisons
- [ ] Marks sum to 1.0 (if partial credit)
- [ ] Language-specific rules from Section 2 followed
- [ ] Auto-fix rules from Section 8 applied before Jobe calls
- [ ] **ALL test cases returned outcome 15 from Jobe** (Full Pipeline mode)
- [ ] **ALL expected values are Jobe stdout (never hand-written)** (Full Pipeline mode)
- [ ] If Fallback Mode: warned user to validate on import with `Validate on save` enabled

---

## 11. File Naming

- Questions: `{module}_{topic}_coderunner.xml`
- Example: `oop1_polymorphism_coderunner.xml`

---

## 12. Moodle Import

1. Course > Question bank > Import
2. Format: Moodle XML
3. Upload `.xml` file
4. Import and review
