Sourcecode documentation
*************************************************
The Spreadsheet Energy System Model Generator has a hierarchical structure and
consists of a total of four work blocks, which in turn consist of various functions and subfunctions.
The individual (sub-)functions are documented with docstrings according to
the PEP 257 standard. Thus, the descriptions of functions, any information about
input and output variables and further details can be easily accessed via the python
help function. The model generator’s flow chart is shown in the following figure, including all
input and output data, used functions and Python libraries.

.. figure:: ../images/program_flow.pdf
	:width: 100%
	:alt: Program-Flow
	:align: center
	
	Program flow of the Spreadsheet Energy System Model Generator (grey,
	center), as well as local inputs and outputs (bottom) and used Python libraries
	(top).
	
**Create Energy System**. In the first block, the Python library Pandas is used to read
the input xlsx-spreadsheet file. Subsequently, an oemof time index (time steps for a
time horizon with a resolution defined in the input file) is created on the basis of the
parameters imported. This block is the basis for creating the model. The model does
not yet contain any system components, these must be added in the following blocks.

**Create Objects**. In the second block, the system components defined in the xlsxscenario
file are created according to the oemof specifications, and added to the model.
At first, the buses are initialized, followed by the sources, sinks, transformers, storages
and links. With the creation of sources, commodity sources are created first and photovoltaic
sources second. The creation of sinks is divided into six sub-functions, one for
each type of sinks: unfixed sinks, sinks with a given time series, sinks using standard
load profiles (residential heat, commercial heat, electricity) as well as sinks using load
profiles that were created with the Richardson tool. Although it is untypical to convert
a function into a single sub-function, this alternative was chosen for the creation of
transformers and storages. This offers the option to add further sub-functions such as
additional types of transformers and storages lateron. Lastly, the creation of links is
divided into the creation of undirected and directed links.

**Optimize Model**. Within the third block, the CBC solver is utilized to solve the energy
system for minimum costs. It returns the “best” scenario. This block only contains one
function. Again, further functions may be added lateron, for example the combination
of more than one assessment criterion.

**Create Results**. In the last block, the scenario as returned from the CBC solver is
analyzed and prepared for further processing. With the first function of this block, the
results are saved within xlsx-files. It contains ingoing and outgoing energy flows for
every time step of the entire time horizon. With the second function, a set of statistics
for every component is returned into a log-file. Finally, the results are illustrated as
shown in the chapters above.

define_energy_system()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ======================================================================================
      def program_files.create_energy_system.define_energy_system (*filepath*, *nodes_data*) 
      ======================================================================================

   .. container:: memdoc

      Creates an energy system.

      Creates an energy system with the parameters defined in the given
      .xlsx- file. The file has to contain a sheet called "timesystem",
      which must have the following structure:

      =================== =================== ======== ===================
      start_date          end_date            holidays temporal resolution
      =================== =================== ======== ===================
      YYYY-MM-DD hh:mm:ss YYYY-MM-DD hh:mm:ss          h
      =================== =================== ======== ===================

      --------------

      Parameters
         
         String filename : path to excel scenario file
         String sheet : sheet in excel file, where the timesystem is defined
         dict   nodes_data : dictionary containing data from excel scenario file
         

      --------------

      Return values
         
         dict esys : oemof energy system
        

import_scenario()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ===================================================================
      def program_files.create_energy_system.import_scenario (*filepath*) 
      ===================================================================

   .. container:: memdoc

      Imports data from a spreadsheet scenario file.

      The excel sheet has to contain the following sheets:

      -  timesystem
      -  buses
      -  transformers
      -  sinks
      -  sources
      -  storages
      -  powerlines
      -  time_series

      --------------

      Parameters
         
         String filename : path to excel scenario file
         

      --------------

      Return values
         
         dict nodes_data : dictionary containing data from excel scenario file
		 
		 
buses()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ==============================================================
      def program_files.create_objects.buses (*nodes_data*, *nodes*)   
      ==============================================================

   .. container:: memdoc

      Creates bus objects.

      Creates bus objects with the parameters given in 'nodes_data' and
      adds them to the list of components 'nodes'.

      --------------

      Parameters
         
          obj:'str' nodes_data : dictionary containing parameters of the buses to be created. The following parameters have to be provided: label, active, excess, shortage, shortage costs /(CU/kWh), excess costs /(CU/kWh)           
          obj:'list' nodes : list of components created before (can be empty)                            
         
      --------------

      Return values
         
         obj:'dict' busd : dictionary containing all buses created
         

links()
-------------------------------------------------
.. container:: memitem

   .. container:: memproto

      =====================================================================
      def program_files.create_objects.links (*nodes_data*, *nodes*, *bus*)   
      =====================================================================

   .. container:: memdoc

      Creates link objects.

      Creates links objects as defined in 'nodes_data' and adds them to
      the list of components 'nodes'.

      --------------

      Parameters
         
         obj:'dict' nodes_data : dictionary containing data from excel scenario file. The following data have to be provided: label, active, bus_1, bus_2, (un)directed, efficiency, existing capacity /(kW), min. investment capacity /(kW), max. investment capacity /(kW), variable costs  /(CU/kWh), periodical costs /(CU/(kW a))
         obj:'dict' bus : dictionary containing the busses of the energy system
         obj:'list' nodes : list of components

sinks()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      =================================================================================
      def program_files.create_objects.sinks (*nodes_data*, *bus*, *nodes*, *filepath*)   
      =================================================================================

   .. container:: memdoc

      Creates sink objects.

      Creates sinks objects with the parameters given in 'nodes_data'
      and adds them to the list of components 'nodes'.

      --------------

      Parameters
        
         obj:'dict' nodes_data : dictionary containing parameters of sinks to  be created. The following data have to be provided: label, active, input, input2, load profile, nominal value /(kW), annual demand /(kWh/a), occupants [RICHARDSON], building class [HEAT SLP ONLY], wind class [HEAT SLP ONLY], fixed
         obj:'dict' bus : dictionary containing the busses of the energy system             
         obj:'str' filepath : path to .xlsx scenario-file containing a "weather data" sheet with         timeseries for                                                     
-  "dhi" (diffuse horizontal irradiation) W/m^2             
-  "dirhi" (direct horizontal     irradiance) W/m^2              
-  "pressure" in Pa               
-  "temperature" in °C            
-  "windspeed" in m/s             
-  "z0" (roughness length) in m   
         obj:'list' nodes : list of components created before (can be empty)     
         

sources()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ===================================================================================
      def program_files.create_objects.sources (*nodes_data*, *nodes*, *bus*, *filepath*)   
      ===================================================================================

   .. container:: memdoc

      Creates source objects.

      Creates source objects with the parameters given in 'nodes_data'
      and adds them to the list of components 'nodes'. If the parameter
      'technology' in nodes_data is labeled as 'commodity source', a
      source with defined timeseries will be created. If technology is
      labeled as 'photovoltaic' a photovoltaic system component will be
      created.

      --------------

      Parameters
         
         obj:'dict' nodes_data : dictionary containing parameters of sources to be created. The following data have to be provided: label, active, output, technology, variable costs /(CU/kWh), existing capacity /(kW), min. investment capacity /(kW), max. investment capacity /(kW), periodical costs /(CU/(kW a)), technology database (PV ONLY), inverter database (PV ONLY), Modul Model (PV ONLY), Inverter Model (PV ONLY), Azimuth (PV ONLY), Surface Tilt (PV ONLY), Albedo (PV ONLY), Altitude (PV ONLY), Latitude (PV ONLY), Longitude (PV ONLY)               
         obj:'dict' bus : dictionary containing the buses of the energy system 
         obj:'list' nodes : list of components created before (can be empty) 
		 obj:'str' filepath : path to .xlsx scenario-file containing a "weather data" sheet with         timeseries for                                                     
		 -  "dhi" (diffuse horizontal irradiation) W/m^2             
		 -  "dirhi" (direct horizontal     irradiance) W/m^2              
		 -  "pressure" in Pa               
		 -  "temperature" in °C            
		 -  "windspeed" in m/s             
		 -  "z0" (roughness length) in m

storages()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ========================================================================
      def program_files.create_objects.storages (*nodes_data*, *nodes*, *bus*)   
      ========================================================================

   .. container:: memdoc

      Creates storage objects.

      Creates storage objects as defined in 'nodes_data' and adds them
      to the list of components 'nodes'.

      --------------

      Parameters
         
         obj:'dict' nodes_data : dictionary containing data from excel scenario file. The following data have to be provided: label, active, bus, existing capacity /(kW), min. investment capacity /(kW), max. investment capacity /(kW), periodical costs /(CU/(kW a)), capacity inflow, capacity outflow, capacity loss, efficiency inflow, efficiency outflow, initial capacity, capacity min, capacity max, variable input costs, variable output costs 
         obj:'dict' bus : dictionary containing the busses of the energy system                          
         obj:'list' nodes : list of components                          

transformers()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ============================================================================
      def program_files.create_objects.transformers (*nodes_data*, *nodes*, *bus*)   
      ============================================================================

   .. container:: memdoc

      Creates a transformer object.

      Creates transformers objects as defined in 'nodes_data' and adds
      them to the list of components 'nodes'.

      --------------

      Parameters
         
         obj:'dict' nodes_data : dictionary containing data from excel scenario file. The following data have to be provided: label, active, transformer type, input, output, output2, efficiency, efficency2, variable input costs /(CU/kWh), variable output costs /(CU/kWh), existing capacity /(kW), max. investment capacity /(kW), min. investment capacity /(kW), periodical costs /(CU/(kW a))
         obj:'dict' bus : dictionary containing the busses of the energy system  
         obj:'list'nodes : list of components                             

least_cost_model()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      =================================================================================
      def program_files.optimize_model.least_cost_model (*nodes_data*, *energy_system*)   
      =================================================================================

   .. container:: memdoc

      Solves a given energy system model.

      Solves a given energy system for least costs and returns the
      optimized energy system.

      --------------

      Parameters
         
         obj:'str' nodes_data : dictionary containing data from excel   scenario file
         obj energy_system : energy system consisting a number of components 
		 
      --------------

      Return values
         
         obj:'dict' nodes_data : dictionary containing data from excel scenario file                              
create_graph()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      ============================================================================================
      def program_files.create_graph.create_graph (*filepath*, *nodes_data*, *legend* = ``False``)   
      ============================================================================================

   .. container:: memdoc

      Visualizes the energy system as graph.

      Creates, using the library Graphviz, a graph containing all
      components and connections from "nodes_data" and returns this as a
      PNG file.

      --------------

      Parameters
         
         String filepath : path, where the PNG-result shall be saved  
         obj:'dict' nodes_data : dictionary containing data from excel scenario file.                    
         obj:'bool' legend : specifies, whether a legend will be added to the graph or not   

         
charts()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      =============================================================================================
      def program_files.create_results.charts (*nodes_data*, *optimization_model*, *energy_system*)   
      =============================================================================================

   .. container:: memdoc

      Plots model results.

      Plots the in- and outgoing flows of every bus of a given,
      optimized energy system

      --------------

      Parameters
         
          obj:'dict' nodes_data : dictionary containing data from excel scenario file    
          obj:'oemof.solph.models.Model' optimization_model: optimized energy system                     
          obj energy_system: original (unoptimized) energy system        

      --------------

      Return values
         
          plots plots displaying in and outgoing flows of the energy systems' buses.    
        

prepare_plotly_results()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

     ====================================================================================================
      def program_files.create_results.prepare_plotly_results (*nodes_data*, *optimization_model*, *energy_system*, *result_path*)
	 ====================================================================================================
   .. container:: memdoc

      Function which prepares the results for the creation of a HTML
      page.

      Creates three pandas data frames and saves them, which are
      required for creating an interactive HTML result page:

      -  df_list_of_components: Consists all components with several
         properties
      -  df_result_table: Consists timeseries of al components
      -  df_summary: Consists summarizing results of the modelling

      --------------

      Parameters
         
         obj:'dict' nodes_data: dictionary containing data from excel scenario file      
         obj:'oemof.solph.models.Model' optimization_model: optimized energy system                    
		 obj energy_system: original (unoptimized) energy system
         String result_path: path, where the data frames shall be saved as csv-file  


statistics()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      =================================================================================================
      def program_files.create_results.statistics (*nodes_data*, *optimization_model*, *energy_system*)   	  
	  =================================================================================================

   .. container:: memdoc

      Returns a list of all defined components with the following
      information:

      +--------------+------------------------------------------------------+
      | component    | information                                          |
      +==============+======================================================+
      | sinks        | Total Energy Demand                                  |
      +--------------+------------------------------------------------------+
      | sources      | Total Energy Input, Max. Capacity, Variable Costs,   |
      |              | Periodical Costs                                     |
      +--------------+------------------------------------------------------+
      | transformers | Total Energy Output, Max. Capacity, Variable Costs,  |
      |              | Investment Capacity, Periodical Costs                |
      +--------------+------------------------------------------------------+
      | storages     | Energy Output, Energy Input, Max. Capacity, Total    |
      |              | variable costs, Investment Capacity, Periodical      |
      |              | Costs                                                |
      +--------------+------------------------------------------------------+
      | links        | Total Energy Output                                  |
      +--------------+------------------------------------------------------+

      Furthermore, a list of recommended investments is printed.

      --------------

      Parameters
         
         obj:'dict' nodes_data: dictionary containing data from excel scenario file 
         obj:'oemof.solph.models.Model' optimization_model: optimized energy system                      
         obj energy_system: original (unoptimized) energy system 
        

xlsx()
-------------------------------------------------

.. container:: memitem

   .. container:: memproto

      =======================================================================================================
      def program_files.create_results.xlsx (*nodes_data*, *optimization_model*, *energy_system*, *filepath*)   
	      =======================================================================================================

   .. container:: memdoc

      Returns model results as xlsx-files.

      Saves the in- and outgoing flows of every bus of a given,
      optimized energy system as .xlsx file

      --------------

      Parameters
         
         dict nodes_data : dictionary containing data from excel scenario file         
         obj:'oemof.solph.models.Model' optimization_model: optimized energy system        
         obj energy_system: original (unoptimized) energy system    
         String filepath: path, where the results will be stored 
         
      --------------

      Return values
         
         obj'.xlsx' results: xlsx files containing in and outgoing flows of the energy systems' buses.               
