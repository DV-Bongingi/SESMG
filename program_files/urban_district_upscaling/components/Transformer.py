transf_dict = {
    "building_gchp_transformer": [
        '_gchp_transformer',
        '_hp_elec_bus',
        '_heat_bus',
        'None'],
    "building_ashp_transformer": [
        '_ashp_transformer',
        '_hp_elec_bus',
        '_heat_bus',
        'None'],
    'building_gasheating_transformer': [
        '_gasheating_transformer',
        '_gas_bus',
        '_heat_bus',
        'None'],
    "building_electricheating_transformer": [
        '_electricheating_transformer',
        '_electricity_bus',
        '_heat_bus',
        'None']}


def create_transformer(building_id, transformer_type,
                       building_type=None, area="None", specific="None",
                       output="None"):
    from program_files import create_standard_parameter_comp
    from program_files import Bus

    # TODO for gchps
    # probe_length = \
    #    transformers_standard_parameters.loc['building_gchp_transformer'][
    #        'length of the geoth. probe']
    # heat_extraction = \
    #    transformers_standard_parameters.loc['building_gchp_transformer'][
    #        'heat extraction']
    # min_bore_hole_area = \
    #    transformers_standard_parameters.loc['building_gchp_transformer'][
    #        'min. borehole area']
    transf_dict.update({
        "central_" + specific + "_chp": [
            "_" + specific + '_chp_transformer',
            "_chp_" + specific + "_bus",
            "_chp_" + specific + "_elec_bus",
            output],
        "central_naturalgas_heating_plant_transformer": [
            "_" + specific + '_heating_plant_transformer',
            "_" + specific + "_plant_bus",
            output,
            "None"],
        "central_" + specific + "_transformer": [
            "_" + specific + "_transformer",
            "_heatpump_elec_bus",
            output,
            "None"],
        "central_biomass_transformer": [
            '_biomass_transformer',
            "_biomass_bus",
            output,
            "None"],
        "central_electrolysis_transformer": [
            "_electrolysis_transformer",
            "_electricity_bus",
            "_h2_bus",
            "None"],
        "central_methanization_transformer":[
            '_methanization_transformer',
             "_h2_bus",
            "_naturalgas_bus",
             "None"],
        "central_fuelcell_transformer": [
            '_fuelcell_transformer',
            "_h2_bus",
            "_electricity_bus",
            output]
    })
    if building_type is not None:
        if building_type == "RES":
            bus = 'building_res_gas_bus'
        elif building_type == "IND":
            bus = 'building_ind_gas_bus'
        else:
            bus = 'building_com_gas_bus'
            # building gas bus
        Bus.create_standard_parameter_bus(label=str(building_id) + "_gas_bus",
                                          bus_type=bus)
    create_standard_parameter_comp(
        specific_param={
            'label': str(building_id) + transf_dict.get(transformer_type)[0],
            'comment': 'automatically_created',
            'input': str(building_id) + transf_dict.get(transformer_type)[1],
            'output': (str(building_id) + transf_dict.get(transformer_type)[2])
            if output == "None" else output,
            'output2': transf_dict.get(transformer_type)[3],
            'area': area},
        type="transformers",
        index="comment",
        standard_param_name=transformer_type)


def building_transformer(building, p2g_link, true_bools):
    """

    """
    from program_files import Link
    transf_dict = {
        'ashp': [None, "building_ashp_transformer"],
        'gas heating': [building['building type'],
                        "building_gasheating_transformer"],
        'electric heating': [None, "building_electricheating_transformer"]}
    for transf in transf_dict:
        # creates air source heat-pumps
        if building[transf] in true_bools:
            create_transformer(
                building_id=building['label'],
                building_type=transf_dict[transf][0],
                transformer_type=transf_dict[transf][1])
            if transf == 'gas heating' and p2g_link:
                Link.create_link(
                        label='central_naturalgas_' + building['label']
                              + 'link',
                        bus_1='central_naturalgas_bus',
                        bus_2=building['label'] + '_gas_bus',
                        link_type='central_naturalgas_building_link')
    
    
def cluster_transf_information(transformer, transf_param, transf_type, sheets):
    """
        Collects the transformer information of the selected type, and
        inserts it into the dict containing the cluster specific
        transformer data.

        :param transformer: Dataframe containing the transformer under \
            investigation
        :type transformer: pd.DataFrame
        :param transf_param: dictionary containing the cluster summed \
            transformer information
        :type transf_param: dict
        :param type: transformer type needed to define the dict entry \
            to be modified
        :type type: str

        :return:
    """
    param_dict = {0: 1,
                  1: transformer["efficiency"],
                  3: transformer["periodical costs"],
                  4: transformer["variable output constraint costs"]}
    for num in param_dict:
        # counter
        transf_param[transf_type][num] += param_dict[num]

    if transf_type in ["ashp", "gchp"]:
        transf_param[transf_type][2] += transformer["efficiency2"]
    
    if transf_type == "gchp":
        transf_param[transf_type][5] += transformer["area"]
    # remove the considered tranformer from transformer sheet
    sheets["transformers"] = \
        sheets["transformers"].drop(index=transformer["label"])
    # return the modified transf_param dict to the transformer clustering
    # method
    return transf_param, sheets

    
def transformer_clustering(building, sheets_clustering,
                           transf_param, heat_buses_gchps, sheets):
    """
        Main method to collect the information about the transformer
        (gasheating, ashp, gchp, electric heating), which are located
        in the considered cluster.

        :param building: DataFrame containing the building row from the\
            pre scenario sheet
        :type building: pd.Dataframe
        :param sheets_clustering:
        :type sheets_clustering: pd.DataFrame
        :param transf_param: dictionary containing the collected \
            transformer information
        :type transf_param: dict
        :param heat_buses_gchps: list, used to collect the gchps heat \
            output buses
        :type heat_buses_gchps: list

        :return:
    """
    for index, transformer in sheets_clustering["transformers"].iterrows():
        label = transformer["label"]
        technologies = ["gasheating",  "electricheating", "ashp"]
        # collect gasheating transformer information
        if str(building[0]) in label and label in sheets["transformers"].index:
            if label.split("_")[1] in technologies:
                transf_param, sheets = cluster_transf_information(
                    transformer, transf_param, label.split("_")[1], sheets)

        # if parcel label != 0
        if str(building[1]) != "0":
            # collect gchp data
            if str(building[1])[-9:] in transformer["label"] \
                    and "gchp" in transformer["label"] \
                    and transformer["label"] in sheets["transformers"].index:
                transf_param, sheets = cluster_transf_information(
                    transformer, transf_param, "gchp", sheets)
                sheets["buses"].set_index("label", inplace=True, drop=False)
                if transformer["output"] in sheets["buses"].index:
                    sheets["buses"] = \
                        sheets["buses"].drop(index=transformer["output"])
                if transformer["label"] in sheets["transformers"]:
                    sheets["transformers"] = \
                        sheets["transformers"].drop(index=transformer["label"])
    # return the collected data to the main clustering method
    return heat_buses_gchps, transf_param


def create_cluster_transformer(type, transf_param, cluster):
    """

    :param type:
    :param transf_param:
    :return:
    """
    from program_files import read_standard_parameters, append_component
    type_dict = {"gasheating": "building_gasheating_transformer",
                 "electricheating": "building_electricheating_transformer",
                 "ashp":  "building_ashp_transformer",
                 "gchp": "building_gchp_transformer"}
    standard_param, keys = read_standard_parameters(
            "building_gchp_transformer", "transformers", "comment")
    specific_dict = {
        "label": str(cluster) + transf_dict.get(type_dict.get(type))[0],
        "comment": "automatically created",
        "input": str(cluster) + transf_dict.get(type_dict.get(type))[1],
        "output": str(cluster) + transf_dict.get(type_dict.get(type))[2],
        "output2": "None",
        "efficiency": transf_param[type][1] / transf_param[type][0],
        "periodical costs": transf_param[type][3] / transf_param[type][0],
        "variable output constraint costs":
            transf_param[type][4] / transf_param[type][0],
        "max. investment capacity":
            standard_param["max. investment capacity"] * transf_param[type][0],
        "area":  transf_param["gchp"][5] if type == "gchp" else "None"}
    
    if type == "ashp" or type == "gchp":
        specific_dict["efficiency2"] = transf_param[type][2] \
                                    / transf_param[type][0]

    # produce a pandas series out of the dict above due to
    # easier appending
    append_component("transformers", specific_dict)
