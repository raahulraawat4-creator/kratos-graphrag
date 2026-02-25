This README is designed for a professional architect's portfolio. It covers the technical stack you've built: **LangGraph**, **Neo4j**, and a **FastAPI** A2A (Agent-to-Agent) layer, with a **Streamlit** frontend for human interaction.

---

# : Agentic GraphRAG Framework

 **GraphRAG** (Retrieval-Augmented Generation) engine that leverages **Neo4j** for structured knowledge and **LangGraph** for autonomous agentic reasoning. It exposes a dual interface: a **Streamlit UI** for human operators and an **A2A Server** for machine-to-machine protocol communication.

## 🏗️ Architecture Overview

The system is built on a "Reason-Act" (ReAct) loop that allows the agent to navigate complex graph ontologies dynamically.

### Core Components

1. **The Architect (LangGraph Agent):** A cyclic state machine that manages conversation history and decides which tools to invoke based on user intent.
2. **Schema Tool (APOC Meta):** Uses `apoc.meta.graph()` to provide the agent with real-time "triplets" (Node-Relationship-Node), ensuring the agent understands the graph's topology before writing queries.
3. **Cypher Executor:** A protected tool that executes read-only Cypher queries and handles self-correction if the database returns an error.
4. **A2A Protocol Layer:** A FastAPI server that wraps the agent in a structured messaging envelope (sender, receiver, performative, content) for autonomous inter-agent communication.

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* Neo4j Database (with APOC plugin installed)

### Installation
```
pip install neo4j-graphrag neo4j openai

```

### 2. Environment Setup

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_key_here
NEO4J_URI=bolt+ssc://your_db_id.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

```

---

## 🛠️ Running the Application

### Option A: Streamlit UI (Human-to-Agent)

Best for testing, debugging, and visualizing the graph reasoning.

```bash
streamlit run app_ui.py

```

### Option B: A2A Server (Agent-to-Agent)

Exposes a standardized protocol endpoint for other autonomous services to call.

```bash
python a2a_server.py

```

---

## 📋 A2A Protocol Specification

To communicate with this agent programmatically, send a `POST` request to `/protocol/v1/message`:

**Request Body:**

```json
{
  "sender": "external_agent_id",
  "receiver": "_agent",
  "performative": "REQUEST",
  "content": {
    "query": "Identify all DataProducts owned by 'Sales' domain."
  },
  "conversation_id": "uuid-1234"
}

```

**Response:**
Returns a structured `INFORM` performative containing the graph data extracted and summarized by the agent.

---

## 🧩 GraphRAG Agent Logic Flow

The agent operates in a four-stage cycle:

1. **Ontology Extraction:** Calls the Schema Tool to see valid relationship paths.
2. **Cypher Generation:** Writes a query based on the retrieved schema and user query.
3. **Execution & Validation:** Runs the query against Neo4j. If it fails, the error is fed back into the agent for a second attempt.
4. **A2A Packaging:** The final result is cleaned of conversational "fluff" and returned as structured data.

---

Would you like me to help you generate the **`requirements.txt`** file based on the libraries we've used?