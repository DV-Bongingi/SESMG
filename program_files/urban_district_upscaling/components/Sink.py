def create_standard_parameter_sink(sink_type: str, label: str,
                                   sink_input: str, annual_demand: int,
                                   sheets):
    """
        creates a sink with standard_parameters, based on the standard
        parameters given in the "standard_parameters" dataset and adds
        it to the "sheets"-output dataset.

        :param sink_type: needed to get the standard parameters of the
                          link to be created
        :type sink_type: str
        :param label: label, the created sink will be given
        :type label: str
        :param sink_input: label of the bus which will be the input of the
                      sink to be created
        :type sink_input: str
        :param annual_demand: #todo formula
        :type annual_demand: int
        :param sheets:
        :type sheets:
    """
    from program_files import create_standard_parameter_comp
    return create_standard_parameter_comp(
        specific_param={'label': label,
                        'input': sink_input,
                        'annual demand': annual_demand},
        standard_parameter_info=[sink_type, "sinks", "sink_type"],
        sheets=sheets)
    

def create_sinks(building, standard_parameters, sheets):
    """
        TODO DOCSTRING
    """
    # electricity demand
    if building['building type'] not in ['None', '0', 0]:
        # TODO rename living space
        area = building['living space'] * building['floors']
        # get sinks standard parameters
        sinks_standard_param = standard_parameters.parse('sinks')
        sinks_standard_param.set_index("sink_type", inplace=True)
        
        if "RES" in building['building type']:
            elec_demand_res = {}
            standard_param = standard_parameters.parse('ResElecDemand')
            for i in range(len(standard_param)):
                elec_demand_res[standard_param['household size'][i]] = \
                    [standard_param[building['building type'] + ' (kWh/a)'][i]]

            if building['occupants per unit'] <= 5:
                demand_el = elec_demand_res[building['occupants per unit']][0]\
                            * building['units']
            else:
                demand_el = \
                    (elec_demand_res[5][0]) / 5 \
                    * building['occupants per unit'] * building['units']
        else:
            # commercial parameters
            elec_demand_com_ind = standard_parameters.parse(
                'ComElecDemand' if "COM" in building['building type']
                else "IndElecDemand")

            elec_demand_com_ind.set_index("commercial type", inplace=True)
            demand_el = elec_demand_com_ind.loc[building['building type']][
                'specific demand (kWh/(sqm a))']
            net_floor_area = area * sinks_standard_param.loc[
                building['building type'] + "_electricity_sink"][
                'net_floor_area / area']
            demand_el *= net_floor_area

        sheets = create_standard_parameter_sink(
            sink_type=building['building type'] + "_electricity_sink",
            label=str(building["label"]) + "_electricity_demand",
            sink_input=str(building["label"]) + "_electricity_bus",
            annual_demand=demand_el,
            sheets=sheets)

        # heat demand
        if "RES" in building['building type']:
            # read standard values from standard_parameter-dataset
            heat_demand_standard_param = \
                standard_parameters.parse('ResHeatDemand')
        elif "COM" in building['building type']:
            heat_demand_standard_param = \
                standard_parameters.parse('ComHeatDemand')
        elif "IND" in building['building type']:
            heat_demand_standard_param = \
                standard_parameters.parse('IndHeatDemand')
        else:
            raise ValueError("building_type does not exist")
        heat_demand_standard_param.set_index(
            "year of construction", inplace=True)
        yoc = int(building['year of construction']) \
            if int(building['year of construction']) > 1918 else "<1918"
        units = str(building['units']) if building['units'] < 12 else "> 12"

        if "RES" in building['building type']:
            specific_heat_demand = \
                heat_demand_standard_param.loc[yoc][units + ' unit(s)']
        else:
            specific_heat_demand = \
                heat_demand_standard_param.loc[yoc][building['building type']]
        net_floor_area = area * sinks_standard_param \
            .loc[building['building type'] + "_heat_sink"][
             'net_floor_area / area']
        demand_heat = specific_heat_demand * net_floor_area

        sheets = create_standard_parameter_sink(
            sink_type=building['building type'] + "_heat_sink",
            label=str(building["label"]) + "_heat_demand",
            sink_input=str(building["label"]) + "_heat_bus",
            annual_demand=demand_heat,
            sheets=sheets)
        
    return sheets


def sink_clustering(building, sink, sink_parameters):
    """
        In this method, the current sinks of the respective cluster are
        stored in dict and the current sinks are deleted. Furthermore,
        the heat buses and heat requirements of each cluster are
        collected in order to summarize them afterwards.

        :param building: DataFrame containing the building row from the\
            pre scenario sheet
        :type building: pd.Dataframe
        :param sink: sink dataframe
        :type sink: pd.Dataframe
        :parameter sink_parameters: list containing clusters' sinks \
            information
        :type sink_parameters: list
    """
    # get cluster electricity sinks
    if str(building[0]) in sink["label"] and "electricity" in sink["label"]:
        # get res elec demand
        if "RES" in building[2]:
            sink_parameters[0] += sink["annual demand"]
            sink_parameters[8].append(sink["label"])
        # get com elec demand
        elif "COM" in building[2]:
            sink_parameters[1] += sink["annual demand"]
            sink_parameters[9].append(sink["label"])
        # get ind elec demand
        elif "IND" in building[2]:
            sink_parameters[2] += sink["annual demand"]
            sink_parameters[10].append(sink["label"])
    # get cluster heat sinks
    elif str(building[0]) in sink["label"] and "heat" in sink["label"]:
        # append heat bus to cluster heat buses
        sink_parameters[3].append((building[2], sink["input"]))
        # get res heat demand
        if "RES" in building[2]:
            sink_parameters[4] += sink["annual demand"]
        # get com heat demand
        elif "COM" in building[2]:
            sink_parameters[5] += sink["annual demand"]
        # get ind heat demand
        elif "IND" in building[2]:
            sink_parameters[6] += sink["annual demand"]
        sink_parameters[7].append((building[2], sink["label"]))
    return sink_parameters


def create_cluster_elec_sinks(standard_parameters, sink_parameters, cluster,
                              central_electricity_network, sheets):
    """

        :return:
    """
    from program_files.urban_district_upscaling.components import Link
    from program_files.urban_district_upscaling.components import Bus
    bus_parameters = standard_parameters.parse('buses', index_col='bus_type')
    total_annual_demand = (
            sink_parameters[0] + sink_parameters[1] + sink_parameters[2])
    if total_annual_demand > 0:
        if cluster + "_electricity_bus" not in sheets["buses"].index:
            sheets = Bus.create_standard_parameter_bus(
                label=str(cluster) + "_electricity_bus",
                bus_type='building_res_electricity_bus', sheets=sheets)
            sheets["buses"].set_index("label", inplace=True, drop=False)
            cost_type = "shortage costs"
            label = "_electricity_bus"
            sheets["buses"].loc[(str(cluster) + label), cost_type] = \
                ((sink_parameters[0] / total_annual_demand)
                 * bus_parameters.loc["building_res" + label][cost_type]
                 + (sink_parameters[1] / total_annual_demand)
                 * bus_parameters.loc["building_com" + label][cost_type]
                 + (sink_parameters[2] / total_annual_demand)
                 * bus_parameters.loc["building_ind" + label][cost_type])
        if central_electricity_network:
            sheets = Link.create_central_elec_bus_connection(cluster, sheets)
    
    # create clustered electricity sinks
    if sink_parameters[0] > 0:
        for i in sink_parameters[8]:
            sheets["sinks"].loc[sheets["sinks"]["label"] == i, "input"] \
                = str(cluster) + "_res_electricity_bus"
    if sink_parameters[1] > 0:
        for i in sink_parameters[9]:
            sheets["sinks"].loc[sheets["sinks"]["label"] == i, "input"] \
                = str(cluster) + "_com_electricity_bus"
    if sink_parameters[2] > 0:
        for i in sink_parameters[10]:
            sheets["sinks"].loc[sheets["sinks"]["label"] == i, "input"] \
                = str(cluster) + "_ind_electricity_bus"
    
    return sheets
