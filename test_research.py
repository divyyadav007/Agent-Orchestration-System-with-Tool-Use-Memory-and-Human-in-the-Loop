from src.core.specialists.research import ResearchSpecialist

specialist = ResearchSpecialist()
task = "Search for recent news about AI regulations and summarize top 3 findings."
result = specialist.execute_task(task)
print("Result:", result)