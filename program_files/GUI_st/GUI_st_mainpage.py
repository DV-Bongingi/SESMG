#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 29 13:23:07 2022

@author: jantockloth
"""

import streamlit as st
import pandas as pd
from PIL import Image
import os
from datetime import datetime 

from program_files.preprocessing.Spreadsheet_Energy_System_Model_Generator import sesmg_main

from program_files.GUI_st.GUI_st_US import *




####################################
###### Main SESMG Application ######
####################################


def main_application_sesmg():    
    
        
    ####################################
    ############## Sidebar #############
    
    ########## Scenario Input ##########
    # Functions to upload the scenario sheet file.
        
    # Header
    st.sidebar.title("Upload Scenario File")
    
    #'''
    #### Fileuploader not able to print file path
    ## Upload Scenario Sheet File 
    #scenario_input_sheet = st.sidebar.file_uploader("Select Scenario File")
    #if scenario_input_sheet is not None:
    #     dataframe = pd.read_excel(scenario_input_sheet)
    #     st.write(dataframe)
    #'''
    
    scenario_input_sheet_path = st.sidebar.text_input(
        "Type in path to your scenario input sheet.",
        help="Give the full path from your main directory ending with \
                /inputscenario.xlsx . \
                You can choose the filenames and directorties as you want.") 
    
    # ###### Run Model Visualization #####
    # # Function to create and display the model structure without optimizung the system.
    
    # with st.sidebar.form("Visualization"):
        
    #     submitted_vis_structure = st.form_submit_button(label="Visualize model")
    
    
    ########## Modelrun Parameter Input ##########
    # Creating Frame as st.form_submit_button
    with st.sidebar.form("Input Parameters"):
        
        # Submit button to start optimization.
        submitted_optimization = st.form_submit_button("Start Optimization")
            
        # Header
        st.title("Input Parameters")
        
        ####################################
        # Input Processing Parameters
        # Functions to input the modelling parameters.
        
        # Header
        st.subheader("Processing Parameters")

        # Checkboxes Processing Graph
        st.checkbox("Show Graph")
        # Slider Number of Threads
        input_num_threads = st.slider("Number of threads",min_value=1,max_value=35, help="Number of threads to use on your machine")
        # Choosing Solver
        input_solver = st.selectbox("Optimization Solver", ("cbc", "gurobi"))

        ####################################
        # Input Preprocessing Parameters
        # Functions to input the preprocessing parameters.
        
        # Header
        st.subheader("Preprocessing Parameters")

        ### Functions to input the parameters for timeseries preparation.
        # TimeSeries Preparation
        # Choosable Algorithms
        timeseries_algorithm_list = \
            ["None", "k_means", "k_medoids", "averaging", "slicing A",
             "slicing B", "downsampling A", "downsampling B",
             "heuristic selection", "random sampling"]
        # Choosable clustering crtieria
        timeseries_cluster_criteria_list = \
            ["None", "temperature", "dhi", "el_demand_sum", "heat_demand_sum"]
        # Timeseries Index Range
        timeseries_index_range_start = ["None"]
        timeseries_index_range_values = [i for i in range(1, 366)]
        timeseries_index_range_list = timeseries_index_range_start + timeseries_index_range_values
        
        # Timeseries preparation input inside an expander. 
        with st.expander("Timeseries Preparation"):
            # Choosing Timeseries Parameters - Algorithm
            input_timeseries_algorithm = st.selectbox("Algorithm", timeseries_algorithm_list)
            # Choosing Timeseries Parameters - Index
            input_timeseries_cluster_index = st.selectbox("Index", timeseries_index_range_list)
            # Choosing Timeseries Parameters - Cluster Criterion
            input_timeseries_criterion = st.selectbox("Cluster Criterion", timeseries_cluster_criteria_list)
            # Choosing Timeseries Parameters - Period
            input_timeseries_period = st.selectbox("Period", ["None","hours", "days", "weeks"])
            # Choosing Timeseries Parameters - Season
            input_timeseries_season = st.selectbox("Season", ["None",4,12])
        
        
        # Checkboxes Modeling
        input_cluster_dh = st.checkbox("Clustering District Heating Network")
        
        ### Function to upload the Distrct Heating Precalulation inside an expander.
        with st.expander("Advanced District Heating Precalculation"):
            #'''
            #### Fileuploader not able to print file path
            ## Upload DH Precalc File 
            #district_heating_precalc = st.file_uploader("Select District Heating File")
            #'''
            district_heating_precalc_path = st.text_input("Type in path to your District Heating File input file.") 
        
        
        ####################################
        # Input Postprocessing Parameters
        # Functions to input the postprocessing parameters.
        
        # Header
        st.subheader("Postprocessing Parameters")
       
        # Input Result Processing Parameters
        input_xlsx_results = st.checkbox("Create xlsx-files")
        input_console_results = st.checkbox("Create console-log")


        # Elements to set the pareto points.
        with st.expander("Pareto Point Options"):
            
            input_criterion_switch = st.checkbox("Switch Criteria")
            
            # List of Pareto Points wich can be chosen.
            pareto_options = [100 - 5*i for i in range(1,20)]
            
            # Multiselect Element
            input_pareto_points = st.multiselect("Pareto Points", options=pareto_options)
            input_pareto_points.sort(reverse=True)
        


            
        
    ####################################
    ############ Result Page ###########
    
    ########## Show Model Graph ########
    #Function to display the energy systems structure.
    
    # Header
    st.subheader("The structure of the modeled energy system:")
    
    # Importing and printing the Energy System Graph
    es_graph = Image.open(os.path.dirname(__file__) + "/graph.gv.png", "r")
    st.image(es_graph, caption="Beispielgraph.",)
    
    
    ########## Result Summary ########
    # Functions to display a summary of the modeled energy system.
    
    # Import summary csv and create dataframe
    df_summary = pd.read_csv(os.path.dirname(__file__) + "/summary.csv")
    
    # Display and import time series values
    #time1, time2 = st.columns(2)
    #time1.metric(label="Start Date", value=str(df_summary['Start Date']))
    #time2.metric(label="End Date", value=str(df_summary['End Date']))
    #time3.metric(label="Temporal Resolution", value=str(df_summary['Resolution']))            
    '''Hier Problem mit Darstellung des Typs Datetime'''
    
    # Display and import simulated cost values from summary dataframe
    cost1, cost2, cost3, cost4 = st.columns(4)
    cost1.metric(label="Total System Costs", value=round(df_summary['Total System Costs'],1), delta="1.2 °F")
    cost2.metric(label="Total Constraint Costs", value=round(df_summary['Total Constraint Costs'],1), delta="1.2 °F")
    cost3.metric(label="Total Variable Costs", value=round(df_summary['Total Variable Costs'],1), delta="-1.2 °F")
    cost4.metric(label="Total Periodical Costs", value=round(df_summary['Total Periodical Costs'],1), delta="1.2 °F")
    
    # Display and import simulated energy values from summary dataframe
    ener1, ener2 = st.columns(2)
    ener1.metric(label="Total Energy Demand", value=round(df_summary['Total Energy Demand'],1), delta="1.2 °F")
    ener2.metric(label="Total Energy Usage", value=round(df_summary['Total Energy Usage'],1), delta="1.2 °F")        
    
    
    ####################################
    # Starting Process if "Start Optimization"-Button is clicked
    if submitted_optimization:
        
        if scenario_input_sheet_path is not "":
            
            
            timeseries_prep_param = \
                [input_timeseries_algorithm,
                 input_timeseries_cluster_index,
                 input_timeseries_criterion,
                 input_timeseries_period,
                 0 if input_timeseries_season == "None" else input_timeseries_season]
            
            st.write(timeseries_prep_param)
            st.write(scenario_input_sheet_path)
            
            res_folder_path = os.path.join(os.path.dirname(__file__),'results')
            res_path = res_folder_path \
                        + '/' \
                        + scenario_input_sheet_path.split("/")[-1][:-5] \
                        + datetime.now().strftime('_%Y-%m-%d--%H-%M-%S')
            os.mkdir(res_path)
            
    
            sesmg_main(
                scenario_file=scenario_input_sheet_path,
                result_path=res_path,
                num_threads=input_num_threads,
                timeseries_prep=timeseries_prep_param,
#TODO: Implementieren 
                graph=False,
                criterion_switch=input_criterion_switch,
                xlsx_results=input_xlsx_results,
                console_results=input_console_results,
                solver=input_solver,
                district_heating_path=district_heating_precalc_path,
                cluster_dh=input_cluster_dh
                )
                        
            
        else:
             st.write(input_pareto_points)
             
    
        
    




####################################
###### SESMG Advanced Results ######
####################################


def advanced_result_page():
    
    udu_page = st.container()
    
    with udu_page:
        st.title("Hier werden erweitere Ergebnisaufbereitungen dargestellt.")
        

####################################
############ DEMO Tool #############
####################################


def demo_result_page():
    
    demo_page = st.container()
    
    with demo_page:
        st.title("Hier wird das Demotool platziert.")





####################################
######## STREAMLIT SETTINGS ########
####################################


def st_settings_global():
    """
    Function to define settings for the Streamlit GUI.

    """
    
    # Global page settings
    st.set_page_config(
        page_title=('SESMG'),
        layout='wide', 
        menu_items={'Get Help': 'https://spreadsheet-energy-system-model-generator.readthedocs.io/en/latest/',
                    'Report a Bug': 'https://github.com/chrklemm/SESMG/issues'})



####################################
########### RUN THE APP ############
####################################

# Import settings
st_settings_global()

app_mode = st.sidebar.selectbox(
    "Choose the app mode",
    [
     "Urban District Upscaling Tool",
     "Main SESMG Application", 
     "Advanced Model Results",
     "SESMG Demo Tool"])


if app_mode == "Main SESMG Application":
    main_application_sesmg()
elif app_mode == "Urban District Upscaling Tool":
    us_application()
elif app_mode == "Advanced Model Results":
    advanced_result_page()
elif app_mode == "SESMG Demo Tool":
    demo_result_page()
    
    
    

















