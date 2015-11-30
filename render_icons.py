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



import pyfits # for reading fits files
import numpy # for numbers and such
import string # string manipulation
import os # for path related operations
import re # for filename parsing
import json # for json
from PIL import Image # for Image manipulation
from PIL import ImageDraw # for spec icon stitching
import matplotlib.pyplot as plt # for plotting the spectra
import argparse # for input argument parsing
import sys # for stderr, stdout
import multiprocessing as mp # for smp
from bs4 import BeautifulSoup # for html parsing
from StringIO import StringIO # for the file like objects to hold the spec icons until saving on hard disk
from shutil import copyfileobj# to copy the StringIO-Objects to real files
import csv # for csv input/output



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
    return (2**(2 * (max_zoom - zoom)))
    

##returns the tile coordinates in the coordinate_system of lower zoom level
def get_tile_at_zoom(tile_x, tile_y, max_zoom, at_zoom):
    number_of_tiles = 2**(max_zoom - at_zoom)
    return(tile_x / number_of_tiles, tile_y / number_of_tiles)



#adds empty Icon as Image Object to Iconlist
def return_icon_to_paste_to(icons, coordinates_at_zoom):
    x_at_zoom, y_at_zoom = coordinates_at_zoom
    icon_size = icons['icon_size']
    try:
        result = icons[x_at_zoom][y_at_zoom]
        return result
    except KeyError:
        try:
            icons[x_at_zoom][y_at_zoom] = {'touched': 0, 'icon': Image.new('RGBA', (icon_size, icon_size), None)}
            result = icons[x_at_zoom][y_at_zoom]
            return result
        except KeyError:
            icons[x_at_zoom] = {y_at_zoom: {'touched': 0, 'icon': Image.new('RGBA', (icon_size, icon_size), None)}}
            result = icons[x_at_zoom][y_at_zoom]
            return result

#plots input spectrum, returns file like object containing png representation of plot
def plot_spectrum(spectrum, icon_size, max_zoom, zoom):
    output_icon = StringIO()
    number_of_tiles = 2**(max_zoom - zoom)
    #downsized_spectrum = average_over_spectrum(spectrum.tolist(), icon_size)
#    plt.clf()
    if len(spectrum) == 0:
        plot_size = (icon_size / number_of_tiles , icon_size / number_of_tiles)
        empty_icon = Image.new('RGBA', plot_size, None)
        empty_icon.save(output_icon, "PNG")
    else:
        plot_size = (icon_size / number_of_tiles / 100.0, icon_size / number_of_tiles / 100.0)
        fig = plt.figure(figsize=plot_size)
        ax = plt.subplot(111,aspect = 'auto')
        ax.set_xlim(0, len(spectrum));
        plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        plt.axis('off')
        plt.plot(spectrum, antialiased = True, linewidth=1.0, color='black')
        fig.savefig(output_icon, transparent=True, format='png')
        plt.close()
    return output_icon

#pastes a spec_plot into an icon at position
#expects a plot as png file like object, an icon as Image object and the position within the image object as tuple (x,y)
def paste_plot_to_icon(plot, icon, position):
    at_x, at_y = position
    try:

        #~ if not os.path.exists('/var/tmp/test.png'):
            #~ my_plot = plot   
            #~ with open('/var/tmp/test.png', 'w') as testpng:
                #~ my_plot.seek(0)
                #~ copyfileobj(my_plot, testpng)  
            #~ my_plot.close()
            #~ my_plot.seek(0)
            #~ temp_image = Image.new('RGBA', (256, 256), None)
            #~ temp_image.paste(Image.open(my_plot), (0,0))
            #~ temp_image.save('/var/tmp/test.png', "PNG")
        plot.seek(0)
        icon['icon'].paste(Image.open(plot), position)
        #temp_plot = Image.open(plot)
        #temp_plot.load()
        #icon['icon'].paste(temp_plot, (0,0))
        #~ if not os.path.exists('/var/tmp/test.png'):
            #~ icon['icon'].save('/var/tmp/test.png', "PNG")
        icon['touched'] = icon['touched'] + 1
        plot.close()
        del(plot)
        return True
    except Exception, e:
        return False

#returns the relative position of a plot in pixels within a spec icon at a certain zoomlevel
def return_paste_position_in_icon(som_coordinates, icon_size, max_zoom, zoom):
    number_of_tiles = 2**(max_zoom - zoom)
    shift_width = icon_size / number_of_tiles
    som_x, som_y = som_coordinates
    #zoomed_x, zoomed_y = get_tile_at_zoom(som_x, som_y, max_zoom, zoom)
    paste_position = ((som_x % number_of_tiles) * shift_width, (som_y % number_of_tiles) * shift_width)
    return paste_position
    

def save_icon_to_file(icon, spec_dir, zoom, icon_x, icon_y):
    spectrum_output_path = ''.join((spec_dir, '/', str(icon_x), '-', str(icon_y), '.png'))
    try:
        icon['icon'].save(spectrum_output_path, "PNG")
        del(icon)
    except IOError:
        sys.stderr.write(''.join(('Error: Could not write file: ', spectrum_output_path)))
    finally:
        return True


##worker function
def spec_worker(plot_queue, max_zoom, zoom, icon_size, output_directory):
    icons = {'spec_dir': '/'.join((output_directory, "icons", str(zoom))), 'icon_size': icon_size, 'zoom': zoom, 'max_zoom': max_zoom}
    if not os.path.exists(icons['spec_dir']):
        os.makedirs(icons['spec_dir'])    
    plots_per_tile = get_plots_per_tile_at_zoom(max_zoom, zoom)
    try:
        for task in iter(plot_queue.get, 'STOP'):
            if zoom > 7:
                try:            
                    spectrum, som_coordinates = task
                    som_x, som_y = som_coordinates
                    icon_to_paste_to = return_icon_to_paste_to(icons, get_tile_at_zoom(som_x, som_y, max_zoom, zoom))
                    paste_icon_x, paste_icon_y = get_tile_at_zoom(som_x, som_y, max_zoom, zoom)
                    plotted_spectrum = plot_spectrum(spectrum, icon_size, max_zoom, zoom) # this is freed in paste_plot_to_icon ()
                    plotted_spectrum.seek(0)
                    if zoom == 10:
                        print("pasting plot of som: ", som_coordinates, "in icon", paste_icon_x, paste_icon_y, "at ", return_paste_position_in_icon(som_coordinates, icon_size, max_zoom, zoom), 'with speclen: ', len(spectrum))
                    paste_plot_to_icon(plotted_spectrum, icon_to_paste_to , return_paste_position_in_icon(som_coordinates, icon_size, max_zoom, zoom))
                    if icon_to_paste_to['touched'] == plots_per_tile:
                        save_icon_to_file(icon_to_paste_to, icons['spec_dir'], zoom, paste_icon_x, paste_icon_y)
                        print (''.join(('Info: Have written (zoom, x, y) : ', str(zoom), ', ', str(paste_icon_x), ',', str(paste_icon_y))))

                    #~ if len(spectrum) > 0:
                        #~ my_plot = plot_spectrum(spectrum, icon_size, max_zoom, zoom)
                        #~ with open(''.join(('/var/tmp/sdssdr7specs/icons/', str(zoom),'/',str(som_x),'-', str(som_y),'.png')),'w') as output_png:
                            #~ my_plot.seek(0)
                            #~ copyfileobj(my_plot, output_png)
                        #~ my_plot.close()
                        #~ del(my_plot)
                            
                            
                    #~ my_plot = plot_spectrum(spectrum, icon_size, max_zoom, zoom)
                    #~ im = Image.open(my_plot)
                    #~ im.save(''.join(('/var/tmp/sdssdr7specs/icons/', str(zoom),'/',str(som_x),'-', str(som_y),'.png')))
                    #~ my_plot.close()
                    #~ del(my_plot)
                    #~ with open(''.join(('/var/tmp/sdssdr7specs/icons/', str(zoom),'/',str(som_x),'-', str(som_y),'.png')),'w') as output_png:
                        #~ my_plot = plot_spectrum(spectrum, icon_size, max_zoom, zoom)
                        #~ my_plot.seek(0,2)
                        #~ print("size outside",my_plot.tell())
                        #~ #my_plot.seek(0)
                        #~ copyfileobj(my_plot, output_png)
                        #~ my_plot.close()
                        #~ del(my_plot)
                except Exception, e:
                    sys.stderr.write(''.join(('Something went wrong with ', str(task[1]), " Exception: ", str(e), " zoom: ", str(zoom), "spec_length: ", str(len(spectrum)), "\n")))

    except Exception, e:
        sys.stderr.write("Something went wrong with one of the processes.\n")
    return True

def fill_plot_queue_csv(queues, input_file, plate_directory, icon_size, som_dimension):
    empty_spectrum = []
    try:
        mapping_data_file = csv.DictReader(open(input_file, "rb"), delimiter=";")
        som_x = 0
        som_y = 0
        for row in mapping_data_file:
            data = dict()
            data = row
            csv_som_x = int(data['x'])
            csv_som_y = int(data['y'])
            csv_mjd = int(data['MJD'])
            csv_plateid = int(data['plateID'])
            csv_fiberid = int(data['fibID'])
            
            if csv_som_x > som_x:
                for x in range(som_x, csv_som_x):
                    if csv_som_y > som_y:
                        for y in range(som_y, csv_som_y):
                            mjd = -1
                            plateid = -1
                            fiberid = -1
                            for queue in queues:
                                queue.put((empty_spectrum, (x,y)))
                            som_y = som_y +1
                    else:
                        mjd = -1
                        plateid = -1
                        fiberid = -1
                        for queue in queues:
                            queue.put((empty_spectrum, (x,som_y)))
                    som_x = som_x + 1
                    if som_x == som_dimension:
                        som_x = 0
                        som_y = som_y +1
                        
            

            ##for sdss dr7 specs
            padded_plateid = ''.join(('0000', str(csv_plateid)))
            padded_plateid = padded_plateid[-4:]
            padded_fiberid = ''.join(('000', str(csv_fiberid)))
            padded_fiberid = padded_fiberid[-3:]
            fits_file_path=''.join((plate_directory, '/', str(csv_plateid), '/spSpec-', str(csv_mjd), '-', padded_plateid,'-',padded_fiberid, '.fit'))
            
            try:
                fits_file = pyfits.open(fits_file_path)
                ##data from the first HDU
                #~ data_fields = ['tai', 'ra', 'dec', 'equinox', 'az', 'alt', 'mjd', 'quality', 'radeg', 'decdeg', 'plateid', 'tileid', 'cartid', 'mapid', 'name', 'objid', 'objtype', 'raobj', 'decobj', 'fiberid', 'z', 'z_err', 'z_conf', 'z_status', 'z_warnin', 'spec_cln']
                #~ data = dict()
                #~ value_string = ""
                #~ for data_field in data_fields:
                    #~ data[data_field] = fits_file[0].header[data_field]
                spectrum=average_over_spectrum(fits_file[0].data[0].tolist(), icon_size)
                #spectrum=average_over_spectrum(spectrum.tolist(), icon_size)
                fits_file.close()
            except:
                spectrum = []
            for queue in queues:
                queue.put((spectrum, (som_x, som_y)))
            som_x = som_x + 1
            if som_x == som_dimension:
                som_x = 0
                som_y = som_y +1            


    except IOError:
        sys.exit(''.join(('Error: cannot read input csv file: ', input_file)))

def fill_plot_queue_html(queues, input_file, plate_directory, icon_size):
    with open(input_file, 'r') as f:
        plain_html = f.read()
    html_content = BeautifulSoup(plain_html)
    table = html_content.find_all('table')
    tr = table[0].find_all('tr') #change this to [0] to parse first table

    som_y = 0
    for row in tr:
        som_x = 0
        for cell in row.find_all('td'):
            link=""
            src=""
            image_file=""
            img = cell.find_all('img', src=True)
            for src in img:
                image_file_path = src['src']
            a = cell.find_all('a', href=True)
            for links in a:
                link = links['href']
            #~ print link
            if image_file_path == "empty.png":
                mjd = -1
                plateid = -1
                fiberid = -1
            else:
                #extract mjd,plateid,fiberid from fits.png-Filename
                fits_filename = os.path.basename(image_file_path)
                fits_filename = str.replace(fits_filename, '.', '-')
                sdss_ids = fits_filename.split('-')
                if sdss_ids[0] == 'spec':
                    #sdss dr12 (and others?)
                    plateid = int(sdss_ids[1])
                    mjd = int(sdss_ids[2])
                    fiberid = int(sdss_ids[3])
                    padded_plateid = ''.join(('0000', str(plateid)))
                    padded_plateid = padded_plateid[-4:]
                    padded_fiberid = ''.join(('0000', str(fiberid)))
                    padded_fiberid = padded_fiberid[-4:]
                    fits_file_path=''.join((str(padded_plateid), '/spec-', padded_plateid, '-', str(mjd), '-',padded_fiberid, '.fits'))
                elif sdss_ids[0] == 'spSpec':
                    #sdss dr7 and before
                    plateid = int(sdss_ids[2])
                    mjd = int(sdss_ids[1])
                    fiberid = int(sdss_ids[3])
                    padded_plateid = ''.join(('0000', str(plateid)))
                    padded_plateid = padded_plateid[-4:]
                    padded_fiberid = ''.join(('000', str(fiberid)))
                    padded_fiberid = padded_fiberid[-3:]
                    fits_file_path=''.join((plate_directory, '/', str(plateid), '/spSpec-', str(mjd), '-', padded_plateid,'-',padded_fiberid, '.fit'))
                else:
                    print "Don't know how to scrape ids from fits.png filename. Using empty values..."
                    mjd = -1
                    plateid = -1
                    fiberid = -1
                
                if mjd == -1:
                    spectrum = numpy.array([])
                else:
                    try:
                        fits_file = pyfits.open(fits_file_path)
                        ##data from the first HDU
                        #~ data_fields = ['tai', 'ra', 'dec', 'equinox', 'az', 'alt', 'mjd', 'quality', 'radeg', 'decdeg', 'plateid', 'tileid', 'cartid', 'mapid', 'name', 'objid', 'objtype', 'raobj', 'decobj', 'fiberid', 'z', 'z_err', 'z_conf', 'z_status', 'z_warnin', 'spec_cln']
                        #~ data = dict()
                        #~ value_string = ""
                        #~ for data_field in data_fields:
                            #~ data[data_field] = fits_file[0].header[data_field]
                        spectrum=average_over_spectrum(fits_file[0].data[0].tolist(), icon_size)
                        #spectrum=average_over_spectrum(spectrum.tolist(), icon_size)
                        fits_file.close()
                    except:
                        spectrum = numpy.array([])
            for queue in queues:
                queue.put((spectrum, (som_x, som_y)))

            som_x = som_x +1
        som_y = som_y + 1
                    



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
        sys.stderr.write("Something went wrong with one of the processes.\n")
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
                plt.ioff()
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
    parser.add_argument("-i", "--inputdir", type=str, required=True, help="Directory containing directories named after plates, containing fit(s) files.")
    parser.add_argument("-I", "--inputfile", type=str, required=True, help="input file like full0_0.html generated by ASPECT")
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
            #~ if args.uglyicons:
                #~ icon_style='ugly'
            if args.niceicons:
                icon_style='nice'

            if args.nomultiprocessing:
                #~ os.path.walk( args.inputdir, processDirectory, {"icon_size": args.iconsize, "icon_style": icon_style, "output_dir": args.outputdir, "multiprocessing": False})                
                sys.exit('single processing not implementet')
            else:
                if os.path.exists(args.inputfile):
                    som_dimension = get_som_dimension_from_csv(args.inputfile, ';')
                    #get_som_dimension_from_html(args.inputfile)
                    max_zoom = get_max_zoom(som_dimension)
                    workers = max_zoom + 1
                    plot_queues = []
                    processes = []
                    for worker in range(workers):
                        plot_queues.append(mp.Queue())
                        p = mp.Process(target=spec_worker, args=(plot_queues[worker], max_zoom, worker, args.iconsize, args.outputdir))
                        p.start()
                        processes.append(p)
                    
                    #fill_plot_queue_html(plot_queues, args.inputfile, args.inputdir, args.iconsize)
                    fill_plot_queue_csv(plot_queues, args.inputfile, args.inputdir, args.iconsize, som_dimension)
                    
                    for worker in range(workers):
                        plot_queues[worker].put('STOP')
                    for process in processes:
                        process.join()
                        
                else:
                    sys.exit(''.join(('Error: Input file does not exist:', inputfile)))
                
                #~ workers = args.numberofprocesses
                #~ work_queue = mp.Queue()
                #~ processes = []
                
                #~ for worker in range(workers):
                    #~ p = mp.Process(target=smp_fits_to_files, args=(work_queue,))
                    #~ p.start()
                    #~ processes.append(p)

                #~ os.path.walk( args.inputdir, processDirectory, {"icon_size": args.iconsize, "icon_style": icon_style, "output_dir": args.outputdir, "multiprocessing": True})

                #~ for worker in range(workers):
                    #~ work_queue.put('STOP')
                    
                #~ for process in processes:
                    #~ process.join()
               
        else:
            sys.exit(''.join(("Output Directory does not exist. Please create: ", args.outputdir)))
    else:
        sys.exit(''.join(("Input directory does not exist: ", args.inputdir, " Please check!")))

    
    
