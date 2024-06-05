import json
import os
import shutil
import subprocess
import logging
import networkx as nx

from deltaPDG.Util.merge_nameflow import add_nameflow_edges
from deltaPDG.Util.pygraph_util import read_graph_from_dot, obj_dict_to_networkx

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s][%(name)s] %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[logging.StreamHandler()])


class PdgGenerator:
    """
    This class serves as a wrapper to abstract away calling the Java or c# compiled PDG extractor
    """

    def __init__(self, repository_location, target_filename="pdg.dot",
                 target_location=os.getcwd(), extractor_location="./PDGExtractor/TinyPDG-1.0.0.jar"):
        self.repository_location = repository_location
        self.target_filename = target_filename
        self.target_location = target_location
        self.extractor_location = extractor_location

    def __call__(self, filename, src_code):
        if src_code == 'java':
            # if the file does not exist, return
            if not os.path.exists(self.repository_location + filename):
                return
            logging.info(f"Extracting PDG for {os.path.join(self.repository_location, filename)}")
            # jar_path = "./PDGExtractor/PropertyGraph.jar"
            # jar_path = "./PDGExtractor/TinyPDG-0.1.0.jar"
            # command = ["java", "-jar", self.extractor_location, "-d", self.repository_location + filename,
            #            "-p", os.path.join(self.target_location, self.target_filename)]
            command = ["java", "-jar", self.extractor_location,
                       self.repository_location + filename, os.path.join(self.target_location, self.target_filename)]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stderr:
                logging.error(stderr)

        # t_filename = os.path.basename(filename).split('.')[0]
        # bin_path = t_filename + '.bin'
        # command1 = ["javasrc2cpg -J-Xmx4096m", self.repository_location + filename, "--output", bin_path]
        # command2 = ["joern-export", "--repr", "pdg", "--out", t_filename]
        # process1 = subprocess.Popen(command1)
        # process1.wait()
        # print("当前工作执行目录：")
        # print(os.getcwd() + self.repository_location)
        # print("当前分析文件：")
        # print(filename)
        # process2 = subprocess.Popen(command2, cwd=os.getcwd() + self.repository_location + filename)
        # process2.wait()
        elif src_code == 'csharp':
            if not os.path.exists(self.repository_location + filename):
                return
            logging.info(f"Extracting PDG for {os.path.join(self.repository_location, filename)}")
            generate_a_pdg = subprocess.Popen([self.extractor_location, '.', '.' + filename],
                                              bufsize=1, cwd=self.repository_location)
            stdout, stderr = generate_a_pdg.communicate()
            if stderr:
                logging.error(stderr)

            try:
                dir_name = os.path.dirname(self.repository_location + filename)
                base_name = os.path.basename(filename).split('.')[0]
                logging.info("Moving %s to %s" % (dir_name + '/PDG/' + base_name + '_pdg.dot',
                                                  os.path.join(self.target_location, self.target_filename)))
                shutil.move(dir_name + '/PDG/' + base_name + '_pdg.dot',
                            os.path.join(self.target_location, self.target_filename))
                # shutil.move(os.path.join(self.repository_location, 'pdg.dot'),
                #             os.path.join(self.target_location, self.target_filename))
            except FileNotFoundError:
                with open(os.path.join(self.target_location, self.target_filename), 'w') as f:
                    f.write('digraph "extractedGraph"{\n}\n')

        try:
            if src_code == 'csharp':
                shutil.move(os.path.join(self.repository_location, 'nameflows.json'),
                            os.path.join(self.target_location,
                                         'nameflows_' + self.target_filename.split('.')[0] + '.json'))
            with open(os.path.join(self.repository_location, 'nameflows.json'), encoding='utf-8-sig') as json_data:
                nameflow_data = json.loads(json_data.read())

            # Normalise the nameflow json
            if nameflow_data is not None:
                for node in nameflow_data['nodes']:
                    file, line = node['Location'].split(' : ')
                    node['Location'] = (file[len(self.repository_location):]
                                        if self.repository_location in file
                                        else file,
                                        line)
                    node['Infile'] = \
                        os.path.normcase(os.path.normpath(filename)) == os.path.normcase(os.path.normpath(file[1:]))

            nameflow_data['relations'] = [[] if v is None else v for v in nameflow_data['relations']]

            # And add nameflow edges
            apdg = obj_dict_to_networkx(read_graph_from_dot(os.path.join(self.target_location, self.target_filename)))
            apdg = add_nameflow_edges(nameflow_data, apdg)
            nx.drawing.nx_pydot.write_dot(apdg, os.path.join(self.target_location, self.target_filename))

        except FileNotFoundError:
            # No file, nothing to add
            pass
        except Exception as e:
            logging.error(f"Error adding nameflow edges: {e}")
