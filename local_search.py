import os
from typing import Dict, List
import pandas as pd
from neo4j import Result
from langchain_community.graphs import Neo4jGraph
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from neo4j import GraphDatabase
import asyncio
from knowledge_graph_creator import DB_CONFIG, db_query
from dotenv import load_dotenv


TOP_CHUNKS = 3
TOP_COMMUNITIES = 3
TOP_OUTSIDE_RELS = 10
TOP_INSIDE_RELS = 10
TOP_ENTITIES = 10


# Vector store setup
lc_retrieval_query = """
WITH collect(node) as nodes
// Entity - Text Unit Mapping
WITH
collect {
    UNWIND nodes as n
    MATCH (n)<-[:HAS_ENTITY]->(c:__Chunk__)
    WITH c, count(distinct n) as freq
    RETURN c.text AS chunkText
    ORDER BY freq DESC
    LIMIT $topChunks
} AS text_mapping,
// Entity - Report Mapping
collect {
    UNWIND nodes as n
    MATCH (n)-[:IN_COMMUNITY]->(c:__Community__)
    WITH c, c.rank as rank, c.weight AS weight
    RETURN c.summary 
    ORDER BY rank, weight DESC
    LIMIT $topCommunities
} AS report_mapping,
// Outside Relationships 
collect {
    UNWIND nodes as n
    MATCH (n)-[r:RELATED]-(m) 
    WHERE NOT m IN nodes
    RETURN r.description AS descriptionText
    ORDER BY r.rank, r.weight DESC 
    LIMIT $topOutsideRels
} as outsideRels,
// Inside Relationships 
collect {
    UNWIND nodes as n
    MATCH (n)-[r:RELATED]-(m) 
    WHERE m IN nodes
    RETURN r.description AS descriptionText
    ORDER BY r.rank, r.weight DESC 
    LIMIT $topInsideRels
} as insideRels,
// Entities description
collect {
    UNWIND nodes as n
    RETURN n.description AS descriptionText
} as entities
// We don't have covariates or claims here
RETURN {Chunks: text_mapping, Reports: report_mapping, 
       Relationships: outsideRels + insideRels, 
       Entities: entities} AS text, 1.0 AS score, {} AS metadata
"""

def local_search(neo4j_config: Dict, query: str, k: int = 5) -> List[Dict]:
    REDUCE_SYSTEM_PROMPT = """
    You are a helpful assistant responding to questions about a dataset by synthesizing perspectives from multiple analysts.

    Generate a response of the target length and format that responds to the user's question, summarizing all the reports from multiple analysts who focused on different parts of the dataset.

    Note that the analysts' reports provided are ranked in descending order of importance.

    If you don't know the answer or if the provided reports do not contain sufficient information to provide an answer, just say so. Do not make anything up.

    The final response should:
    1. Remove all irrelevant information from the analysts' reports
    2. Merge the cleaned information into a comprehensive answer
    3. Provide explanations of all key points and implications appropriate for the response length and format
    4. Add sections and commentary as appropriate for the length and format
    5. Style the response in markdown

    Preserve the original meaning and use of modal verbs such as "shall", "may" or "will".

    Preserve all data references previously included in the analysts' reports, but do not mention the roles of multiple analysts in the analysis process.

    Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

    Example:
    "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Reports (2, 7, 34, 46, 64, +more)]. He is also CEO of company X [Data: Reports (1, 3)]"
    where 1, 2, 3, 7, 34, 46, and 64 represent the id (not the index) of the relevant data record.
    Do not include information where supporting evidence is not provided.

    ---Target response length and format---

    multiple paragraphs

    ---Analyst Reports---

    {report_data}
    """

    reduce_prompt = ChatPromptTemplate.from_messages([
        ("system", REDUCE_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    # Set up LLM
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("DEPLOYMENT_NAME"),
        temperature=0,
    )
    reduce_chain = reduce_prompt | llm | StrOutputParser()


    lc_vector = Neo4jVector.from_existing_index(
        AzureOpenAIEmbeddings(model=os.getenv("DEPLOYMENT_NAME_EMBEDDINGS"),api_key=os.getenv("AZURE_OPENAI_API_KEY_EMBEDDINGS")),      
        url=neo4j_config["url"],
        username=neo4j_config["username"],
        password=neo4j_config["password"],
        index_name=neo4j_config.get("index_name", "entity"),
        retrieval_query=lc_retrieval_query
    )


    report_data = lc_vector.similarity_search(
        query,
        k=k,
        params={
            "topChunks": TOP_CHUNKS,
            "topCommunities": TOP_COMMUNITIES,
            "topOutsideRels": TOP_OUTSIDE_RELS,
            "topInsideRels": TOP_INSIDE_RELS,
        },
    )

    final_response = reduce_chain.invoke({
        "report_data": report_data,
        "question": query,
    })
    
    return final_response



def local_search_test():
    neo4j_config = {
        "url": "bolt://54.236.31.6:7687",
        "username": "neo4j",
        "password": "rules-knowledge-selection",
        "index_name": "entity"
    }
    
    result = local_search(neo4j_config, "Who is Scrooge?")
    print(result)

if __name__ == "__main__":
    local_search_test()