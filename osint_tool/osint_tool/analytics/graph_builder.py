# analytics/graph_builder.py
import networkx as nx
import os

# Hardcoded HTML template for PyVis (minimal)
PYVIS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Network Graph</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
    <style>
        #mynetwork { height: 750px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <div id="mynetwork"></div>
    <script>
        var nodes = new vis.DataSet({{ nodes|safe }});
        var edges = new vis.DataSet({{ edges|safe }});
        var container = document.getElementById('mynetwork');
        var data = { nodes: nodes, edges: edges };
        var options = { physics: { enabled: true } };
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>
"""

def build_graph(findings):
    """Build a networkx graph from a list of Finding objects."""
    G = nx.Graph()
    for f in findings:
        node_id = f"{f.type}:{f.value}"
        label = f.value
        G.add_node(node_id, label=label, type=f.type, source=f.source)
        # Connect to other findings that share same value (co‑occurrence)
        for other in findings:
            if other is not f and other.value == f.value:
                other_id = f"{other.type}:{other.value}"
                G.add_edge(node_id, other_id, relation="same_value")
    return G

def export_graph_html(G, filename="output/graph.html"):
    """Export graph as interactive HTML using a built‑in template."""
    import json
    # Convert to vis.js format
    nodes = []
    edges = []
    for node, attrs in G.nodes(data=True):
        nodes.append({
            "id": node,
            "label": attrs.get("label", node),
            "title": attrs.get("type", ""),
            "shape": "dot"
        })
    for u, v, attrs in G.edges(data=True):
        edges.append({
            "from": u,
            "to": v,
            "title": attrs.get("relation", ""),
            "arrows": "to"  # optional
        })

    # Render template
    from jinja2 import Template
    template = Template(PYVIS_TEMPLATE)
    html_content = template.render(
        nodes=json.dumps(nodes, indent=2),
        edges=json.dumps(edges, indent=2)
    )

    # Ensure output directory exists
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename