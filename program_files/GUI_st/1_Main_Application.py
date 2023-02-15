"""
Created on Thu Sep 29 13:23:07 2022

@author: Jan Tockloth - jan.tockloth@fh-muenster.de
"""
import streamlit as st
import pandas as pd
from PIL import Image
import os
from datetime import datetime 
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode 
import plotly.express as px
import sys

# Setting new system path to be able to refer to perent directories
parent = os.path.abspath('.')
sys.path.insert(1, parent)

#TODO:problem mit reativen Pfaden!
from GUI_st_global_functions import clear_GUI_main_settings, safe_GUI_input_values, import_GUI_input_values_json, st_settings_global, run_SESMG
from program_files.preprocessing.pareto_optimization import run_pareto



####################################
# settings the initial streamlit page settings
st_settings_global()


####################################
#opening the input value dict, which will be safed as a json
GUI_main_dict = {}


####################################
###### Main SESMG Application ######
####################################

def main_start_page():
    """
    Definition of the start page for the GUI with introducing texts.
    """
    st.header("Spread Sheet Energy System Model Generator")
    st.subheader("Welcome using the SESMG!")
    st.write("This is the main application. You will find the differend modes over the dropdown menu in the sidebar.")
    st.write("To use this application you need to configurate your model run \
             in the sidebar on the left. Each with a short help text. You can \
             start a new model run and reopen earlier generated results as an \
                 overview. The GUI settings will be safed between your sessions,\
                which can be cleared.")
    st.subheader("Detailed Documentation!")
    st.write("The documentation, which includes detailed instructions for \
             installation and use, troubleshooting and much more, can be \
                 accessed via the following link:")
    st.write("https://spreadsheet-energy-system-model-generator.readthedocs.io/en/latest/")
    st.subheader("Questions?")
    st.write("Use the our discussion section and ask other users for help, if \
              you can not fix your problem with the documentation, via the \
                  following link:")
    st.write("https://github.com/SESMG/SESMG/discussions")

             
             
def main_output_result_overview(result_path_summary, result_path_components, result_path_results, result_path_graph):   
    """
    Function building the result overview of the SESMG main application. 
        :param result_path_summary: path to a result summary.csv file
        :type result_path_summary: str
        :param result_path_components: path to a result components.csv file
        :type result_path_components: str
        :param result_path_results: path to a result results.csv file
        :type result_path_results: str
        :param result_path_graph: path to a result graph.gv.png file
        :type result_path_graph: str
    """
    
    ####################################
    ############ Result Page ###########
    
    ########## Result Summary ########
    # Functions to display a summary of the modeled energy system.
    
    # Import summary.csv and create dataframe
    #df_summary = pd.read_csv(os.path.dirname(__file__) + "/summary.csv")
    df_summary = pd.read_csv(result_path_summary)
    # Create list with headers
    summary_headers = list(df_summary)
    
    # Display and import time series values
    time1, time2 = st.columns(2)
    time1.metric(label="Start Date", value=str(df_summary.iloc[0,0]))
    time2.metric(label="End Date", value=str(df_summary.iloc[0,1]))
    #time3.metric(label="Temporal Resolution", value=str(df_summary['Resolution']))            
    '''Hier Problem mit Darstellung des Typs Datetime'''
    
#TODO: add delta functions based on the latest results    
    # Display and import simulated cost values from summary dataframe
    cost1, cost2, cost3, cost4 = st.columns(4)
    cost1.metric(label=summary_headers[3], value=round(df_summary[summary_headers[3]],1))
    cost2.metric(label=summary_headers[4], value=round(df_summary[summary_headers[4]],1))
    cost3.metric(label=summary_headers[5], value=round(df_summary[summary_headers[5]],1))
    cost4.metric(label=summary_headers[6], value=round(df_summary[summary_headers[6]],1))
    
    # Display and import simulated energy values from summary dataframe
    ener1, ener2 = st.columns(2)
    ener1.metric(label=summary_headers[7], value=round(df_summary[summary_headers[7]],1))
    ener2.metric(label=summary_headers[8], value=round(df_summary[summary_headers[8]],1))   
    
    
    ########## Result Summary ########
    # Functions to display a summary of the modeled energy system.
    
    # Import components.csv and create dataframe
    df_components = pd.read_csv(result_path_components)
    # CSS to inject contained in a string
    hide_dataframe_row_index = """
                <style>
                .row_heading.level0 {display:none}
                .blank {display:none}
                </style>
                """
    # Inject CSS with Markdown
    st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
    # Creating st_aggrid table
    AgGrid(df_components, height = 400, fit_columns_on_grid_load=True, update_mode=GridUpdateMode.SELECTION_CHANGED)
    
    
    ####################  
    # hier plotly import
    # loading result.csv as a dataframe
    result_df = pd.read_csv(result_path_results)
    st.dataframe(result_df)
    # creating column headers to select
    column_headers_result = list(result_df.columns.values)
    # column headers without date
    list_headers = column_headers_result[1:]
    # selecting headers
    select_headers = st.multiselect("Select a bus:", list_headers)
    # filtered dataframe
    filtered_df = result_df[select_headers]
    # plotting
    fig = px.line(filtered_df)
    st.plotly_chart(fig, theme="streamlit", use_container_width=True)

    ########## Show Model Graph ########
    #Function to display the energy systems structure.
    
    # Header
    st.subheader("The structure of the modeled energy system:")
    
    # Importing and printing the energy system graph
    with st.expander("Show the structure of the modeled energy system"):
        es_graph = Image.open(result_path_graph, "r")
        st.image(es_graph)




def main_application_sesmg():    
    """
    Function building the sidebar of the main application including all 
    input options and starting the processes.

    """

    # Import the saved GUI settings from the last session
    settings_cache_dict_reload = import_GUI_input_values_json(os.path.dirname(__file__) + "/GUI_st_cache.json")    
    
    ####################################
    ############## Sidebar #############
    
    ###### Run Model Visualization #####
    # Function to create and display the model structure without optimizung the system.
    
    with st.sidebar.form("Visualization"):
        
        if "state_submitted_vis_existing_results" not in st.session_state:
            st.session_state["state_submitted_vis_existing_results"] = "not done"
        
        submitted_vis_existing_results = st.form_submit_button(label="Visualize existing model results", on_click=change_state_submitted_vis_existing_results)
        
        with st.expander("File Upload"):
            
            #importing an existing summary file
            GUI_main_dict["existing_summary_csv"] = st.file_uploader("Existing summary.csv file")
        
            #importing an existing components file
            GUI_main_dict["existing_components_csv"] = st.file_uploader("Existing components.csv file")
            
            #importing an existing results file
            GUI_main_dict["existing_results_csv"] = st.file_uploader("Existing results.csv file")
    
    
    ########## Modelrun Parameter Input ##########
    # Creating Frame as st.form_submit_button
    with st.sidebar.form("Input Parameters"):
    
        
        if "state_submitted_optimization" not in st.session_state:
            st.session_state["state_submitted_optimization"] = "not done"
            
            
        # Submit button to start optimization.
        submitted_optimization = st.form_submit_button(label="Start Optimization", on_click=change_state_submitted_optimization)
        
        #Functions to upload the scenario sheet file.
           
        # Header
        st.title("Upload Model Definition")
       
        scenario_input_sheet_path = st.file_uploader(label=
           "Upload your model definition sheet.",
           help="muss noch geschrieben werden.")
        
        # Header
        st.title("Input Parameters")
    
        
        ####################################
        # Input processing parameters
        # Functions to input the modeling parameters.
        
        # Header
        st.subheader("Processing Parameters")

        # Checkboxes processing graph
        GUI_main_dict["input_show_graph"] = st.checkbox(label="Show Graph")
        # Slider number of threads
        GUI_main_dict["input_num_threads"] = st.slider(label="Number of threads",min_value=1,max_value=35, help="Number of threads to use on your machine", value=settings_cache_dict_reload["input_num_threads"])
        #indexing the chosen solver of the cache session as an inputvalue for st. selectbox
        
        # Dict of choosable solvers the streamlit input index for selectbox's preselections
        input_solver_dict = {"cbc": 0,
                             "gurobi": 1}
        # chosing the solver in an select box
        GUI_main_dict["input_solver"] = st.selectbox(label="Optimization Solver", options=input_solver_dict.keys(), index=settings_cache_dict_reload["input_solver_index"])
        
        #preparing input_timeseries_season for GUI cache as an streamlit input index
        GUI_main_dict["input_solver_index"] = input_solver_dict[GUI_main_dict["input_solver"]]       
    
        ####################################
        # Input preprocessing parameters
        # Functions to input the preprocessing parameters.
        
        # Header
        st.subheader("Preprocessing Parameters")

        ### Functions to input the parameters for timeseries preparation.
        # TimeSeries Preparation
        # Dict of choosable algorithms matching the streamlit input index for selectbox's preselections
        timeseries_algorithm_dict = {"None": 0,
                                     "k_means": 1, 
                                     "k_medoids": 2, 
                                     "averaging": 3, 
                                     "slicing A": 4,
                                     "slicing B": 5, 
                                     "downsampling A": 6, 
                                     "downsampling B": 7,
                                     "heuristic selection": 8, 
                                     "random sampling": 9}
        
        # Timeseries Index Range
        timeseries_index_range_start = ["None"]
        timeseries_index_range_values = [i for i in range(1, 366)]
        # None or 1 to 365
        timeseries_index_range_list = timeseries_index_range_start + timeseries_index_range_values
        
        # Dict of choosable clustering crtieria matching the streamlit input index for selectbox's preselections 
        timeseries_cluster_criteria_dict = {"None": 0, 
                                            "temperature": 1, 
                                            "dhi": 2, 
                                            "el_demand_sum": 3, 
                                            "heat_demand_sum": 4}
        
        # Dict of choosable timeseries periods matching the streamlit input index for selectbox's preselections 
        input_timeseries_period_dict = {"None": 0,
                                        "hours": 1, 
                                        "days": 2 , 
                                        "weeks": 3}
        
        # Dict of choosable timeseries periods matching the streamlit input index for selectbox's preselections 
        input_timeseries_season_dict = {"None": 0,
                                        4: 1, 
                                        12: 2}

        # Timeseries preparation input inside an expander. 
        with st.expander("Timeseries Simplification"):
            # Choosing timeseries parameters - algorithm
            GUI_main_dict["input_timeseries_algorithm"] = st.selectbox(label="Algorithm", options=timeseries_algorithm_dict.keys(), index=settings_cache_dict_reload["input_timeseries_algorithm_index"])
            # Choosing timeseries parameters - index
            GUI_main_dict["input_timeseries_cluster_index"] = st.selectbox(label="Index", options=timeseries_index_range_list, index=settings_cache_dict_reload["input_timeseries_cluster_index_index"])
            # Choosing timeseries parameters - cluster criterion
            GUI_main_dict["input_timeseries_criterion"] = st.selectbox(label="Cluster Criterion", options=timeseries_cluster_criteria_dict.keys(), index=settings_cache_dict_reload["input_timeseries_criterion_index"])
            # Choosing timeseries parameters - period
            GUI_main_dict["input_timeseries_period"] = st.selectbox(label="Period", options=input_timeseries_period_dict.keys(), index=settings_cache_dict_reload["input_timeseries_period_index"])
            # Choosing timeseries parameters - season
            GUI_main_dict["input_timeseries_season"] = st.selectbox(label="Season", options=input_timeseries_season_dict.keys(), index=settings_cache_dict_reload["input_timeseries_season_index"])
            
        # transform input values of Timeseries Simplification to an index which will be safed in the GUI cache to be able to reload setting. Needs to be an index for st.selectboxes.
        #preparing input_timeseries_algorithm for GUI cache as an streamlit input index
        GUI_main_dict["input_timeseries_algorithm_index"] = timeseries_algorithm_dict[GUI_main_dict["input_timeseries_algorithm"]]
        #preparing input_timeseries_cluster_index for GUI cache as an streamlit input index
        if GUI_main_dict["input_timeseries_cluster_index"] == "None":
            GUI_main_dict["input_timeseries_cluster_index_index"] = 0
        else: 
            GUI_main_dict["input_timeseries_cluster_index_index"] = GUI_main_dict["input_timeseries_cluster_index"]
        #preparing input_timeseries_criterion for GUI cache as an streamlit input index
        GUI_main_dict["input_timeseries_criterion_index"] = timeseries_cluster_criteria_dict[GUI_main_dict["input_timeseries_criterion"]]
        #preparing input_timeseries_period for GUI cache as an streamlit input index
        GUI_main_dict["input_timeseries_period_index"] = input_timeseries_period_dict[GUI_main_dict["input_timeseries_period"]]
        #preparing input_timeseries_season for GUI cache as an streamlit input index
        GUI_main_dict["input_timeseries_season_index"] = input_timeseries_season_dict[GUI_main_dict["input_timeseries_season"]]
        
        
        # Pre-Model setting and pre-model timeseries preparation input inside an expander.
        with st.expander("Pre-Modeling Settings"):
            
            # Checkbox to activate the pre-modeling
            GUI_main_dict["input_activate_premodeling"] = st.checkbox(label="Activate Pre-Modeling", value=settings_cache_dict_reload["input_activate_premodeling"])
            
            # Activate functions to reduce the maximum design capacity
            GUI_main_dict["input_premodeling_invest_boundaries"] = st.checkbox(label="Investment Boundaries Tightening", value=settings_cache_dict_reload["input_premodeling_invest_boundaries"])
            # Slider to set the tightening factor for maximum design capacity
            GUI_main_dict["input_premodeling_tightening_factor"] = st.slider(label="Investment Tightening Factor", min_value=1, max_value=100, value=settings_cache_dict_reload["input_premodeling_tightening_factor"])
            
            # Choosing pre-model timeseries parameters - algorithm
            GUI_main_dict["input_premodeling_timeseries_algorithm"] = st.selectbox(label="Algorithm (Pre-Model)", options=timeseries_algorithm_dict.keys(), index=settings_cache_dict_reload["input_premodeling_timeseries_algorithm_index"])
            # Choosing pre-model timeseries parameters - index
            GUI_main_dict["input_premodeling_timeseries_cluster_index"] = st.selectbox(label="Index (Pre-Model)", options=timeseries_index_range_list, index=settings_cache_dict_reload["input_premodeling_timeseries_cluster_index_index"])
            # Choosing pre-model timeseries parameters - cluster criterion
            GUI_main_dict["input_premodeling_timeseries_criterion"] = st.selectbox(label="Cluster Criterion (Pre-Model)", options=timeseries_cluster_criteria_dict.keys(), index=settings_cache_dict_reload["input_premodeling_timeseries_criterion_index"])
            # Choosing pre-model timeseries parameters - period
            GUI_main_dict["input_premodeling_timeseries_period"] = st.selectbox(label="Period (Pre-Model)", options=input_timeseries_period_dict.keys(), index=settings_cache_dict_reload["input_premodeling_timeseries_period_index"])
            # Choosing pre-model timeseries parameters - season
            GUI_main_dict["input_premodeling_timeseries_season"] = st.selectbox(label="Season (Pre-Model)", options=input_timeseries_season_dict.keys(), index=settings_cache_dict_reload["input_premodeling_timeseries_season_index"])
 
        # transform input values of Timeseries Simplification to an index which will be safed in the GUI cache to be able to reload setting. Needs to be an index for st.selectboxes.
        #preparing input_timeseries_algorithm for GUI cache as an streamlit input index
        GUI_main_dict["input_premodeling_timeseries_algorithm_index"] = timeseries_algorithm_dict[GUI_main_dict["input_premodeling_timeseries_algorithm"]]
        #preparing input_timeseries_cluster_index for GUI cache as an streamlit input index
        if GUI_main_dict["input_premodeling_timeseries_cluster_index"] == "None":
            GUI_main_dict["input_premodeling_timeseries_cluster_index_index"] = 0
        else: 
            GUI_main_dict["input_premodeling_timeseries_cluster_index_index"] = GUI_main_dict["input_premodeling_timeseries_cluster_index"]
        #preparing input_timeseries_criterion for GUI cache as an streamlit input index
        GUI_main_dict["input_premodeling_timeseries_criterion_index"] = timeseries_cluster_criteria_dict[GUI_main_dict["input_premodeling_timeseries_criterion"]]
        #preparing input_timeseries_period for GUI cache as an streamlit input index
        GUI_main_dict["input_premodeling_timeseries_period_index"] = input_timeseries_period_dict[GUI_main_dict["input_premodeling_timeseries_period"]]
        #preparing input_timeseries_season for GUI cache as an streamlit input index
        GUI_main_dict["input_premodeling_timeseries_season_index"] = input_timeseries_season_dict[GUI_main_dict["input_premodeling_timeseries_season"]]       
    
        
 #TODO: check functionality of underlaying functions and implement in streamlit GUI
        # Checkboxes modeling while using district heating clustering.
        GUI_main_dict["input_cluster_dh"] = st.checkbox(label="Clustering District Heating Network", value=settings_cache_dict_reload["input_cluster_dh"])
        
        ### Function to upload the distrct heating precalulation inside an expander.
        with st.expander("Advanced District Heating Precalculation"):
            #### Fileuploader not able to print file path
            ## Upload DH Precalc File 
            #district_heating_precalc = st.file_uploader("Select District Heating File")
            district_heating_precalc_path = st.text_input("Type in path to your District Heating File input file.") 
        
        
        ####################################
        # Input Postprocessing Parameters
        # Functions to input the postprocessing parameters.
        
        # Header
        st.subheader("Postprocessing Parameters")
       
        # Input result processing parameters
        GUI_main_dict["input_xlsx_results"] = st.checkbox(label="Create xlsx-files", value=settings_cache_dict_reload["input_xlsx_results"])
        GUI_main_dict["input_console_results"] = st.checkbox(label="Create console-log", value=settings_cache_dict_reload["input_console_results"])
        GUI_main_dict["input_criterion_switch"] = st.checkbox(label="Switch Criteria", value=settings_cache_dict_reload["input_criterion_switch"])

        # Elements to set the pareto points.
        with st.expander("Pareto Point Options"):
            
            # List of pareto points wich can be chosen.
            pareto_options = [i for i in range(1,100)]
            
            # Multiselect element
            input_pareto_points = st.multiselect(label="Pareto Points", options=pareto_options, default=settings_cache_dict_reload["input_pareto_points"])
            if input_pareto_points is not None: 
                input_pareto_points.sort(reverse=True)
            
            GUI_main_dict["input_pareto_points"] = input_pareto_points
            
    ####### Clear the GUI settings cache
    # creating sidebar form submit strucutre
    with st.sidebar.form("Clear Cache"):
        
        # set initial sessin state for clear cache seubmit button
        if "state_submitted_clear_cache" not in st.session_state:
            st.session_state["state_submitted_clear_cache"] = "not done"
        
        # create submit button
        submitted_clear_cache = st.form_submit_button(label="Clear all GUI Settings", on_click=change_state_submitted_clear_cache)
        
        #button if latest path should be cleard as well
        clear_path = st.checkbox(label="Clear result paths")
    
    
    #################################### 
    # Clear all GUI settings if clear latest result paths clicked
#TOFDO: session state für clear dict
        
    if st.session_state["state_submitted_clear_cache"] == "done" and clear_path == True:
        #create and safe dict, set paths empty
        clear_GUI_main_settings(result_path="",
                                premodeling_result_path="",
                                json_file_path=os.path.dirname(__file__) + "/GUI_st_cache.json")
        #reset session state for clear cache
        st.session_state["state_submitted_clear_cache"] = "not done"
        #rerun whole script to update GUI settings
        st.experimental_rerun()
        
    elif st.session_state["state_submitted_clear_cache"] == "done" and clear_path == False:
        #create and safe dict, set paths as before
        clear_GUI_main_settings(result_path=settings_cache_dict_reload["res_path"],
                                premodeling_result_path=settings_cache_dict_reload["premodeling_res_path"],
                                json_file_path=os.path.dirname(__file__) + "/GUI_st_cache.json")
        #reset session state for clear cache
        st.session_state["state_submitted_clear_cache"] = "not done"
        #rerun whole script to update GUI settings
        st.experimental_rerun()  
            
    st.write(st.session_state)
    
    ###### Start Result Overview #######
    ###################################
    # Starting process if "Visualize existing model results"-button is clicked    
    # if not submitted_vis_existing_results or submitted_optimization: 
    #     # Display the start page
    if st.session_state["state_submitted_optimization"] == "not done" \
        and st.session_state["state_submitted_vis_existing_results"] == "not done":    
        main_start_page()
 
        
    
    ####################################
    # Starting process if "Visualize existing model results"-button is clicked    
    if st.session_state["state_submitted_vis_existing_results"] == "done":

        # run main result page with uploaded existiag files  
        main_output_result_overview(result_path_summary=GUI_main_dict["existing_summary_csv"], 
                                    result_path_components=GUI_main_dict["existing_components_csv"],
                                    result_path_results=GUI_main_dict["existing_results_csv"])
    
    
    ####################################
    # Starting process if "Start Optimization"-button is clicked
    
    if st.session_state["state_submitted_optimization"] == "done":
        
        #st.session_state["state_submitted_optimization"] = "not done"
        
        if scenario_input_sheet_path == None:
            
            #raise an error advice
            st.header("Model definition is missing!")
            st.write("Plase make sure to upload a model definition in the sidebar.")
            main_start_page()
        
        elif scenario_input_sheet_path != "":
            
            # Creating the timeseries preperation settings list for the main model
            GUI_main_dict["timeseries_prep_param"] = \
                [GUI_main_dict["input_timeseries_algorithm"],
                 GUI_main_dict["input_timeseries_cluster_index"],
                 GUI_main_dict["input_timeseries_criterion"],
                 GUI_main_dict["input_timeseries_period"],
                 0 if GUI_main_dict["input_timeseries_season"] == "None" else GUI_main_dict["input_timeseries_season"]]
            

            # Creating the timeseries preperation settings list for the pre-model
            GUI_main_dict["pre_model_timeseries_prep_param"] = \
                [GUI_main_dict["input_premodeling_timeseries_algorithm"],
                 GUI_main_dict["input_premodeling_timeseries_cluster_index"],
                 GUI_main_dict["input_premodeling_timeseries_criterion"],
                 GUI_main_dict["input_premodeling_timeseries_period"],
                 0 if GUI_main_dict["input_premodeling_timeseries_season"] == "None" else GUI_main_dict["input_premodeling_timeseries_season"]]

             # Setting the path where to safe the modeling results
            res_folder_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),'results')
            GUI_main_dict["res_path"] = res_folder_path \
                        + '/' \
                        + scenario_input_sheet_path.name.split("/")[-1][:-5] \
                        + datetime.now().strftime('_%Y-%m-%d--%H-%M-%S')
            os.mkdir(GUI_main_dict["res_path"])             
            
# HIER NOCHMAL ANSEHEN WIE / WO DIE DATEI GESPEICHERT WERDEN SOLL            
            # Setting the path where to safe the pre-modeling results
 #           premodeling_res_folder_path = res_path + "/pre_model_results"
 #           premodeling_res_path = premodeling_res_folder_path \
 #                       + '/' \
 #                       + scenario_input_sheet_path.name.split("/")[-1][:-5] \
 #                       + datetime.now().strftime('_%Y-%m-%d--%H-%M-%S')
            GUI_main_dict["premodeling_res_path"] = GUI_main_dict["res_path"] + "/pre_model_results"
            #os.mkdir(premodeling_res_path)

                       
            # safe the GUI_main_dice as a chache for the next session
            safe_GUI_input_values(input_values_dict=GUI_main_dict, 
                                  json_file_path=os.path.dirname(__file__) + "/GUI_st_cache.json")
            
            
                
                     
            
            # Starting the waiting / processing screen
            st.spinner(text="Modeling in Progress.")
            
            # Starting the model run            
            if len(GUI_main_dict["input_pareto_points"]) == 0:
                
                with st.spinner("Modeling in Progress..."):
                    
                    run_SESMG(GUI_main_dict=GUI_main_dict, 
                              model_definition=scenario_input_sheet_path, 
                              save_path=GUI_main_dict["res_path"])
                
                st.header('Modeling completed!')
                # run main result page with new modeled files 
                main_output_result_overview(result_path_summary=GUI_main_dict["res_path"] + "/summary.csv", 
                                            result_path_components=GUI_main_dict["res_path"] + "/components.csv",
                                            result_path_results=GUI_main_dict["res_path"] + "/results.csv",
                                            result_path_graph=GUI_main_dict["res_path"] + "/graph.gv.png")
                

            # Starting a pareto modeul rum
            elif len(GUI_main_dict["input_pareto_points"]) != 0:

                run_pareto(
                    limits=[i/100 for i in GUI_main_dict["input_pareto_points"]],
                    model_definition=scenario_input_sheet_path,
                    GUI_main_dict=GUI_main_dict)
    
                st.header('Modeling completed!')
               
                
            else:
                
                #main_output_result_overview()
                st.spinner("Modeling in Progress...")
                st.write("Hallo")
             

def change_state_submitted_optimization():
    """
    Setup session state for the optimization form-submit as an 
    change event as on-click to switch the state.
    """
    st.session_state["state_submitted_optimization"] = "done"
    return


def change_state_submitted_vis_existing_results():
    """
    Setup session state for the vis_excisting_results form-submit as an 
    change event as on-click to switch the state.
    """
    st.session_state["state_submitted_vis_existing_results"] = "done"
    return


def change_state_submitted_clear_cache():
    """
    Setup session state for the vis_excisting_results form-submit as an 
    change event as on-click to switch the state.
    """
    st.session_state["state_submitted_clear_cache"] = "done"
    st.session_state["state_submitted_optimization"] = "not done"
    st.session_state["state_submitted_vis_existing_results"] = "not done"
    return



# Start main page
main_application_sesmg()






# ####################################
# ############ TEST PAGE #############
# ####################################
                
             



# def test_page():
    
#     from GUI_streamlit import (import_GUI_input_values_json, \
#         safe_GUI_input_values, \
#         clear_GUI_input_values)
        
#     settings_cache_dict_reload = import_GUI_input_values_json(os.path.dirname(__file__) + "/GUI_test_setting_cache.json")

#     st.write(settings_cache_dict_reload)
    
    
#     st.title("Hier werden erweitere Ergebnisaufbereitungen dargestellt.")
       
    
#     if st.sidebar.button("Clear Cache"):

#         settings_cache_dict_reload_2 = clear_GUI_input_values(settings_cache_dict_reload, "main_page", os.path.dirname(__file__) + "/GUI_test_setting_cache.json")
        
#         #rerun whole script to update GUI settings
#         st.experimental_rerun()

        
#     with st.sidebar.form("Input Parameters"):
        
#         # Submit button to start optimization.
#         submitted_optimization = st.form_submit_button("Start Inputs")
#         input1 = st.text_input("Test Input 1", value=settings_cache_dict_reload["input1"])
#         input2 = st.text_input("Test Input 2", value=settings_cache_dict_reload["input2"])
    
#         if  submitted_optimization:
            
#             settings_cache_dict = {"input1": input1, "input2": input2}
            
#             #sfe GUI settings dict
#             safe_GUI_input_values(settings_cache_dict, os.path.dirname(__file__) + "/GUI_test_setting_cache.json")
            
#             #rerun whole script to update GUI settings
#             st.experimental_rerun()

        

# ####################################
# ############ DEMO Tool #############
# ####################################


# def demo_result_page():
    
#     demo_page = st.container()
    
#     with demo_page:
#         st.title("Hier wird das Demotool platziert.")

















