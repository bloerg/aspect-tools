#!/usr/bin/python
# -*- coding: utf-8 -*-
import math
import json
import argparse
import os

class SOM:
    'Class of a two-dimensional SOM'

    # __som contains the x,y,data_id array
    __som=dict()
    
    # __som_max_zoom is set after data has been added to __som
    __som_max_zoom = 0
    
    # __som_dimension has the value of the largest x or y index of __som + 1 (i. e. the edge length of the som)
    __som_dimension = 0
    
    # type_of_data can be json, image, ...
    # transformation function is a callback function accepting max_zoom, at_zoom, x_at_zoom, y_at_zoom and the __som and returns a representation of the __som at the given zoom level
    # som_properties is a dict of properties (base_directory of images for instance)
    # som_properties should have at least the keys: dest_dir
    def __init__(self, name, type_of_data, transformation_function, som_properties):
        self.name = name
        self.type_of_data = type_of_data
        self.transformation_function = transformation_function
        self.som_properties = som_properties
        self.som_properties['name'] = name
    
    # returns the lower and upper limit of x and y - ranges of tiles in the highest zoom level which are contained in a tile of a given zoom level
    def __get_x_y_range_at_zoom(self, tile_x, tile_y, at_zoom, max_zoom):
        number_of_subtiles = 2**(max_zoom - at_zoom)
        result=dict()
        result['x_low'] = tile_x * number_of_subtiles
        result['x_high'] = result['x_low'] + number_of_subtiles - 1
        result['y_low'] = tile_y * number_of_subtiles
        result['y_high'] = result['y_low'] + number_of_subtiles - 1

        return result
    def get_x_y_range_at_zoom(self, tile_x, tile_y, at_zoom, max_zoom):
        return self.__get_x_y_range_at_zoom(tile_x, tile_y, at_zoom, max_zoom)
        
    
    # set_som_element is a function to be called with coordinates and some data (real data, reference id to file, ...) describing the point in the som
    # x and y are integers, the type of data depends on the data
    def set_som_element(self, x, y, data):
        self.__som[(x,y)] = data
        new_som_dimension = max(x+1, y+1)
        if (new_som_dimension > self.__som_dimension):
            self.__som_dimension = new_som_dimension
            self.__som_max_zoom = int(math.ceil(math.log(self.__som_dimension, 2)))
            self.som_properties['max_zoom'] = self.__som_max_zoom
            self.som_properties['som_dimension'] = self.__som_dimension



    def get_som_at_zoom(self, at_zoom):
        self.transformation_function(self.__som, at_zoom)
    
    # returns a dict containing the subtiles' data at highest zoom level of a tile at a given zoom level
    # also, the returned dict contains the x,y boundaries at highest zoom level of the given tile
    def get_tile_data_at_zoom(self, at_zoom, tile_x, tile_y):
        result = dict()
        tile_boundaries = self.__get_x_y_range_at_zoom(tile_x, tile_y, at_zoom, self.__som_max_zoom)
        result['boundaries'] = tile_boundaries
        result['tile_x'] = tile_x
        result['tile_y'] = tile_y
        for x in xrange(tile_boundaries['x_low'], tile_boundaries['x_high'] + 1):
            for y in xrange(tile_boundaries['y_low'], tile_boundaries['y_high'] + 1):
                if ( (x,y) in self.__som):
                    result[(x,y)] = self.__som[(x,y)]
        return (result)
   
    def get_som_at_max_zoom(self):
        return self.__som

    def get_som_dimension(self):
        return self.__som_dimension
    
    def get_som_dimension_at_zoom(self, at_zoom):
        return 2**at_zoom
    
    def get_som_max_zoom(self):
        return self.__som_max_zoom

    # trigger the aggregation and dump of a tile at a certain zoom level
    # to this end use the transformation function given at the initialisation of the som
    def transform_tile(self, at_zoom, x, y):
        self.transformation_function(self.get_tile_data_at_zoom(at_zoom, x,y), self.som_properties, at_zoom)

    
    # print a csv list of x,y coordinates and the value of each existing (x,y) key in the som
    def to_csv(self):
        print 'x,y,'+self.name
        for item in self.__som.iteritems():
            (som_x, som_y), value = item
            print str(som_x) + ',' + str(som_y) + ',' + str(value)

    # export the config file in json format for aspect-ui
    def write_aspect_ui_config_to_disk(self):
        print("Writing config file for aspect-ui\n")
        config = {}
        config['max_zoom'] = self.get_som_max_zoom()
        config['min_zoom'] = self.som_properties['min_zoom']
        if ('icon_size' in self.som_properties):
            config['tile_size'] = self.som_properties['icon_size']
        config['min_x'] = 0
        config['max_x'] = self.get_som_dimension()
        config['min_y'] = 0
        config['max_y'] = self.get_som_dimension()
        config['base_directory'] = "./som"
        #config['page_title'] = ''
        config['has_no_background'] = True  #means that there is no information regarding redshift and such, which could be used for background coloring
        config_file_path = '/'.join((self.som_properties['dest_dir'], "../config.json"))
        with open(config_file_path, 'w') as config_file:
            json.dump(config, config_file)

########################################################################
## INPUT FILTERS

# IMAGE FILE PATHS FROM CSV IMPORT
# takes input file with three columns: data, x, y
# expects space as delimiter
def image_links_to_som_from_csv(csv_input_file, som):
    import os
    import csv
    with open(csv_input_file, 'rb') as f:
        csv_content = csv.reader(f, delimiter=' ')
    for row in csv_content:
        if ('x' in row and 'y' in row and 'data' in row):
            som.set_som_element(int(x),int(y),str(data))


# IMAGE FILE PATHS FROM HTML IMPORT
# takes input file like full0_0.html and fills a given som object with image file paths
def image_links_to_som_from_html(html_input_file, som):
    from bs4 import BeautifulSoup
    from urlparse import urlparse
    import os
    with open(html_input_file, 'r') as f:
        plain_html = f.read()
    html_content = BeautifulSoup(plain_html, "lxml")
    table = html_content.find_all('table')
    tr = table[0].find_all('tr') #change [0] to parse another table
    som_y = 0
    for row in tr:
        som_x = 0
        for cell in row.find_all('td'):
            image_file=""
            img = cell.find_all('img', src=True)
            for src in img:
                image_file_path = src['src']
            som.set_som_element(som_x, som_y, image_file_path)
            som_x = som_x +1
        som_y = som_y + 1


# IMAGE FILE PATHS FROM ASPECT DUMPFILE
# takes input file ASPECT reverse dump output, i. e. sofmnet.bin -> allSpectra.txt
def image_links_to_som_from_dumpfile(dump_input_file, som):
    import os
    import math
    with open(dump_input_file, 'r') as f:
        row_count = 0
        for row in f:
            row_count+=1
        edge_length = math.sqrt(row_count)
        if ( int(edge_length) != edge_length ):
            sys.stderr.write('Error: Number of lines in dumpfile is not equal to the square of an integer. This means that there are not enough or too many lines in the dumpfile to generate a square map of spectra icons.')
        else:
            edge_length = int(edge_length)
            som_x = 0
            som_y = 0
            f.seek(0)
            for row in f:
                image_filename_string = row
                image_filename_string = str.replace(image_filename_string, '.', '-')
                sdss_ids = image_filename_string.split('-')
                if sdss_ids[0] == 'spec':
                    #sdss dr10 and later
                    plateid = int(sdss_ids[1])
                    mjd = int(sdss_ids[2])
                    fiberid = int(sdss_ids[3])
                elif sdss_ids[0] == 'spSpec':
                    #sdss dr9 and before
                    plateid = int(sdss_ids[2])
                    mjd = int(sdss_ids[1])
                    fiberid = int(sdss_ids[3])
                else:
                    mjd = -1
                    plateid = -1
                    fiberid = -1
                image_file_path = str(plateid) + '/' + '-'.join( sdss_ids[0:4] ) + '.fits.png'
                som.set_som_element(som_x, som_y, image_file_path)
                ## increase som coordinate counts
                som_x+=1
                if (som_x == edge_length):
                    som_x = 0
                    som_y+=1
                

# MJD,PLATEID,FIBERID FROM HTML IMPORT
# takes input file like full0_0.html and fills a given som object with mjd,fiberid,plateid
def mjd_plate_fiberid_to_som_from_html(html_input_file, som):
    from bs4 import BeautifulSoup
    from urlparse import urlparse
    import os
    with open(html_input_file, 'r') as f:
        plain_html = f.read()
    html_content = BeautifulSoup(plain_html, "lxml")
    table = html_content.find_all('table')
    tr = table[0].find_all('tr') #change [0] to parse another table
    som_y = 0
    for row in tr:
        som_x = 0
        for cell in row.find_all('td'):
            image_file=""
            img = cell.find_all('img', src=True)
            for src in img:
                image_file_path = src['src']
            a = cell.find_all('a', href=True)
            for links in a:
                link = links['href']
            #extract mjd,plateid,fiberid from fits.png-Filename
            image_filename = os.path.basename(image_file_path)
            image_filename = str.replace(image_filename, '.', '-')
            sdss_ids = image_filename.split('-')
            if sdss_ids[0] == 'spec':
                #sdss dr10 and later
                plateid = int(sdss_ids[1])
                mjd = int(sdss_ids[2])
                fiberid = int(sdss_ids[3])
            elif sdss_ids[0] == 'spSpec':
                #sdss dr9 and before
                plateid = int(sdss_ids[2])
                mjd = int(sdss_ids[1])
                fiberid = int(sdss_ids[3])
            else:
                mjd = -1
                plateid = -1
                fiberid = -1
            som.set_som_element(som_x, som_y, {'mjd': mjd, 'plateid': plateid, 'fiberid':fiberid, 'sdsslink':link, 'som_x':som_x, 'som_y': som_y})
            som_x = som_x +1
        som_y = som_y + 1


# MJD,PLATEID,FIBERID FROM DUMPFILE IMPORT
# takes input file like allSpectra.txt from aspect dump -i sofmnet and fills a given som object with mjd,fiberid,plateid
def mjd_plate_fiberid_to_som_from_dumpfile(dump_input_file, som):
    import os
    import math
    with open(dump_input_file, 'r') as f:
        row_count = 0
        for row in f:
            row_count+=1
        edge_length = math.sqrt(row_count)
        if ( int(edge_length) != edge_length ):
            sys.stderr.write('Error: Number of lines in dumpfile is not equal to the square of an integer. This means that there are not enough or too many lines in the dumpfile to generate a square map of spectra icons.')
        else:
            edge_length = int(edge_length)
            som_x = 0
            som_y = 0
            f.seek(0)
            for row in f:
                image_filename_string = row
                image_filename_string = str.replace(image_filename_string, '.', '-')
                sdss_ids = image_filename_string.split('-')
                if sdss_ids[0] == 'spec':
                    #sdss dr10 and later
                    plateid = int(sdss_ids[1])
                    mjd = int(sdss_ids[2])
                    fiberid = int(sdss_ids[3])
                elif sdss_ids[0] == 'spSpec':
                    #sdss dr9 and before
                    plateid = int(sdss_ids[2])
                    mjd = int(sdss_ids[1])
                    fiberid = int(sdss_ids[3])
                else:
                    mjd = -1
                    plateid = -1
                    fiberid = -1
                som.set_som_element(som_x, som_y, {'mjd': mjd, 'plateid': plateid, 'fiberid':fiberid, 'som_x':som_x, 'som_y': som_y})
                ## increase som coordinate counts
                som_x+=1
                if (som_x == edge_length):
                    som_x = 0
                    som_y+=1


########################################################################
## TRANSFORMATION /OUTPUT FUNCTIONS

# EXISTING IMAGE TRANSFORMATION
# takes links of existing images and stitches new tiles out of those
# requires in som_properties: source_dir, dest_dir, icon_size
def combine_tile_images(tile_data, som_properties, at_zoom):
    from PIL import Image
    from PIL import ImageDraw
    import os
    x_low = tile_data['boundaries']['x_low']
    y_low = tile_data['boundaries']['y_low']
    x_high = tile_data['boundaries']['x_high']
    y_high = tile_data['boundaries']['y_high']
    tile_x = tile_data['tile_x']
    tile_y = tile_data['tile_y']
    icon_size = som_properties['icon_size']
    source_dir = som_properties['source_dir']
    dest_dir = som_properties['dest_dir'] + '/' + som_properties['name']
    temp_icon_size = (icon_size *  (x_high +1 - x_low ), icon_size * (y_high +1 - y_low))
    temp_icon = Image.new('RGBA', temp_icon_size, (255,255,255,0))
    # changed to True when something gets pasted to temp_icon
    write_icon_to_disk = False
    for x in xrange(x_low, x_high + 1):
        for y in xrange(y_low, y_high + 1):
            if ( (x,y) in tile_data):
                #print (x,y)
                source_icon_path = ''.join((source_dir, '/', tile_data[(x,y)]))
                if os.path.exists(source_icon_path):
                    source_icon = Image.open(source_icon_path)
                    #~ temp_icon.paste(source_icon, ( (x - x_low) * icon_size + 2, (y - y_low) * icon_size + 2))
                    if (at_zoom > som_properties['max_zoom'] - 4):
                        source_icon = source_icon.resize((icon_size - 8, icon_size - 8))
                        temp_icon.paste(source_icon, ( (x - x_low) * icon_size + 4, (y - y_low) * icon_size + 4))
                    else:
                        source_icon = source_icon.resize((icon_size, icon_size))
                        temp_icon.paste(source_icon, ( (x - x_low) * icon_size, (y - y_low) * icon_size))
                    del source_icon
                    write_icon_to_disk = True
    temp_icon = temp_icon.resize((icon_size, icon_size))
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if not os.path.exists(dest_dir + '/' + str(at_zoom)):
        os.makedirs(dest_dir + '/' + str(at_zoom))
    if write_icon_to_disk:
        temp_icon.save(''.join((dest_dir, '/', str(at_zoom), '/' , str(tile_x), '-', str(tile_y), '.png')), "PNG")
    del temp_icon


# EXTRACT METADATA FROM IMAGE FILENAMES
# extracts MJD, Plateid, Fiberid from spec-MJD-PLATEID-FIBERID.fit.png-Files
# requires in som_properties: source_dir, dest_dir
def write_metadata_to_json(tile_data, som_properties, at_zoom):
    import json
    import os
    source_dir = som_properties['source_dir']
    dest_dir = som_properties['dest_dir'] + '/' + 'specmetadata'
    mjd=tile_data[(tile_data['tile_x'], tile_data['tile_y'])]['mjd']
    plateid=tile_data[(tile_data['tile_x'], tile_data['tile_y'])]['plateid']
    fiberid=tile_data[(tile_data['tile_x'], tile_data['tile_y'])]['fiberid']
    som_x = tile_data['tile_x']
    som_y = tile_data['tile_y']

    # write data for aspect-ui onclick popups
    file_path = ''.join((dest_dir, '/', str(som_x), '-', str(som_y), '.json'))
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if not os.path.exists(file_path):
        with open(file_path, 'w') as json_data_file:
            json.dump(tile_data[(som_x, som_y)], json_data_file)

    # write idmapping som_x, som_y -> mjd, plateid, fiberid and vice versa
    dest_dir = som_properties['dest_dir'] + '/' + 'idmapping'
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    idmapping_file_path = ''.join((dest_dir, '/', str(som_x), '-', str(som_y), '.json'))
    if not os.path.exists(idmapping_file_path):
        with open(idmapping_file_path, 'w') as idmapping_file:
            json.dump({"mjd": int(mjd), "plateid":int(plateid), "fiberid": int(fiberid) }, idmapping_file)
    idmapping_file_path = ''.join((dest_dir, '/', str(mjd), '-', str(plateid), '-', str(fiberid), '.json'))
    if not os.path.exists(idmapping_file_path):
        with open(idmapping_file_path, 'w') as idmapping_file:
            json.dump({"som_x": int(som_x), "som_y":int(som_y)}, idmapping_file)
    
    # make couchdb bulk import files
    if ('couch_db' in som_properties):
        couchdb_file_path = ''.join((dest_dir, '/../idmapping.couchdb'))
        with open(couchdb_file_path, 'a') as couchdb_file:
            json.dump({"_id": "idmapping_" + str(som_x) + "-" + str(som_y) + ".json" , "data": {"mjd": int(mjd), "plateid":int(plateid), "fiberid": int(fiberid) } }, couchdb_file)
            json.dump({"_id": "idmapping_" + str(mjd) + "-" + str(plateid) + '-' + str(fiberid) + ".json" , 
                "data": {"som_x": int(som_x), "som_y":int(som_y)} }, couchdb_file)
        couchdb_file_path = ''.join((dest_dir, '/../specmetadata.couchdb'))
        with open(couchdb_file_path, 'a') as couchdb_file:
            json.dump({"_id": "specmetadata_" + str(som_x) + "-" + str(som_y) + ".json", "data": tile_data[(som_x, som_y)] }, couchdb_file)

########################################################################
## example implementation
def example():
    # Icons
    som1 = SOM("icons", "image", combine_tile_images, {'source_dir': '/var/tmp/Bin1', 'dest_dir': '/var/tmp/out', 'icon_size': 64})
    image_links_to_som_from_html("/var/tmp/full0_0.html", som1)
    for zoom in xrange(0, som1.get_som_max_zoom() +1):
        for x in xrange(0, som1.get_som_dimension_at_zoom(zoom) ):
            for y in xrange(0, som1.get_som_dimension_at_zoom(zoom) ):
                som1.transform_tile(zoom,x,y)
    som1.write_aspect_ui_config_to_disk()

    # Metadata and idmapping data to json
    som2 = SOM("specmetadata", "json", write_metadata_to_json, {'source_dir': '/var/tmp/Bin1', 'dest_dir': '/var/tmp/out', 'icon_size': 64})
    mjd_plate_fiberid_to_som_from_html("/var/tmp/full0_0.html", som2)
    for x in xrange(0, som2.get_som_dimension()):
        for y in xrange(0, som2.get_som_dimension()):
            som2.transform_tile(som2.get_som_max_zoom(),x,y)


########################################################################
## main

if __name__ == '__main__':

    #input parameter parsing
    parser = argparse.ArgumentParser()
    exclusive_input_group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument("-i", "--inputdir", type=str, required=True, help="Directory containing plate folders with fits.png files, i. e. the spec icons computed by ASPECT.")
    parser.add_argument("-o", "--outputdir", type=str, required=True, help="Output directory for plotted spectra icons and metadata.")
    exclusive_input_group.add_argument("-H", "--htmlfile", type=str, help="A file similar to full0_0.html in the export directory of the ASPECT output.")
    exclusive_input_group.add_argument("-D", "--dumpfile", type=str, help="A file generated by the ASPECT dump utility. (usually allSpectra.txt as output of dump -i sofmnet.bin) Each line of this file contains the name of a fits file. The number of lines has to be the square of an integer which corresponds to the map's edge length - 1.")
    parser.add_argument("-s", "--iconsize", type=int, default=256, help="Dimension of the spec icons in Pixels. Default: 256")
    parser.add_argument("-z", "--minzoom", type=int, default=1, help="Minimum zoom level")
    args = parser.parse_args()

    print("creating directory structure\n")

    ##directory initialisation
    ##everything will be saved somewhere below the output directory
    output_directory = args.outputdir
    output_directory = ''.join((output_directory, '/web'))
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    output_directory += '/som'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    print ("rendering icons...\n")
    som_icons = SOM("icons", "image", combine_tile_images, {'source_dir': args.inputdir, 'dest_dir': output_directory, 'icon_size': args.iconsize, 'min_zoom': args.minzoom})
    
    ## html file given as map input
    if (args.htmlfile != None):
        image_links_to_som_from_html(args.htmlfile, som_icons)
    ## ASPECT dump file given as map input
    if (args.dumpfile != None):
        image_links_to_som_from_dumpfile(args.dumpfile, som_icons)
    
    for zoom in xrange(min(args.minzoom, som_icons.get_som_max_zoom()), som_icons.get_som_max_zoom() +1):
        print("zoom level " + str(zoom) + " of " + str(som_icons.get_som_max_zoom()) + "...\n")
        for y in xrange(0, som_icons.get_som_dimension_at_zoom(zoom) ):
            for x in xrange(0, som_icons.get_som_dimension_at_zoom(zoom) ):
                som_icons.transform_tile(zoom,x,y)
    som_icons.write_aspect_ui_config_to_disk()


    # Metadata and idmapping data to json
    print ("writing metadata...\n")
    som_metadata = SOM("specmetadata", "json", write_metadata_to_json, {'source_dir': args.inputdir, 'dest_dir': output_directory, 'icon_size': args.iconsize, 'couch_db': 1})
    if (args.htmlfile != None):
        mjd_plate_fiberid_to_som_from_html(args.htmlfile, som_metadata)
    if (args.dumpfile != None):
        mjd_plate_fiberid_to_som_from_dumpfile(args.dumpfile, som_metadata)
    for x in xrange(0, som_metadata.get_som_dimension()):
        for y in xrange(0, som_metadata.get_som_dimension()):
            som_metadata.transform_tile(som_metadata.get_som_max_zoom(),x,y)
            
    print ("Done...\n")
