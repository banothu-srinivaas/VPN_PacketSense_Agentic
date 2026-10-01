"""Render DOT files to PNG/SVG (wrapper)."""
from graphviz import Source

def render_dot(dot_path, out_path=None):
    s = Source.from_file(dot_path)
    if out_path:
        s.render(out_path, cleanup=True)
    else:
        s.view()
