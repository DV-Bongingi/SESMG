# TODO Docstrings zu Ende schreiben
from operator import itemgetter
import numpy
import math
from sympy import Symbol, solve
from pyproj import Transformer
import pandas as pd
import dhnx
import dhnx.plotting
import dhnx.network
import dhnx.optimization_oemof_heatpipe
import matplotlib.pyplot as plt
import dhnx.optimization as optimization
import oemof.solph as solph
import os
import logging

thermal_network = dhnx.network.ThermalNetwork()

transf_WGS84_GK = Transformer.from_crs("EPSG:4326", "EPSG:31466")
transf_GK_WGS84 = Transformer.from_crs("EPSG:31466", "EPSG:4326")
component_param = \
        pd.read_csv("program_files/technical_data"
                    "/district_heating/component_parameters.csv",
                    index_col="label")


def convert_dh_street_sections_list(street_sections):
    """
        convert street sections Dataframe to GK to reduce redundancy
        :param street_sections: Dataframe holding start and end points
                                of the streets under investigation
        :type street_sections: pd.Dataframe
        :return: - **street_sections** (pd.Dataframe) - holding converted
                                                        points
    """
    for num, point in street_sections.iterrows():
        (street_sections.at[num, "lat. 1st intersection"],
         street_sections.at[num, "lon. 1st intersection"]) \
            = transf_WGS84_GK.transform(point["lat. 1st intersection"],
                                        point["lon. 1st intersection"])
        (street_sections.at[num, "lat. 2nd intersection"],
         street_sections.at[num, "lon. 2nd intersection"]) \
            = transf_WGS84_GK.transform(point["lat. 2nd intersection"],
                                        point["lon. 2nd intersection"])
    return street_sections


def calc_perpendicular_distance_line_point(p1, p2, p3, converted=False):
    """
        Determination of the perpendicular foot point as well as the
        distance between point and straight line
        p1 - Starting point of the road section
        p2 - Ending point of the road section
        p3 - point of the building under consideration
        Are three geographical points where p1 and p2 represent the
        street as the crow flies and p3 represents the house under
        consideration.
        The points consist an array e.g [51.5553878, 7.21026385] which
        northern latitude and eastern longitude.
        distance = sqrt(dx * dx + dy * dy)

        distance:
        dx = 111.3 * cos(lat) * (lon1 - lon2)
        lat = (lat1 + lat2) / 2 * 0.01745
        dy = 111.3 * (lat1 - lat2)
        lat1, lat2, lon1, lon2: northern latitude, eastern longitude in
        degree
    """
    # check rather the third point is already converted or not
    if not converted:
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:31466")
        (p3[0], p3[1]) = transformer.transform(p3[0], p3[1])
    house = numpy.array(p3)
    road_part_limit1 = numpy.array(p1)
    road_part_limit2 = numpy.array(p2)
    # Determining the distance via the orthogonality condition
    # Direction vector of the straight line
    vec_direction = road_part_limit2 - road_part_limit1
    t = Symbol("t")
    vec_l = road_part_limit1 + vec_direction * t
    # Determining the distance via the orthogonality condition;
    # Solve with SymPy
    t = solve(numpy.dot(vec_l - house, vec_direction), t)
    if 0 <= t[0] <= 1:
        # pnt 4 is the closest point on the street to the house
        pnt4 = road_part_limit1 + vec_direction * t
        perp_foot = numpy.array([float(pnt4[0]), float(pnt4[1])])
        perp_foot[0], perp_foot[1] = transf_GK_WGS84.transform(perp_foot[0],
                                                               perp_foot[1])
        house[0], house[1] = transf_GK_WGS84.transform(house[0], house[1])
        # arithmetic mean of latitudes
        lat = (perp_foot[0] + house[0]) / 2
        # distance calculation
        dx = 111.3 * (perp_foot[1] - house[1]) * numpy.cos(numpy.deg2rad(lat))
        dy = 111.3 * (perp_foot[0] - house[0])
        distance = math.sqrt(dx ** 2 + dy ** 2) * 1000
        return [perp_foot[0], perp_foot[1], distance, t[0]]
    else:
        return []


def get_nearest_perp_foot_point(building, streets, index, building_type):
    """
        Uses the calc_perpendicular_distance_line_point method and finds
        the shortest distance to a road from its results.
        
        :param building: coordinates of the building under investigation
        :type building: dict
        :param streets: Dataframe holding all street section of the
                        territory under investigation
        :type streets: pd.Dataframe
        :param index: integer used for unique indexing of the foot points.
        :type index: int
        :param building_type: specifies building type
        :type building_type: str
        :return: - **foot_point** (list) - list containing information
                                           of the perpendicular foot point
    """
    foot_points = []
    (lat, lon) = transf_WGS84_GK.transform(float(building["lat"]),
                                           float(building["lon"]))
    for num, street in streets.iterrows():
        # calculation of perpendicular foot point if it is within the
        # limits of the route
        perp_foot_point = calc_perpendicular_distance_line_point(
            [street["lat. 1st intersection"],
             street["lon. 1st intersection"]],
            [street["lat. 2nd intersection"],
             street["lon. 2nd intersection"]],
            [lat, lon], True)
        if perp_foot_point:
            foot_points.append(perp_foot_point
                               + [street["street section name"]])
    # check if more than one result was found
    if len(foot_points) > 1:
        # iterate threw the results to find the nearest
        # point of the calculated points
        num = 0
        while num < len(foot_points) - 1:
            if foot_points[num][2] > foot_points[num + 1][2]:
                foot_points.pop(num)
            else:
                foot_points.pop(num + 1)
            num = 0
            continue
    foot_point = [building_type + "-{}".format(str(index)) + "-fork"]
    foot_point.extend(foot_points[0])
    return foot_point


def create_fork(point, label, bus=None):
    """
        outsourced from creation algorithm to reduce redundancy
        
        :param point: list containing information of the point to be
                      appended
        :type point:list
        :param label: id of the fork to be created
        :type label: int
        :param bus: bus is used for producers forks identification
        :type bus: str
    """
    fork_dict = {"id": label, "lat": point[1], "lon": point[2],
                 "component_type": "Fork", "street": point[5], "t": point[4]}
    if bus:
        fork_dict.update({"bus": bus})
    # create consumers forks pandas Dataframe for thermal network
    thermal_network.components["forks"] = \
        thermal_network.components["forks"].append(
                pd.Series(data=fork_dict), ignore_index=True)


def remove_redundant_sinks(oemof_opti_model):
    """
    """
    sinks = []
    for i in range(len(oemof_opti_model.nodes)):
        # get demand created bei dhnx and add them to the list "sinks"
        if "demand" in str(oemof_opti_model.nodes[i]):
            sinks.append(i)
    already_deleted = 0
    for sink in sinks:
        oemof_opti_model.nodes.pop(sink - already_deleted)
        already_deleted += 1
    return oemof_opti_model


def create_connection_points(consumers, road_sections):
    """
        create the entries for the connection points and adds them to
        thermal network forks, consumers and pipes

        :param consumers: holding nodes_data["sinks"]
        :type consumers: pandas.Dataframe
        :param road_sections: holding nodes_data["road sections"]
        :type road_sections: pandas.Dataframe
    """
    consumer_counter = 0
    for num, consumer in consumers.iterrows():
        if consumer['active']:
            if consumer['district heating']:
                # TODO label of sinks has to be id_...
                label = consumer['label'].split("_")[0]
                foot_point = \
                    get_nearest_perp_foot_point(consumer, road_sections,
                                                consumer_counter, "consumers")
                # add consumer to thermal network components (dummy
                # because cut from system after creating dhnx components
                thermal_network.components["consumers"] = \
                    thermal_network.components["consumers"].append(
                        pd.Series(data={
                            "id": "consumers-{}".format(consumer_counter),
                            "lat": float(consumer['lat']),
                            "lon": float(consumer['lon']),
                            "component_type": "Consumer",
                            "P_heat_max": 1,
                            "input": consumer["input"],
                            "label": consumer["label"],
                            "street": foot_point[5]}),
                        ignore_index=True)
                # add fork of perpendicular foot point to the dataframe
                # of forks
                create_fork(foot_point, foot_point[0][10:-5])
                # add pipe between the perpendicular foot point and the
                # building to the dataframe of pipes
                thermal_network.components["pipes"] = \
                    thermal_network.components["pipes"].append(
                        pd.Series(data={
                            "id": "pipe-{}".format(foot_point[0][10:-5]),
                            "from_node":
                                "forks-{}".format(foot_point[0][10:-5]),
                            "to_node": foot_point[0][:-5],
                            "length": foot_point[3],
                            "component_type": "Pipe"}),
                        ignore_index=True)
                consumer_counter += 1
                logging.info("\t Connected {} to district heating network"
                             .format(label))


def create_intersection_forks(road_sections):
    """
        creates the forks of the scenario given street points
        :param road_sections: pandas Dataframe containing the street
                              sections beginning and ending points
        :type road_sections: pandas.Dataframe
    """
    road_section_points = {}
    fork_num = len(thermal_network.components["forks"])
    for num, street in road_sections.iterrows():
        if not ([street["lat. 1st intersection"],
                 street["lon. 1st intersection"]]
                in road_section_points.values()):
            road_section_points.update(
                    {"forks-{}".format(fork_num):
                        [street["lat. 1st intersection"],
                         street["lon. 1st intersection"]]})
            fork_num += 1
        if not ([street["lat. 2nd intersection"],
                 street["lon. 2nd intersection"]]
                in road_section_points.values()):
            road_section_points.update(
                    {"forks-{}".format(fork_num):
                        [street["lat. 2nd intersection"],
                         street["lon. 2nd intersection"]]})
            fork_num += 1

    for point in road_section_points:
        thermal_network.components["forks"] = \
            thermal_network.components["forks"].append(
                pd.Series({"id": point[6:],
                           "lat": road_section_points[point][0],
                           "lon": road_section_points[point][1],
                           "component_type": "Fork"}), ignore_index=True)


def create_producer_connection_point(nodes_data, road_sections):
    """
        create the entries for the producers  connection points and adds
        them to thermal network forks, producers and pipes
        
        :param nodes_data:
        :type nodes_data: pandas.Dataframe
        :param road_sections: Dataframe containing the street sections
                              start and end points
        :type road_sections: pandas.Dataframe
    """
    number = 0
    for i, bus in nodes_data['buses'].iterrows():
        if bus["district heating conn."] == "dh-system" and bus['active'] == 1:
            # create a producer buses and its connections point and pipe
            # due to the given lat and lon from buses sheet
            thermal_network.components["producers"] = \
                thermal_network.components["producers"].append(
                    pd.Series({"id": number, "lat": bus["lat"],
                               "lon": bus["lon"], "component_type": "Producer",
                               "active": 1}), ignore_index=True)
            foot_point = \
                get_nearest_perp_foot_point(bus, road_sections,
                                            number, "producers")
            create_fork(foot_point,
                        len(thermal_network.components["forks"]) + 1,
                        bus["label"])
            thermal_network.components['pipes'] = \
                thermal_network.components['pipes'].append(pd.Series(data={
                    "id": "pipe-{}".format(
                        len(thermal_network.components['pipes']) + 1),
                    "from_node": "producers-{}".format(number),
                    "to_node": "forks-{}".format(
                        len(thermal_network.components["forks"])),
                    "length": foot_point[3],
                    "component_type": "Pipe"}), ignore_index=True)
            number += 1
            logging.info("\t Connected {} to district heating network"
                         .format(bus["label"]))


def calc_street_lengths(connection_points: list) -> list:
    """
        calculates the distances between the points of a given street
        given as connection_points
        :param connection_points: list of connection_points on the
                                  given street
        :type connection_points: list
        :return: - **ordered_road_section_points** (list) - list
            containing all points of a certain street in an ordered
            sequence
    """
    # sorts the points created on a road piece according to their
    # position on the same
    connection_points.sort(key=itemgetter(4))
    ordered_road_section_points = []
    for point in range(0, len(connection_points) - 1):
        # Calculation of the mean latitude
        lat = (connection_points[point][1]
               + connection_points[point + 1][1]) / 2
        # Calculation of the x distance according to:
        # (lon1 - lon2) * 111.3km * cos(lat)
        dx = 111.3 * (connection_points[point][2]
                      - connection_points[point + 1][2]) \
                   * numpy.cos(numpy.deg2rad(lat))
        # Calculation of the y distance according to: (lat1 - lat2) * 111.3km
        dy = 111.3 * (connection_points[point][1]
                      - connection_points[point + 1][1])
        # Calculation of the actual distance and conversion to meters
        distance = math.sqrt(dx ** 2 + dy ** 2) * 1000
        # append the calculated distance and the information of the two
        # forks to the list of the ordered_road_section_points
        # Structure of the list
        # 1. Fork_at_the_beginning - Fork at the end
        # 2. calculated distance
        # 3. (lat1, lon1)
        # 4. (lat2, lon2)
        ordered_road_section_points.append(
            ["{} - {}".format(connection_points[point][0],
                              connection_points[point + 1][0]),
             distance,
             (connection_points[point][1],
              connection_points[point][2]),
             (connection_points[point + 1][1],
              connection_points[point + 1][2])])

    return ordered_road_section_points


def create_supply_line(streets):
    """

    :param streets: road sections Dataframe including the scenario sheet
    :type streets: pandas.Dataframe
    """
    pipes = {}
    for num, street in streets.iterrows():
        road_section = []
        for key, point in thermal_network.components["forks"].iterrows():
            if point["lat"] == street["lat. 1st intersection"] \
                    and point["lon"] == street["lon. 1st intersection"]:
                # check if begin of road section is begin or end of another
                road_section.append([point["id"],
                                     street["lat. 1st intersection"],
                                     street["lon. 1st intersection"],
                                     0, 0.0, street['street section name']])
            if point["lat"] == street["lat. 2nd intersection"] \
                    and point["lon"] == street["lon. 2nd intersection"]:
                # check if begin of road section is begin or end of another
                road_section.append([point["id"],
                                     street["lat. 2nd intersection"],
                                     street["lon. 2nd intersection"],
                                     0, 1.0, street['street section name']])
            if "street" in point:
                if point["street"] == street["street section name"]:
                    road_section.append([point["id"], point["lat"],
                                         point["lon"], 0, point["t"],
                                         street["street section name"]])

        # Order Connection points on the currently considered road section
        pipes.update({street['street section name']:
                     calc_street_lengths(road_section)})
        
    for street in pipes:
        for pipe in pipes[street]:
            ends = pipe[0].split(" - ")
            if "fork" in ends[0] and "consumers" in ends[0]:
                ends[0] = "forks-{}".format(ends[0][10:-5])
            else:
                ends[0] = "forks-{}".format(ends[0])
            if "fork" in ends[1] and "consumers" in ends[1]:
                ends[1] = "forks-{}".format(ends[1][10:-5])
            else:
                ends[1] = "forks-{}".format(ends[1])
            thermal_network.components["pipes"] = \
                thermal_network.components["pipes"].append(pd.Series(data={
                    "id": "pipe-{}".format(
                        len(thermal_network.components["pipes"]) + 1),
                    "from_node": ends[0], "to_node": ends[1],
                    "length": pipe[1], "component_type": "Pipe"}),
                        ignore_index=True)


def adapt_dhnx_style():
    """
        Brings the created dicts to the dhnx style
    """
    for i, p in thermal_network.components["consumers"].iterrows():
        if "consumers" in p["id"]:
            thermal_network.components["consumers"].replace(
                to_replace=p['id'], value=p['id'][10:], inplace=True)
    for i, p in thermal_network.components["pipes"].iterrows():
        if type(p["id"]) != int:
            thermal_network.components["pipes"].replace(
                to_replace=p['id'], value=p['id'][5:], inplace=True)
    thermal_network.components["consumers"].index = \
        thermal_network.components["consumers"]['id']
    thermal_network.components["forks"].index = \
        thermal_network.components["forks"]['id']
    thermal_network.components["pipes"].index = \
        thermal_network.components["pipes"]['id']
    thermal_network.components["prodcuers"].index = \
        thermal_network.components["prodcuers"]['id']


def create_components(nodes_data):
    """
        runs dhnx methods for creating thermal network oemof components
        :param nodes_data: Dataframe holing scenario sheet information
        :type nodes_data: pd.Dataframe
        :return: - **oemof_opti_model** () - model holding dh components
    """
    frequency = nodes_data['energysystem']['temporal resolution'].values
    start_date = str(nodes_data['energysystem']['start date'].values[0])
    # set standard investment options that do not require user modification
    invest_opt = {
        'consumers':
            {'bus': pd.DataFrame({"label_2": "heat", "active": 1, "excess": 0,
                                             "shortage": 0}, index=[0]),
             'demand': pd.DataFrame({"label_2": "heat", "active": 1,
                                     "nominal_value": 1}, index=[0])},
        'producers':
            {'bus': pd.DataFrame({"Unnamed: 0": 1, "label_2": "heat",
                                  "active": 1, "excess": 0, "shortage": 0},
                                 index=[0]),
             'source': pd.DataFrame({"label_2": "heat", "active": 0},
                                    index=[0])},
        'network': {'pipes': pd.read_csv(os.path.join("program_files",
                                                      "technical_data",
                                                      "district_heating",
                                                      "pipes.csv"))}}
    # start dhnx algorithm to create dh components
    oemof_opti_model = \
        optimization.setup_optimise_investment(
            thermal_network=thermal_network,
            invest_options=invest_opt,
            num_ts=nodes_data['energysystem']['periods'],
            start_date=(str(start_date[9:10]) + "/" + str(start_date[6:7])
                        + "/" + str(start_date[0:4])),
            frequence=(str(frequency[0])).upper()
        )
    return oemof_opti_model


def connect_dh_to_system(oemof_opti_model, busd):
    """
        method which creates links to connect the scenario based
        created sinks to the thermal network components created before
        :param oemof_opti_model: Oemof model holing thermal network
        :type oemof_opti_model:
        :param busd: dictionary containing scenario buses
        :type busd: dict
        :return: - **oemof_opti_model** () - oemof dh model within
            connection to the main model
    """
    # TODO DISCUSS COMPONENT LABEL
    oemof_opti_model = remove_redundant_sinks(oemof_opti_model)
    # create link to connect consumers heat bus to the dh-system
    for num, consumer in thermal_network.components["consumers"].iterrows():
        oemof_opti_model.nodes.append(solph.custom.Link(
            label=("consumers_connection_dh-c{}-".format(consumer["id"])
                   + consumer["label"][:-12]),
            inputs={
                oemof_opti_model.buses[
                    dhnx.optimization_oemof_heatpipe.Label(
                        'consumers', 'heat', 'bus',
                        'consumers-{}'.format(consumer["id"]))]:
                            solph.Flow(),
                busd[consumer["input"]]: solph.Flow()},
            outputs={
                busd[consumer["input"]]: solph.Flow(
                    investment=solph.Investment(
                        ep_costs=float(component_param.loc["dh_heatstation"]
                                       ["costs"]),
                        minimum=0,
                        maximum=999 * len(consumer["input"]),
                        existing=0,
                        nonconvex=False)
                ),
                oemof_opti_model.buses[
                    dhnx.optimization_oemof_heatpipe.Label(
                        'consumers', 'heat', 'bus',
                        'consumers-{}'.format(consumer["id"]))]:
                            solph.Flow()},
            conversion_factors={
                (oemof_opti_model.buses[
                     dhnx.optimization_oemof_heatpipe.Label(
                         'consumers', 'heat', 'bus',
                         'consumers-{}'.format(consumer["id"]))],
                 busd[consumer["input"]]):
                     float(component_param.loc["dh_heatstation"]
                           ["efficiency"]),
                (busd[consumer["input"]],
                 oemof_opti_model.buses[
                     dhnx.optimization_oemof_heatpipe.Label(
                         'consumers', 'heat', 'bus',
                         'consumers-{}'.format(consumer["id"]))]): 1}))
    return oemof_opti_model


def connect_clustered_dh_to_system(oemof_opti_model, busd):
    """
        method which creates links to connect the scenario based
        created sinks to the thermal network components created before
        :param oemof_opti_model: Oemof model holing thermal network
        :type oemof_opti_model:
        :param busd: dictionary containing scenario buses
        :type busd: dict
    """
    oemof_opti_model = remove_redundant_sinks(oemof_opti_model)
    # create link to connect consumers heat bus to the dh-system
    for num, consumer in thermal_network.components["consumers"].iterrows():
        bus = solph.Bus(label="clustered_consumers_{}".format(consumer["id"]))
        oemof_opti_model.nodes.append(bus)
        busd["clustered_consumers_{}".format(consumer["id"])] = bus
        oemof_opti_model.nodes.append(solph.Transformer(
                label=("link-dhnx-c{}-".format(consumer["id"])
                       + "clustered_consumers-{}-".format(consumer["id"])
                       + str(consumer["length"])),
                inputs={oemof_opti_model.buses[
                    dhnx.optimization_oemof_heatpipe.Label(
                            'consumers', 'heat', 'bus',
                            'consumers-{}'.format(consumer["id"]))]:
                        solph.Flow(investment=solph.Investment(
                                ep_costs=float(component_param.loc[
                                                   "clustered_consumer_link"]
                                               ["costs"] * consumer["length"]),
                                # *len(consumer["input"]))), # TODO 17,
                                #  28€/(m*a) 24.42kW bie DN25
                                periodical_constraint_costs=float(
                                        component_param.loc[
                                            "clustered_consumer_link"]
                                        ["constraint costs"]
                                        * consumer["length"]),
                                maximum=200 * len(consumer["input"]),  # TODO
                                minimum=0, existing=0, nonconvex=False))},
                outputs={
                    busd["clustered_consumers_{}".format(consumer["id"])]:
                        solph.Flow()
                },
                # TODO Verlust der Hausübergabe Station
                #  15.8689kWh/(m*a) bei 1500 Vollaststunden/a
                conversion_factors={
                    busd["clustered_consumers_{}".format(consumer["id"])]:
                        1 - (((15.8689 / 1500) * consumer["length"]) / 24.42)
                }))
        counter = 1
        for consumer_input in consumer["input"]:
            oemof_opti_model.nodes.append(solph.Transformer(
                    label="clustered_consumers_{}".format(consumer["id"])
                          + "-" + str(consumer_input),
                    inputs={
                        busd["clustered_consumers_{}".format(consumer["id"])]:
                            solph.Flow(investment=solph.Investment(
                                    ep_costs=float(component_param.loc[
                                                       "dh_heatstation"]
                                                   ["costs"]),
                                    minimum=0,
                                    maximum=999 * len(consumer["input"]),
                                    existing=0,
                                    nonconvex=False))},
                    outputs={busd[consumer_input]: solph.Flow()},
                    conversion_factors={busd[consumer_input]:
                                        float(component_param.loc[
                                                  "dh_heatstation"]
                                              ["efficiency"])}))
            counter += 1
    return oemof_opti_model


def add_excess_shortage_to_dh(oemof_opti_model, nodes_data, busd):
    """
        TODO TEST
    """
    busses = []
    for i, bus in nodes_data['buses'].iterrows():
        if bus["district heating conn."] != 0 and bus["active"] == 1 \
                and bus["district heating conn."] != "dh-system":
            busses.append(bus)
    for bus in busses:
        conn_point = bus['district heating conn.'].split("-")
        lat = None
        lon = None
        for i, street in nodes_data['road sections'].iterrows():
            if street['street section name'] == conn_point[0]:
                if conn_point[1] == "1":
                    lat = street["lat. 1st intersection"]
                    lon = street["lon. 1st intersection"]
                elif conn_point[1] == "2":
                    lat = street["lat. 2nd intersection"]
                    lon = street["lon. 2nd intersection"]
                else:
                    raise ValueError("invalid district heating conn.")
        if lat is None or lon is None:
            raise ValueError
        for key, fork in thermal_network.components["forks"].iterrows():
            if fork["lat"] == lat and fork["lon"] == lon:
                oemof_opti_model.nodes.append(solph.custom.Link(
                    label=("link-dhnx-" + bus['label']
                           + "-f{}".format(fork["id"])),
                    inputs={
                        oemof_opti_model.buses[
                            dhnx.optimization_oemof_heatpipe.Label(
                                    'infrastructure', 'heat', 'bus',
                                    str("forks-{}".format(fork["id"])))]:
                                        solph.Flow(),
                        busd[bus['label']]: solph.Flow()},
                    outputs={busd[bus['label']]: solph.Flow(),
                             oemof_opti_model.buses[
                                dhnx.optimization_oemof_heatpipe.Label(
                                    'infrastructure', 'heat', 'bus',
                                    str("forks-{}".format(fork["id"])))]:
                                        solph.Flow()},
                    conversion_factors={
                        (oemof_opti_model.buses[
                             dhnx.optimization_oemof_heatpipe
                         .Label('infrastructure', 'heat',
                                'bus', str("forks-{}".format(fork["id"])))],
                         busd[bus['label']]): 1,
                        (busd[bus['label']],
                         oemof_opti_model.buses[
                             dhnx.optimization_oemof_heatpipe
                         .Label('infrastructure', 'heat',
                                'bus', str("forks-{}".format(fork["id"])))]): 1
                    }))

    return oemof_opti_model


def create_producer_connection(oemof_opti_model, busd):
    """
        This method creates a link that connects the heat producer to
        the heat network.
        :param oemof_opti_model: dh model created before
        :type oemof_opti_model:
        :param busd: dictionary containing the energysystem busses
        :type busd: dict
        :return: - **oemof_opti_model** () - dhnx model within the new links
    """
    counter = 0
    for key, producer in thermal_network.components["forks"].iterrows():
        if str(producer["bus"]) != "nan":
            oemof_opti_model.nodes.append(solph.custom.Link(
                label=(str(key) + "-dhnx-source-link"),
                inputs={
                    oemof_opti_model.buses[
                        dhnx.optimization_oemof_heatpipe.Label(
                                'producers', 'heat', 'bus',
                                str("producers-{}".format(str(counter))))]:
                                    solph.Flow(),
                    busd[producer["bus"]]: solph.Flow()},
                outputs={
                    busd[producer["bus"]]: solph.Flow(),
                    oemof_opti_model.buses[
                        dhnx.optimization_oemof_heatpipe.Label(
                                'producers', 'heat', 'bus',
                                str("producers-{}".format(str(counter))))]:
                                    solph.Flow()},
                conversion_factors={
                    (oemof_opti_model.buses[
                         dhnx.optimization_oemof_heatpipe.Label(
                                 'producers', 'heat', 'bus',
                                 str("producers-{}".format(str(counter))))],
                     busd[producer["bus"]]): 1,
                    (busd[producer["bus"]],
                     oemof_opti_model.buses[
                         dhnx.optimization_oemof_heatpipe.Label(
                                 'producers', 'heat', 'bus',
                                 str("producers-{}".format(str(counter))))]):
                                    float(component_param.loc["pump"]
                                          ["efficiency"])}))

    return oemof_opti_model


def create_connect_dhnx(nodes_data, busd, clustering=False):
    """

    """
    thermal_network.is_consistent()
    thermal_network.set_timeindex()
    # create components of district heating system
    oemof_opti_model = create_components(nodes_data)
    if clustering:
        connect_clustered_dh_to_system(oemof_opti_model, busd)
    else:
        # connect non dh and dh system using links to represent losses
        connect_dh_to_system(oemof_opti_model, busd)
    # remove dhnx flows that are not used due to deletion of sinks
    for i in range(len(oemof_opti_model.nodes)):
        outputs = oemof_opti_model.nodes[i].outputs.copy()
        for j in outputs.keys():
            if ('consumers' in str(j) and 'heat' in str(j)
                    and 'demand' in str(j)):
                oemof_opti_model.nodes[i].outputs.pop(j)

    oemof_opti_model = \
        add_excess_shortage_to_dh(oemof_opti_model, nodes_data,
                                  busd)
    oemof_opti_model = \
        create_producer_connection(oemof_opti_model, busd)

    return oemof_opti_model.nodes


def district_heating(nodes_data, nodes, busd, district_heating_path,
                     save_dh_calculations, result_path, cluster_dh):
    """
    
    """
    dh = False
    # check rather saved calculation are distributed
    if district_heating_path == "":
        # check if the scenario includes road sections
        if len(nodes_data["road sections"]) != 0:
            street_sections = \
                convert_dh_street_sections_list(
                        nodes_data['road sections'].copy())
            # create pipes and connection point for building-streets connection
            create_connection_points(nodes_data['sinks'],
                                     street_sections)
            # appends the intersections to the thermal network forks
            create_intersection_forks(nodes_data['road sections'])
            # create pipes and connection point for producer-streets connection
            create_producer_connection_point(nodes_data, street_sections)
            # create supply line laid on the road
            create_supply_line(nodes_data['road sections'])
            # if any consumers where connected to the thermal network
            if thermal_network.components['consumers'].values.any():
                adapt_dhnx_style()
                if save_dh_calculations:
                    for i in ["consumers", "pipes", "producers", "forks"]:
                        thermal_network.components[i].to_csv(
                            result_path + "/" + i + ".csv")

                static_map = dhnx.plotting.StaticMap(thermal_network)
                static_map.draw(background_map=False)
                plt.title('Given network')
                plt.scatter(
                    thermal_network.components.consumers['lon'],
                    thermal_network.components.consumers['lat'],
                    color='tab:green', label='consumers',
                    zorder=2.5, s=50)
                plt.scatter(
                    thermal_network.components.producers['lon'],
                    thermal_network.components.producers['lat'],
                    color='tab:red', label='producers', zorder=2.5,
                    s=50)
                plt.scatter(thermal_network.components.forks['lon'],
                            thermal_network.components.forks['lat'],
                            color='tab:grey', label='forks',
                            zorder=2.5, s=50)
                plt.text(-2, 32, 'P0', fontsize=14)
                plt.text(82, 0, 'P1', fontsize=14)
                plt.legend()
                plt.savefig(result_path + "/district_heating.jpeg")
                dh = True
    else:
        for i in ["consumers", "pipes", "producers", "forks"]:
            thermal_network.components[i] = \
                pd.read_csv(district_heating_path + "/" + i + ".csv")
        adapt_dhnx_style()
        dh = True
        if cluster_dh:
            clustering_dh_network(nodes_data)
        for i in ["consumers", "pipes", "producers", "forks"]:
            thermal_network.components[i].to_csv(
                result_path + "/" + i + "_clustered.csv")
    if dh:
        if cluster_dh == 1: 
            new_nodes = create_connect_dhnx(nodes_data, busd, True)
        else:
            new_nodes = create_connect_dhnx(nodes_data, busd, False)
        thermal_network.components["pipes"].to_csv(
                "program_files/technical_data/district_heating/pipes_save.csv")
        for i in new_nodes:
            nodes.append(i)
    return nodes


def clustering_dh_network(nodes_data):
    """

    """
    forks = thermal_network.components["forks"].copy()
    pipes = thermal_network.components["pipes"].copy()
    consumers = thermal_network.components["consumers"].copy()
    forks_street = {}
    # put all forks of a given street part to forks_street dict
    for index, street in nodes_data["road sections"].iterrows():
        street_forks = []
        for num, fork in forks.iterrows():
            if fork["street"] == street["street section name"]:
                street_forks.append(fork["id"])
        forks_street.update({street["street section name"]: street_forks})
    streets_pipe_length = {}
    # get the length of all pipes connecting street part to consumer of
    # a given street part and put them to streets_pipe_length
    for street in forks_street:
        if forks_street[street]:
            num = 0
            for fork in forks_street[street]:
                forks_street[street][num] = "forks-{}".format(fork)
                num += 1
            for num, pipe in pipes.iterrows():
                if pipe["from_node"] in forks_street[street]:
                    if "consumers" in pipe["to_node"]:
                        if street not in streets_pipe_length:
                            streets_pipe_length.update(
                                {street: [[pipe["id"], pipe["from_node"],
                                           pipe["to_node"], pipe["length"]]]})
                        else:
                            streets_pipe_length[street].append(
                                [pipe["id"], pipe["from_node"],
                                 pipe["to_node"], pipe["length"]])
                        thermal_network.components["pipes"] = \
                            thermal_network.components["pipes"].drop(
                                index=pipe["id"])
    streets_consumer = {}

    # get consumer information of a given street part
    for street in streets_pipe_length:
        counter = 0
        lat = 0
        lon = 0
        inputs = []
        for street_consumer in streets_pipe_length[street]:
            for num, consumer in consumers.iterrows():
                if street_consumer[2] == \
                        "consumers-{}".format(consumer["id"]):
                    counter += 1
                    lat += consumer["lat"]
                    lon += consumer["lon"]
                    inputs.append(consumer["input"])
                    thermal_network.components["consumers"] = \
                        thermal_network.components["consumers"].drop(
                            index=consumer["id"])
        streets_consumer.update({street: [counter, lat, lon, inputs]})
    counter = 0
    # clear pipes Dataframe
    for num, pipe in thermal_network.components["pipes"].iterrows():
        thermal_network.components["pipes"] = \
            thermal_network.components["pipes"].drop(index=num)
    # clear forks Dataframe
    for num, fork in thermal_network.components["forks"].iterrows():
        thermal_network.components["forks"] = \
            thermal_network.components["forks"].drop(index=num)
    thermal_network.components["forks"] = \
        thermal_network.components["forks"].reset_index(drop=True)
    # calc the summed length of consumer pipes of a given street path
    for street in streets_pipe_length:
        length = 0
        for i in streets_pipe_length[street]:
            length += i[3]
        streets_pipe_length.update({street: length})
    # create the clustered consumer and its fork and pipe
    for street in streets_consumer:
        # add consumer to thermal network components (dummy
        # because cut from system after creating dhnx components
        thermal_network.components["consumers"] = \
            thermal_network.components["consumers"].append(
                pd.Series(data={
                    "id": "consumers-{}".format(counter),
                    "lat": float(streets_consumer[street][1]
                                 / streets_consumer[street][0]),
                    "lon": float(streets_consumer[street][2]
                                 / streets_consumer[street][0]),
                    "component_type": "Consumer",
                    "P_heat_max": 1,
                    "input": streets_consumer[street][3],
                    "label": "",
                    "street": street,
                    "length": streets_pipe_length[street]}),
                ignore_index=True)
        # calculate the foot point of the new clustered consumer
        foot_point = \
            get_nearest_perp_foot_point(
                {"lat": float(streets_consumer[street][1]
                              / streets_consumer[street][0]),
                 "lon": float(streets_consumer[street][2]
                              / streets_consumer[street][0])},
                nodes_data["road sections"], counter, "consumers")
        # add the pipe to the clustered consumer to the list of pipes
        thermal_network.components["pipes"] = \
            thermal_network.components["pipes"].append(pd.Series(
                    data={"id": "pipe-{}".format(len(
                            thermal_network.components["pipes"])),
                          "from_node":
                              "forks-{}".format(foot_point[0][10:-5]),
                          "to_node": "consumers-{}".format(counter),
                          "length": foot_point[3], "component_type": "Pipe"}),
                ignore_index=True)
        # create fork of the new calculated foot point
        create_fork(foot_point, foot_point[0][10:-5])
        counter += 1
    
    street_sections = \
        convert_dh_street_sections_list(
                nodes_data['road sections'].copy())
    create_intersection_forks(nodes_data['road sections'])
    create_producer_connection_point(nodes_data, street_sections)
    create_supply_line(nodes_data['road sections'])
    adapt_dhnx_style()
