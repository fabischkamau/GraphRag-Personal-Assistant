import os
import time
from typing import List, Dict
import pandas as pd
from neo4j import GraphDatabase, Result
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "url": "bolt://your-neo4j-host:7687",
    "username": "neo4j",
    "password": "your-password",
    "database": "neo4j",
    "index_name": "entity"
}

def db_query(cypher: str, params: Dict = {}) -> pd.DataFrame:
    """Executes a Cypher statement and returns a DataFrame"""
    driver = GraphDatabase.driver(DB_CONFIG["url"], auth=(DB_CONFIG["username"], DB_CONFIG["password"]))
    return driver.execute_query(
        cypher, parameters_=params, result_transformer_=Result.to_df
    )
driver = GraphDatabase.driver(DB_CONFIG["url"], auth=(DB_CONFIG["username"], DB_CONFIG["password"]))

def batched_import(statement: str, df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Import a dataframe into Neo4j using a batched approach.

    Args:
        statement (str): The Cypher query to execute.
        df (pd.DataFrame): The dataframe to import.
        batch_size (int): The number of rows to import in each batch.

    Returns:
        int: Total number of rows imported.
    """
    total = len(df)
    start_time = time.time()
    for start in range(0, total, batch_size):
        batch = df.iloc[start:min(start + batch_size, total)]
        result = driver.execute_query(
            "UNWIND $rows AS value " + statement,
            rows=batch.to_dict('records'),
            database_=DB_CONFIG["database"]
        )
        print(result.summary.counters)
    print(f'{total} rows imported in {time.time() - start_time:.2f} seconds.')
    return total

def create_constraints():
    """Create necessary constraints in the database."""
    statements = [
        "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:__Chunk__) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:__Document__) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (c:__Community__) REQUIRE c.community IS UNIQUE",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:__Entity__) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT entity_title IF NOT EXISTS FOR (e:__Entity__) REQUIRE e.name IS UNIQUE",
        "CREATE CONSTRAINT entity_title IF NOT EXISTS FOR (e:__Covariate__) REQUIRE e.title IS UNIQUE",
        "CREATE CONSTRAINT related_id IF NOT EXISTS FOR ()-[rel:RELATED]->() REQUIRE rel.id IS UNIQUE"
    ]

    for statement in statements:
        print(f"Executing: {statement}")
        driver.execute_query(statement)

def import_documents(graph_folder: str):
    """Import documents into the database."""
    doc_df = pd.read_parquet(f'{graph_folder}/output/documents.parquet', columns=["id", "title"])
    statement = """
    MERGE (d:__Document__ {id: value.id})
    SET d += value {.title}
    """
    batched_import(statement, doc_df)

def import_text_units(graph_folder: str):
    """Import text units into the database."""
    text_df = pd.read_parquet(f'{graph_folder}/output/text_units.parquet',
                              columns=["id", "text", "n_tokens", "document_ids"])
    statement = """
    MERGE (c:__Chunk__ {id: value.id})
    SET c += value {.text, .n_tokens}
    WITH c, value
    UNWIND value.document_ids AS document
    MATCH (d:__Document__ {id: document})
    MERGE (c)-[:PART_OF]->(d)
    """
    batched_import(statement, text_df)

def import_entities(graph_folder: str):
    """Import entities into the database."""
    entity_df = pd.read_parquet(f'{graph_folder}/output/entities.parquet',
                                columns=["id", "human_readable_id", "title", "type", "description", "text_unit_ids"])
    entity_statement = """
    MERGE (e:__Entity__ {id: value.id})
    SET e += value {.human_readable_id, .description, name: replace(value.title, '"', '')}
    WITH e, value
    CALL apoc.create.addLabels(e, CASE WHEN coalesce(value.type, "") = "" THEN [] ELSE [apoc.text.upperCamelCase(replace(value.type, '"', ''))] END) YIELD node
    UNWIND value.text_unit_ids AS text_unit
    MATCH (c:__Chunk__ {id: text_unit})
    MERGE (c)-[:HAS_ENTITY]->(e)
    """
    batched_import(entity_statement, entity_df)

def import_relationships(graph_folder: str):
    """Import relationships into the database."""
    rel_df = pd.read_parquet(f'{graph_folder}/output/relationships.parquet',
                             columns=["id", "human_readable_id", "source", "target", "description", "weight", "text_unit_ids"])
    rel_statement = """
    MATCH (source:__Entity__ {name: replace(value.source, '"', '')})
    MATCH (target:__Entity__ {name: replace(value.target, '"', '')})
    MERGE (source)-[rel:RELATED {id: value.id}]->(target)
    SET rel += value {.weight, .human_readable_id, .description, .text_unit_ids}
    RETURN count(*) AS createdRels
    """
    batched_import(rel_statement, rel_df)

def import_communities(graph_folder: str):
    """Import communities into the database."""
    community_df = pd.read_parquet(f'{graph_folder}/output/communities.parquet',
                                   columns=["id", "level", "title", "text_unit_ids", "relationship_ids"])
    statement = """
    MERGE (c:__Community__ {community: value.id})
    SET c += value {.level, .title}
    WITH *
    UNWIND value.relationship_ids AS rel_id
    MATCH (start:__Entity__)-[:RELATED {id: rel_id}]->(end:__Entity__)
    MERGE (start)-[:IN_COMMUNITY]->(c)
    MERGE (end)-[:IN_COMMUNITY]->(c)
    RETURN count(DISTINCT c) AS createdCommunities
    """
    batched_import(statement, community_df)

def import_community_reports(graph_folder: str):
    """Import community reports into the database."""
    community_report_df = pd.read_parquet(f'{graph_folder}/output/community_reports.parquet',
                                          columns=["id", "community", "level", "title", "summary", "findings", 
                                                  "rank", "rating_explanation", "full_content"])
    community_statement = """
    MERGE (c:__Community__ {community: value.community})
    SET c += value {.level, .title, .rank, rating_explanation: value.rating_explanation, .full_content, .summary}
    WITH c, value
    UNWIND range(0, size(value.findings)-1) AS finding_idx
    WITH c, value, finding_idx, value.findings[finding_idx] AS finding
    MERGE (c)-[:HAS_FINDING]->(f:Finding {id: finding_idx})
    SET f += finding
    """
    batched_import(community_statement, community_report_df)

def create_vector_index():
    db_query(
        """
    CREATE VECTOR INDEX """
        + DB_CONFIG["index_name"]
        + """ IF NOT EXISTS FOR (e:__Entity__) ON e.description_embedding
    OPTIONS {indexConfig: {
    `vector.dimensions`: 3072,
    `vector.similarity_function`: 'cosine'
    }}
    """
)

def get_entities_from_database():
    """
    Fetch entities from Neo4j database that need embeddings
    Returns a list of (id, description) tuples
    """
    with driver.session(database=DB_CONFIG["database"]) as session:
        result = session.run(
            """
            MATCH (e:__Entity__)
            WHERE e.description IS NOT NULL AND e.description_embedding IS NULL
            RETURN e.id AS id, e.description AS description
            LIMIT 1000
            """
        )
        return [(record["id"], record["description"]) for record in result]

def get_entities_from_parquet(graph_folder):
    """
    Alternative: Read entities from parquet file
    """
    entity_df = pd.read_parquet(
        f'{graph_folder}/output/entities.parquet',
        columns=["id", "description"]
    )
    return [(row.id, row.description) for _, row in entity_df.iterrows() if row.description]

def update_entity_embeddings(entity_id, embedding):
    """
    Update a single entity with its embedding in Neo4j
    """
    with driver.session(database=DB_CONFIG["database"]) as session:
        result = session.run(
            """
            MATCH (e:__Entity__ {id: $id})
            SET e.description_embedding = $embedding
            RETURN e.id
            """,
            id=entity_id,
            embedding=embedding
        )
        return result.single()

def batch_update_embeddings(entity_embeddings, batch_size=100):
    """
    Batch update entities with embeddings
    """
    total = len(entity_embeddings)
    start_time = time.time()
    
    for i in range(0, total, batch_size):
        batch = entity_embeddings[i:min(i + batch_size, total)]
        
        with driver.session(database=DB_CONFIG["database"]) as session:
            result = session.run(
                """
                UNWIND $batch AS item
                MATCH (e:__Entity__ {id: item.id})
                SET e.description_embedding = item.embedding
                RETURN count(*) as updated
                """,
                batch=[{"id": eid, "embedding": emb} for eid, emb in batch]
            )
            updated = result.single()["updated"]
            print(f"Batch {i//batch_size + 1}: Updated {updated} entities")
    
    print(f'Processed {total} entities in {time.time() - start_time:.2f} seconds')

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

def import_microsoft_graph(graph_folder: str):
    """Main function to orchestrate the import process."""
    create_constraints()
    import_documents(graph_folder)
    import_text_units(graph_folder)
    import_entities(graph_folder)
    import_relationships(graph_folder)
    import_communities(graph_folder)
    import_community_reports(graph_folder)
    create_vector_index()
    process_entity_embeddings(source="database")


if __name__ == "__main__":
    import_microsoft_graph("ragtest")