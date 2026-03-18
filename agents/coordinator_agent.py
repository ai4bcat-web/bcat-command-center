from finance_agent import FinanceAgent
from tools.terminal_executor import run_terminal_command
try:
    import agent_registry as _registry
except Exception:
    _registry = None


class CoordinatorAgent:

    def __init__(self):
        self.finance_agent = FinanceAgent()
        self.finance_agent.ingest_data('ivan_cartage_expenses.csv')
        if _registry:
            _registry.register("CoordinatorAgent", "Message routing and agent orchestration")

    # -----------------------------
    # Terminal Execution Tool
    # -----------------------------
    def run_terminal(self, command: str):
        """
        Allows OpenClaw to execute terminal commands.
        """
        try:
            result = run_terminal_command(command)
            return result
        except Exception as e:
            return {"error": str(e)}

    # -----------------------------
    # Message Routing
    # -----------------------------
    def handle(self, message: str, channel_name: str):
        if _registry:
            _registry.set_status("CoordinatorAgent", "busy", message[:80])

        text = message.lower().strip()

        # Finance questions
        if any(word in text for word in [
            "revenue",
            "profit",
            "margin",
            "carrier",
            "customer",
            "load",
            "ivan",
            "amazon"
        ]):
            return self.finance_agent.answer_question(text)

        # Terminal command execution
        if text.startswith("run:"):
            command = text.replace("run:", "").strip()
            result = self.run_terminal(command)

            if isinstance(result, dict):
                output = result.get("stdout", "") + result.get("stderr", "")
                return f"Terminal output:\n{output}"

            return str(result)

        # Finance channel commands
        if channel_name == "finance" and text.startswith("/input_expenses"):
            result = self.finance_agent.request_monthly_expenses()
            if _registry:
                _registry.set_status("CoordinatorAgent", "idle")
            return result

        if _registry:
            _registry.set_status("CoordinatorAgent", "idle")
