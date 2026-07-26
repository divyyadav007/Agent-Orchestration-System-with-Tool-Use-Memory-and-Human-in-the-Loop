import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.specialists.research import ResearchSpecialist

if __name__ == "__main__":
    specialist = ResearchSpecialist()
    task = "Search for recent news about AI regulations and summarize top 3 findings."
    result = specialist.execute_task(task)
    print("Result:", result)
