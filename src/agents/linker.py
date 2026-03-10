
import duckdb
import time
import networkx as nx
import itertools

def find_unlinked_clusters(con):
    graph = con.execute("""
    WITH
    edges AS (
        SELECT
             unnest(regexp_extract_all(content, '\[(.*?)\]\(\.\/(.*?)\.md', 2)) as link_to,
             parse_filename(file_path, true) as link_from, *
        FROM read_markdown_sections('wiki/*.md', filename = true)   
    ),
    nodes AS (
        SELECT parse_filename(file_path, true) as file FROM read_markdown('wiki/*.md',filename = true)
    )
    -- SELECT link_from, link_to, file FROM edges LEFT JOIN nodes ON edges.link_to == nodes.file
    SELECT * FROM edges
    """).df()

    G = nx.from_pandas_edgelist(graph[["link_from", "link_to"]], source = "link_from", target = "link_to")

    groups = ["\n".join(["-" + a + ".md" for a in n]) for n in nx.connected_components(G)]
    pairs = list(itertools.combinations(groups, 2))

    return pairs

def linker_prompt(pair, session_name):
    prompt = f"""
    You are an AI agent tasked with maintaining links within a personal wiki stored as markdown files in `/wiki`. We have found that there are no linkages between this cluster of articles:
{pair[0]}

    And this cluster:
{pair[1]}

    If you think there should be some sort of linkage between any of these separate clusters, please make the appropriate updates to files and add any necessary links. Do not feel the need to add unnecessary or contrived links.

    
    When you're done:
    1. Document your changes in `sessions/{session_name}/docs/changes.md` (what you changed and why)
    2. Create a brief summary in `sessions/{session_name}/docs/linker.txt` (one line description)
    """

    return prompt
