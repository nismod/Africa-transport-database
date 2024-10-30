"""Functions for preprocessing road data
    WILL MODIFY LATER
"""
import sys
import os
import json
import network as ntx
import numpy as np
import pandas as pd
import igraph as ig
import networkx
import geopandas as gpd
import fiona
from shapely.geometry import shape, mapping, LineString
from scipy.spatial import cKDTree
from tqdm import tqdm
tqdm.pandas()


def link_nodes_to_nearest_edge(network, condition=None, tolerance=1e-9):
    """Link nodes to all edges within some distance"""
    new_node_geoms = []
    new_edge_geoms = []
    for node in tqdm(
        network.nodes.itertuples(index=False), desc="link", total=len(network.nodes)
    ):
        # for each node, find edges within
        edge = ntx.nearest_edge(node.geometry, network.edges)
        if condition is not None and not condition(node, edge):
            continue
        # add nodes at points-nearest
        point = ntx.nearest_point_on_line(node.geometry, edge.geometry)
        if point != node.geometry:
            new_node_geoms.append(point)
            # add edges linking
            line = LineString([node.geometry, point])
            new_edge_geoms.append(line)

    new_nodes = ntx.matching_gdf_from_geoms(network.nodes, new_node_geoms)
    all_nodes = ntx.concat_dedup([network.nodes, new_nodes])

    new_edges = ntx.matching_gdf_from_geoms(network.edges, new_edge_geoms)
    all_edges = ntx.concat_dedup([network.edges, new_edges])

    # split edges as necessary after new node creation
    unsplit = ntx.Network(nodes=all_nodes, edges=all_edges)

    # this step is typically the majority of processing time
    split = ntx.split_edges_at_nodes(unsplit,tolerance=tolerance)

    return split
def convert_json_geopandas(df,epsg=4326):
    layer_dict = []    
    for key, value in df.items():
        if key == "features":
            for feature in value:
                if any(feature["geometry"]["coordinates"]):
                    d1 = {"geometry":shape(feature["geometry"])}
                    d1.update(feature["properties"])
                    layer_dict.append(d1)

    return gpd.GeoDataFrame(pd.DataFrame(layer_dict),geometry="geometry", crs=f"EPSG:{epsg}")

def components(edges,nodes,
                node_id_column="id",edge_id_column="id",
                from_node_column="from_id",to_node_column="to_id"):
    G = networkx.Graph()
    G.add_nodes_from(
        (getattr(n, node_id_column), {"geometry": n.geometry}) for n in nodes.itertuples()
    )
    G.add_edges_from(
        (getattr(e,from_node_column), getattr(e,to_node_column), 
            {edge_id_column: getattr(e,edge_id_column), "geometry": e.geometry})
        for e in edges.itertuples()
    )
    components = networkx.connected_components(G)
    for num, c in enumerate(components):
        print(f"Component {num} has {len(c)} nodes")
        edges.loc[(edges[from_node_column].isin(c) | edges[to_node_column].isin(c)), "component"] = num
        nodes.loc[nodes[node_id_column].isin(c), "component"] = num

    return edges, nodes

def add_lines(x,from_nodes_df,to_nodes_df,from_nodes_id,to_nodes_id):
    from_point = from_nodes_df[from_nodes_df[from_nodes_id] == x[from_nodes_id]]
    to_point = to_nodes_df[to_nodes_df[to_nodes_id].isin([x[to_nodes_id]])] 
    return LineString([from_point.geometry.values[0],to_point.geometry.values[0]])

def ckdnearest(gdA, gdB):
    """Taken from https://gis.stackexchange.com/questions/222315/finding-nearest-point-in-other-geodataframe-using-geopandas
    """
    nA = np.array(list(gdA.geometry.apply(lambda x: (x.x, x.y))))
    nB = np.array(list(gdB.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(nB)
    dist, idx = btree.query(nA, k=1)
    gdB_nearest = gdB.iloc[idx].drop(columns="geometry").reset_index(drop=True)
    gdf = pd.concat(
        [
            gdA.reset_index(drop=True),
            gdB_nearest,
            pd.Series(dist, name='dist')
        ], 
        axis=1)

    return gdf

def gdf_geom_clip(gdf_in, clip_geom):
    """Filter a dataframe to contain only features within a clipping geometry

    Parameters
    ---------
    gdf_in
        geopandas dataframe to be clipped in
    province_geom
        shapely geometry of province for what we do the calculation

    Returns
    -------
    filtered dataframe
    """
    return gdf_in.loc[gdf_in['geometry'].apply(lambda x: x.within(clip_geom))].reset_index(drop=True)

def get_nearest_values(x,input_gdf,column_name):
    polygon_index = input_gdf.distance(x.geometry).sort_values().index[0]
    return input_gdf.loc[polygon_index,column_name]

def extract_gdf_values_containing_nodes(x, input_gdf, column_name):
    a = input_gdf.loc[list(input_gdf.geometry.contains(x.geometry))]
    if len(a.index) > 0:
        return a[column_name].values[0]
    else:
        polygon_index = input_gdf.distance(x.geometry).sort_values().index[0]
        return input_gdf.loc[polygon_index,column_name]

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    config_path = os.path.join(script_dir,'..','..', 'config.json')

    with open(config_path, 'r') as config_fh:
        config = json.load(config_fh)
    return config

def create_network_from_nodes_and_edges(nodes,edges,node_edge_prefix,
                        snap_distance=None,geometry_precision=False,by=None):
    edges.columns = map(str.lower, edges.columns)
    if "id" in edges.columns.values.tolist():
        edges.rename(columns={"id": "e_id"}, inplace=True)

    # Deal with empty edges (drop)
    empty_idx = edges.geometry.apply(lambda e: e is None or e.is_empty)
    if empty_idx.sum():
        empty_edges = edges[empty_idx]
        print(f"Found {len(empty_edges)} empty edges.")
        print(empty_edges)
        edges = edges[~empty_idx].copy()

    network = ntx.Network(nodes, edges)
    print("* Done with network creation")

    network = ntx.split_multilinestrings(network)
    print("* Done with splitting multilines")
    if geometry_precision is True:
        network = ntx.round_geometries(network, precision=5)
        print("* Done with rounding off geometries")

    if nodes is not None:
        if snap_distance is not None:
            # network = ntx.link_nodes_to_edges_within(network, snap_distance, tolerance=1e-10)
            network = link_nodes_to_nearest_edge(network, tolerance=1e-9)
            print ('* Done with joining nodes to edges')
        else:
            network = ntx.snap_nodes(network)
            print ('* Done with snapping nodes to edges')
        # network.nodes = ntx.drop_duplicate_geometries(network.nodes)
        # print ('* Done with dropping same geometries')

        # network = ntx.split_edges_at_nodes(network,tolerance=9e-10)
        # print ('* Done with splitting edges at nodes')

    network = ntx.add_endpoints(network)   
    print ('* Done with adding endpoints')

    network.nodes = ntx.drop_duplicate_geometries(network.nodes)
    print ('* Done with dropping same geometries')

    network = ntx.split_edges_at_nodes(network,tolerance=1e-9)
    print ('* Done with splitting edges at nodes')
    
    network = ntx.add_ids(network, 
                            edge_prefix=f"{node_edge_prefix}e", 
                            node_prefix=f"{node_edge_prefix}n")
    network = ntx.add_topology(network, id_col='id')
    print ('* Done with network topology')

    if by is not None:
        network = ntx.merge_edges(network,by=by)
        print ('* Done with merging network')

    network.edges.rename(columns={'from_id':'from_node',
                                'to_id':'to_node',
                                'id':'edge_id'},
                                inplace=True)
    network.nodes.rename(columns={'id':'node_id'},inplace=True)
    
    return network

def network_od_path_estimations(graph,
    source, target, cost_criteria,path_id_column):
    """Estimate the paths, distances, times, and costs for given OD pair

    Parameters
    ---------
    graph
        igraph network structure
    source
        String/Float/Integer name of Origin node ID
    source
        String/Float/Integer name of Destination node ID
    tonnage : float
        value of tonnage
    vehicle_weight : float
        unit weight of vehicle
    cost_criteria : str
        name of generalised cost criteria to be used: min_gcost or max_gcost
    time_criteria : str
        name of time criteria to be used: min_time or max_time
    fixed_cost : bool

    Returns
    -------
    edge_path_list : list[list]
        nested lists of Strings/Floats/Integers of edge ID's in routes
    path_dist_list : list[float]
        estimated distances of routes
    path_time_list : list[float]
        estimated times of routes
    path_gcost_list : list[float]
        estimated generalised costs of routes

    """
    paths = graph.get_shortest_paths(source, target, weights=cost_criteria, output="epath")


    edge_path_list = []
    path_gcost_list = []
    # for p in range(len(paths)):
    for path in paths:
        edge_path = []
        path_gcost = 0
        if path:
            for n in path:
                edge_path.append(graph.es[n][path_id_column])
                path_gcost += graph.es[n][cost_criteria]

        edge_path_list.append(edge_path)
        path_gcost_list.append(path_gcost)

    
    return edge_path_list, path_gcost_list