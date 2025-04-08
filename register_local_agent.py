from flask import Flask, request, jsonify
from flask_cors import CORS
from uagents.crypto import Identity
from fetchai.registration import register_with_agentverse
from fetchai.communication import parse_message_from_agent, send_message_to_agent
import logging
import os
from dotenv import load_dotenv
import asyncio
from local_search import local_search

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)

# Initialising client identity to get registered on agentverse
client_identity = None

# Function to register agent
def init_client():
    """Initialize and register the client agent."""
    global client_identity
    try:
        # Load the agent secret key from environment variables
        client_identity = Identity.from_seed(os.getenv("LOCAL_AGENT_SECRET_KEY"), 0)
        logger.info(f"Local search agent started with address: {client_identity.address}")

        readme = """
        ![domain:knowledge-discovery](https://img.shields.io/badge/knowledge--discovery-3D8BD3)
        domain:entity-focused-rag-agent

        <description>
        The Entity-Focused RAG Agent specializes in targeted knowledge retrieval around specific entities within a Neo4j knowledge graph. Unlike global search agents that traverse the entire graph, this agent conducts focused, high-precision searches by exploring entity neighborhoods, retrieving relevant text chunks, entity relationships, and community connections. It excels at providing detailed answers about specific entities, their properties, and immediate relationships, making it ideal for domain-specific knowledge exploration and entity-centric analysis.
        </description>

        <use_cases>
            <use_case>To answer specific questions about individual entities, their attributes, and direct relationships within a knowledge domain.</use_case>
            <use_case>To provide detailed explanations of how entities relate to their immediate network of connections in the knowledge graph.</use_case>
            <use_case>To extract relevant text passages and summarize information specifically about named entities rather than broader concepts.</use_case>
            <use_case>To support precise entity resolution and disambiguation by focusing on the unique properties of specific nodes in the graph.</use_case>
        </use_cases>

        <payload_requirements>
        <description>This agent expects a payload with a query message and database configuration.</description>
        <payload>
            <requirement>
                <parameter>input</parameter>
                <description>A query string focused on specific entities to search within the knowledge graph.</description>
            </requirement>
            <requirement>
                <parameter>db_config</parameter>
                <description>Database configuration object containing url, username, password, and index_name for Neo4j.</description>
            </requirement>
            <requirement>
                <parameter>top_k</parameter>
                <description>Optional. Number of entities to retrieve (default: 5).</description>
            </requirement>
        </payload>
        </payload_requirements>

        ![tag:entity-search](https://img.shields.io/badge/entity--search-3D8BD3)
        ![tag:neo4j](https://img.shields.io/badge/neo4j-3D8BD3)
        """

        # Register the agent with Agentverse
        register_with_agentverse(
            identity=client_identity,
            url="http://localhost:5003/webhook",
            agentverse_token=os.getenv("AGENTVERSE_API_KEY"),
            agent_title="GraphRag Entity-Focused Assistant",
            readme=readme
        )

        logger.info("Entity-Focused RAG agent registration complete!")

    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise

# app route to receive the messages from other agents
@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming messages"""
    global client_identity
    try:
        # Parse the incoming webhook message
        data = request.get_data().decode("utf-8")
        logger.info("Received entity search query")

        message = parse_message_from_agent(data)
        message_payload = message.payload
        agent_address = message.sender
        input_query = message_payload.get("input")
        db_config = message_payload.get("db_config")
        top_k = message_payload.get("top_k", 5)
        
        # Validate required payload fields
        if not input_query:
            logger.error("Missing input query in payload")
            return jsonify({"error": "Missing input query in payload"}), 400
            
        if not db_config or not all(key in db_config for key in ["url", "username", "password", "index_name"]):
            logger.error("Missing or incomplete db_config in payload")
            return jsonify({"error": "db_config must contain url, username, password, and index_name"}), 400
        
        logger.info(f"Received entity query from {agent_address}")
        logger.info(f"Query: {input_query}")
        logger.info(f"Using database: {db_config['url']} with index: {db_config['index_name']}")
        
        # Process the query using local search functionality
        search_results = local_search(
            neo4j_config=db_config,
            query=input_query,
        )
        
        # Prepare the response payload
        payload = {
            "output": search_results,
            "source": "entity_focused_search"
        }
        
        logger.info(f"Sending response to agent: {agent_address}")
        send_message_to_agent(client_identity, agent_address, payload)
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    load_dotenv()       # Load environment variables
    init_client()       # Register your agent on Agentverse
    app.run(host="0.0.0.0", port=5003)