# Sample A2A Server

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


# Standardized A2A Envelope
class A2AMessage(BaseModel):
    sender: str
    receiver: str
    performative: str = Field(..., description="e.g., REQUEST, INFORM, PROPOSE")
    content: Dict[str, Any] = Field(..., description="The actual data or query")
    conversation_id: str


@app_api.post("/protocol/v1/message")
async def handle_a2a_request(envelope: A2AMessage):
    # 1. Protocol Translation
    # Convert A2A 'content' into something LangGraph understands
    query = envelope.content.get("query")

    # 2. Agent Execution
    config = {"configurable": {"thread_id": envelope.conversation_id}}
    result = await app.ainvoke({"messages": [("user", query)]}, config=config)

    # 3. Protocol Response
    # Instead of human text, return structured data for the calling agent
    return A2AMessage(
        sender="GraphRagAgent",
        receiver=envelope.sender,
        performative="INFORM",
        content={
            "data": result["messages"][-1].content,
            "status": "SUCCESS"
        },
        conversation_id=envelope.conversation_id
    )

@app_api.get("/protocol/v1/manifest")
async def get_manifest():
    return {
        "agent_id": "graphRagAgent",
        "capabilities": ["query_lineage", "check_compliance", "fetch_metadata"],
        "protocol": "A2A-v1.2"
    }