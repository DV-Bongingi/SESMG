def create_central_heat_component(
    comp_type, bus, central_elec_bus, central_chp, sheets, area
):
    """
    In this method, all heat supply systems are calculated for a
    heat input into the district heat network.

    :param comp_type: defines the component type
    :type comp_type: str
    :param bus: defines the output bus which is one of the heat
        input buses of the district heating network
    :type bus: str
    :param central_elec_bus:
    :param central_chp:
    :param sheets:
    :return:
    """
    from program_files import Storage

    print(comp_type)
    if comp_type in ["naturalgas_chp", "biogas_chp", "pellet_chp", "woodchips_chp"]:
        sheets = create_central_chp(
            gas_type=comp_type.split("_")[0],
            output=bus,
            central_elec_bus=central_elec_bus,
            sheets=sheets,
        )
    # central natural gas heating plant
    if comp_type == "naturalgas_heating_plant":
        sheets = create_central_gas_heating_transformer(
            gas_type="naturalgas", output=bus, central_chp=central_chp, sheets=sheets
        )
    # central swhp
    central_heatpump_indicator = 0
    if (
        comp_type == "swhp_transformer"
        or comp_type == "ashp_transformer"
        or comp_type == "gchp_transformer"
    ):
        specification_dict = {
            "swhp_transformer": "swhp",
            "ashp_transformer": "ashp",
            "gchp_transformer": "gchp",
        }
        sheets = create_central_heatpump(
            specification=specification_dict.get(comp_type),
            create_bus=True if central_heatpump_indicator == 0 else False,
            output=bus,
            central_elec_bus=central_elec_bus,
            sheets=sheets,
            area=area,
        )
        central_heatpump_indicator += 1

    # create central thermal storage
    if comp_type == "thermal_storage":
        sheets = Storage.create_storage(
            building_id="central",
            storage_type="thermal",
            de_centralized="central",
            bus=bus,
            sheets=sheets,
        )
    # power to gas system
    if comp_type == "power_to_gas":
        sheets = create_power_to_gas_system(bus=bus, sheets=sheets)

    return sheets


def central_comp(central, true_bools, sheets):
    """
        In this method, the central components of the energy system are
        added to the scenario, first checking if a heating network is
        foreseen and if so, creating the feeding components, and then
        creating Power to Gas and battery storage if defined in the pre
        scenario.

        :param central: pandas Dataframe holding the information from the \
                prescenario file "central" sheet
        :type central: pd.Dataframe
        :param true_bools:
        :type true_bools:
        :param sheets:
        :type sheets:
        :param central_elec_bus:
        :type central_elec_bus:
    """
    from program_files import Bus, Storage, Source, Link, get_central_comp_active_status

    central_elec_bus = False
    # creation of the bus for the local power exchange
    if get_central_comp_active_status(central, "electricity_exchange"):
        sheets = Bus.create_standard_parameter_bus(
            label="central_electricity_bus",
            bus_type="central_electricity_bus",
            sheets=sheets,
        )
        central_elec_bus = True

    # create central pv systems
    for num, pv in central.loc[
        ((central["technology"] == "st") | (central["technology"] == "pv&st"))
        & (central["active"] == 1)
    ].iterrows():
        if (
            len(
                central.loc[
                    (central["component"] == pv["dh_connection"])
                    & (central["active"] == 1)
                ]
            )
            >= 1
        ):
            # create pv bus
            sheets = Bus.create_standard_parameter_bus(
                label=pv["component"] + "_pv_bus",
                bus_type="central_pv_bus",
                sheets=sheets,
            )
            # house electricity bus
            sheets = Bus.create_standard_parameter_bus(
                label=(pv["component"] + "_electricity_bus"),
                bus_type="building_com_electricity_bus",
                sheets=sheets,
            )

            if central_elec_bus:
                # link from pv bus to central electricity bus
                sheets = Link.create_link(
                    label=pv["component"] + "pv_central_electricity_link",
                    bus_1=pv["component"] + "_pv_bus",
                    bus_2="central_electricity_bus",
                    link_type="building_pv_central_link",
                    sheets=sheets,
                )
                # link from central elec bus to building electricity bus
                sheets = Link.create_link(
                    label=pv["component"] + "central_electricity_link",
                    bus_1="central_electricity_bus",
                    bus_2=pv["component"] + "_electricity_bus",
                    link_type="building_central_building_link",
                    sheets=sheets,
                )

            sheets = Source.create_sources(
                {
                    "label": pv["component"],
                    "building type": "central",
                    "st or pv %1d" % 1: str(pv["technology"]),
                    "azimuth (°) {}".format(1): pv["azimuth"],
                    "surface tilt (°) {}".format(1): pv["surface tilt"],
                    "latitude": pv["lat."],
                    "longitude": pv["lon."],
                    "roof area (m²) {}".format(1): pv["area (m2)"],
                    "roof area (m²) {}".format(2): 0,
                },
                False,
                sheets,
                "central_" + pv["dh_connection"] + "_bus",
            )

    # central heat supply
    if (
        True
        in (
            central.loc[central["technology"] == "heat_input_bus"]["active"] == 1
        ).values
    ):
        for num, bus in central.loc[
            (central["technology"] == "heat_input_bus") & (central["active"] == 1)
        ].iterrows():
            # create bus which would be used as producer bus in
            # district heating network
            sheets = Bus.create_standard_parameter_bus(
                label="central_{}_bus".format(bus["component"]),
                bus_type="central_heat_input_bus",
                cords=[bus["lat."], bus["lon."], "dh-system"],
                sheets=sheets,
            )
            central_chp = (
                True
                if len(
                    central.loc[
                        (central["technology"].str.contains("chp"))
                        & (central["active"] == 1)
                    ].values
                )
                >= 1
                else False
            )
            # create components connected to the producer bus
            for num, comp in central.loc[
                central["dh_connection"] == bus["component"]
            ].iterrows():
                if comp["active"] in true_bools:
                    sheets = create_central_heat_component(
                        comp_type=comp["technology"],
                        bus="central_{}_bus".format(bus["component"]),
                        central_elec_bus=central_elec_bus,
                        central_chp=central_chp,
                        sheets=sheets,
                        area=comp["area (m2)"]
                        if comp["technology"] == "gchp_transformer"
                        else "0",
                    )

    # central battery storage
    if central.loc[(central["technology"] == "battery")]["active"].values[0] == 1:
        sheets = Storage.create_storage(
            building_id="central",
            storage_type="battery",
            de_centralized="central",
            sheets=sheets,
        )

    if (
        central.loc[(central["technology"] == "timeseries_source")]["active"].values[0]
        == 1
    ):
        # house electricity bus
        sheets = Bus.create_standard_parameter_bus(
            label=("screw_turbine_" + "_electricity_bus"),
            bus_type="central_pv_bus",
            sheets=sheets,
        )

        if central_elec_bus:
            # link from pv bus to central electricity bus
            sheets = Link.create_link(
                label="screw_turbine_" + "pv_central_electricity_link",
                bus_1="screw_turbine_" + "_electricity_bus",
                bus_2="central_electricity_bus",
                link_type="building_pv_central_link",
                sheets=sheets,
            )
        sheets = Source.create_timeseries_source(
            sheets, "screw_turbine", "screw_turbine_" + "_electricity_bus"
        )
    return sheets


def create_power_to_gas_system(bus, sheets):
    """
    TODO DOCSTRING TEXT

    :param bus:
    :type bus:
    :param sheets:
    :type sheets:
    """
    from program_files import Bus, Transformer, Storage, Link

    for bus_type in ["central_h2_bus", "central_naturalgas_bus"]:
        if bus_type not in sheets["buses"]["label"].to_list():
            # h2 bus
            sheets = Bus.create_standard_parameter_bus(
                label=bus_type, bus_type=bus_type, sheets=sheets
            )

    for transformer in [
        "central_electrolysis_transformer",
        "central_methanization_transformer",
        "central_fuelcell_transformer",
    ]:
        sheets = Transformer.create_transformer(
            building_id="central",
            transformer_type=transformer,
            output=bus,
            sheets=sheets,
        )

    # storages
    for storage_type in ["h2_storage", "naturalgas_storage"]:
        sheets = Storage.create_storage(
            building_id="central",
            storage_type=storage_type,
            de_centralized="central",
            sheets=sheets,
        )

    # link to chp_naturalgas_bus
    return Link.create_link(
        label="central_naturalgas_chp_naturalgas_link",
        bus_1="central_naturalgas_bus",
        bus_2="central_chp_naturalgas_bus",
        link_type="central_naturalgas_chp_link",
        sheets=sheets,
    )


def create_central_heatpump(
    specification, create_bus, central_elec_bus, output, sheets, area
):
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
     :param sheets:
     :type sheets:
     :param area:
     :type area: str
     :return: bool
    """
    from program_files import Bus, Transformer, Link

    if (
        create_bus
        and "central_heatpump_elec_bus" not in sheets["buses"]["label"].to_list()
    ):
        sheets = Bus.create_standard_parameter_bus(
            label="central_heatpump_elec_bus",
            bus_type="central_heatpump_electricity_bus",
            sheets=sheets,
        )
        if central_elec_bus:
            # connection to central electricity bus
            sheets = Link.create_link(
                label="central_heatpump_electricity_link",
                bus_1="central_electricity_bus",
                bus_2="central_heatpump_elec_bus",
                link_type="building_central_building_link",
                sheets=sheets,
            )

    return Transformer.create_transformer(
        building_id="central",
        output=output,
        specific=specification,
        transformer_type="central_" + specification + "_transformer",
        sheets=sheets,
        area=area,
    )


def create_central_gas_heating_transformer(gas_type, output, central_chp, sheets):
    """
    In this method, a central heating plant unit with specified gas
    type is created, for this purpose the necessary data set is
    obtained from the standard parameter sheet, and the component is
    attached to the transformers sheet.

    :param gas_type: string which defines rather naturalgas or biogas
                    is used
    :type gas_type: str
    :param output: str containing the transformers output
    :type output: str
    :param central_chp: defines rather a central chp is investable
    :type central_chp: bool
    :param sheets:
    :type sheets:
    """
    from program_files import Bus, Transformer, Link

    # plant gas bus
    sheets = Bus.create_standard_parameter_bus(
        label="central_" + gas_type + "_plant_bus",
        bus_type="central_chp_naturalgas_bus",
        sheets=sheets,
    )

    if central_chp:
        sheets = Link.create_link(
            label="heating_plant_" + gas_type + "_link",
            bus_1="central_chp_naturalgas_bus",
            bus_2="central_" + gas_type + "_plant_bus",
            link_type="central_naturalgas_building_link",
            sheets=sheets,
        )

    return Transformer.create_transformer(
        building_id="central",
        specific=gas_type,
        output=output,
        sheets=sheets,
        transformer_type="central_naturalgas_heating_plant_transformer",
    )


def create_central_chp(gas_type, output, central_elec_bus, sheets):
    """
        In this method, a central CHP unit with specified gas type is
        created, for this purpose the necessary data set is obtained
        from the standard parameter sheet, and the component is attached
         to the transformers sheet.

        :param gas_type: string which defines rather naturalgas or \
            biogas is used
        :type gas_type: str
        :param output: string containing the heat output bus name
        :type output: str
        :param central_elec_bus: determines if the central power \
            exchange exists
        :param sheets
    """
    from program_files import Bus, Transformer, Link

    # chp gas bus
    sheets = Bus.create_standard_parameter_bus(
        label="central_chp_" + gas_type + "_bus",
        bus_type="central_chp_" + gas_type + "_bus",
        sheets=sheets,
    )

    # chp electricity bus
    sheets = Bus.create_standard_parameter_bus(
        label="central_chp_" + gas_type + "_elec_bus",
        bus_type="central_chp_" + gas_type + "_electricity_bus",
        sheets=sheets,
    )

    if central_elec_bus:
        # connection to central electricity bus
        sheets = Link.create_link(
            label="central_chp_" + gas_type + "_elec_central_link",
            bus_1="central_chp_" + gas_type + "_elec_bus",
            bus_2="central_electricity_bus",
            link_type="central_chp_elec_central_link",
            sheets=sheets,
        )

    return Transformer.create_transformer(
        building_id="central",
        transformer_type="central_" + gas_type + "_chp",
        specific=gas_type,
        output=output,
        sheets=sheets,
    )
