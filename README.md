# Africa transport database
We present the first comprehensive geolocated multi-modal transport database for the whole continent of Africa, the **African Transport Systems Database (AfTS-Db)**, including road, rail, aviation, maritime and inland waterway networks. To do so, we created and standardized asset and network data across all transport modes, including inter-modal connections, attributes of road and rail corridors and estimated annual statistics for airports and ports. The African Transport Systems Database includes 234 airports including their airline routes, 179 maritime ports and their connections with each other, 132 inland ports and docking sites with river and lake connections, 4,412 railway stations connected across 99,373 kilometers of rail lines, and 1,004,512 kilometers of roads mainly comprised of all motorways, trunk roads, primary and secondary routes across Africa and some local roads that connect to other transport modes. The AfTS-Db provides key information for transport planning, resilience assessments, asset management and development of transport models and applications. Furthermore, we expect the data will also be of relevance for environmental, health, social and economic studies. <br/>
This GitHub folder contains the scripts that have been used to create the database, of particular importance the road network creation and the multimodal edges creation ones.

## About the scripts
All the scripts used to create the datasets are available and free to use in the [**scripts folder**](https://github.com/nismod/Africa-transport-database/tree/main/scripts), ensuring replicability of the database. Most of them represent simple cleaning and validation (in the [**preprocess**](https://github.com/nismod/Africa-transport-database/tree/main/scripts/preprocess) folder) or plots and figures (in the [**maps and stats**](github.com/nismod/Africa-transport-database/tree/main/scripts/maps%20and%20stats) and [**plot**](https://github.com/nismod/Africa-transport-database/tree/main/scripts/plot) folders) reproduction codes. <br/>
Of major importance and representing the novelty of how the dataset has been developed, are the [road network creation](https://github.com/nismod/Africa-transport-database/blob/main/scripts/preprocess/road_connectivity.py) and the [multimodal links creation](https://github.com/nismod/Africa-transport-database/blob/main/scripts/preprocess/multi_modal_edges_creation.py).

### Road network creation
The road topological network creation follows 5 maing steps: <br/>
<br/>
Step 1: Input the different location data from different extracts (infrastructures, cities, ...)<br/>
Step 2: Input the road edges data for Africa (already extracted from Oper Street Map)<br/>
Step 3: Filter the OSM roads to the preferred geographical scale (in this case up to secondary roads)<br/>
Step 4: Connect the points of interest with the closest point of the road network, creating a topological network <br/>
Step 5: Create a more capillary network when the resolution of the filtered roads is not enough to connect specific points, connect the selection of smaller roads to the network<br/>


### Multimodal links creation


