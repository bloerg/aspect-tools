#!/usr/bin/python
# -*- coding: utf-8 -*-
#from lxml import etree

#script that uses the full0_0.html file of an ASPECT run to make a mapping file from mjd-plateid-fiber-id to som_x,som_y
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

##Globals
input_file = './full0_0.html'



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

##first try to read full0_0.html
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
            elif sdss_ids[0] == 'spSpec':
                #sdss dr7 and before
                plateid = int(sdss_ids[2])
                mjd = int(sdss_ids[1])
                fiberid = int(sdss_ids[3])
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
            #copyfile(image_file_path, spectrum_output_path)
            temp_icon_size = (icon_size[0], icon_size[1])
            temp_icon = Image.new('RGBA', temp_icon_size, None)            
            source_icon = Image.open(image_file_path)
            temp_icon.paste(source_icon, (2, 2))
            temp_icon.save(spectrum_output_path, "PNG")
            
        
        som_x = som_x +1
    som_y = som_y + 1



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
    config['has_no_background'] = True
    config_file_path = '/'.join((output_directory, "../config.json"))
    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file)
    
else:
    #FIXME: better debug messages
    print(''.join(("There are no spectra in ", original_som_directory,". That is a bad thing and means that something went wrong before.")))

