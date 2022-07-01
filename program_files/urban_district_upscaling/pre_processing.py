import xlsxwriter
import pandas as pd
import os
import program_files.urban_district_upscaling.clustering as clustering_py
from program_files.urban_district_upscaling.components \
    import Sink, Source, Storage, Transformer, Link, Bus, Insulation


true_bools = ["yes", "Yes", 1]


def append_component(sheet: str, comp_parameter: dict):
    """
        :param sheet:
        :type sheet: str
        :param comp_parameter:
        :type comp_parameter: dict
    """
    series = pd.Series(comp_parameter)
    sheets[sheet] = pd.concat([sheets[sheet], pd.DataFrame([series])])


def read_standard_parameters(name, param_type, index):
    """
        searches the right entry within the standard parameter sheet

        :param name: component's name
        :type name: str
        :param param_type: determines the technology type
        :type param_type: str
        :param index: defines on which column the index of the parsed \
            Dataframe will be set in order to locate the component's \
            name specific row
        :returns standard_param: technology specific parameters of name
        :rtype standard_param: pandas.Dataframe
        :returns standard_keys: technology specific keys of name
        :rtype standard_keys: list
    """
    # get the param_type sheet from standard parameters
    standard_param_df = standard_parameters.parse(param_type)
    # reset the dataframes index to the index variable set in args
    standard_param_df.set_index(index, inplace=True)
    # locate the row labeled name
    standard_param = standard_param_df.loc[name]
    # get the keys of the located row
    standard_keys = standard_param.keys().tolist()
    # return parameters and keys
    return standard_param, standard_keys


def create_standard_parameter_comp(specific_param: dict,
                                   type,
                                   index,
                                   standard_param_name):
    """
        creates a storage with standard_parameters, based on the
        standard parameters given in the "standard_parameters" dataset
        and adds it to the "sheets"-output dataset.

        :param specific_param: dictionary holding the storage specific
                               parameters (e.g. ng_storage specific, ...)
        :type specific_param: dict
        :param standard_param_name: string defining the storage type
                                    (e.g. central_naturalgas_storage,...)
                                    to locate the right standard parameters
        :type standard_param_name: str
    """
    # extracts the storage specific standard values from the
    # standard_parameters dataset
    standard_param, standard_keys = read_standard_parameters(
        standard_param_name, type, index)
    # insert standard parameters in the components dataset (dict)
    for i in range(len(standard_keys)):
        specific_param[standard_keys[i]] = standard_param[standard_keys[i]]
    # appends the new created component to storages sheet
    append_component(type, specific_param)


def create_central_heat_component(type, bus, central_elec_bus, central_chp):
    """
        In this method, all heat supply systems are calculated for a
        heat input into the district heat network.
        
        :param type: defines the component type
        :type type: str
        :param bus: defines the output bus which is one of the heat
            input buses of the district heating network
        :type bus: str
        :param central_elec_bus:
        :param central_chp:
        :return:
    """
    if type in ['naturalgas_chp', 'biogas_chp']:
        create_central_chp(gastype=type.split("_")[0],
                           output=bus,
                           central_elec_bus=central_elec_bus)
    # central natural gas heating plant
    if type == 'naturalgas_heating_plant':
        create_central_gas_heating_transformer(
            gastype='naturalgas',
            output=bus,
            central_chp=central_chp)
    # central swhp
    central_heatpump_indicator = 0
    if type == 'swhp_transformer' or 'ashp_transformer':
        create_central_heatpump(
            specification='swhp' if type == "swhp_transformer" else "ashp",
            create_bus=True if central_heatpump_indicator == 0 else False,
            output=bus, central_elec_bus=central_elec_bus)
        central_heatpump_indicator += 1

    # central biomass plant
    if type == 'biomass_plant':
        # biomass bus
        Bus.create_standard_parameter_bus(label="central_biomass_bus",
                                          bus_type="central_biomass_bus")

        Transformer.create_transformer(
            building_id="central", output=bus,
            transformer_type="central_biomass_transformer")
    # create central thermal storage
    if type == 'thermal_storage':
        Storage.create_storage(
            building_id="central",
            storage_type="thermal",
            de_centralized="central",
            bus=bus)
    # power to gas system
    if type == 'power_to_gas':
        create_power_to_gas_system(bus=bus)


def central_comp(central):
    """
        In this method, the central components of the energy system are
        added to the scenario, first checking if a heating network is
        foreseen and if so, creating the feeding components, and then
        creating Power to Gas and battery storage if defined in the pre
        scenario.

        :param central: pandas Dataframe holding the information from the \
                prescenario file "central" sheet
        :type central: pd.Dataframe
    """
    j = next(central.iterrows())[1]
    # creation of the bus for the local power exchange
    if j['electricity_bus'] in true_bools:
        Bus.create_standard_parameter_bus(label='central_electricity_bus',
                                          bus_type="central_electricity_bus")

    # central heat supply
    if j["central_heat_supply"] in true_bools:
        num = 1
        column_1 = "heat_input_{}".format(str(num))
        while column_1 in j.keys and j[column_1] in true_bools:
            # create bus which would be used as producer bus in
            # district heating network
            Bus.create_standard_parameter_bus(
                label='central_heat_input{}_bus'.format(num),
                bus_type="central_heat_input_bus",
                dh="dh-system",
                cords=[j["lat.heat_input-{}".format(num)],
                       j["lon.heat_input-{}".format(num)]])
            column = "connected_components_heat_input{}".format(num)
            # create components connected to the producer bus
            for comp in str(j[column]).split(","):
                if j[comp] in true_bools:
                    create_central_heat_component(
                        comp,
                        'central_heat_input{}_bus'.format(num),
                        True if j['electricity_bus'] in true_bools else False,
                        True if j['naturalgas_chp'] in true_bools else False)
            num += 1
            
    # central battery storage
    if j['battery_storage'] in true_bools:
        Storage.create_storage(
            building_id="central",
            storage_type="battery",
            de_centralized="central")


def create_power_to_gas_system(bus):
    """
        TODO DOCSTRING TEXT

        :param bus:
        :type bus:
    """
    for bus_type in ["central_h2_bus", "central_naturalgas_bus"]:
        if bus_type not in sheets["buses"]["label"].to_list():
            # h2 bus
            Bus.create_standard_parameter_bus(label=bus_type,
                                              bus_type=bus_type)
    
    for transformer in ["central_electrolysis_transformer",
                        "central_methanization_transformer",
                        "central_fuelcell_transformer"]:
        Transformer.create_transformer(
            building_id="central", transformer_type=transformer, output=bus)
        
    # storages
    for storage_type in ["h2_storage", "naturalgas_storage"]:
        Storage.create_storage(building_id="central",
                               storage_type=storage_type,
                               de_centralized="central")
        
    # link to chp_naturalgas_bus
    Link.create_link(label='central_naturalgas_chp_naturalgas_link',
                     bus_1='central_naturalgas_bus',
                     bus_2='central_chp_naturalgas_bus',
                     link_type='central_naturalgas_chp_link')


def create_central_heatpump(specification, create_bus,
                            central_elec_bus, output):
    """
        In this method, a central heatpump unit with specified gas type
        is created, for this purpose the necessary data set is obtained
        from the standard parameter sheet, and the component is attached
        to the transformers sheet.
        
       :param specification: string giving the information which type
                              of heatpump shall be added.
        :type specification: str
        :param create_bus: indicates whether a central heatpump
                           electricity bus and further parameters shall
                           be created or not.
        :param central_elec_bus: indicates whether a central elec exists
        :type central_elec_bus: bool
        :param output:
        :type output:
        :return: bool
    """

    if create_bus and "central_heatpump_elec_bus" not in \
            sheets["buses"]["label"].to_list():
        Bus.create_standard_parameter_bus(
            label="central_heatpump_elec_bus",
            bus_type="central_heatpump_electricity_bus")
        if central_elec_bus:
            # connection to central electricity bus
            Link.create_link(label="central_heatpump_electricity_link",
                             bus_1="central_electricity_bus",
                             bus_2="central_heatpump_elec_bus",
                             link_type="building_central_building_link")
    
    Transformer.create_transformer(
            building_id="central", output=output, specific=specification,
            transformer_type='central_' + specification + '_transformer')


def create_central_gas_heating_transformer(gastype,
                                           output, central_chp):
    """
        In this method, a central heating plant unit with specified gas
        type is created, for this purpose the necessary data set is
        obtained from the standard parameter sheet, and the component is
        attached to the transformers sheet.

        :param gastype: string which defines rather naturalgas or biogas
                        is used
        :type gastype: str
        :param output: str containing the transformers output
        :type output: str
        :param central_chp: defines rather a central chp is investable
        :type central_chp: bool
    """

    # plant gas bus
    Bus.create_standard_parameter_bus(label="central_" + gastype + "_plant_bus",
                                  bus_type="central_chp_naturalgas_bus")
    
    if central_chp:
        Link.create_link(label="heating_plant_" + gastype + "_link",
                         bus_1="central_chp_naturalgas_bus",
                         bus_2="central_" + gastype + "_plant_bus",
                         link_type="central_naturalgas_building_link")

    Transformer.create_transformer(
        building_id="central", specific=gastype, output=output,
        transformer_type="central_naturalgas_heating_plant_transformer")


def create_central_chp(gastype, output, central_elec_bus):
    """
        In this method, a central CHP unit with specified gas type is
        created, for this purpose the necessary data set is obtained
        from the standard parameter sheet, and the component is attached
         to the transformers sheet.

        :param gastype: string which defines rather naturalgas or \
            biogas is used
        :type gastype: str
        :param output: string containing the heat output bus name
        :type output: str
        :param central_elec_bus: determines if the central power \
            exchange exists
    """
    # chp gas bus
    Bus.create_standard_parameter_bus(
        label="central_chp_" + gastype + "_bus",
        bus_type="central_chp_" + gastype + "_bus")

    # chp electricity bus
    Bus.create_standard_parameter_bus(
        label="central_chp_" + gastype + "_elec_bus",
        bus_type="central_chp_" + gastype + "_electricity_bus")
    
    if central_elec_bus:
        # connection to central electricity bus
        Link.create_link(label="central_chp_" + gastype + "_elec_central_link",
                         bus_1="central_chp_" + gastype + "_elec_bus",
                         bus_2="central_electricity_bus",
                         link_type="central_chp_elec_central_link")

    Transformer.create_transformer(
        building_id="central",
        transformer_type="central_" + gastype + "_chp",
        specific=gastype,
        output=output)


def create_buses(building, pv_bus: bool, central_elec_bus: bool, gchps):
    """
        todo docstring
        :param building_id: building identification
        :type building_id: str
        :param pv_bus: boolean which defines rather a pv bus is created or not
        :type pv_bus: bool
        :param building_type: defines rather it is a residential or a
                              commercial building
        :type building_type: str
        :param hp_elec_bus: defines rather a heat pump bus and its link
                            is created or not
        :type hp_elec_bus: bool
        :param central_elec_bus: defines rather buildings can be
                                 connected to central elec net or not
        :type central_elec_bus: bool
        :param gchp: defines rather the building can connected to a
                     parcel gchp or not
        :type gchp: bool
        :param gchp_heat_bus:
        :type gchp_heat_bus: str
        :param gchp_elec_bus:
        :type gchp_elec_bus: str

    """
    hp_elec_bus = \
        True if (building['parcel'] != 0
                 and building["gchp"] not in ["No", "no", 0]) \
        or building['ashp'] not in ["No", "no", 0] else False
    gchp = True if building['parcel'] != 0 else False,
    gchp_heat_bus = (building['parcel'][-9:] + "_heat_bus") \
        if (building['parcel'] != 0 and building['parcel'][-9:] in gchps) \
        else None
    gchp_elec_bus = (building['parcel'][-9:] + "_hp_elec_bus") \
        if (building['parcel'] != 0 and building['parcel'][-9:] in gchps) \
        else None

    if building["building type"] == "RES":
        bus = 'building_res_electricity_bus'
    elif building["building type"] == "IND":
        bus = 'building_ind_electricity_bus'
    else:
        bus = 'building_com_electricity_bus'
    if pv_bus or building["building type"] != "0":
        # house electricity bus
        Bus.create_standard_parameter_bus(
            label=(str(building['label']) + "_electricity_bus"),
            bus_type=bus)
        if central_elec_bus:
            # link from central elec bus to building electricity bus
            Link.create_link(
                label=str(building['label']) + "central_electricity_link",
                bus_1="central_electricity_bus",
                bus_2=str(building['label']) + "_electricity_bus",
                link_type="building_central_building_link")

    if building["building type"] not in ["0", 0]:
        # house heat bus
        Bus.create_standard_parameter_bus(
            label=str(building['label']) + "_heat_bus",
            bus_type='building_heat_bus',
            dh="1" if building["latitude"] is not None else "0",
            cords=[building["latitude"], building["longitude"]])

    if hp_elec_bus:
        # building hp electricity bus
        Bus.create_standard_parameter_bus(
            label=str(building['label']) + "_hp_elec_bus",
            bus_type='building_hp_electricity_bus',
            dh="0")
        # electricity link from building electricity bus to hp elec bus
        Link.create_link(label=str(building['label']) + "_gchp_building_link",
                         bus_1=str(building['label']) + "_electricity_bus",
                         bus_2=str(building['label']) + "_hp_elec_bus",
                         link_type="building_hp_elec_link")

        if gchp and gchp_elec_bus is not None:
            Link.create_link(
                label=str(building['label']) + "_parcel_gchp_elec",
                bus_1=str(building['label']) + "_hp_elec_bus",
                bus_2=gchp_elec_bus,
                link_type="building_hp_elec_link")
            Link.create_link(label=str(building['label']) + "_parcel_gchp",
                             bus_1=gchp_heat_bus,
                             bus_2=str(building['label']) + "_heat_bus",
                             link_type="building_hp_elec_link")

    # todo excess constraint costs
    if pv_bus:
        # building pv bus
        Bus.create_standard_parameter_bus(
            label=str(building['label']) + "_pv_bus",
            bus_type='building_pv_bus')

        # link from pv bus to building electricity bus
        Link.create_link(
            label=str(building['label']) + "pv_" + str(building['label'])
                  + "_electricity_link",
            bus_1=str(building['label']) + "_pv_bus",
            bus_2=str(building['label']) + "_electricity_bus",
            link_type="building_pv_central_link")
        if central_elec_bus:
            # link from pv bus to central electricity bus
            Link.create_link(
                label=str(building['label']) + "pv_central_electricity_link",
                bus_1=str(building['label']) + "_pv_bus",
                bus_2="central_electricity_bus",
                link_type="building_pv_central_link")


def create_central_elec_bus_connection(cluster):
    if (cluster + "central_electricity_link") not in sheets["links"].index:
        Link.create_link(
            cluster + "central_electricity_link",
            bus_1="central_electricity_bus",
            bus_2=cluster + "_electricity_bus",
            link_type="building_central_building_link")
        sheets["links"].set_index("label", inplace=True, drop=False)
    if (cluster + "pv_" + cluster + "_electricity_link") \
            not in sheets["links"].index \
            and (cluster + "pv_central") in sheets["links"].index:
        Link.create_link(
            cluster + "pv_" + cluster + "_electricity_link",
            bus_1=cluster + "_pv_bus",
            bus_2=cluster + "_electricity_bus",
            link_type="building_pv_central_link")
        sheets["links"].set_index("label", inplace=True, drop=False)
        

def load_input_data(plain_sheet, standard_parameter_path, pre_scenario):
    global sheets
    global standard_parameters
    sheets = {}
    columns = {}
    # get keys from plain scenario
    plain_sheet = pd.ExcelFile(plain_sheet)
    # load standard parameters from standard parameter file
    standard_parameters = pd.ExcelFile(standard_parameter_path)
    # import the sheet which is filled by the user
    pre_scenario_pd = pd.ExcelFile(pre_scenario)
    
    for i in range(1, len(plain_sheet.sheet_names)):
        if plain_sheet.sheet_names[i] not in ["weather data", "time series"]:
            columns[plain_sheet.sheet_names[i]] = \
                plain_sheet.parse(plain_sheet.sheet_names[i]).keys()
    # append worksheets' names to the list of worksheets
    worksheets = [column for column in columns.keys()]
    # get spreadsheet units from plain sheet
    for sheet in worksheets:
        sheets.update({sheet: pd.DataFrame(columns=(columns[sheet]))})
        units_series = pd.Series(data={a: "x" for a in sheets[sheet].keys()})
        sheets[sheet] = pd.concat([sheets[sheet],
                                   pd.DataFrame([units_series])])
    worksheets += ["weather data", "time series"]
    
    # get the input sheets
    tool = pre_scenario_pd.parse("tool")
    parcel = pre_scenario_pd.parse("parcel")
    central = pre_scenario_pd.parse("central")
    
    return central, parcel, tool, worksheets


def create_gchp(tool, parcel):
    # create GCHPs parcel wise
    gchps = {}
    for num, parcel in parcel.iterrows():
        build_parcel = tool[(tool["active"] == 1)
                            & (tool["gchp"].isin(["Yes", "yes", 1]))
                            & (tool["parcel"] == parcel['ID parcel'])]
        if not build_parcel.empty:
            gchps.update({parcel['ID parcel'][-9:]: parcel['gchp area (m²)']})
    # create gchp relevant components
    for gchp in gchps:
        Transformer.create_transformer(
                building_id=gchp,
                area=gchps[gchp],
                transformer_type="building_gchp_transformer")
        Bus.create_standard_parameter_bus(
                label=gchp + "_hp_elec_bus",
                bus_type="building_hp_electricity_bus")
        Bus.create_standard_parameter_bus(label=gchp + "_heat_bus",
                                          bus_type="building_heat_bus")
    return gchps
    

def urban_district_upscaling_pre_processing(pre_scenario: str,
                                            standard_parameter_path: str,
                                            output_scenario: str,
                                            plain_sheet: str,
                                            clustering: bool,
                                            clustering_dh: bool):
    """
        TODO DOCSTRING TEXT

        :param pre_scenario: path of the pre_scenario file
        :type pre_scenario: str
        :param standard_parameter_path: path of the standard_parameter
                                        file
        :type standard_parameter_path: str
        :param output_scenario: path to which the scenario should be
                                created
        :type output_scenario: str
        :param plain_sheet: path to plain sheet file (holding structure)
        :type plain_sheet: str
        :param clustering: boolean for decision rather the buildings are
                           clustered spatially
        :tpye clustering: bool
        :param clustering_dh: boolean for decision rather the district
            heating connection will be clustered cluster_id wise
        :type clustering_dh: bool
    """

    print('Creating scenario sheet...')
    # loading typical scenario structure from plain sheet
    central, parcel, tool, worksheets = \
        load_input_data(plain_sheet, standard_parameter_path, pre_scenario)
    
    # create central components
    central_comp(central)
    
    # set variable for central heating / electricity if activated to
    # decide rather a house can be connected to the central heat
    # network / central electricity network or not
    central_electricity_network = False
    p2g_link = False
    # update the values regarding the values given in central sheet
    for i, j in central.iterrows():
        if j['electricity_bus'] in ['Yes', 'yes', 1]:
            central_electricity_network = True
        if j['power_to_gas'] in ['Yes', 'yes', 1]:
            p2g_link = True

    gchps = create_gchp(tool, parcel)
    
    for num, building in tool[tool["active"] == 1].iterrows():
        label = building["label"]
        # foreach building the three necessary buses will be created
        pv_bool = False
        for roof_num in range(1, 29):
            if building['st or pv %1d' % roof_num] == "pv&st":
                pv_bool = True
        create_buses(
            building=building,
            pv_bus=pv_bool,
            central_elec_bus=central_electricity_network,
            gchps=gchps)
        Sink.create_sinks(sink_id=label,
                          building_type=building['building type'],
                          units=building['units'],
                          occupants=building['occupants per unit'],
                          yoc=building['year of construction'],
                          area=building['living space'] * building['floors'],
                          standard_parameters=standard_parameters)

        Insulation.create_building_insulation(
            building_id=label,
            yoc=building['year of construction'],
            areas=[building["windows"], building["walls_wo_windows"],
                   building["roof area"]],
            roof_type=building["rooftype"],
            standard_parameters=standard_parameters)
        
        # create sources
        Source.create_sources(building=building, clustering=clustering)
        # create transformer
        Transformer.building_transformer(building, p2g_link, true_bools)
        # create storages
        Storage.building_storages(building, true_bools)

        print(str(label) + ' subsystem added to scenario sheet.')
    for sheet_tbc in ["energysystem", "weather data", "time series",
                      "district heating"]:
        sheets[sheet_tbc] = standard_parameters.parse(sheet_tbc)

    if clustering:
        clustering_py.clustering_method(tool, standard_parameters, worksheets,
                                        sheets, central_electricity_network,
                                        clustering_dh)
    # open the new excel file and add all the created components
    j = 0
    writer = pd.ExcelWriter(output_scenario, engine='xlsxwriter')
    for i in sheets:
        sheets[i].to_excel(writer, worksheets[j], index=False)
        j = j + 1
    print("Scenario created. It can now be executed.")
    writer.save()
