import os
import re
import time
from typing import TypedDict, List, Dict, Any
from neo4j import GraphDatabase
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.llm import OpenAILLM

# =========================================================
# CONFIG
# =========================================================

NEO4J_URI = "bolt+ssc://7b053b5c.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "ksC9hrbgmB73zh4y60m9FWs95EH-W1SgmpLUNocYl_o"

# Change with Claude as per Need basis
GROQ_MODEL = ""
GROQ_API_KEY = ""

if not GROQ_API_KEY:
    raise ValueError("Set GROQ_API_KEY environment variable")


# =========================================================
# Commented
# =========================================================

# from neo4j import GraphDatabase
#
# # Demo database credentials
# URI = "neo4j+s://demo.neo4jlabs.com"
# AUTH = ("recommendations", "recommendations")
#
# # Connect to Neo4j database
# driver = GraphDatabase.driver(URI, auth=AUTH)



# =========================================================
# STATE
# =========================================================

class GraphState(TypedDict):
    user_query: str
    intent: str
    ontology: Dict[str, Any]
    cypher_query: str
    graph_result: List[Dict[str, Any]]
    compressed_context: str
    final_answer: str

# =========================================================
# NEO4J TOOL
# =========================================================

class Neo4jTool:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run(self, query: str, params: dict = None):
        with self.driver.session() as session:
            result = session.run(query, params or {}, timeout=5000)
            return [record.data() for record in result]

    def close(self):
        self.driver.close()

neo = Neo4jTool(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

# =========================================================
# LLM (Groq)
# =========================================================

llm = ChatOpenAI(
    model=GROQ_MODEL,
    openai_api_key=GROQ_API_KEY,
    openai_api_base="https://api.groq.com/openai/v1",
    temperature=0
)

# =========================================================
# APOC SCHEMA CACHE
# =========================================================

SCHEMA_CACHE = None

def fetch_ontology(state: GraphState):
    global SCHEMA_CACHE

    if SCHEMA_CACHE:
        state["ontology"] = SCHEMA_CACHE
        return state

    result = neo.run("CALL apoc.meta.schema()")

    schema_data = result[0]["value"]

    labels = []
    relationships = []
    properties = {}

    for key, value in schema_data.items():

        if value["type"] == "node":
            labels.append(key)
            properties[key] = list(value.get("properties", {}).keys())

        elif value["type"] == "relationship":
            relationships.append(key)

    SCHEMA_CACHE = {
        "labels": labels,
        "relationships": relationships,
        "properties": properties
    }

    state["ontology"] = SCHEMA_CACHE
    return state

# =========================================================
# INTENT
# =========================================================

def detect_intent(state: GraphState):
    prompt = f"""
    Classify the intent of:
    {state['user_query']}

    Options:
    - lineage
    - impact
    - dependency
    - rca
    - generic
    """

    state["intent"] = llm.invoke(prompt).content.strip()
    return state

# =========================================================
# GENERATE CYPHER
# =========================================================

def generate_cypher(state: GraphState):
    ontology = state["ontology"]

    # Format relationships for the LLM to understand start/end points if possible
    prompt = f"""
    You are a Neo4j Cypher expert. 
    Your goal is to convert a user's question into a valid, READ-ONLY Cypher query.

    [SCHEMA]
    Node Labels: {ontology['labels']}
    Relationship Types: {ontology['relationships']}
    Properties by Label: {ontology['properties']}

    [RULES]
    1. Use ONLY the labels and relationships provided above.
    2. If direction is unknown, use undirected: (a)-[:RELATIONSHIP]-(b)
    3. For variable-length paths, use: -[*1..3]-
    4. Always use aliases for nodes and relationships, e.g., MATCH (n:Label)-[r:REL]->(m:Other)
    5. Return ONLY the raw Cypher query, no explanation or markdown.

    [EXAMPLES]
    - Single Node: "Find person Rahul" -> MATCH (n:Person) WHERE n.name = 'Rahul' RETURN n
    - Relationship: "What projects does Rahul work on?" -> MATCH (p:Person {{name: 'Rahul'}})-[:WORKS_ON]->(proj:Project) RETURN proj

    User Query: {state['user_query']}
    Intent: {state['intent']}
    """

    response = llm.invoke(prompt).content.strip()
    # Clean output
    response = re.sub(r'```cypher|```', '', response).strip()
    state["cypher_query"] = response
    return state


# =========================================================
# CYPHER VALIDATION (APOC-based schema)
# =========================================================

def validate_cypher(state: GraphState):

    query = state["cypher_query"]
    query_clean = query.strip().lower()

    # Must contain MATCH
    if "match" not in query_clean:
        raise ValueError("Query must contain MATCH clause")

    # Block write operations
    forbidden = ["create", "merge", "delete", "set", "drop", "remove"]
    if any(word in query_clean for word in forbidden):
        raise ValueError("Write operations not allowed")

    # Validate labels
    labels_used = re.findall(r"\(\w*:(\w+)", query)
    for label in labels_used:
        if label not in state["ontology"]["labels"]:
            raise ValueError(f"Invalid label used: {label}")

    # Validate relationships
    rels_used = re.findall(r"\[:(\w+)", query)
    for rel in rels_used:
        if rel not in state["ontology"]["relationships"]:
            raise ValueError(f"Invalid relationship used: {rel}")

    # Validate properties safely
    props_used = re.findall(r"\b\w+\.(\w+)", query)

    for prop in props_used:
        valid = any(
            prop in props
            for props in state["ontology"]["properties"].values()
        )
        if not valid:
            raise ValueError(f"Invalid property used: {prop}")

    return state

# =========================================================
# EXECUTE
# =========================================================

def execute_query(state: GraphState):
    start = time.time()
    result = neo.run(state["cypher_query"])
    duration = time.time() - start

    print("Generated Cypher:", state["cypher_query"])
    print("Execution Time:", duration)

    state["graph_result"] = result
    return state

# =========================================================
# BASELINE GRAPHRAG component
# =========================================================


#
# # Create LLM object
# t2c_llm = OpenAILLM(model_name="gpt-3.5-turbo")
#
# # (Optional) Specify your own Neo4j schema
# neo4j_schema = """
#   Node properties:
#   Person {name: STRING, born: INTEGER}
#   Movie {tagline: STRING, title: STRING, released: INTEGER}
#   Relationship properties:
#   ACTED_IN {roles: LIST}
#   REVIEWED {summary: STRING, rating: INTEGER}
#   The relationships:
#   (:Person)-[:ACTED_IN]->(:Movie)
#   (:Person)-[:DIRECTED]->(:Movie)


# =========================================================
# COMPRESS
# =========================================================

def compress_graph(state: GraphState):

    results = state["graph_result"]

    if not results:
        state["compressed_context"] = "No data found."
        return state

    structured = [str(record) for record in results[:50]]
    state["compressed_context"] = "\n".join(structured)
    return state

# =========================================================
# FINAL ANSWER
# =========================================================

def generate_answer(state: GraphState):

    prompt = f"""
    Question:
    {state['user_query']}

    Graph Data:
    {state['compressed_context']}

    Provide structured explanation.
    """

    state["final_answer"] = llm.invoke(prompt).content
    return state

# =========================================================
# LANGGRAPH WORKFLOW
# =========================================================

workflow = StateGraph(GraphState)

workflow.add_node("ontology", fetch_ontology)
workflow.add_node("intent", detect_intent)
workflow.add_node("cypher", generate_cypher)
workflow.add_node("validate", validate_cypher)
workflow.add_node("query", execute_query)
workflow.add_node("compress", compress_graph)
workflow.add_node("answer", generate_answer)

workflow.set_entry_point("ontology")

workflow.add_edge("ontology", "intent")
workflow.add_edge("intent", "cypher")
workflow.add_edge("cypher", "validate")
workflow.add_edge("validate", "query")
workflow.add_edge("query", "compress")
workflow.add_edge("compress", "answer")
workflow.add_edge("answer", END)

app = workflow.compile()

# =========================================================
# PUBLIC FUNCTION
# =========================================================

def ask_graph(question: str):
    result = app.invoke({"user_query": question})
    return result["final_answer"]