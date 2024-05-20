# Copyright 2019-2020 the ProGraML authors.
#
# Contact Chris Cummins <chrisc.101@gmail.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from concurrent.futures.thread import ThreadPoolExecutor

import networkx as nx
import pytest

import programl as pg
from torch_geometric.data import HeteroData
from tests.test_main import main

pytest_plugins = ["tests.plugins.llvm_program_graph"]


@pytest.fixture(scope="session")
def graph() -> pg.ProgramGraph:
    return pg.from_cpp("int A() { return 0; }")

@pytest.fixture(scope="session")
def graph2() -> pg.ProgramGraph:
    return pg.from_cpp("int B() { return 1; }")

@pytest.fixture(scope="session")
def graph3() -> pg.ProgramGraph:
    return pg.from_cpp("int B(int x) { return x + 1; }")

def assert_equal_graphs(
    graph1: HeteroData,
    graph2: HeteroData,
    equality: bool = True
):
    if equality:
        assert graph1['nodes']['full_text'] == graph2['nodes']['full_text']

        assert graph1['nodes', 'control', 'nodes'].edge_index.equal(graph2['nodes', 'control', 'nodes'].edge_index)
        assert graph1['nodes', 'data', 'nodes'].edge_index.equal(graph2['nodes', 'data', 'nodes'].edge_index)
        assert graph1['nodes', 'call', 'nodes'].edge_index.equal(graph2['nodes', 'call', 'nodes'].edge_index)
        assert graph1['nodes', 'type', 'nodes'].edge_index.equal(graph2['nodes', 'type', 'nodes'].edge_index)

    else:
        text_different = graph1['nodes']['full_text'] != graph2['nodes']['full_text']

        control_edges_different = not graph1['nodes', 'control', 'nodes'].edge_index.equal(
            graph2['nodes', 'control', 'nodes'].edge_index
        )
        data_edges_different = not graph1['nodes', 'data', 'nodes'].edge_index.equal(
            graph2['nodes', 'data', 'nodes'].edge_index
        )
        call_edges_different = not graph1['nodes', 'call', 'nodes'].edge_index.equal(
            graph2['nodes', 'call', 'nodes'].edge_index
        )
        type_edges_different = not graph1['nodes', 'type', 'nodes'].edge_index.equal(
            graph2['nodes', 'type', 'nodes'].edge_index
        )

        assert (
            text_different
            or control_edges_different
            or data_edges_different
            or call_edges_different
            or type_edges_different
        )

def test_to_pyg_simple_graph(graph: pg.ProgramGraph):
    graphs = list(pg.to_pyg([graph]))
    assert len(graphs) == 1
    assert isinstance(graphs[0], HeteroData)

def test_to_pyg_simple_graph_single_input(graph: pg.ProgramGraph):
    pyg_graph = pg.to_pyg(graph)
    assert isinstance(pyg_graph, HeteroData)

def test_to_pyg_different_two_different_inputs(
    graph: pg.ProgramGraph,
    graph2: pg.ProgramGraph,
):
    pyg_graph = pg.to_pyg(graph)
    pyg_graph2 = pg.to_pyg(graph2)

    #  Ensure that the graphs are different
    assert_equal_graphs(pyg_graph, pyg_graph2, equality=False)

def test_to_pyg_different_inputs(
    graph: pg.ProgramGraph,
    graph2: pg.ProgramGraph,
    graph3: pg.ProgramGraph
):
    pyg_graph = pg.to_pyg(graph)
    pyg_graph2 = pg.to_pyg(graph2)
    pyg_graph3 = pg.to_pyg(graph3)

    #  Ensure that the graphs are different
    assert_equal_graphs(pyg_graph, pyg_graph2, equality=False)
    assert_equal_graphs(pyg_graph, pyg_graph3, equality=False)
    assert_equal_graphs(pyg_graph2, pyg_graph3, equality=False)

def test_to_pyg_two_inputs(graph: pg.ProgramGraph):
    graphs = list(pg.to_pyg([graph, graph]))
    assert len(graphs) == 2
    assert_equal_graphs(graphs[0], graphs[1], equality=True)

def test_to_pyg_generator(graph: pg.ProgramGraph):
    graphs = list(pg.to_pyg((graph for _ in range(10)), chunksize=3))
    assert len(graphs) == 10
    for x in graphs[1:]:
        assert_equal_graphs(graphs[0], x, equality=True)

def test_to_pyg_generator_parallel_executor(graph: pg.ProgramGraph):
    with ThreadPoolExecutor() as executor:
        graphs = list(
            pg.to_pyg((graph for _ in range(10)), chunksize=3, executor=executor)
        )
    assert len(graphs) == 10
    for x in graphs[1:]:
        assert_equal_graphs(graphs[0], x, equality=True)


def test_to_pyg_smoke_test(llvm_program_graph: pg.ProgramGraph):
    graphs = list(pg.to_pyg([llvm_program_graph]))

    num_nodes = len(graphs[0]['nodes']['text'])
    num_control_edges = graphs[0]['nodes', 'control', 'nodes'].edge_index.size(1)
    num_data_edges = graphs[0]['nodes', 'data', 'nodes'].edge_index.size(1)
    num_call_edges = graphs[0]['nodes', 'call', 'nodes'].edge_index.size(1)
    num_type_edges = graphs[0]['nodes', 'type', 'nodes'].edge_index.size(1)
    num_edges = num_control_edges + num_data_edges + num_call_edges + num_type_edges

    assert len(graphs) == 1
    assert isinstance(graphs[0], HeteroData)
    assert num_nodes == len(llvm_program_graph.node)
    assert num_edges <= len(llvm_program_graph.edge)


if __name__ == "__main__":
    main()