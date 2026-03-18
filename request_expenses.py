import asyncio
from agents.coordinator_agent import CoordinatorAgent

class MockContext:
    async def send(self, message):
        print(f"Bot Message: {message}")

async def main():
    coordinator = CoordinatorAgent()
    mock_ctx = MockContext()  # Create mock context
    await coordinator.finance_agent.request_monthly_expenses(mock_ctx)

asyncio.run(main())
