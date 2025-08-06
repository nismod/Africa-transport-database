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
                            processed_data_path,
                            "infrastructure",
                            "africa_multimodal.gpkg"))
    class_types = list(set(proximity_matches["link_type"].values.tolist()))
    closest_classes = [(c,str(c).upper()) for c in class_types]
    colors = [
                "#d53e4f","#f46d43","#fdae61","#fee08b","#ffffbf","#e6f598","#abdda4","#66c2a5","#3288bd"
            ]
    cl_df = pd.DataFrame(closest_classes,columns=["link_type","link_class"])
    proximity_matches = pd.merge(proximity_matches,cl_df,how="left",on=["link_type"])
    df = []
    closest_types = list(set(proximity_matches["link_class"].values.tolist()))
    fig, ax1 = plt.subplots()
    for ct in closest_types:
        df.append(proximity_matches[proximity_matches["link_class"] == ct]["length_m"].values)
    
    counts, edges, bars = ax1.hist(df,histtype='barstacked',bins=30)
    counts = [0.5*c for c in counts]
    max_y = max([max(c) for c in counts])

    fig, axe = plt.subplots(1,1,figsize=(18,9),dpi=500)
    for idx,(ct,cl) in enumerate(zip(closest_types,colors[:len(closest_types)])):
        if idx == 0:
            axe.bar(edges[:-1],counts[idx],width=np.diff(edges),color=cl,edgecolor='w',linewidth=0.5,label=ct)  # make bar plots
        else:
            yval = counts[idx] - counts[idx-1]
            axe.bar(edges[:-1],yval,bottom=counts[idx-1],width=np.diff(edges),color=cl,edgecolor='w',linewidth=0.5,label=ct)  # make bar plots
        if idx == len(closest_types) - 1:
            text = [str(int(c)) for c in counts[idx]]
            for jdx,(x,y,s) in enumerate(zip(edges[:-1],counts[idx],text)):
                if int(s) > 0:  
                    axe.text(x,1.02*y,s,fontweight='bold',fontsize=11,ha='center')
    
    legend = axe.legend(title ="Multi-modal connection type",loc='upper right',fontsize=15,title_fontproperties={'weight':'bold'})
    plt.setp(legend.get_title(),fontsize=18)
    axe.set_xlabel("Edge length (meters)",fontweight='bold',fontsize=15)
    axe.set_ylabel("Count of multi-modal links by length (#)",fontweight='bold',fontsize=15)
    axe.set_ylim(0,1.1*max_y)
    axe.tick_params(axis='y',labelsize=15)
    axe.tick_params(axis='x',labelsize=15)
    axe.set_title(
                    "Lengths of connections to indicate multi-modal proximity",
                    fontweight='bold',
                    fontsize=18
                )
    axe.set_axisbelow(True)
    axe.grid(which='major', axis='y', linestyle='-', zorder=0)
    save_fig(os.path.join(figures,
                "multi_modal_proximity.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)