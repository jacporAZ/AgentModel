"""
This is the main entry point for the fact-checking agent.

It reads questions from a JSON file, uses the agent to find answers,
and writes the answers to an output file.
"""

import json
from agent import answer_query


def _extract_query(item) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        if "input" in item and isinstance(item["input"], str):
            return item["input"].strip()
        if "query" in item and isinstance(item["query"], str):
            return item["query"].strip()
    return ""

def main():
    """
    Main function to run the fact-checking process.
    """
    input_file = "data/input_questions.json"
    output_file = "answers.json"

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file}")
        return

    answers = []
    for item in questions:
        query_text = _extract_query(item)
        if query_text:
            result = answer_query(query_text)
            answers.append(result)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=4, ensure_ascii=False)

    print(f"Answers have been saved to {output_file}")

if __name__ == "__main__":
    main()
