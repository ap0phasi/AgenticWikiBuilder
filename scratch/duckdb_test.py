import duckdb
import time
import networkx as nx
import itertools


con = duckdb.connect()

con.execute("""
INSTALL markdown FROM community;
LOAD markdown;
            """)

base_file_path = r".\working"

# df = con.execute(f"""
#     SELECT * EXCLUDE file_path, parse_filename(file_path, true), split(section_path, '/') splits, ROW_NUMBER() OVER() FROM read_markdown_sections('{base_file_path}/raw/*.md', filename = true)
#                  """).df()

# breakpoint()
print("running")
tic = time.time()
graph = con.execute(f"""
WITH
edges AS (
    SELECT
         unnest(regexp_extract_all(content, '\[(.*?)\]\(\.\/(.*?)\.md', 2)) as link_to,
         parse_filename(file_path, true) as link_from, *
    FROM read_markdown_sections('{base_file_path}/wiki/*.md', filename = true)   
),
nodes AS (
    SELECT parse_filename(file_path, true) as file FROM read_markdown('{base_file_path}/wiki/*.md',filename = true)
)
-- SELECT link_from, link_to, file FROM edges LEFT JOIN nodes ON edges.link_to == nodes.file
SELECT * FROM edges
""").df()
toc = time.time()
print(graph)
print("time elapsed: ", toc - tic)

G = nx.from_pandas_edgelist(graph[["link_from", "link_to"]], source = "link_from", target = "link_to")

# # Remove 'index.md' from G
# G.remove_node('index')

groups = ["\n".join(["-" + a + ".md" for a in n]) for n in nx.connected_components(G)]
print(groups)
print(len(groups))
pairs = list(itertools.combinations(groups, 2))
print(pairs)
