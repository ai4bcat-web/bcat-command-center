from finance_agent import FinanceAgent
from tools.terminal_executor import run_terminal_command
try:
    import agent_registry as _registry
except Exception:
    _registry = None


class CoordinatorAgent:

    def __init__(self):
        self.finance_agent = FinanceAgent()
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

        # Finance questions — return a live summary from the finance agent
        if any(word in text for word in [
            "revenue", "profit", "margin", "carrier",
            "customer", "load", "ivan", "amazon"
        ]):
            try:
                self.finance_agent.ingest_data()
                brokerage = self.finance_agent.calculate_brokerage_metrics()
                from finance_agent import get_ivan_expense_metrics
                ivan = get_ivan_expense_metrics()
                total = float(brokerage.get("gross_revenue", 0)) + float(ivan.get("ivan_cartage_revenue", 0))
                if _registry:
                    _registry.set_status("CoordinatorAgent", "idle")
                return (
                    f"📊 BCAT Finance Summary\n"
                    f"Total Company Revenue: ${total:,.2f}\n"
                    f"Brokerage — Revenue: ${brokerage.get('gross_revenue', 0):,.2f} | "
                    f"Profit: ${brokerage.get('gross_profit', 0):,.2f} | "
                    f"Margin: {brokerage.get('margin_percentage', 0):.1f}%\n"
                    f"Ivan Cartage — Revenue: ${ivan.get('ivan_cartage_revenue', 0):,.2f} | "
                    f"Profit: ${ivan.get('ivan_true_profit', 0):,.2f}"
                )
            except Exception as e:
                if _registry:
                    _registry.set_status("CoordinatorAgent", "idle")
                return f"Could not load finance data: {e}"

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
