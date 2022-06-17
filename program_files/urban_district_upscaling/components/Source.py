from program_files.postprocessing.plotting import get_pv_st_dir


def create_pv_source(building_id, plant_id, azimuth, tilt, area,
                     latitude, longitude):
    """
        TODO DOCSTRINGTEXT
        :param building_id: building label
        :type building_id: str
        :param plant_id: roof part number
        :type plant_id: str
        :param azimuth: azimuth of given roof part
        :type azimuth: float
        :param tilt: tilt of given roof part
        :type tilt: float
        :param area: area of the given roof part
        :type area: float
        :param latitude: geographic latitude of the building
        :type latitude: float
        :param longitude: geographic longitude of the building
        :type longitude: float
    """
    from program_files.urban_district_upscaling.pre_processing \
        import append_component, read_standard_parameters
    # technical parameters
    pv_dict = \
        {'label': str(building_id) + '_' + str(plant_id) + '_pv_source',
         'existing capacity': 0,
         'min. investment capacity': 0,
         'output': str(building_id) + '_pv_bus',
         'Azimuth': azimuth,
         'Surface Tilt': tilt,
         'Latitude': latitude,
         'Longitude': longitude,
         'input': 0}
    # extracts the pv source specific standard values from the
    # standard_parameters dataset
    pv_param, pv_keys = read_standard_parameters(
            'fixed photovoltaic source', "sources", "comment")
    for i in range(len(pv_keys)):
        pv_dict[pv_keys[i]] = pv_param[pv_keys[i]]

    pv_dict['max. investment capacity'] = \
        pv_param['Capacity per Area (kW/m2)'] * area

    # produce a pandas series out of the dict above due to easier appending
    append_component("sources", pv_dict)
    
    
def create_solarthermal_source(building_id, plant_id, azimuth, tilt, area,
                               latitude, longitude):
    """
        TODO DOCSTRINGTEXT
        :param building_id: building label
        :type building_id: str
        :param plant_id: roof part number
        :type plant_id: str
        :param azimuth: azimuth of given roof part
        :type azimuth: float
        :param tilt: tilt of given roof part
        :type tilt: float
        :param area: area of the given roof part
        :type area: float
        :param latitude: geographic latitude of the building
        :type latitude: float
        :param longitude: geographic longitude of the building
        :type longitude: float
    """
    from program_files.urban_district_upscaling.pre_processing \
        import append_component, read_standard_parameters
    # technical parameters
    st_dict = \
        {'label': (str(building_id) + '_' + str(plant_id)
                   + '_solarthermal_source'),
         'existing capacity': 0,
         'min. investment capacity': 0,
         'output': str(building_id) + '_heat_bus',
         'Azimuth': azimuth,
         'Surface Tilt': tilt,
         'Latitude': latitude,
         'Longitude': longitude,
         'input': str(building_id) + '_electricity_bus'}
    # extracts the st source specific standard values from the
    # standard_parameters dataset
    st_param, st_keys = read_standard_parameters(
            'solar_thermal_collector', "sources", "comment")
    for i in range(len(st_keys)):
        st_dict[st_keys[i]] = st_param[st_keys[i]]

    st_dict['max. investment capacity'] = \
        st_param['Capacity per Area (kW/m2)'] * area
    
    append_component("sources", st_dict)
    
    
def create_competition_constraint(component1, component2, limit):
    """
        TODO DOCSTRINGTEXT
        :param component1: label of the first component in competition
        :type component1: str
        :param component2: label of the second component in competition
        :type component2: str
        :param limit:
        :type limit: float
    """
    from program_files.urban_district_upscaling.pre_processing \
        import append_component, read_standard_parameters
    pv_param, pv_keys = read_standard_parameters(
            'fixed photovoltaic source', "sources", "comment")
    st_param, st_keys = read_standard_parameters(
            'solar_thermal_collector', "sources", "comment")
    # define individual values
    constraint_dict = {'component 1': component1,
                       'factor 1': 1 / pv_param['Capacity per Area (kW/m2)'],
                       'component 2': component2,
                       'factor 2': 1 / st_param['Capacity per Area (kW/m2)'],
                       'limit': limit, 'active': 1}
    append_component("competition constraints", constraint_dict)


def create_sources(building, clustering):
    """
    
    """
    # create pv-sources and solar thermal-sources including area
    # competition
    for roof_num in range(1, 29):
        if building['roof area (m²) %1d' % roof_num]:
            plant_id = str(roof_num)
            if building['st or pv %1d' % roof_num] == "pv&st":
                create_pv_source(
                        building_id=building['label'],
                        plant_id=plant_id,
                        azimuth=building['azimuth (°) %1d' % roof_num],
                        tilt=building['surface tilt (°) %1d' % roof_num],
                        area=building['roof area (m²) %1d' % roof_num],
                        latitude=building['latitude'],
                        longitude=building['longitude'])
            if building['st or pv %1d' % roof_num] in ["st", "pv&st"] \
                    and building["building type"] not in ["0", 0]:
                create_solarthermal_source(
                        building_id=building['label'],
                        plant_id=plant_id,
                        azimuth=building['azimuth (°) %1d' % roof_num],
                        tilt=building['surface tilt (°) %1d' % roof_num],
                        area=building['roof area (m²) %1d' % roof_num],
                        latitude=building['latitude'],
                        longitude=building['longitude'])
            if building['st or pv %1d' % roof_num] == "pv&st" \
                    and building["building type"] != "0" \
                    and not clustering:
                create_competition_constraint(
                    component1=(building['label'] + '_'
                                + plant_id + '_pv_source'),
                    component2=(building['label'] + '_' + plant_id
                                + '_solarthermal_source'),
                    limit=building['roof area (m²) %1d' % roof_num])


def cluster_sources_information(source, source_param, azimuth_type, type):
    """
        Collects the source information of the selected type, and
        inserts it into the dict containing the cluster specific
        sources data.

        :param source: Dataframe containing the source under \
            investigation
        :type source: pd.DataFrame
        :param source_param: dictionary containing the cluster summed \
            source information
        :type source_param: dict
        :param azimuth_type: definies the celestial direction of the \
            source to be clustered
        :type azimuth_type: str
        :param type: source type needed to define the dict entry \
            to be modified
        :type type: str

        :return: - **source_param** (dict) - dict extended by a new \
            entry
    """
    # counter
    source_param[type + "_{}".format(azimuth_type)][0] += 1
    # maxinvest
    source_param[type + "_{}".format(azimuth_type)][1] \
        += source["max. investment capacity"]
    # periodical_costs
    source_param[type + "_{}".format(azimuth_type)][2] \
        += source["periodical costs"]
    # periodical constraint costs
    source_param[type + "_{}".format(azimuth_type)][3] \
        += source["periodical constraint costs"]
    # variable costs
    source_param[type + "_{}".format(azimuth_type)][4] \
        += source["variable costs"]
    # albedo
    source_param[type + "_{}".format(azimuth_type)][5] += source["Albedo"]
    # altitude
    source_param[type + "_{}".format(azimuth_type)][6] += source["Altitude"]
    # azimuth
    source_param[type + "_{}".format(azimuth_type)][7] += source["Azimuth"]
    # surface tilt
    source_param[type + "_{}".format(azimuth_type)][8] \
        += source["Surface Tilt"]
    # latitude
    source_param[type + "_{}".format(azimuth_type)][9] += source["Latitude"]
    # longitude
    source_param[type + "_{}".format(azimuth_type)][10] += source["Longitude"]
    # remove the considered source from sources sheet
    sheets["sources"] = sheets["sources"].drop(index=source["label"])
    # return the modified source_param dict to the sources clustering
    # method
    return source_param


def sources_clustering(source_param, building, sheets_clustering):
    """
        In this method, the information of the photovoltaic and solar
        thermal systems to be clustered is collected, and the systems
        whose information has been collected are deleted.
        :param source_param: dictionary containing the cluster summed \
            source information
        :type source_param: dict
        :param building: DataFrame containing the building row from the\
            pre scenario sheet
        :type building: pd.Dataframe
        :param sheets_clustering: copy of the scenario created within \
            the pre_processing.py
        :type sheets_clustering: pd.DataFrame

        :return: - **source_param** (dict) - containing the cluster \
            summed source information attached within this method
    """
    for index, sources in sheets_clustering["sources"].iterrows():
        # collecting information for bundled photovoltaic systems
        if sources["technology"] in ["photovoltaic",
                                     "solar_thermal_flat_plate"]:
            # check the azimuth type for clustering in 8 cardinal
            # directions
            dir_dict = {"south_west": [-157.5, -112.5],
                        "west": [-112.5, -67.5],
                        "north_west": [-67.5, -22.5],
                        "north": [-22.5, 22.5],
                        "north_east": [22.5, 67.5],
                        "east": [67.5, 112.5],
                        "south_east": [112.5, 157.5]}
            azimuth_type = None
            for dire in dir_dict:
                if not dir_dict[dire][0] <= sources["Azimuth"] \
                       < dir_dict[dire][1]:
                    pass
                else:
                    azimuth_type = dire
            azimuth_type = "south" if azimuth_type is None else azimuth_type
            # Photovoltaic clustering - collecting the sources
            # information for each cluster
            if str(building[0]) in sources["label"] \
                    and sources["technology"] == "photovoltaic" \
                    and sources["label"] in sheets["sources"].index:
                source_param = \
                    cluster_sources_information(sources, source_param,
                                                azimuth_type, "pv")
            # Solar thermal clustering - collecting the sources
            # information for each cluster
            if str(building[0]) in sources["label"] \
                    and sources["technology"] == \
                    "solar_thermal_flat_plate" \
                    and sources["label"] in sheets["sources"].index:
                source_param = \
                    cluster_sources_information(sources, source_param,
                                                azimuth_type, "st")
    # return the collected data to the main clustering method
    return source_param
