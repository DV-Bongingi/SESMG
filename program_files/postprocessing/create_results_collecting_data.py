import oemof.solph as solph
from oemof.network.network import Bus, Sink, Source, Transformer
from oemof.solph.custom import Link
from oemof.solph.components import GenericStorage
from dhnx.optimization_oemof_heatpipe import HeatPipeline
import csv


def get_flows(nd, results, esys):
    inputs = list(nd.inputs) if len(list(nd.inputs)) != 0 else None
    outputs = list(nd.outputs) if len(list(nd.outputs)) != 0 else None
    
    component = solph.views.node(results, str(nd.label))
    comp_input1 = [0 for i in range(0, len(esys.timeindex))]
    comp_input2 = [0 for i in range(0, len(esys.timeindex))]
    comp_output1 = [0 for i in range(0, len(esys.timeindex))]
    comp_output2 = [0 for i in range(0, len(esys.timeindex))]

    if inputs:
        comp_input1 = component['sequences'][
            ((str(inputs[0].label), str(nd.label)), 'flow')]
        if len(inputs) == 2:
            comp_input2 = component['sequences'][
                ((str(inputs[1].label), str(nd.label)), 'flow')]
    if outputs:
        comp_output1 = component['sequences'][
            ((str(nd.label), str(outputs[0].label)), 'flow')]
        if len(outputs) == 2:
            comp_output2 = component['sequences'][
                ((str(nd.label), str(outputs[1].label)), 'flow')]
    return comp_input1, comp_input2, comp_output1, comp_output2
    
    
def get_investment(nd, esys, results, storage):
    """

    """
    component_node = esys.groups[str(nd.label)]
    if not storage:
        bus_node = esys.groups[str(list(nd.outputs)[0].label)]
    else:
        bus_node = None
    if "invest" in results[component_node, bus_node]['scalars']:
        return results[component_node, bus_node]['scalars']['invest']
    else:
        return 0


def calc_periodical_costs(nd, investment, storage, link, cost_type):
    """

    """
    ep_costs = 0
    offset = 0
    attributes = {
        "costs": ["ep_costs", "offset"],
        "emissions": ["periodical_constraint_costs", "fix_constraint_costs"]}
    
    if investment > 0 and not storage:
        ep_costs = getattr(nd.outputs[list(nd.outputs.keys())[0]].investment,
                           attributes.get(cost_type)[0])
        offset = getattr(nd.outputs[list(nd.outputs.keys())[0]].investment,
                         attributes.get(cost_type)[1])
    elif investment > 0 and storage:
        ep_costs = getattr(nd.investment, attributes.get(cost_type)[0])
        offset = getattr(nd.investment, attributes.get(cost_type)[1])
        
    if link:
        return (investment * 2 * ep_costs) + 2 * offset
    else:
        return investment * ep_costs + offset
    

def calc_variable_costs(nd, comp_dict, attr):
    costs = 0
    type_dict = {
        "inputs": [nd.inputs, comp_dict[0], comp_dict[1]],
        "outputs": [nd.outputs, comp_dict[2], comp_dict[3]]}
    for flow_type in type_dict:
        for i in range(0, 1):
            if sum(type_dict[flow_type][i + 1]) > 0:
                costs += \
                    sum(type_dict[flow_type][i + 1]
                        * getattr(type_dict[flow_type][0]
                                  [list(type_dict[flow_type][0].keys())[i]],
                                  attr))

    return costs


def get_comp_type(nd, comp_dict):
    if isinstance(nd, HeatPipeline):
        comp_dict[str(nd.label)].append("dh")
    elif isinstance(nd, Sink):
        comp_dict[nd.label].append("sink")
    elif isinstance(nd, Source):
        comp_dict[nd.label].append("source")
    elif isinstance(nd, Transformer) and not isinstance(nd, HeatPipeline):
        comp_dict[nd.label].append("transformer")
    elif isinstance(nd, GenericStorage):
        comp_dict[nd.label].append("storage")
    elif isinstance(nd, Link):
        comp_dict[nd.label].append("link")
        
        
def collect_data(nodes_data, results, esys):
    total_demand = 0
    # dictionary containing energy system components data
    # label: [flow input1, flow input2, flow output1, flow output2,
    # investment, periodical costs, variable costs, constraint costs]
    comp_dict = {}
    for nd in esys.nodes:
        investment = None
        label = str(nd.label)
        undirected_link = \
            True if isinstance(nd, Link) \
            and str(nodes_data["links"].loc[
                        nodes_data["links"]["label"] == nd.label]
                    ["(un)directed"]) == "undirected" else False
        storage = True if isinstance(nd, GenericStorage) else False
        # get component flows from each component except buses
        if not isinstance(nd, Bus):
            comp_dict.update({label: []})
            comp_input1, comp_input2, comp_output1, comp_output2 = get_flows(
                nd,
                results,
                esys)
            comp_dict[label] += [comp_input1,
                                 comp_input2,
                                 comp_output1,
                                 comp_output2]
        if not (isinstance(nd, Source) and "shortage" in nd.label) \
                and not isinstance(nd, Sink) and not isinstance(nd, Bus):
            # get investment
            investment = get_investment(nd, esys, results, storage)
            comp_dict[label].append(investment)
            # get periodical costs
            periodical_costs = calc_periodical_costs(
                nd, investment, storage, undirected_link, "costs")
            comp_dict[label].append(periodical_costs)
        elif not isinstance(nd, Bus):
            comp_dict[label] += [0, 0]
        if not (isinstance(nd, Sink)
                and nd.label in list(nodes_data["sinks"]["label"])) \
                and not isinstance(nd, Bus):
            variable_costs = calc_variable_costs(nd, comp_dict[label],
                                                 "variable_costs")
            comp_dict[label].append(variable_costs)
            
            constraint_costs = \
                calc_variable_costs(nd, comp_dict[label], "emission_factor")
            if investment:
                constraint_costs += calc_periodical_costs(
                    nd, investment, storage, undirected_link, "emissions")
            comp_dict[label].append(constraint_costs)
        elif not isinstance(nd, Bus):
            comp_dict[label] += [0, 0]
            total_demand += sum(comp_input1)

        get_comp_type(nd, comp_dict)
    return comp_dict, total_demand
