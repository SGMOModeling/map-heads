import sys
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from matplotlib.table import table
from matplotlib.backends.backend_pdf import PdfPages

def read_from_command_line(args):
    ''' returns a list of inputs provided in a text file for running a program '''
    if len(args) == 2:
        with open(args[-1], 'r') as f:
            input_data = f.read()

    elif len(args) == 1:
        file_name = input("Please specify the name of the input file:\n")
        with open(file_name, 'r') as f:
            input_data = f.read()

    else:
        raise TypeError("Too many arguments were provided.")

    input_list = input_data.split('\n')

    clean_list = [item for item in input_list if len(item) !=0 and item[0] != '#']

    return clean_list

def get_header_from_headsout_file(headsout_file):
    ''' returns the row above the first row of data as a list '''
    with open(headsout_file, 'r') as f:        
        for line in f:
            try:
                if line[0] != '*':
                    header = previous_line.split()
                    return header[1:]
            except NameError:
                return
            else:
                previous_line = line

def headsout_to_csv(headsout_file, headsout_csv):
    ''' converts an IWFM headsout text file to csv format '''
    header = get_header_from_headsout_file(headsout_file)
    num_columns = len(header)
    header.insert(1, 'Layer')
    with open(headsout_csv, 'w') as out_csv:
        out_csv.write(','.join(header))
        with open(headsout_file, 'r') as f:
            for i, line in enumerate(f):
                if line[0] != '*':
                    line_list = line.split()
                    if len(line_list) == num_columns:
                        # reset layer when date is present
                        layer = 1
                        
                        # store date when present
                        date = line_list[0]
                    elif len(line_list) == num_columns - 1:
                        # add 1 for subsequent layer when date is not present
                        layer += 1
                        
                        # insert date when not present
                        line_list.insert(0, date)
                    else:
                        raise ValueError('line {} in file does not have the correct number of values'.format(i+1))
                        
                    out_csv.write('\n')
                    line_list.insert(1, str(layer))
                    out_csv.write(','.join(line_list))


if __name__ == '__main__':

    # get all inputs from file
    inputs_list = read_from_command_line(sys.argv)

    # convert inputs_list to individual variables    
    nodes_file = inputs_list[0]
    skiprows_nodes = int(inputs_list[1])
    node_names = inputs_list[2].split(',')
    stratigraphy_file = inputs_list[3]
    skiprows_strat = int(inputs_list[4])
    stratigraphy_names = inputs_list[5].split(',')
    headsout_file = inputs_list[6]
    headsout_csv = inputs_list[7]
    out_pdf = inputs_list[8]

    
    # convert heads to csv if csv doesn't already exist
    if not os.path.exists(headsout_csv):
        headsout_to_csv(headsout_file, headsout_csv)
    
    # read nodes
    nodes = pd.read_csv(nodes_file, header=None, 
                        names=node_names, skiprows=skiprows_nodes, 
                        delim_whitespace=True)
    
    # read stratigraphy
    stratigraphy = pd.read_csv(stratigraphy_file, header=None, 
                               names=stratigraphy_names, skiprows=skiprows_strat, 
                               delim_whitespace=True)
   
    # read heads
    heads = pd.read_csv(headsout_csv)

    # process heads
    heads['Date'] = pd.to_datetime(heads['TIME'].apply(lambda x: x.split('_')[0]), format='%m/%d/%Y')
    heads.drop('TIME', axis=1, inplace=True)
    
    sim_heads = heads.set_index(['Date', 'Layer']).stack().reset_index()
    sim_heads.rename(columns={'level_2': 'NodeID', 0: 'Heads'}, inplace=True)
    sim_heads['NodeID'] = sim_heads['NodeID'].astype(int)
    
    # merge heads with x-y coordinates and GSE by NodeID
    data = pd.merge(nodes, stratigraphy[['NodeID', 'GSE']], on='NodeID')
    data = pd.merge(sim_heads, data, on='NodeID')

    # calculate Depth to Water
    data['DTW'] = data['GSE'] - data['Heads']

    # obtain array of dates to loop over
    unique_dates = pd.Series(data['Date'].unique(), name="Date")
    dates = unique_dates.dt.strftime('%m/%d/%Y')
    
    # obtain list of Layers to loop over
    layers = data['Layer'].unique()

    # plot and save to PDF
    with PdfPages(out_pdf) as pdf:
        plt.ioff()
      
        for dt in dates:
            for lyr in layers:
                print('Plotting {} for Layer {}'.format(dt, lyr))

                # get selection of single date and layer with depths to water above G.S.
                h = data[(data['Date'] == dt) & (data['Layer'] == lyr) & (data['DTW'] < 0)]
                num_values = len(h)

                fig, ax = plt.subplots(figsize=(8.5, 11))
                
                # set plot properties
                ax.set_aspect('equal')
                ax.set_xlabel('Easting (m)')
                ax.set_ylabel('Northing (m)')
                ax.set_title('Depth to Water on {} for Layer {}'.format(dt, lyr))
                ax.grid(True)

                # use rasterized=True to reduce size of pdf
                ax.scatter(nodes.X, nodes.Y, s=1, c='0.9', rasterized=True)

                if num_values > 0:
                    pcm = ax.scatter(h['X'], h['Y'], s=2, c=h['DTW'], cmap='viridis', rasterized=True, vmin=-50, vmax=0)

                    # add color bar for reference
                    cbar = fig.colorbar(pcm, ax=ax)
                    cbar.solids.set_rasterized(True)
                    cbar.set_label('Head Above Ground Surface (ft)', fontsize=16)

                    # add table to note maximum depths to water above ground surface
                    max_dtw = h['DTW'].min() # minimum value because heads above g.s. are negative
                    max_values = h[h['DTW'] == max_dtw]
                    num_max_values = len(max_values)        
                
                    table_vals = [['Number of Heads\nAbove Ground Surface', str(num_values)], 
                                  ['Maximum Head above\nLand Surface (ft)', str(round(abs(max_dtw), 2))], 
                                  ['Number of Locations\nwith Max Head', str(num_max_values)]]
                    
                    cell_color = [['white', 'white'],
                                  ['white', 'white'],
                                  ['white', 'white']]

                    tbl = table(ax, cellText=table_vals,
                                cellColours=cell_color,
                                bbox=[0.5, 0.7, 0.40, 0.2],
                                rasterized=True,
                                zorder=10)

                    tbl.auto_set_font_size(False)
                    tbl.set_fontsize(8)

                    tbl.auto_set_column_width(col=[0,1])
                                
                    # plot locations of max heads above ground surface
                    ax.scatter(max_values.X, max_values.Y, s=50, facecolors='none', edgecolors='r')

                    ax1 = fig.add_axes([0.25, 0.15, 0.2, 0.1])

                    ax1.hist(h['DTW'], bins=30, rasterized=True)
                    ax1.set_xlabel("DTW above land surface (ft)")
                    ax1.set_ylabel("Count")

                else:
                    ax.text(0.5, 0.5, 'No Values Above Land Surface', horizontalalignment='center',
                            verticalalignment='center', transform=ax.transAxes)

                plt.tight_layout()
                pdf.savefig()

                plt.cla()
                plt.close('all')

        plt.ion()
