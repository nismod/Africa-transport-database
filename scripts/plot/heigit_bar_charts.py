"""Generate bar plots
"""
import os
import sys
import pandas as pd
pd.options.mode.copy_on_write = True
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
from matplotlib.ticker import (MaxNLocator,LinearLocator, MultipleLocator)
from itertools import cycle, islice
import matplotlib.pyplot as plt
from matplotlib import cm
from map_plotting_utils import *
from tqdm import tqdm
tqdm.pandas()

# mpl.style.use('ggplot')
# mpl.rcParams['font.size'] = 10.
# mpl.rcParams['font.family'] = 'tahoma'
# mpl.rcParams['axes.labelsize'] = 12.
# mpl.rcParams['xtick.labelsize'] = 10.
# mpl.rcParams['ytick.labelsize'] = 10.


def plot_clustered_stacked(fig,axe,
                            dfall,
                            bar_colors,
                            labels=None,
                            ylabel="Y-values",
                            legend_title=None,
                            title="multiple stacked bar plot",
                            H="/",**kwargs):
    """ 
        Source: https://stackoverflow.com/questions/22787209/how-to-have-clusters-of-stacked-bars
        Given a list of dataframes, with identical columns and index, create a clustered stacked bar plot. 
        labels is a list of the names of the dataframe, used for the legend
        title is a string for the title of the plot
        H is the hatch used for identification of the different dataframe
    """

    """
        # create fake dataframes
        df1 = pd.DataFrame(np.random.rand(4, 5),
                           index=["A", "B", "C", "D"],
                           columns=["I", "J", "K", "L", "M"])
        df2 = pd.DataFrame(np.random.rand(4, 5),
                           index=["A", "B", "C", "D"],
                           columns=["I", "J", "K", "L", "M"])
        df3 = pd.DataFrame(np.random.rand(4, 5),
                           index=["A", "B", "C", "D"], 
                           columns=["I", "J", "K", "L", "M"])

        # Then, just call :
        plot_clustered_stacked([df1, df2, df3],["df1", "df2", "df3"])
    """

    n_df = len(dfall)
    n_col = len(dfall[0].columns) 
    n_ind = len(dfall[0].index)
    # axe = plt.subplot(111)

    for d in range(len(dfall)): # for each data frame
        df = dfall[d]
        bc = bar_colors[d]
        axe = df.plot(kind="bar",
                      linewidth=1.0,
                      stacked=True,
                      ax=axe,
                      legend=False,
                      grid=False,
                      color = bc,
                      edgecolor = 'white',
                      **kwargs)  # make bar plots

    h,l = axe.get_legend_handles_labels() # get the handles we want to modify
    for i in range(0, n_df * n_col, n_col): # len(h) = n_col * n_df
        for j, pa in enumerate(h[i:i+n_col]):
            for rect in pa.patches: # for each index
                rect.set_x(rect.get_x() + 1 / float(n_df + 1) * i / float(n_col))
                if H is not None:
                    rect.set_hatch(H * int(i / n_col)) #edited part     
                rect.set_width(1 / float(n_df + 1))

    # sec.set_xticks([5, 15, 25], labels=['\nOughts', '\nTeens', '\nTwenties'])
    axe.set_xticks((np.arange(0, 2 * n_ind, 2) + 1 / float(n_df + 1)) / 2.)
    # axe.set_xticks(np.arange(0,n_ind, 1))
    axe.set_xticklabels(df.index,rotation=90,ma="left",fontsize=10,fontweight="bold")
    axe.set_xlabel('')
    axe.set_ylabel(ylabel,fontweight='bold',fontsize=15)
    axe.tick_params(axis='y',labelsize=15)
    axe.set_title(title,fontweight='bold',fontsize=18)
    axe.set_axisbelow(True)
    axe.grid(which='major', axis='x', linestyle='-', zorder=0)

    legend_handles = []
    titles = [legend_title]
    legend_handles.append(axe.plot([],[],
                                    color="none",
                                    label=legend_title)[0])
    for d in range(len(dfall)):
        bcs = bar_colors[d]
        lbls = labels[d]
        for idx,(bc,bl) in enumerate(zip(bcs,l[:n_col])):
            if H is not None:
                legend_handles.append(mpatches.Patch(facecolor=bc,edgecolor='white',
                                        label=lbls[idx],hatch=H*d))
            else:
                legend_handles.append(mpatches.Patch(facecolor=bc,edgecolor='white',
                                        label=lbls[idx]))
    leg = axe.legend(
                handles=legend_handles, 
                fontsize=15, 
                loc='upper left',
                frameon=False)

    # Move titles to the left 
    for item, label in zip(leg.legend_handles, leg.texts):
        if label._text in titles:
            width = item.get_window_extent(fig.canvas.get_renderer()).width
            label.set_ha('left')
            label.set_position((-10.0*width,0))
    return axe

def main(config):
    processed_data_path = config['paths']['data']
    output_data_path = config['paths']['results']
    figure_path = config['paths']['figures']

    make_plot = True
    if make_plot is True:
        multiply_factor = 0.001
        results_file = os.path.join(output_data_path,
                                    "merged_validation_datasets_corrected.csv")
        road_columns = [["length_db_m_paved","length_db_m_unpaved"],["length_heigit_m_paved","length_heigit_m_unpaved"]]
        iso_column = "country_iso_a3"
        road_colors = [
                    ["#d53e4f","#f46d43"],["#014636","#a6bddb"]
                ]
        road_labels = [["Our database - Paved","Our database - Unpaved"],["HeiGIT - Paved","HeiGIT - Unpaved"]]
    
        fig, ax = plt.subplots(1,1,figsize=(18,9),dpi=500)
        data_df = pd.read_csv(results_file)
        country_name = pd.read_excel(
                            os.path.join(
                                processed_data_path,
                                "admin_boundaries",
                                "country_codes.xlsx"))[["country_name_full","iso_3digit_alpha"]]
        country_name.rename(columns={"iso_3digit_alpha":iso_column},inplace=True)
        data_df = pd.merge(data_df,country_name)
        data_df = data_df.sort_values(by="country_name_full",ascending=True)
        dfall = []
        for rt in road_columns:
            df = data_df[["country_name_full"] + rt]
            df[rt] = multiply_factor*df[rt]
            dfall.append(df.set_index(["country_name_full"]))
        ax = plot_clustered_stacked(
                                    fig,ax,dfall,road_colors,
                                    labels=road_labels,
                                    ylabel="Road length (km)", 
                                    legend_title = "$\\bf{Road \, types}$",
                                    title="Heigit vs Our database - Length comparisons between paved and unpaved roads")
        plt.grid()
        plt.tight_layout()
        save_fig(os.path.join(figure_path,
                    "heigit_comparison.png"))
        plt.close()

        road_columns = [["length_paved_diff"],["length_unpaved_diff"]]
        road_colors = [
                    ["#d53e4f"],["#014636"]
                ]
        road_labels = [["Paved"],["Unpaved"]]

        data_df["length_paved_diff"
            ] = np.where(data_df["length_db_m_paved"] > 0,
                    100.0*(data_df["length_heigit_m_paved"] - data_df["length_db_m_paved"])/data_df["length_db_m_paved"],0)
        data_df["length_unpaved_diff"
            ] = np.where(data_df["length_db_m_unpaved"] > 0,
                    100.0*(data_df["length_heigit_m_unpaved"] - data_df["length_db_m_unpaved"])/data_df["length_db_m_unpaved"],0)

        data_df.to_csv(os.path.join(output_data_path,
                                    "merged_validation_datasets_differences.csv"))
        fig, ax = plt.subplots(1,1,figsize=(18,9),dpi=500)
        multiply_factor = 1.0
        dfall = []
        for rt in road_columns:
            df = data_df[["country_name_full"] + rt]
            df[rt] = multiply_factor*df[rt]
            dfall.append(df.set_index(["country_name_full"]))
        ax = plot_clustered_stacked(
                                    fig,ax,dfall,road_colors,
                                    labels=road_labels,
                                    ylabel="Length difference (%)", 
                                    legend_title = "$\\bf{Road \, types}$",
                                    H=None,
                                    title="Heigit vs Our database - Length differences between paved and unpaved roads")
        plt.grid()
        plt.tight_layout()
        save_fig(os.path.join(figure_path,
                    "heigit_difference.png"))
        plt.close()

    
    make_plot = True
    if make_plot is True:
        results_file = os.path.join(output_data_path,
                                "rails.xlsx")
        multiply_factor = 1.0
        rail_columns = [["CIA"],["WorldPop Review"],["Railway network database "]]
        rail_colors = [
                    ["#41b6c4"],["#99d8c9"],["#014636"]
                ]
        rail_labels = [["CIA"],["WorldPop Review"],["Our database"]]
        fig, ax = plt.subplots(1,1,figsize=(18,9),dpi=500)
        data_df = pd.read_excel(results_file,sheet_name="lengths")
        data_df = data_df.sort_values(by="Country",ascending=True)
        dfall = []
        for rt in rail_columns:
            df = data_df[["Country"] + rt]
            df[rt] = multiply_factor*df[rt]
            dfall.append(df.set_index(["Country"]))
        ax = plot_clustered_stacked(
                                    fig,ax,dfall,rail_colors,
                                    labels=rail_labels,
                                    ylabel="Railways length (km)",
                                    H=None,
                                    legend_title="$\\bf{Railways \, data \, sources}$", 
                                    title="CIA vs Worlpop Review vs Our database - Length comparisons between railways")
        plt.grid()
        plt.tight_layout()
        save_fig(os.path.join(figure_path,
                    "rail_comparisons.png"))
        plt.close()



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
