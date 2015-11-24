# -*- coding: utf-8 -*-
import pyfits
import string
import os
import re
import json
from PIL import Image
from PIL import ImageDraw



##Configuration


#SOM
#SOM_dimension is the edge length of the map. It is one terminated.
som_dimension = 1104
max_zoom = 12

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
    ewcount=0
    for ew in fits_file[2].data['ew']:
        restWave=str(fits_file[2].data['restWave'][ewcount]).replace(".","_")
        #print('ew_',restWave, ': ', ew)
        ewcount = ewcount+1

    #Das Spektrum
    spectrum=fits_file[0].data[0]
    output_path = ''.join(['./outputspecs/', str(data['plateid'])])
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_filename = ''.join([output_path, '/', str(data['mjd']), '-', str(data['plateid']), '-', str(data['fiberid']),'.png'])
    png_spec_file = open(output_filename, 'w')
    temp_icon_size = (256, 256)
    temp_icon = Image.new('RGBA', temp_icon_size, None)            
    draw = ImageDraw.Draw(temp_icon)
    draw.line(zip(range(256), normalize_spectrum(average_over_spectrum(spectrum.tolist(), 256), 256)), fill = 'black', width = 2)
    del draw
    temp_icon.save(output_filename, "PNG")

def processDirectory (args, dirname, filenames ):
    #print dirname
    for filename in filenames:
        if re.match('.*\.fit$', filename):
            fits_to_files(dirname + "/" + filename)




if __name__ == '__main__':

    base_dir = "./spectra/sub/spectra.txt"
    os.path.walk( base_dir, processDirectory, None )


    
    
