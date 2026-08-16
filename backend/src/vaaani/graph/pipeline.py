from langgraph.graph import END, START, StateGraph

from vaaani.graph.nodes import PipelineNodes
from vaaani.graph.state import GraphState


def _as_update(node):  # type: ignore[no-untyped-def]
    async def update(state: GraphState) -> dict:  # type: ignore[type-arg]
        result = await node(state)
        return {key: value for key, value in result.items() if value != state.get(key)}

    return update


async def _after_topic(state: GraphState) -> str:
    return "refuse" if state["refused"] else "continue"


async def _after_confidence(state: GraphState) -> str:
    return "refuse" if state["refused"] else "continue"


async def _after_groundedness(state: GraphState) -> str:
    return "refuse" if state["refused"] else "continue"


def build_pipeline(nodes: PipelineNodes):  # type: ignore[no-untyped-def]
    builder = StateGraph(GraphState)
    builder.add_node("stt", _as_update(nodes.stt_node))
    builder.add_node("classify", _as_update(nodes.query_classify_node))
    builder.add_node("rewrite", _as_update(nodes.query_rewrite_node))
    builder.add_node("retrieve", _as_update(nodes.retrieve_node))
    builder.add_node("rerank", _as_update(nodes.rerank_node))
    builder.add_node("confidence_gate", _as_update(nodes.confidence_gate_node))
    builder.add_node("generate", _as_update(nodes.generate_node))
    builder.add_node("groundedness", _as_update(nodes.groundedness_check_node))
    builder.add_node("refuse", _as_update(nodes.refuse_node))
    builder.add_node("tts", _as_update(nodes.tts_node))
    builder.add_node("response", _as_update(nodes.response_node))

    builder.add_edge(START, "stt")
    builder.add_edge("stt", "classify")
    builder.add_conditional_edges(
        "classify", _after_topic, {"refuse": "refuse", "continue": "rewrite"}
    )
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("retrieve", "rerank")
    builder.add_edge("rerank", "confidence_gate")
    builder.add_conditional_edges(
        "confidence_gate", _after_confidence, {"refuse": "refuse", "continue": "generate"}
    )
    builder.add_edge("generate", "groundedness")
    builder.add_conditional_edges(
        "groundedness", _after_groundedness, {"refuse": "refuse", "continue": "tts"}
    )
    builder.add_edge("refuse", "response")
    builder.add_edge("tts", "response")
    builder.add_edge("response", END)
    return builder.compile()
