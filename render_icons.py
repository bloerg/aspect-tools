# -*- coding: utf-8 -*-

#script that uses an input file similar to the full0_0.html files of an ASPECT run to make a mapping file from mjd-plateid-fiber-id to som_x,som_y
#please install python-beautifulsoup4, python-lxml

#in ubuntu do: sudo aptitude install python-bs4 python-lxml
#in fedora do: dnf install python-beautifulsoup4 python-lxml
#in suse linux: do FIXME



##License information
    #~ This program is free software: you can redistribute it and/or modify
    #~ it under the terms of the GNU General Public License as published by
    #~ the Free Software Foundation, either version 3 of the License, or
    #~ (at your option) any later version.

    #~ This program is distributed in the hope that it will be useful,
    #~ but WITHOUT ANY WARRANTY; without even the implied warranty of
    #~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #~ GNU General Public License for more details.

    #~ You should have received a copy of the GNU General Public License
    #~ along with this program.  If not, see <http://www.gnu.org/licenses/>.

    #~ Dieses Programm ist Freie Software: Sie können es unter den Bedingungen
    #~ der GNU General Public License, wie von der Free Software Foundation,
    #~ Version 3 der Lizenz oder (nach Ihrer Wahl) jeder neueren
    #~ veröffentlichten Version, weiterverbreiten und/oder modifizieren.

    #~ Dieses Programm wird in der Hoffnung, dass es nützlich sein wird, aber
    #~ OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
    #~ Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
    #~ Siehe die GNU General Public License für weitere Details.

    #~ Sie sollten eine Kopie der GNU General Public License zusammen mit diesem
    #~ Programm erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.



import pyfits
import string
import os
import re
import json
from PIL import Image
from PIL import ImageDraw
import matplotlib.pyplot as plt
import argparse
import sys
import multiprocessing as mp
from bs4 import BeautifulSoup



##tries to read file like full0_0.html
##returns scalar: the maximum number of spec icons (empty or not) in x, and y-direction
##returns -1 if file does not exist
def get_som_dimension_from_html(input_file):
    if os.path.exists(input_file):
        with open(input_file, 'r') as f:
            plain_html = f.read()
        html_content = BeautifulSoup(plain_html)
        table = html_content.find_all('table')
        tr = table[0].find_all('tr')
        som_y = 0
        for row in tr:
            som_x = 0
            for cell in row.find_all('td'):
                som_x = som_x +1
            som_y = som_y + 1
        return(max(som_x, som_y))
    else:
        sys.stderr.write(''.join(('Error: File does not exist: ', input_file)))
        return -1


##tries to read mapping file containing the fields x, y, mjd, plateid, fiberid, separated by $delim
##returns scalar: the maximum number of spec icons (empty or not) in x, and y-direction
def get_som_dimension_from_csv(input_file, delim):
    if os.path.exists(input_file):
        with open(input_file, "r") as csv_input:
            mapping_data_file = csv.DictReader(csv_input, delimiter=delim)
            som_dimension = 0
            for row in mapping_data_file:
                som_dimension = max(int(row['x']), int(row['y']), som_dimension)
        return(som_dimension + 1 ) # +1, because x, y starts at 0 while dimension starts at 1
    else:
        sys.stderr.write(''.join(('Error: File does not exist: ', input_file)))
        return -1


##compute the maximum zoom level of the final map from the maximum som_x, som_y extend
##returns integer for max_zoom
def get_max_zoom(som_dimension):
    if som_dimension > 0:
        max_zoom=0
        while 2**max_zoom <= som_dimension:
            max_zoom = max_zoom + 1
        return(max_zoom)
    else:
        return 0
    
##computes the number of downscaled tiles per tile at a certain zoom level
def get_plots_per_tile_at_zoom(max_zoom, zoom):
    return 2**(2 * max_zoom - zoom)


##used if graph plotted with PIL draw
##be careful: the return value is vertically flipped because PIL coordinates start at the top left
def normalize_spectrum(spectrum, new_height):
    max_spectrum = max(spectrum)
    min_spectrum = min(spectrum)
    input_spec_height = max_spectrum - min_spectrum
    if input_spec_height > 0:
        output_spectrum = []
        for element in spectrum:
            output_spectrum.append(new_height - int((element - min_spectrum) * new_height / input_spec_height))
    else:
        output_spectum = input_spectrum
    return output_spectrum



def average_over_spectrum (spectrum, new_spec_width):
    bin_width = len(spectrum) / new_spec_width
    bin_width_modulus = len(spectrum) % new_spec_width
    bin_average = 0
    bin_element_count = 0
    output_spectrum = []
    
    for element in spectrum:
        bin_average = bin_average + element
        bin_element_count = bin_element_count + 1
        if bin_element_count == bin_width:
            bin_average = bin_average / bin_width
            output_spectrum.append(bin_average)
            bin_element_count = 0
            bin_average = 0
            #in case some values would be left over after the last bin
            if len(output_spectrum) == new_spec_width - 1:
                bin_width = bin_width + bin_width_modulus
    return output_spectrum



def smp_fits_to_files ( queue ):
    try:
        for task in iter(queue.get, 'STOP'):
            try:
                fits_to_files( task[0], task[1], task[2], task[3])
            except:
                sys.stderr.write(''.join(('Something went wrong with ', task[0], "\n")))
    except Exception, e:
        sys.stderr.write("Something went wrong with one of the processes.\n")))
    return True
    

def fits_to_files ( filename, icon_size, icon_style, output_base_dir):
    fits_file_name = filename
    
    try:
        fits_file = pyfits.open(fits_file_name)
        
        
        ##Die Daten aus dem ersten HDU
        data_fields = ['tai', 'ra', 'dec', 'equinox', 'az', 'alt', 'mjd', 'quality', 'radeg', 'decdeg', 'plateid', 'tileid', 'cartid', 'mapid', 'name', 'objid', 'objtype', 'raobj', 'decobj', 'fiberid', 'z', 'z_err', 'z_conf', 'z_status', 'z_warnin', 'spec_cln']
        data = dict()
        value_string = ""
        for data_field in data_fields:
            data[data_field] = fits_file[0].header[data_field]
            #print(data_field, ': ' , data[data_field])
        
        ##we don't need equivalent widths for now
        #~ ewcount=0
        #~ for ew in fits_file[2].data['ew']:
            #~ restWave=str(fits_file[2].data['restWave'][ewcount]).replace(".","_")
            #~ ewcount = ewcount+1

        #read the spectrum from the fits file
        spectrum=fits_file[0].data[0]
        
        fits_file.close()
        
        output_path = ''.join([output_base_dir, '/', str(data['plateid'])])
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        #output_filename = ''.join([output_path, '/', str(data['mjd']), '-', str(data['plateid']), '-', str(data['fiberid']),'.png'])
        
        output_filename = ''.join([output_path, '/', os.path.basename(fits_file_name), '.png'])
        if not os.path.exists(output_filename):
            if icon_style == 'ugly':
                ##with PIL
                png_spec_file = open(output_filename, 'w')
                temp_icon_size = (icon_size, icon_size)
                temp_icon = Image.new('RGBA', temp_icon_size, None)            
                draw = ImageDraw.Draw(temp_icon)
                draw.line(zip(range(icon_size), normalize_spectrum(average_over_spectrum(spectrum.tolist(), icon_size), icon_size)), fill = 'black', width = 2)
                del draw
                temp_icon.save(output_filename, "PNG")
            if icon_style == 'nice':
                ##with pyplot
                downsized_spectrum = average_over_spectrum(spectrum.tolist(), icon_size)
                plt.clf()
                fig = plt.figure(figsize=(icon_size / 100.0, icon_size / 100.0))
                ax = plt.subplot(111,aspect = 'auto')
                ax.set_xlim(0, len(downsized_spectrum));
                #ax.set_ylim(min(downsized_spectrum), max(downsized_spectrum));
                plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
                plt.axis('off')
                plt.plot(downsized_spectrum, antialiased = True, linewidth=1.0, color='black')
                fig.savefig(output_filename, transparent=True)
                plt.close()
    except IOError:
        sys.stderr.write(''.join(('Error: could not read fits file: ', filename, "\n")))

def processDirectory (args, dirname, filenames ):
    
    for filename in filenames:
        if re.match('.*\.fit$', filename):
            if args['multiprocessing']:
                work_queue.put([dirname + "/" + filename, args['icon_size'], args['icon_style'], args['output_dir']])
            else:
                fits_to_files(dirname + "/" + filename, args['icon_size'], args['icon_style'], args['output_dir'])


if __name__ == '__main__':

    #input parameter parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputdir", type=str, required=True, help="Directory containing fits files with spectra. Can have sub directories.")
    parser.add_argument("-o", "--outputdir", type=str, required=True, help="Output directory for plotted spectra icons.")
    parser.add_argument("-s", "--iconsize", type=int, default=256, help="Dimension of the spec icons in Pixels. Default: 256")
    exclusive_output_options = parser.add_mutually_exclusive_group(required = True)
    exclusive_output_options.add_argument("-u", "--uglyicons", action="store_true", help="Use Python Image Library to plot basic and ugly graphs.")
    exclusive_output_options.add_argument("-n", "--niceicons", action="store_true",  help="Use Matplotlib to plot nicer graphs. (Default)")
    parser.add_argument("-l", "--nomultiprocessing", action="store_true", help="Use only one process for computing instead of several")
    parser.add_argument("-p", "--numberofprocesses", type=int, default=4, help="Number of Processes to use when multiprocessing")
    parser.add_argument("-d", "--delimiter", type=str, default=';', help='Delimiter for csv mapping of mjd,plateid,fiberid to som_x, som_y (defaults to ";")')
    args = parser.parse_args()    

    if os.path.exists(args.inputdir):
        if os.path.exists(args.outputdir):
            if args.uglyicons:
                icon_style='ugly'
            if args.niceicons:
                icon_style='nice'

            if args.nomultiprocessing:
                os.path.walk( args.inputdir, processDirectory, {"icon_size": args.iconsize, "icon_style": icon_style, "output_dir": args.outputdir, "multiprocessing": False})                
            else:
                workers = args.numberofprocesses
                work_queue = mp.Queue()
                processes = []
                
                for worker in range(workers):
                    p = mp.Process(target=smp_fits_to_files, args=(work_queue,))
                    p.start()
                    processes.append(p)

                os.path.walk( args.inputdir, processDirectory, {"icon_size": args.iconsize, "icon_style": icon_style, "output_dir": args.outputdir, "multiprocessing": True})

                for worker in range(workers):
                    work_queue.put('STOP')
                    
                for process in processes:
                    process.join()
               
        else:
            sys.exit(''.join(("Output Directory does not exist. Please create: ", args.outputdir)))
    else:
        sys.exit(''.join(("Input directory does not exist: ", args.inputdir, " Please check!")))

    
    
