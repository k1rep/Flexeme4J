from typing import List, Tuple

import networkx as nx
import pygraphviz


def mark_pdg_nodes(apdg, marker: str,
                   diff: List[Tuple[str, str, int, int, str]]) -> pygraphviz.AGraph:
    marked_pdg = apdg.copy()
    index = 2 if marker == '+' else 3
    change_label = 'green' if marker == '+' else 'red'
    anchor_label = 'orange'
    diff_ = [(l[0], l[1], l[index], l[-1]) for l in diff]
    c_diff = [ln for m, f, ln, line in diff_ if m == marker]
    # a_diff = [ln for m, f, ln, line in diff_ if m == ' ']
    for node, data in marked_pdg.nodes(data=True):
        if 'Entry' in data['label'] or 'Exit' in data['label']:
            attr = data
            attr['label'] += ' %s' % data['cluster']
            apdg.add_node(node, **attr)
            continue  # Do not mark entry and exit nodes.
        try:
            start, end = [int(ln) for ln in data['span'].split('-') if '-' in data['span']]
        except ValueError:
            continue
        # We will use the changed nodes as anchors via neighbours
        change = any([start <= cln - 0 <= end for cln in c_diff])
        # anchor = any([start <= aln - 1 <= end for aln in a_diff])
        if change:
            attr = data
            attr['color'] = change_label if change else anchor_label
            apdg.add_node(node, **attr)

    # print("This is the marked pdg:", marked_pdg)
    # nx.drawing.nx_pydot.write_dot(marked_pdg, 'marked_pdg.dot')
    return marked_pdg
