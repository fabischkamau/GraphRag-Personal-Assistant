from quart import Quart, request, jsonify
from quart_cors import cors
from uagents.crypto import Identity
from fetchai import fetch
from fetchai.registration import register_with_agentverse
from fetchai.communication import parse_message_from_agent, send_message_to_agent
import logging
import os
from dotenv import load_dotenv
import asyncio
from global_search_test import perform_global_search

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Quart(__name__)
app = cors(app)

# Initialising client identity to get registered on agentverse
client_identity = None

# Function to register agent
def init_client():
    """Initialize and register the client agent."""
    global client_identity
    try:
        # Load the agent secret key from environment variables
        client_identity = Identity.from_seed(os.getenv("GLOBAL_AGENT_SECRET_KEY"), 0)
        logger.info(f"Client agent started with address: {client_identity.address}")

        readme = """
        ![domain:innovation-lab](https://img.shields.io/badge/innovation--lab-3D8BD3)
        domain:knowledge-graph-rag-agent

        <description>
        This Agent uses Graph-based Retrieval Augmented Generation (GraphRAG) to provide intelligent answers about products and services. Upon receiving a query message with database configuration, the agent retrieves information from a knowledge graph in Neo4j, processes relationships between entities, and generates comprehensive responses using Azure OpenAI.
        </description>

        <use_cases>
            <use_case>To provide intelligent product recommendations based on a knowledge graph of product relationships and attributes.</use_case>
            <use_case>To answer complex queries that require understanding relationships between different products, features, and categories.</use_case>
            <use_case>To support decision-making by analyzing connections between products and user preferences stored in a knowledge graph.</use_case>
        </use_cases>

        <payload_requirements>
        <description>This agent expects a payload with a query message and database configuration.</description>
        <payload>
            <requirement>
                <parameter>input</parameter>
                <description>A query string that will be processed against the knowledge graph.</description>
            </requirement>
            <requirement>
                <parameter>db_config</parameter>
                <description>Database configuration object containing url, username, password, and index_name for Neo4j.</description>
            </requirement>
        </payload>
        </payload_requirements>

        ![tag : innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
        """

        # Register the agent with Agentverse
        register_with_agentverse(
            identity=client_identity,
            url="http://localhost:5002/webhook",
            agentverse_token=os.getenv("AGENTVERSE_API_KEY"),
            agent_title="GraphRag Global Assistant",
            readme=readme
        )

        logger.info("Knowledge Graph RAG agent registration complete!")

    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise

# app route to receive the messages from other agents
@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming messages"""
    global client_identity
    try:
        # Parse the incoming webhook message
        data = await request.get_data()
        data = data.decode("utf-8")
        logger.info("Received query")

        message = parse_message_from_agent(data)
        message_payload = message.payload
        agent_address = message.sender
        input_query = message_payload.get("input")
        db_config = message_payload.get("db_config")
        
        # Validate required payload fields
        if not input_query:
            logger.error("Missing input query in payload")
            return jsonify({"error": "Missing input query in payload"}), 400
            
        if not db_config or not all(key in db_config for key in ["url", "username", "password"]):
            logger.error("Missing or incomplete db_config in payload")
            return jsonify({"error": "db_config must contain url, username, password, and index_name"}), 400
        
        logger.info(f"Received query from {agent_address}")
        logger.info(f"Query: {input_query}")
        
        # Process the query using GraphRAG - properly await the result
        search_results = await perform_global_search(
            db_config=db_config,
            query=input_query,
        )
        
        # Prepare the response payload
        payload = {
            "output": search_results,
            "source": "global_search"
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
    
    # Run with hypercorn or another ASGI server
    import hypercorn.asyncio
    import hypercorn.config
    
    config = hypercorn.config.Config()
    config.bind = ["0.0.0.0:5002"]  
    asyncio.run(hypercorn.asyncio.serve(app, config))