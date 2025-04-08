from flask_cors import CORS
from uagents.crypto import Identity
from fetchai import fetch
from fetchai.registration import register_with_agentverse
from fetchai.communication import parse_message_from_agent, send_message_to_agent
import logging
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)


client_identity = None
global_response = None

def init_client():
   """Initialize and register the client agent."""
   global client_identity
   try:
       # Load the client identity from environment variables
       client_identity = Identity.from_seed(os.getenv("USER_AGENT_SECRET_KEY"), 0)
       logger.info(f"Client agent started with address: {client_identity.address}")

       # Define the client agent's metadata
       readme = """
        ![domain:knowledge-discovery](https://img.shields.io/badge/knowledge--discovery-3D8BD3)  
        domain:graphrag-frontend-agent

        <description>
        This agent serves as an intelligent frontend for Graph-based Retrieval Augmented Generation (GraphRAG) that dynamically selects between local entity-focused searches and global knowledge graph exploration based on query characteristics. It analyzes incoming queries to determine the optimal search strategy - directing entity-specific questions to the local GraphRAG engine for precision and broader conceptual questions to the global GraphRAG engine for comprehensive coverage. The agent then unifies responses into coherent, contextually rich answers that leverage the Neo4j knowledge graph structure.
        </description>

        <use_cases>
            <use_case>To intelligently route user queries to either local or global GraphRAG engines based on query type and content needs.</use_case>
            <use_case>To provide unified responses by combining entity-specific details with broader conceptual understanding from the knowledge graph.</use_case>
            <use_case>To optimize search efficiency by matching query intent with the appropriate GraphRAG strategy (local vs global).</use_case>
            <use_case>To serve as a single access point for all knowledge graph queries regardless of scope or specificity.</use_case>
        </use_cases>

        <payload_requirements>
        <description>This agent expects a payload with a query message that will be analyzed and routed.</description>
        <payload>
            <requirement>
                <parameter>input</parameter>
                <description>The user query to be processed against the knowledge graph.</description>
            </requirement>
            <requirement>
                <parameter>db_config</parameter>
                <description>Database configuration object containing url, username, password, and index_name for Neo4j.</description>
            </requirement>
            <requirement>
                <parameter>response_format</parameter>
                <description>Optional. Desired format for the response (default: "multiple paragraphs").</description>
            </requirement>
        </payload>
        </payload_requirements>

        ![tag:graphrag](https://img.shields.io/badge/graphrag-3D8BD3)
        ![tag:neo4j](https://img.shields.io/badge/neo4j-3D8BD3)
        ![tag:query-routing](https://img.shields.io/badge/query--routing-3D8BD3)
       """

       # Register the agent with Agentverse
       register_with_agentverse(
           identity=client_identity,
           url="http://localhost:5005/api/webhook",
           agentverse_token=os.getenv("AGENTVERSE_API_KEY"),
           agent_title="User agent for Stock Price check",
           readme=readme
       )

       logger.info("Client agent registration complete!")

   except Exception as e:
       logger.error(f"Initialization error: {e}")
       raise

# searching the agents which can create dashboard on agentverse
@app.route('/api/search-agents', methods=['GET'])
def search_agents():
   """Search for available dashboard agents based on user input."""
   try:
       # Extract user input from query parameters
       user_query = request.args.get('query', '')
       if not user_query:
           return jsonify({"error": "Query parameter 'query' is required."}), 400

       # Fetch available agents based on user query
       available_ais = fetch.ai(user_query)  # Pass the user query to the fetch.ai function
       print(f'---------------------{available_ais}----------------------')

       # Access the 'ais' list within 'agents' (assuming fetch.ai returns the correct structure)
       agents = available_ais.get('ais', [])
       print(f'----------------------------------{agents}------------------------------------')

       extracted_data = []
       for agent in agents:
           name = agent.get('name')  # Extract agent name
           address = agent.get('address')

           # Append formatted data to extracted_data list
           extracted_data.append({
               'name': name,
               'address': address,
           })

       # Format the response with indentation for readability
       response = jsonify(extracted_data)
       response.headers.add('Content-Type', 'application/json; charset=utf-8')
       response.headers.add('Access-Control-Allow-Origin', '*')
       response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
       return response, 200

   except Exception as e:
       logger.error(f"Error finding agents: {e}")
       return jsonify({"error": str(e)}), 500

@app.route('/api/send-data', methods=['POST'])
def send_data():
   """Send payload to the selected agent based on provided address."""
   global agent_response
   agent_response = None

   try:
       # Parse the request payload
       data = request.json
       payload = data.get('payload')  # Extract the payload dictionary
       agent_address = data.get('agentAddress')  # Extract the agent address

       # Validate the input data
       if not payload or not agent_address:
           return jsonify({"error": "Missing payload or agent address"}), 400

       logger.info(f"Sending payload to agent: {agent_address}")
       logger.info(f"Payload: {payload}")

       # Send the payload to the specified agent
       send_message_to_agent(
           client_identity,  # Frontend client identity
           agent_address,    # Agent address where we have to send the data
           payload           # Payload containing the data
       )

       return jsonify({"status": "request_sent", "agent_address": agent_address, "payload": payload})

   except Exception as e:
       logger.error(f"Error sending data to agent: {e}")
       return jsonify({"error": str(e)}), 500


# app route to get recieve the messages on the agent
@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle incoming messages from the dashboard agent."""
    global agent_response
    try:
        # Parse the incoming webhook message
        data = request.get_data().decode("utf-8")
        logger.info("Received response")

        message = parse_message_from_agent(data)
        agent_response = message.payload

        logger.info(f"Processed response: {agent_response}")
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-response', methods=['GET'])
def get_response():
    global agent_response
    try:
        if agent_response:
            response = agent_response
            print(f'payload: {response}')
            agent_response = None  # Clear the response after sending
            
            keys = list(response.keys())  # Convert dict_keys to a list
            first_key = keys[0]           # Get the first key
            second_key = keys[1]          # Get the second key
            output = response.get(first_key, "")
            source = response.get(second_key, "")
            logger.info(f"Got response from {source}: {output}")
            return jsonify({"output": output, "source": source})
        else:
            return jsonify({"error": "No response available"}), 404

    except Exception as e:
        logger.error(f"Error getting response: {e}")
        return jsonify({"error": str(e)}), 500

# function to start the flask server
def start_server():
    """Start the Flask server."""
    try:
        # Load environment variables
        load_dotenv()
        init_client()
        app.run(host="0.0.0.0", port=5005)
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    start_server()