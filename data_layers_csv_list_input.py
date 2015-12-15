#!/usr/bin/python
# -*- coding: utf-8 -*-

#script that uses a csv file with x,y,mjd,plateid,fiber header of an ASPECT run to make a mapping file from mjd-plateid-fiber-id to som_x,som_y
#please install python-beautifulsoup4, python-lxml, python-imaging (PIL)

#in ubuntu do: sudo aptitude install python-bs4 python-lxml python-imaging
#in fedora do: dnf install python-beautifulsoup4 python-pillow python-lxml
#in suse linux: do FIXME


from bs4 import BeautifulSoup
from urlparse import urlparse
import json
import os
from shutil import copyfile
from PIL import Image
from PIL import ImageDraw
from math import sqrt
import csv
import shutil

##Globals
input_file = '/var/tmp/zuordnung.csv'
som_dimension = 0
data_layer = 'z'


##directory initialisation
##everything will be saved somewhere below the output directory
output_directory = './web'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
output_directory = './web/som'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

##zoomed_som_directory will contain the the combinations of spectra icons for lower zoom levels
zoomed_som_directory = '/'.join((output_directory, "datalayers"))
if not os.path.exists(zoomed_som_directory):
    os.makedirs(zoomed_som_directory)
zoomed_som_directory = '/'.join((zoomed_som_directory, data_layer))
if not os.path.exists(zoomed_som_directory):
    os.makedirs(zoomed_som_directory)
    
##original_som_directory will contain the unzoomed mapped (mjd, plateid, fiberid to som_x, som_y) spectra icons
##will be renamed to the largest zoom level in the process of computation of the lower zoom level spec icons
original_som_directory = '/'.join((output_directory, "datalayers", data_layer, "originalsomdirectory"))
if not os.path.exists(original_som_directory):
    os.makedirs(original_som_directory)
    
mapping_data_file = csv.DictReader(open(input_file, "rb"), delimiter=";")
for row in mapping_data_file:
    data = dict()
    data = row
    som_x = int(data['x'])
    som_y = int(data['y'])
    mjd = data['MJD']
    plateid = data['plateID']
    fiberid = data['fibID']
    som_dimension = max([som_x, som_y, som_dimension])
    if plateid == -1:
        data_file_path = ""
    else:
        padded_plateid = ''.join(('0000', str(plateid)))
        padded_plateid = padded_plateid[-4:]
        padded_fiberid = ''.join(('000', str(fiberid)))
        padded_fiberid = padded_fiberid[-3:]
        data_file_path=''.join((data_layer, '/', str(padded_plateid), '/spSpec-', str(mjd), '-', padded_plateid,'-',padded_fiberid, '.fit.json'))
       
    if data_file_path == "":
        mjd = -1
        plateid = -1
        fiberid = -1
    else:
        #extract mjd,plateid,fiberid from fits.json-Filename
        fits_filename = os.path.basename(data_file_path)
        fits_filename = str.replace(fits_filename, '.', '-')
        sdss_ids = fits_filename.split('-')
        if sdss_ids[0] == 'spec':
            #sdss dr12 (and others?)
            plateid = sdss_ids[1]
            mjd = sdss_ids[2]
            fiberid = sdss_ids[3]
        elif sdss_ids[0] == 'spSpec':
            #sdss dr7 and before
            plateid = sdss_ids[2]
            mjd = sdss_ids[1]
            fiberid = sdss_ids[3]
        else:
            print "Don't know how to scrape ids from fits.png filename. Using empty values..."
            mjd = -1
            plateid = -1
            fiberid = -1                
    
   
    if os.path.exists(data_file_path):
        data_output_path = ''.join((original_som_directory, '/', str(som_x), '-', str(som_y), '.json'))
        if not os.path.exists(data_output_path):
            #copyfile(image_file_path, spectrum_output_path)
            #shutil.move(dat_file_path, data_output_path)
            with open(data_file_path, 'r') as json_input_file:
                with open(data_output_path, 'w') as json_output_file:
                    json_data = json.load(json_input_file)
                    json.dump({"data": [{"x":som_x,"y":som_y,"val":json_data[0]}]}, json_output_file)
                    try:
                        data_min = min(data_min, json_data[0])
                    except:
                        data_min = json_data[0]

                    try:
                        data_max = max(data_max, json_data[0])
                    except:
                        data_max = json_data[0]


##computation of lower zoom level data

som_dimension = max([som_x+1, som_y+1]) ## not +1 because som_x, som_y increased after the last step of the previous loop
#print som_dimension

max_zoom=0
while 2**max_zoom <= som_dimension:
    max_zoom = max_zoom + 1 



if os.path.exists(original_som_directory):
    
    max_zoom_directory = '/'.join((zoomed_som_directory, str(max_zoom)))
    if not os.path.exists(max_zoom_directory):
        shutil.move(original_som_directory, max_zoom_directory)
        #os.rename(original_som_directory, max_zoom_directory)
        
    for zoom in list(reversed(range(max_zoom))):
        number_of_tiles = 2 ** (max_zoom - zoom)
        zoom_directory = '/'.join((zoomed_som_directory, str(zoom)))
        if not os.path.exists(zoom_directory):
            os.makedirs(zoom_directory)
        
        ##Create icon combined of four icons of the next larger zoom level, i. e. four icons of zoom 12 -> 1 resized icon of zoom 11
        for som_y in range(2**zoom):
            for som_x in range(2**zoom):
                lower_zoom_data = []
                output_json_path = ''.join((zoom_directory, '/', str(som_x), '-', str(som_y), '.json'))
                if not os.path.exists(output_json_path):
                    for y_offset in range(2):
                        for x_offset in range(2):
                            source_data_path = ''.join((zoomed_som_directory, '/', str(zoom + 1), '/', str(som_x * 2 + x_offset), '-', str(som_y * 2 + y_offset), '.json'))
                            #print(source_icon_path)
                            if os.path.exists(source_data_path):
                                with open(source_data_path) as higher_zoom_json:
                                    lower_zoom_data = lower_zoom_data + json.load(higher_zoom_json)['data']
                    
                    with open(output_json_path, 'w') as output_json_file:
                        json.dump({"data":lower_zoom_data}, output_json_file)
    
    ##Config file for the data layer
    config = {}
    config['data_max'] = data_max
    config['data_min'] = data_min
    config['layer_name'] = data_layer
    config['directory'] = '/'.join(("./som", data_layer))
    #config['page_title'] = ''
    config_file_path = '/'.join((output_directory, 'datalayers', data_layer, "config.json"))
    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file)
    
else:
    #FIXME: better debug messages
    print(''.join(("There are no spectra in ", original_som_directory,". That is a bad thing and means that something went wrong before.")))

