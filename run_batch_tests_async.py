import sys
import os
import json
import asyncio
from pathlib import Path  # ✅ This fixes the NameError

sys.path.append("src")  # ✅ Tells Python where to find your crew

from oracle_epm_support.crew import build_crew


sys.path.append("src")  # 👈 This is crucial

from oracle_epm_support.crew import build_crew

# 🔧 Add this line to let Python find the src/ folder
sys.path.append("src")

# CONFIG
WAIT_BETWEEN = 4  # seconds between runs
OUTPUT_PATH = Path("logs/test_results.csv")
INPUT_PATH = Path("test_questions.json")

# Ensure logs/ exists
os.makedirs("logs", exist_ok=True)

# Load questions
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)

# Load CrewAI system
crew = build_crew()

async def run_test(index: int, question: str):
    print(f"🔍 [{index}/{len(questions)}] Question: {question}")
    try:
        response = crew.kickoff(inputs={"problem": question})
    except Exception as e:
        response = f"[ERROR] {e}"

    print(f"✅ Response: {str(response)[:250]}...\n{'-'*60}")

    # Append to CSV
    with open(OUTPUT_PATH, "a", encoding="utf-8") as out:
        q_clean = question.replace('"', '""')
        r_clean = str(response).replace('"', '""').replace("\n", " ")
        out.write(f'"{q_clean}","{r_clean}"\n')

    await asyncio.sleep(WAIT_BETWEEN)

async def main():
    # Write CSV header
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write("question,response\n")

    for i, q in enumerate(questions, 1):
        await run_test(i, q)

if __name__ == "__main__":
    asyncio.run(main())