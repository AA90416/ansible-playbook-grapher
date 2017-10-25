"""
Simple grapher for an Ansible Playbook.

You will need to install Ansible, graphviz on your system (sudo apt-get install graphviz).

Has been tested with Ansible 2.4.
"""

import random
import argparse
import ntpath
import os

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Playbook
from ansible.playbook.block import Block
from ansible.vars.manager import VariableManager
from graphviz import Digraph

__version__ = "0.0.1"

# TODO: add more colors
colors = ["red", "#007FFF", "green", "purple", "brown", "orange", "#F562FF", "#5ED4FF", "#50C878", "#0095B6", "#FFD700",
          "#61FF46", "#CC8899"]


def clean_node_name(node_name):
    return node_name.strip()


class CustomDiagram(Digraph):
    """
    Custom digraph to avoid quoting issue with node names
    """
    _edge = '\t"%s" -> "%s"%s'
    _node = '\t"%s"%s'
    _subgraph = 'subgraph "%s"{'
    _quote = staticmethod(clean_node_name)
    _quote_edge = staticmethod(clean_node_name)


def include_tasks_in_graph(graph, role_name, block, color, current_counter):
    """
    Recursively read all the tasks of the role
    :param graph:
    :param role_name:
    :param block:
    :return:
    """
    loop_counter = current_counter
    # loop through the tasks
    for counter, task_or_block in enumerate(block.block, 1):
        if isinstance(task_or_block, Block):
            loop_counter = include_tasks_in_graph(graph, role_name, task_or_block, color, loop_counter)
        else:
            task_name = clean_node_name(task_or_block.get_name())
            graph.node(task_name, shape="octagon")
            graph.edge(role_name, task_name, label=str(loop_counter + 1), color=color, fontcolor=color, style="bold")

            loop_counter += 1

    return loop_counter


def dump_playbok(playbook, variable_manager, include_tasks):
    playbook_name = playbook._file_name
    output_file_name = os.path.splitext(ntpath.basename(playbook_name))[0]

    graph_attr = {'ratio': "fill", "rankdir": "LR", 'concentrate': 'true', 'ordering': 'in'}
    dot = CustomDiagram(filename=output_file_name, comment="My webservers graph",
                        edge_attr={'sep': "10", "esep": "5"}, graph_attr=graph_attr, format="svg")

    # the root node
    with dot.subgraph(name="cluster" + playbook_name) as root:
        root.node(playbook_name, style="dotted")

    # loop through the plays
    for play_counter, play in enumerate(playbook.get_plays(), 1):
        color = random.choice(colors)
        play_hosts = clean_node_name("hosts: " + str(play).strip())

        play_vars = variable_manager.get_vars(play)

        with dot.subgraph(name=play_hosts) as subgraph:

            # role cluster color
            subgraph.attr(color=color)

            # play node
            subgraph.node(play_hosts, style='filled', shape="box", color=color,
                          tooltip="     ".join(play_vars['ansible_play_hosts']))

            # edge from root node to plays
            subgraph.edge(playbook_name, play_hosts, style="bold", label=str(play_counter), color=color,
                          fontcolor=color)

            # loop through the roles
            for role_counter, role in enumerate(play.get_roles()):
                role_name = str(role)

                with dot.subgraph(name=role_name, node_attr={}) as role_sub_graph:
                    current_counter = play_counter + role_counter

                    when = "".join(role.when)
                    label = str(current_counter) if len(when) == 0 else str(current_counter) + "  [when: " + when + "]"

                    role_sub_graph.edge(play_hosts, role_name, label=label, color=color, fontcolor=color, style="bold")

                    # loop through the tasks of the roles
                    if include_tasks:
                        task_counter = 0
                        for block in role.get_task_blocks():
                            task_counter = include_tasks_in_graph(role_sub_graph, role_name, block, color, task_counter)
                            task_counter += 1

    dot.render()


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("playbook", help="The playbook to grah.")
    parser.add_argument("-i", "--inventory",
                        help="The inventory. Useful if you want to have a tooltip with hostnames on the play nodes.")
    parser.add_argument("--include-tasks", dest="include_tasks", action='store_true',
                        help="Include tasks in the graph.")
    parser.add_argument("--save-dot-file", dest="save_dot", action='store_true',
                        help="Save the dot file use to generate the graph.")
    parser.add_argument("-V", "--version", dest="version", action="store_true", help="Print version and exits")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        exit(0)

    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=args.inventory)
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    pb = Playbook.load(args.playbook, loader=loader, variable_manager=variable_manager)

    dump_playbok(pb, variable_manager, args.include_tasks)


if __name__ == "__main__":
    main()
