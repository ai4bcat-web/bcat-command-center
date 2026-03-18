from finance_agent import FinanceAgent

agent = FinanceAgent(local_data_path=".")
agent.ingest_data()

while True:
    question = input("Ask your finance agent a question (or type 'quit'): ")

    if question.lower() == "quit":
        break

    answer = agent.answer_question(question)
    print("Answer:", answer)
    print()
