#!/usr/bin/env python3
"""Validate CodeRunner questions against a Jobe server.

Parses Moodle XML, constructs full source code per question type,
submits to Jobe for compilation and execution, compares output.

Usage:
    python3 validate_coderunner.py <xml_file> [--jobe-url URL]

Dependencies: Python 3.6+ stdlib only (no pip install needed).
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from html import unescape

# Default Jobe endpoints (AWS instances)
DEFAULT_JOBE_URLS = [
    "http://3.250.73.210:4000",
    "http://3.250.73.210:4001",
    "http://3.250.73.210:4002",
]

CANTERBURY_JOBE = "https://jobe2.cosc.canterbury.ac.nz"

# Map CodeRunner types to Jobe language IDs and source construction mode
TYPE_CONFIG = {
    "java_class":      {"jobe_lang": "java",    "mode": "class"},
    "java_program":    {"jobe_lang": "java",    "mode": "program"},
    "java_method":     {"jobe_lang": "java",    "mode": "method"},
    "python3":         {"jobe_lang": "python3", "mode": "function"},
    "python3_w_input": {"jobe_lang": "python3", "mode": "program"},
    "c_function":      {"jobe_lang": "c",       "mode": "function"},
    "c_program":       {"jobe_lang": "c",       "mode": "program"},
    "cpp_function":    {"jobe_lang": "cpp",     "mode": "function"},
    "cpp_program":     {"jobe_lang": "cpp",     "mode": "program"},
    "nodejs":          {"jobe_lang": "nodejs",  "mode": "function"},
}

# Jobe outcome codes
OUTCOME_SUCCESS = 15
OUTCOME_COMPILE_ERROR = 11
OUTCOME_RUNTIME_ERROR = 12


def extract_java_class_name(source):
    """Extract the public class name from Java source code."""
    match = re.search(r'public\s+class\s+(\w+)', source)
    return match.group(1) if match else "Answer"


def extract_text(element):
    """Extract text content from an XML element, handling CDATA and None."""
    if element is None:
        return ""
    text_el = element.find("text")
    if text_el is not None and text_el.text:
        return text_el.text
    if element.text:
        return element.text
    return ""


def build_source(question_type, model_solution, test_code, stdin=""):
    """Construct the full source code that Jobe will compile and run.

    Returns (source_code, filename, stdin_to_send).
    """
    config = TYPE_CONFIG.get(question_type)
    if not config:
        return model_solution, "test.txt", stdin

    mode = config["mode"]
    lang = config["jobe_lang"]

    if question_type == "java_class":
        # Student writes a class, test code exercises it via a tester main().
        # Strip 'public' from student's class so __Tester__ can be the public
        # class (Java requires filename to match the public class).
        stripped_solution = re.sub(r'\bpublic\s+class\b', 'class', model_solution, count=1)
        if test_code.strip():
            source = (
                f"{stripped_solution}\n\n"
                f"public class __Tester__ {{\n"
                f"    public static void main(String[] args) throws Exception {{\n"
                f"        {test_code}\n"
                f"    }}\n"
                f"}}"
            )
        else:
            source = model_solution
            return source, f"{extract_java_class_name(model_solution)}.java", ""
        return source, "__Tester__.java", ""

    elif question_type == "java_method":
        # Student writes method(s), wrapped in Answer class with test code in main
        source = (
            f"public class Answer {{\n"
            f"    {model_solution}\n\n"
            f"    public static void main(String[] args) throws Exception {{\n"
            f"        {test_code}\n"
            f"    }}\n"
            f"}}"
        )
        return source, "Answer.java", ""

    elif question_type == "java_program":
        # Student writes complete program, test uses stdin
        class_name = extract_java_class_name(model_solution)
        return model_solution, f"{class_name}.java", stdin

    elif question_type == "python3":
        # Student writes functions/classes, test code calls them
        if test_code.strip():
            source = f"{model_solution}\n\n{test_code}"
        else:
            source = model_solution
        return source, "test.py", ""

    elif question_type == "python3_w_input":
        # Student writes complete program, test uses stdin
        return model_solution, "test.py", stdin

    elif question_type in ("c_function", "cpp_function"):
        # Student writes function(s), test code contains main()
        if test_code.strip():
            source = f"{model_solution}\n\n{test_code}"
        else:
            source = model_solution
        ext = ".c" if question_type == "c_function" else ".cpp"
        return source, f"test{ext}", ""

    elif question_type in ("c_program", "cpp_program"):
        # Student writes complete program, test uses stdin
        ext = ".c" if question_type == "c_program" else ".cpp"
        return model_solution, f"test{ext}", stdin

    elif question_type == "nodejs":
        if test_code.strip():
            source = f"{model_solution}\n\n{test_code}"
        else:
            source = model_solution
        return source, "test.js", ""

    return model_solution, "test.txt", stdin


def submit_to_jobe(source, filename, language_id, stdin="", jobe_url=""):
    """Submit code to Jobe server and return the result dict."""
    url = f"{jobe_url}/jobe/index.php/restapi/runs"
    payload = {
        "run_spec": {
            "language_id": language_id,
            "sourcefilename": filename,
            "sourcecode": source,
            "input": stdin,
            "parameters": {"cputime": 10, "memorylimit": 256000},
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"outcome": -1, "cmpinfo": f"HTTP {e.code}: {body[:200]}", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"outcome": -1, "cmpinfo": str(e), "stdout": "", "stderr": ""}


def find_working_jobe(urls):
    """Find the first responsive Jobe server from a list of URLs."""
    for url in urls:
        try:
            test_url = f"{url}/jobe/index.php/restapi/languages"
            req = urllib.request.Request(test_url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return None


def validate_question(question_el, jobe_url):
    """Validate a single CodeRunner question element. Returns result dict."""
    name_el = question_el.find(".//name/text")
    name = name_el.text if name_el is not None else "Unknown"

    qtype_el = question_el.find("coderunnertype")
    qtype = qtype_el.text if qtype_el is not None else "unknown"

    answer_el = question_el.find("answer")
    model_solution = answer_el.text if answer_el is not None else ""

    if not model_solution or not model_solution.strip():
        return {
            "name": name,
            "type": qtype,
            "status": "SKIP",
            "reason": "No model solution found in <answer> tag",
            "tests": []
        }

    if qtype not in TYPE_CONFIG:
        return {
            "name": name,
            "type": qtype,
            "status": "SKIP",
            "reason": f"Unsupported question type: {qtype}",
            "tests": []
        }

    config = TYPE_CONFIG[qtype]
    lang_id = config["jobe_lang"]

    test_results = []
    all_passed = True

    testcases = question_el.findall(".//testcase")
    if not testcases:
        return {
            "name": name,
            "type": qtype,
            "status": "SKIP",
            "reason": "No test cases found",
            "tests": []
        }

    for i, tc in enumerate(testcases):
        test_code = extract_text(tc.find("testcode"))
        stdin = extract_text(tc.find("stdin"))
        expected = extract_text(tc.find("expected"))

        source, filename, actual_stdin = build_source(qtype, model_solution, test_code, stdin)

        # CodeRunner always adds a trailing newline to stdin before sending
        # to Jobe. Without it, Python's input() raises EOFError and some C
        # scanf() calls fail. Match this behavior.
        if actual_stdin and not actual_stdin.endswith("\n"):
            actual_stdin += "\n"

        result = submit_to_jobe(source, filename, lang_id, actual_stdin, jobe_url)

        outcome = result.get("outcome", -1)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        cmpinfo = result.get("cmpinfo", "")

        # Strip trailing newlines for comparison (matches CodeRunner behavior)
        stdout_clean = stdout.rstrip("\n")
        expected_clean = expected.rstrip("\n")

        if outcome == OUTCOME_COMPILE_ERROR:
            error_msg = cmpinfo[:300] if cmpinfo else "Unknown compilation error"
            test_results.append({
                "test": i + 1,
                "passed": False,
                "error_type": "COMPILE_ERROR",
                "error": error_msg
            })
            all_passed = False

        elif outcome == OUTCOME_RUNTIME_ERROR:
            error_msg = stderr[:300] if stderr else "Unknown runtime error"
            test_results.append({
                "test": i + 1,
                "passed": False,
                "error_type": "RUNTIME_ERROR",
                "error": error_msg
            })
            all_passed = False

        elif outcome == OUTCOME_SUCCESS:
            if stdout_clean == expected_clean:
                test_results.append({"test": i + 1, "passed": True})
            else:
                test_results.append({
                    "test": i + 1,
                    "passed": False,
                    "error_type": "WRONG_OUTPUT",
                    "expected": repr(expected_clean),
                    "actual": repr(stdout_clean)
                })
                all_passed = False

        elif outcome == -1:
            # Connection error
            test_results.append({
                "test": i + 1,
                "passed": False,
                "error_type": "JOBE_ERROR",
                "error": cmpinfo
            })
            all_passed = False

        else:
            # Other outcome (timeout, memory limit, etc.)
            error_msg = stderr[:200] or cmpinfo[:200] or f"Outcome code: {outcome}"
            test_results.append({
                "test": i + 1,
                "passed": False,
                "error_type": f"OUTCOME_{outcome}",
                "error": error_msg
            })
            all_passed = False

    return {
        "name": name,
        "type": qtype,
        "status": "PASS" if all_passed else "FAIL",
        "tests": test_results
    }


def validate_xml_file(xml_path, jobe_url=None):
    """Parse XML file and validate all CodeRunner questions."""
    # Find a working Jobe server
    if jobe_url:
        urls_to_try = [jobe_url]
    else:
        urls_to_try = DEFAULT_JOBE_URLS + [CANTERBURY_JOBE]

    working_url = find_working_jobe(urls_to_try)
    if not working_url:
        return {
            "error": "No Jobe server reachable. Tried: " + ", ".join(urls_to_try),
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "questions": []
        }

    # Parse XML
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        return {
            "error": f"XML parse error: {e}",
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "questions": []
        }

    root = tree.getroot()
    questions = root.findall('.//question[@type="coderunner"]')

    if not questions:
        return {
            "error": "No CodeRunner questions found in XML file",
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "questions": []
        }

    results = []
    passed = 0
    failed = 0
    skipped = 0

    for q_el in questions:
        result = validate_question(q_el, working_url)
        results.append(result)

        if result["status"] == "PASS":
            passed += 1
        elif result["status"] == "FAIL":
            failed += 1
        else:
            skipped += 1

    return {
        "jobe_server": working_url,
        "summary": {
            "total": len(questions),
            "passed": passed,
            "failed": failed,
            "skipped": skipped
        },
        "questions": results
    }


def print_results(results):
    """Print human-readable validation results."""
    if "error" in results and results["error"]:
        print(f"\nERROR: {results['error']}")
        return False

    s = results["summary"]
    jobe = results.get("jobe_server", "unknown")
    print(f"\n{'='*60}")
    print(f"  CodeRunner Validation Report")
    print(f"  Jobe Server: {jobe}")
    print(f"{'='*60}")
    print(f"  Total: {s['total']}  |  PASS: {s['passed']}  |  FAIL: {s['failed']}  |  SKIP: {s['skipped']}")
    print(f"{'='*60}\n")

    for q in results["questions"]:
        status_icon = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}.get(q["status"], "????")
        print(f"[{status_icon}] {q['name']} ({q['type']})")

        if q.get("reason"):
            print(f"       Reason: {q['reason']}")

        for t in q.get("tests", []):
            if t["passed"]:
                print(f"       Test {t['test']}: OK")
            else:
                error_type = t.get("error_type", "UNKNOWN")
                if error_type == "WRONG_OUTPUT":
                    print(f"       Test {t['test']}: WRONG OUTPUT")
                    print(f"         Expected: {t['expected']}")
                    print(f"         Actual:   {t['actual']}")
                elif error_type == "COMPILE_ERROR":
                    print(f"       Test {t['test']}: COMPILE ERROR")
                    print(f"         {t['error'][:200]}")
                elif error_type == "RUNTIME_ERROR":
                    print(f"       Test {t['test']}: RUNTIME ERROR")
                    print(f"         {t['error'][:200]}")
                else:
                    print(f"       Test {t['test']}: {error_type}")
                    print(f"         {t.get('error', 'No details')[:200]}")
        print()

    # Also print JSON for programmatic use
    print(f"{'='*60}")
    print("JSON output:")
    print(json.dumps(results, indent=2))

    return s["failed"] == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_coderunner.py <xml_file> [--jobe-url URL]")
        print()
        print("Options:")
        print("  --jobe-url URL    Jobe server URL (default: tries AWS then Canterbury)")
        print()
        print("Examples:")
        print("  python3 validate_coderunner.py questions.xml")
        print("  python3 validate_coderunner.py questions.xml --jobe-url http://3.250.73.210:4000")
        print("  python3 validate_coderunner.py questions.xml --jobe-url https://jobe2.cosc.canterbury.ac.nz")
        sys.exit(1)

    xml_path = sys.argv[1]
    jobe_url = None

    # Parse --jobe-url argument
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--jobe-url" and i + 1 < len(sys.argv):
            jobe_url = sys.argv[i + 1]
            break

    results = validate_xml_file(xml_path, jobe_url)
    success = print_results(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
