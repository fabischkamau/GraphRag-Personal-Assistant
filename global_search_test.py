import os
import asyncio
from typing import Dict, List
from langchain_community.graphs import Neo4jGraph
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def perform_global_search(db_config: Dict, query: str, response_type: str = "multiple paragraphs") -> str:
    """
    Performs a global search on the knowledge graph.
    
    Args:
        db_config: Dictionary containing Neo4j connection details (url, username, password)
        query: The search query
        response_type: Type of response to generate (default: "multiple paragraphs")
        
    Returns:
        The search results as a string
    """
    # Set up Neo4j graph connection
    graph = Neo4jGraph(
        url=db_config["url"],
        username=db_config["username"],
        password=db_config["password"],
        refresh_schema=False,
    )
    
    # Define prompts
    MAP_SYSTEM_PROMPT = """
    You are a helpful assistant responding to questions about data in the provided tables.

    Generate a response consisting of a list of key points that responds to the user's question, summarizing all relevant information in the input data tables.

    Use the data provided in the data tables as the primary context for generating the response.
    If you don't know the answer or if the input data tables do not contain sufficient information to provide an answer, just say so. Do not make anything up.

    Each key point in the response should have the following elements:
    - Description: A comprehensive description of the point.
    - Importance Score: An integer score between 0-100 that indicates how important the point is in answering the user's question. An 'I don't know' type of response should have a score of 0.

    The response should be JSON formatted as follows:
    {{
        "points": [
            {{"description": "Description of point 1 [Data: Reports (report ids)]", "score": score_value}},
            {{"description": "Description of point 2 [Data: Reports (report ids)]", "score": score_value}}
        ]
    }}

    Preserve the original meaning and use of modal verbs such as "shall", "may" or "will".

    Points supported by data should list the relevant reports as references:
    "This is an example sentence supported by data references [Data: Reports (report ids)]"

    Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

    Example:
    "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Reports (2, 7, 64, 46, 34, +more)]. He is also CEO of company X [Data: Reports (1, 3)]"

    Do not include information where supporting evidence is not provided.

    ---Data tables---

    {context_data}
    """

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

    {response_type}

    ---Analyst Reports---

    {report_data}
    """

    map_prompt = ChatPromptTemplate.from_messages([
        ("system", MAP_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    reduce_prompt = ChatPromptTemplate.from_messages([
        ("system", REDUCE_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])
    
    # Set up LLM
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("DEPLOYMENT_NAME"),
        temperature=0,
    )

    # Create chains
    map_chain = map_prompt | llm | StrOutputParser()
    reduce_chain = reduce_prompt | llm | StrOutputParser()
    
    # Set level to 1 as required
    level = 1
    
    # Get community data
    community_data = graph.query(
        """
        MATCH (c:__Community__)
        WHERE c.level = $level
        RETURN c.full_content AS output
        """,
        params={"level": level},
    )

    # Process each community in parallel
    async def process_community(community):
        return await asyncio.to_thread(map_chain.invoke, {
            "question": query,
            "context_data": community["output"]
        })

    intermediate_results = await asyncio.gather(
        *[process_community(community) for community in community_data]
    )

    # Generate final response
    final_response = reduce_chain.invoke({
        "report_data": intermediate_results,
        "question": query,
        "response_type": response_type,
    })
    
    return final_response


# Example usage
async def search():
    db_config = {
        "url": "bolt://54.236.31.6:7687",
        "username": "neo4j",
        "password": "rules-knowledge-selection"
    }
    
    result = await perform_global_search(db_config, "who is scrooges best friend?")
    return result

if __name__ == "__main__":
    result = asyncio.run(search())
    print(result)