"""Create a Graphviz DOT callflow from ordered messages (skeleton)."""
from graphviz import Digraph

def build_callflow_dot(rows, output_path):
    dot = Digraph(comment='Call flow')
    dot.attr(rankdir='LR')
    nodes = set()
    for r in rows:
        src = r.get('src') or r.get('src_ip') or 'SRC'
        dst = r.get('dst') or r.get('dst_ip') or 'DST'
        if src not in nodes:
            dot.node(src)
            nodes.add(src)
        if dst not in nodes:
            dot.node(dst)
            nodes.add(dst)
        label = f"{r.get('msg_type','')}\nframe:{r.get('frame_no','')}"
        dot.edge(src, dst, label=label)
    dot.render(output_path, format='png', cleanup=True)
