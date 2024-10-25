import torch
from torch_geometric.data.data import Data
data = torch.load('data_4.pt')
print(data)
print(data[0]['x'])
print(data[0]['y'])
print(data[0]['edge_index'])
print(data[1]['x'])
print(data[1]['y'])
print(data[1]['edge_index'])
print(data[-1])
print(type(data[0]))
# import os
#
# from Util.general_util import get_pattern_paths
#
# all_graphs = sorted(
#             get_pattern_paths('*merged.dot', os.path.join('.', 'data', 'corpora_clean', 'Commandline')))
# print(all_graphs)

# model = torch.load('model.pt')
# print(model)
