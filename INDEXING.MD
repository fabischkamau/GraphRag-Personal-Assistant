# GraphRAG Neo4j Integration Guide

This README explains how to use Microsoft GraphRAG to index your data and store it in Neo4j. The provided code sets up a Knowledge Graph database that can be used for question answering and information retrieval.

## Prerequisites

- Python 3.8+
- Neo4j database instance
- Microsoft GraphRAG
- Azure OpenAI account or OpenAI API key

## Setup

1. Install required packages:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/MacOS
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

2. Create your project folders:

```bash
mkdir -p ./ragtest/input
```

3. Place your data files in the `./ragtest/input` directory. For example:

```bash
curl https://www.gutenberg.org/cache/epub/24022/pg24022.txt -o ./ragtest/input/book.txt
```

## Configuration

1. Initialize GraphRAG:

```bash
graphrag init --root ./ragtest
```

2. Configure your environment variables in `.env` and `settings.yml` inside the `ragtest` folder:

### For Azure OpenAI Users:

```
AZURE_OPENAI_API_KEY=<your_azure_openai_api_key>
AZURE_OPENAI_API_KEY_EMBEDDINGS=<your_azure_openai_api_key>
AZURE_OPENAI_ENDPOINT=<your_azure_openai_endpoint>
```

### For Standard OpenAI Users:

```
OPENAI_API_KEY=<your_openai_api_key>
GRAPHRAG_API_KEY=<your_openai_api_key>
```

3. Configure your Neo4j database credentials in `knowledge_graph_creator.py`:

```python
DB_CONFIG = {
    "url": "bolt://your-neo4j-host:7687",
    "username": "neo4j",
    "password": "your-password",
    "database": "neo4j",
    "index_name": "entity"
}
```

4. Configure your settings.yaml:

### For Azure OpenAI Users:

```yaml
llm:
  type: azure_openai_chat
  api_base: https://<instance>.openai.azure.com
  api_version: 2024-02-15-preview
  deployment_name: <azure_model_deployment_name>

embeddings:
  type: azure_openai_embedding
  api_base: https://<instance>.openai.azure.com
  api_version: 2024-02-15-preview
  deployment_name: <azure_embedding_deployment_name>
```

### For Standard OpenAI Users:

```yaml
llm:
  type: openai_chat
  model: gpt-4-turbo
  api_key: ${GRAPHRAG_API_KEY}

embeddings:
  type: openai_embedding
  model: text-embedding-3-large
  dimensions: 3072
  api_key: ${GRAPHRAG_API_KEY}
```

## Modifying the Knowledge Graph Creator

To support standard OpenAI embeddings (instead of Azure), modify the `process_entity_embeddings` function in `knowledge_graph_creator.py`:

```python
def process_entity_embeddings(source="database", graph_folder=None):
    """
    Main function to process entity embeddings
    """
    print("Fetching entities...")

    # Check which embedding provider to use
    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "azure").lower()

    if embedding_provider == "azure":
        # Initialize Azure OpenAI Embeddings
        from langchain_openai import AzureOpenAIEmbeddings
        embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=os.getenv("AZURE_OPENAI_API_KEY_EMBEDDINGS"),
            # azure_endpoint will be read from AZURE_OPENAI_ENDPOINT env variable
        )
    else:
        # Initialize Standard OpenAI Embeddings
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            dimensions=3072,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    # Get entities either from database or parquet file
    if source == "database":
        entities = get_entities_from_database()
    else:
        entities = get_entities_from_parquet(graph_folder)

    if not entities:
        print("No entities found that need embeddings.")
        return

    print(f"Found {len(entities)} entities to process")

    # Process embeddings
    entity_embeddings = []

    for i, (entity_id, description) in enumerate(entities):
        if not description:
            continue

        try:
            # Generate embedding for the description
            embedding = embeddings.embed_query(description)
            entity_embeddings.append((entity_id, embedding))

            # Optional: Print progress
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(entities)} entities")

        except Exception as e:
            print(f"Error embedding entity {entity_id}: {str(e)}")

    # Update database with embeddings
    print(f"Updating database with {len(entity_embeddings)} embeddings...")
    batch_update_embeddings(entity_embeddings)

    print("Done!")
```

Make sure to update your imports at the top of the file:

```python
from dotenv import load_dotenv
# Remove the explicit import of AzureOpenAIEmbeddings from the top
# We'll import the appropriate embeddings class inside the function
```

And add a new environment variable to your `.env` file:

```
# Set to "azure" or "openai"
EMBEDDING_PROVIDER=openai
```

## Indexing Process

1. First, run GraphRAG to process your data:

```bash
graphrag index --root ./ragtest
```

2. After GraphRAG completes, it will generate Parquet files in the `./ragtest/output` directory.

3. Run the provided script to import the data into Neo4j:

```bash
python knowledge_graph_creator.py
```

## How It Works

The process has two main stages:

1. **GraphRAG Processing**:

   - Analyzes your input documents
   - Extracts entities, relationships, and communities
   - Creates embeddings for semantic search
   - Generates summary reports for each community
   - Outputs everything as Parquet files

2. **Neo4j Import** (using `knowledge_graph_creator.py`):
   - Creates necessary database constraints
   - Imports documents, text chunks, entities, relationships, and communities
   - Creates vector embeddings for semantic search
   - Establishes connections between all data elements

## Data Structure

The Neo4j database will contain:

- `__Document__` nodes: Source documents
- `__Chunk__` nodes: Text units from documents
- `__Entity__` nodes: Key concepts extracted from the text
- `__Community__` nodes: Clusters of related entities
- `RELATED` relationships: Connections between entities
- `IN_COMMUNITY` relationships: Entity memberships in communities
- `HAS_FINDING` relationships: Community insights

## Querying the Graph

Once imported, you can query your knowledge graph using Cypher:

```cypher
// Find entities related to a concept
MATCH (e:__Entity__ {name: "YourEntityName"})
RETURN e;

// Find all relationships for an entity
MATCH (e:__Entity__ {name: "YourEntityName"})-[r:RELATED]->(related)
RETURN e, r, related;

// Find semantic similarities with vector search
MATCH (e:__Entity__)
WHERE e.description IS NOT NULL
WITH e, gds.similarity.cosine(
  e.description_embedding,
  $embedding
) AS score
WHERE score > 0.7
RETURN e.name, score
ORDER BY score DESC
LIMIT 10;
```

## Troubleshooting

- If you encounter connection errors, verify your Neo4j credentials and check that the database is running.
- For embedding failures, check your API key and endpoint.
- Large documents may require batch processing; adjust the batch_size parameter if needed.
- If using OpenAI embeddings, ensure you have the correct API key and model name set.
- Make sure your Neo4j instance supports vector operations (Neo4j 5.11+ recommended).

## Next Steps

- Create a custom query interface for your knowledge graph
- Implement a RAG (Retrieval-Augmented Generation) system using this graph
- Set up scheduled updates to keep your knowledge graph current

For more information, refer to the Microsoft GraphRAG documentation and Neo4j documentation.
