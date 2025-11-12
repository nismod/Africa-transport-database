# The African Transport Systems Database (AfTS-Db): an open geospatial database of multi-modal connected networks 
We present the first comprehensive geolocated multi-modal transport database for the whole continent of Africa, the **African Transport Systems Database (AfTS-Db)**, including road, rail, aviation, maritime and inland waterway networks. To do so, we created and standardized asset and network data across all transport modes, including inter-modal connections, attributes of road and rail corridors and estimated annual statistics for airports and ports. The African Transport Systems Database includes 234 airports including their airline routes, 179 maritime ports and their connections with each other, 132 inland ports and docking sites with river and lake connections, 4,412 railway stations connected across 99,373 kilometers of rail lines, and 1,004,512 kilometers of roads mainly comprised of all motorways, trunk roads, primary and secondary routes across Africa and some local roads that connect to other transport modes. The AfTS-Db provides key information for transport planning, resilience assessments, asset management and development of transport models and applications. Furthermore, we expect the data will also be of relevance for environmental, health, social and economic studies. <br/><br/>

This GitHub folder contains the scripts that have been used to create the database, of particular importance the road network creation and the multimodal edges creation ones.
<br/><br/>

The codes for operationalization for downloading and creating network representations from OSM raw data, via the Open-Gira repository, are available here: https://github.com/nismod/open-gira. Further Open-Gira documentation is provided here: https://nismod.github.io/open-gira/user-guide/usage/network-creation/road.html and https://nismod.github.io/open-gira/user-guide/usage/network-creation/rail.html. 
<br/><br/>

The spatially explicit, harmonized AfTS-Db is publicly available and can be explored [here](https://doi.org/10.5281/zenodo.15527231). These files can be easily accessed, visualized, and manipulated using standard GIS applications such as QGIS or ArcGIS.
<br/><br/>

This research has been supported by the **Climate Compatible Growth (CCG)** program funded by the UK Foreign, Commonwealth and Development Office ([FCDO](https://devtracker.fcdo.gov.uk/programme/GB-GOV-1-300125/summary)).

## About the scripts
All the scripts used to create the datasets are available and free to use in the [**scripts folder**](https://github.com/nismod/Africa-transport-database/tree/main/scripts), ensuring replicability of the database. Most of them represent simple cleaning and validation (in the [**preprocess**](https://github.com/nismod/Africa-transport-database/tree/main/scripts/preprocess) folder) or plots and figures (in the [**maps and stats**](github.com/nismod/Africa-transport-database/tree/main/scripts/maps%20and%20stats) and [**plot**](https://github.com/nismod/Africa-transport-database/tree/main/scripts/plot) folders) reproduction codes. <br/>
Of major importance and representing the novelty of how the dataset has been developed, are the [road network creation](https://github.com/nismod/Africa-transport-database/blob/main/scripts/preprocess/road_connectivity.py) and the [multimodal links creation](https://github.com/nismod/Africa-transport-database/blob/main/scripts/preprocess/multi_modal_edges_creation.py).

### Road network creation
The road topological network creation follows 5 main steps: <br/>
<br/>
**Step 1:** Input the different location data from different extracts (infrastructure assets, cities, ...)<br/>
**Step 2:** Input the road edges data for Africa (already extracted from Oper Street Map)<br/>
**Step 3:** Filter the OSM roads to the preferred geographical scale (in this case up to secondary roads)<br/>
**Step 4:** Connect the points of interest with the closest point of the road network, creating a topological network <br/>
**Step 5:** Create a more capillary network when the resolution of the filtered roads is not enough to connect specific points, connect the selection of smaller roads to the network<br/>


### Multimodal links creation
The multimodal network creation constists on:<br/>
<br/>
**Step 1:** Input the different point location data from all the transport datasets: airports, maritime ports, inland ports, railway stations and points of interest, road nodes <br/>
**Step 2:** Connect the different nodes to the ground transport network (road and rail nodes) <br/>
**Step 3:** Differentiate the connection between freight transport (specific rail-road connection based on the facility specifics of the rail node) and general freight/passenger transport (the rest of the connections, if not specified) <br/>
**Step 4:** The resulting dataset will include edges identified by unique IDs, along with references to the source and target nodes they connect, as well as details about the link and its usage (freigth ore freight/transport)
 
