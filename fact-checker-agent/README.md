# Fact-Checker Agent

This project is a simple fact-checking agent that uses the Wikipedia API to answer questions.

## How to Run

1.  Install the required packages:
    ```bash
    pip install requests
    ```

2.  Run the main script:
    ```bash
    python src/main.py
    ```

    This will read questions from `data/input_questions.json`, find answers, and save them to `answers.json`.
