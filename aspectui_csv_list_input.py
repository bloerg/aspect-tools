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

##Globals
input_file = './zuordnung.csv'
som_dimension = 0



##directory initialisation
##everything will be saved somewhere below the output directory
output_directory = './web'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
output_directory = './web/som'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
##original_som_directory will contain the unzoomed mapped (mjd, plateid, fiberid to som_x, som_y) spectra icons
##will be renamed to the largest zoom level in the process of computation of the lower zoom level spec icons
original_som_directory = '/'.join((output_directory, "originalsomdirectory"))
if not os.path.exists(original_som_directory):
    os.makedirs(original_som_directory)
##zoomed_som_directory will contain the the combinations of spectra icons for lower zoom levels
zoomed_som_directory = '/'.join((output_directory, "icons"))
if not os.path.exists(zoomed_som_directory):
    os.makedirs(zoomed_som_directory)

#mapping from som_x, som_y to mjd, plateid, fiberid 
idmapping_directory = '/'.join((output_directory, "idmapping"))
if not os.path.exists(idmapping_directory):
    os.makedirs(idmapping_directory)

#spectra meta data files
spec_meta_data_directory = '/'.join((output_directory, "specmetadata"))
if not os.path.exists(spec_meta_data_directory):
    os.makedirs(spec_meta_data_directory)

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
        image_file_path = "empty.png"
        link = ""
    else:
        padded_plateid = ''.join(('0000', str(plateid)))
        padded_plateid = padded_plateid[-4:]
        padded_fiberid = ''.join(('000', str(fiberid)))
        padded_fiberid = padded_fiberid[-3:]
        image_file_path=''.join((str(padded_plateid), '/spSpec-', str(mjd), '-', padded_plateid,'-',padded_fiberid, '.fit.png'))
        link = ''.join(('http://cas.sdss.org/dr7/en/tools/explore/obj.asp?plate=', str(plateid), '&mjd=', str(mjd), '&fiber=', str(fiberid)))
        
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
        
        
        #spectra meta data
        spec_meta_data_file_path = ''.join((spec_meta_data_directory, '/', str(som_x), '-', str(som_y), '.json'))
        if not os.path.exists(spec_meta_data_file_path):
            with open(spec_meta_data_file_path, 'w') as spec_meta_data_file:
                json.dump({"mjd": int(mjd), "plateid":int(plateid), "fiberid": int(fiberid), "sdsslink": link, "som_x": int(som_x), "som_y": int(som_y)}, spec_meta_data_file)
        
        #write idmapping som_x, som_y -> mjd, plateid, fiberid and vice versa
        idmapping_file_path = ''.join((idmapping_directory, '/', str(som_x), '-', str(som_y), '.json'))
        if not os.path.exists(idmapping_file_path):
            with open(idmapping_file_path, 'w') as idmapping_file:
                json.dump({"mjd": int(mjd), "plateid":int(plateid), "fiberid": int(fiberid) }, idmapping_file)
        idmapping_file_path = ''.join((idmapping_directory, '/', str(mjd), '-', str(plateid), '-', str(fiberid), '.json'))
        if not os.path.exists(idmapping_file_path):
            with open(idmapping_file_path, 'w') as idmapping_file:
                json.dump({"som_x": int(som_x), "som_y":int(som_y)}, idmapping_file)            
        
        
        #make empty.png in highest zoom level if it not exists
        if not os.path.exists('/'.join((original_som_directory, "empty.png"))):
            example_icon=Image.open(image_file_path)
            #icon size such, that 2 pixel transparent frame around icon
            icon_size = (example_icon.size[0] + 4, example_icon.size[1] + 4)
            empty_icon = Image.new('RGBA', icon_size, None)
            #transparent_area = (0,0,icon_size[0], icon_size[1])

            #mask=Image.new('L', empty_icon.size, color=255)
            #draw=ImageDraw.Draw(mask) 
            #draw.rectangle(transparent_area, fill=0)
            #empty_icon.putalpha(mask)
            empty_icon.save('/'.join((original_som_directory, "empty.png")), "PNG")
    
    #FIXME: print to file given by script parameter
    print(';'.join((str(som_x), str(som_y), str(mjd), str(plateid), str(fiberid))))
    

    
    #make icon of highest zoom level with transparent 2 pixel margin
    if os.path.exists(image_file_path):
        spectrum_output_path = ''.join((original_som_directory, '/', str(som_x), '-', str(som_y), '.png'))
        if not os.path.exists(spectrum_output_path):
            #copyfile(image_file_path, spectrum_output_path)
            temp_icon_size = (icon_size[0], icon_size[1])
            temp_icon = Image.new('RGBA', temp_icon_size, None)            
            source_icon = Image.open(image_file_path)
            temp_icon.paste(source_icon, (2, 2))
            temp_icon.save(spectrum_output_path, "PNG")
            




##computation of lower zoom level icons

som_dimension = max([som_x, som_y]) ## not +1 because som_x, som_y increased after the last step of the previous loop
#print som_dimension

max_zoom=0
while 2**max_zoom <= som_dimension:
    max_zoom = max_zoom + 1 



if os.path.exists(original_som_directory):
    
    max_zoom_directory = '/'.join((zoomed_som_directory, str(max_zoom)))
    if not os.path.exists(max_zoom_directory):
        os.rename(original_som_directory, max_zoom_directory)
        
    for zoom in list(reversed(range(max_zoom))):
        zoom_directory = '/'.join((zoomed_som_directory, str(zoom)))
        if not os.path.exists(zoom_directory):
            os.makedirs(zoom_directory)
        
        ##Create icon combined of four icons of the next larger zoom level, i. e. four icons of zoom 12 -> 1 resized icon of zoom 11
        for som_x in range(2**zoom):
            for som_y in range(2**zoom):
                temp_icon_size = (icon_size[0] * 2, icon_size[1] * 2)
                temp_icon = Image.new('RGBA', temp_icon_size, None)
                for x_offset in range(2):
                    for y_offset in range(2):
                        source_icon_path = ''.join((zoomed_som_directory, '/', str(zoom + 1), '/', str(som_x * 2 + x_offset), '-', str(som_y * 2 + y_offset), '.png'))
                        #print(source_icon_path)
                        if os.path.exists(source_icon_path):
                            source_icon = Image.open(source_icon_path)
                            #print(str(x_offset * icon_size[0]), str(y_offset * icon_size[1]))
                            temp_icon.paste(source_icon, (x_offset * icon_size[0], y_offset * icon_size[1]))
                        else:
                            #print (source_icon_path, "does not exist")
                            source_icon_path = ''.join((zoomed_som_directory, '/', str(max_zoom), '/empty.png'))
                            source_icon = Image.open(source_icon_path)
                            temp_icon.paste(source_icon, (x_offset * icon_size[0], y_offset * icon_size[1]))

                temp_icon = temp_icon.resize((icon_size[0], icon_size[1]))
                temp_icon.save(''.join((zoom_directory, '/', str(som_x), '-', str(som_y), '.png')), "PNG")
    
    ##Config file for the Webpage
    config = {}
    config['max_zoom'] = max_zoom
    config['tile_size'] = max(icon_size)
    config['min_x'] = 0
    config['max_x'] = som_dimension
    config['min_y'] = 0
    config['max_y'] = som_dimension
    config['base_directory'] = "./som"
    #config['page_title'] = ''
    config_file_path = '/'.join((output_directory, "../config.json"))
    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file)
    
else:
    #FIXME: better debug messages
    print(''.join(("There are no spectra in ", original_som_directory,". That is a bad thing and means that something went wrong before.")))

