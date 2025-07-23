import os
import sys
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from map_plotting_utils import *
from tqdm import tqdm
tqdm.pandas()

def main(config):
    config = load_config()
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    output_path = config['paths']['results']
    figure_path = config['paths']['figures']

    figures = os.path.join(figure_path)
    proximity_matches = gpd.read_file(os.path.join(
                            output_path,
                            "africa-station-google-points",
                            "location_proximity_final.gpkg"))
    closest_classes = [
                        ('air',"Airports"), 
                        ('Mineral Processing Plants', "Mineral Processing Plants - USGS"), 
                        ('manual check',"Manual check - Satellite imagery"), 
                        ('IWW port',"Inland ports"), 
                        ('Manual check',"Manual check - Satellite imagery"), 
                        ('port',"Martime ports"), ('manul check',"Manual check - Satellite imagery"), 
                        ('google',"Google places search"), 
                        ('Oil and Gas Refineries and (or) Petrochemical Complexes',"Oil Refineries - USGS"), 
                        ('mine',"Remote sensed mines"), 
                        ('Mines and Quarries',"Mines and Quarries - USGS"), 
                        ('Martime port',"Martime ports")
                    ]
    colors = [
                "#d53e4f","#f46d43","#fdae61","#fee08b","#ffffbf","#e6f598","#abdda4","#66c2a5","#3288bd"
            ]
    cl_df = pd.DataFrame(closest_classes,columns=["closest_type","closest_class"])
    proximity_matches = pd.merge(proximity_matches,cl_df,how="left",on=["closest_type"])
    df = []
    closest_types = list(set(proximity_matches["closest_class"].values.tolist()))
    fig, ax1 = plt.subplots()
    for ct in closest_types:
        df.append(proximity_matches[proximity_matches["closest_class"] == ct]["closest_distance"].values)
    
    counts, edges, bars = ax1.hist(df,histtype='barstacked',bins=30)
    max_y = max([max(c) for c in counts])

    fig, axe = plt.subplots(1,1,figsize=(18,9),dpi=500)
    for idx,(ct,cl) in enumerate(zip(closest_types,colors)):
        if idx == 0:
            axe.bar(edges[:-1],counts[idx],width=np.diff(edges),color=cl,edgecolor='k',label=ct)  # make bar plots
        else:
            yval = counts[idx] - counts[idx-1]
            axe.bar(edges[:-1],yval,bottom=counts[idx-1],width=np.diff(edges),color=cl,edgecolor='k',label=ct)  # make bar plots
        if idx == len(closest_types) - 1:
            text = [str(int(c)) for c in counts[idx]]
            for jdx,(x,y,s) in enumerate(zip(edges[:-1],counts[idx],text)):  
                axe.text(x,1.02*y,s,fontweight='bold',fontsize=11,ha='center')
    
    legend = axe.legend(title ="Validation data source",loc='upper right',fontsize=15,title_fontproperties={'weight':'bold'})
    plt.setp(legend.get_title(),fontsize=18)
    axe.set_xlabel("Closest distance (meters)",fontweight='bold',fontsize=15)
    axe.set_ylabel("Count of rail facilities by closest asset type (#)",fontweight='bold',fontsize=15)
    axe.set_ylim(0,max_y+10)
    axe.tick_params(axis='y',labelsize=15)
    axe.tick_params(axis='x',labelsize=15)
    axe.set_title(
                    "Proximity of rail facilities to similar locations identified from other data sources",
                    fontweight='bold',
                    fontsize=18
                )
    axe.set_axisbelow(True)
    axe.grid(which='major', axis='y', linestyle='-', zorder=0)
    save_fig(os.path.join(figures,
                "rail_facility_proximity.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)