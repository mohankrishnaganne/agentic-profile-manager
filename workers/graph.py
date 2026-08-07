from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from workers.state import PortfolioState
from workers.agent_parser import parser_node, tool_node
from workers.agent_generator import generator_node
from workers.agent_deployer import deploy_node

def should_continue(state: PortfolioState):
    if state["messages"][-1].tool_calls:
        return "tools"
    return "generator"

workflow = StateGraph(PortfolioState)
workflow.add_node("parser", parser_node)
workflow.add_node("tools", tool_node)
workflow.add_node("generator", generator_node)
workflow.add_node("deployer", deploy_node)

workflow.add_edge(START, "parser")
workflow.add_conditional_edges("parser", should_continue, {"tools": "tools", "generator": "generator"})
workflow.add_edge("tools", "parser")
workflow.add_edge("generator", "deployer")
workflow.add_edge("deployer", END)

memory = MemorySaver()
portfolio_app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["deployer"]
)
