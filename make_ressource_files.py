# -*- coding: utf-8 -*-
import pyfits
import string
import os
import re
import json



##Configuration


#SOM
#SOM_dimension is the edge length of the map. It is one terminated.
som_dimension = 1104
max_zoom = 12

def average_over_spectrum (spectrum, new_spec_width):
    bin_width = len(spectrum) / new_spec_width
    bin_width_modulus = len(spectrum) % new_spec_width
    bin_average = 0
    bin_element_count = 0
    output_spectrum = []
    
    #~ while spec_index < spec_length:
        
        #~ if spec_index + bin_width > spec_length - 1:
            #~ bin_width = spec_length - spec_index -1
        #~ for i in range(binwidth - 1):
            #~ bin_average = bin_average + spectrum[spec_index + i]
        #~ bin_average = bin_average / bin_width
        #~ spec_index = spec_index + bin_width
    for element in spectrum:
        bin_average = bin_average + element
        bin_element_count = bin_element_count + 1
        if bin_element_count == bin_width:
            bin_average = bin_average / bin_width
            output_spectrum.append(bin_average)
            bin_element_count = 0
            bin_average = 0
            #Falls beim letzten Bin noch Werte übrig bleiben würden
            if len(output_spectrum) == new_spec_width - 1:
                bin_width = bin_width + bin_width_modulus
            
    return output_spectrum


def fits_to_files ( filename ):
    fits_file_name = filename
    fits_file = pyfits.open(fits_file_name)
    
#    print fits_file_name
    
    ##Die Daten aus dem ersten HDU
    data_fields = ['tai', 'ra', 'dec', 'equinox', 'az', 'alt', 'mjd', 'quality', 'radeg', 'decdeg', 'plateid', 'tileid', 'cartid', 'mapid', 'name', 'objid', 'objtype', 'raobj', 'decobj', 'fiberid', 'z', 'z_err', 'z_conf', 'z_status', 'z_warnin', 'spec_cln']
    data = dict()
    value_string = ""
    for data_field in data_fields:
        data[data_field] = fits_file[0].header[data_field]
        #print(data_field, ': ' , data[data_field])

    #Die Equivalentbreiten
    #siehe hdu3 für Zuordnung
    #Aus irgendeinem Grund ist hier die Zuordnung von Typen nicht richtig, deswegen +0
#    data['ewhalpha'] = fits_file[2].data['ew'][39] + 0
#    data['ewhdelta'] = fits_file[2].data['ew'][27] + 0
    ewcount=0
    #equivalent_width_data = dict()
    #equivalent_width_data_fields = [
    #equivalent_width_value_string = ""
    for ew in fits_file[2].data['ew']:
        restWave=str(fits_file[2].data['restWave'][ewcount]).replace(".","_")
        #print('ew_',restWave, ': ', ew)
        ewcount = ewcount+1

    #Das Spektrum
    spectrum=fits_file[0].data[0]
    #print(len(spectrum.tolist()))
    #print("averaged spectrum")
    output_path = ''.join(['./outputspecs/', str(data['plateid'])])
    print(output_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_filename = ''.join([output_path, '/', str(data['mjd']), '-', str(data['plateid']), '-', str(data['fiberid']),'.json'])
    json_spec_file = open(output_filename, 'w')
    json.dump({"spectrum": average_over_spectrum(spectrum.tolist(), 256)}, json_spec_file)
    json_spec_file.close()

def processDirectory (args, dirname, filenames ):
    #print dirname
    for filename in filenames:
        if re.match('.*\.fit$', filename):
            fits_to_files(dirname + "/" + filename)
            

def combine_and_resize_spectra():
    output_directory = ('./som')
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    for zoom in list(reversed(range(max_zoom))):
        zoom_subdir = '/'.join([output_directory, str(zoom)])
        if not os.path.exists(zoom_subdir):
            os.makedirs(zoom_subdir)
        number_of_tiles = 2 ** (max_zoom - zoom)
        x_range = range(number_of_tiles - 1, som_dimension - 1, number_of_tiles)
        if x_range[-1] < som_dimension - 1:
            x_range.append(som_dimension)
        y_range = range(number_of_tiles - 1, som_dimension - 1, number_of_tiles)            
        if y_range[-1] < som_dimension - 1:
            y_range.append(som_dimension)


        for x in x_range:
            zoomed_x = (x + 1) / number_of_tiles - 1
            for y in y_range:
                zoomed_y = (y + 1) / number_of_tiles - 1
                
                output_tile = []
                

                output_path = '/'.join(['./som', str(zoom)])
                if not os.path.exists(output_path):
                    os.makedirs(output_path)
                if not os.path.exists('/'.join([output_path, str(zoomed_x)])):
                    os.makedirs('/'.join([output_path, str(zoomed_x)]))    
                output_filename = ''.join([output_path, '/',str(zoomed_x), '/', str(zoomed_x), '-',str(zoomed_y),'.json'])
                if not os.path.exists(output_filename):
                
                    for sub_x in range(x - number_of_tiles, x):
                        for sub_y in range(y - number_of_tiles, y):
                            som_spec_path = '/'.join(['./som', str(max_zoom), str(sub_x)])
                            input_spectrum_filename = ''.join([som_spec_path, '/', str(sub_x), '-', str(sub_y),'.json'])
                            if os.path.exists(input_spectrum_filename):
                                with open(input_spectrum_filename, 'r') as json_input_spec_file:
                                    input_spectrum = json.load(json_input_spec_file)
                                    #~ if zoomed_x > 383 & zoomed_y > 328:
                                        #~ print input_spectrum
                                        #~ print "\n"
                                        #~ print input_spectrum[0]
                                        #~ print "\n"
                                        #~ print input_spectrum[0]['spectrum']
                                    input_spectrum = input_spectrum[0]
                                    original_spec_length = len(input_spectrum['spectrum'])
                                    output_tile.append({"som_x": sub_x, "som_y": sub_y, "spectrum": average_over_spectrum(input_spectrum['spectrum'], original_spec_length / (2 ** (max_zoom - zoom)))})

                    ##output downsized spectra
                        with open(output_filename, 'w') as json_output_spec_file:
                            json.dump(output_tile, json_output_spec_file)


def Kohonen_Fits_Mapping(filename):
    mapping_data_file = csv.DictReader(open(filename, "rb"), delimiter=";")
    for row in mapping_data_file:
        print row
        data = dict()
        data = row
        som_x = str(data['x'])
        som_y = str(data['y'])
        mjd = str(data['MJD'])
        plateid = str(data['plateID'])
        fiberid = str(data['fibID'])
        
        #Hier liegen die Spektren im Json-Format, erstellt von fits_to_files(...)
        input_path = ''.join(['./outputspecs/', plateid])
        input_filename = ''.join([input_path, '/', mjd, '-', plateid, '-', fiberid,'.json'])
        if os.path.exists(input_filename):
            with open(input_filename, 'r') as json_input_spec_file:
                spectrum = json.load(json_input_spec_file)
        
        #Ein Spektrum pro Datei für das höchste Zoomlevel nach ./som/$ZOOMLEVEL/$SOM_X/$SOM_X-$SOM_Y.json schreiben
        
        output_path = '/'.join(['./som', str(max_zoom)])
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        if not os.path.exists('/'.join([output_path, som_x])):
            os.makedirs('/'.join([output_path, som_x]))    
        output_filename = ''.join([output_path, '/',som_x, '/', som_x, '-',som_y,'.json'])
        if not os.path.exists(output_filename):
            with open(output_filename, 'w') as json_output_spec_file:
                json.dump([{"som_x": som_x, "som_y": som_y, "spectrum": spectrum['spectrum']}], json_output_spec_file)



if __name__ == '__main__':

    base_dir = "./spectra/sub/spectra.txt"
    os.path.walk( base_dir, processDirectory, None )

    #insert the Tablef or the SOM - Spectra - Mapping
    Kohonen_Fits_Mapping('./zuordnung.dat')
    combine_and_resize_spectra()

    
    
