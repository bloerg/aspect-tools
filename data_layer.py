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



def smp_fits_to_files ( queue ):
    try:
        for task in iter(queue.get, 'STOP'):
            try:
                fits_to_files( task[0], task[1], task[2])
            except:
                sys.stderr.write(''.join(('Something went wrong with ', task[0], "\n")))
    except Exception, e:
        sys.stderr.write("Something went wrong with one of the processes.\n")
    return True
    

def fits_to_files ( filename, output_base_dir, output_fields):
    fits_file_name = filename
    
    try:
        fits_file = pyfits.open(fits_file_name)
        
        
        ##Die Daten aus dem ersten HDU
        data_fields = ['tai', 'ra', 'dec', 'equinox', 'az', 'alt', 'mjd', 'quality', 'radeg', 'decdeg', 'plateid', 'tileid', 'cartid', 'mapid', 'name', 'objid', 'objtype', 'raobj', 'decobj', 'fiberid', 'z', 'z_err', 'z_conf', 'z_status', 'z_warnin', 'spec_cln', 'sci_sn']
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

        #output_filename = ''.join([output_path, '/', str(data['mjd']), '-', str(data['plateid']), '-', str(data['fiberid']),'.png'])
        for output_field in output_fields.split(','):
            output_path = ''.join([output_base_dir, '/', output_field])
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            output_path = ''.join([output_path, '/', str(data['plateid'])])
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            output_filename = ''.join([output_path, '/', os.path.basename(fits_file_name), '.json'])
            if not os.path.exists(output_filename):
                with open(output_filename, 'w') as f:
                    json.dump([data[output_field]], f)
        fits_file.close()

    except IOError:
        sys.stderr.write(''.join(('Error: could not read fits file: ', filename, "\n")))

def processDirectory (args, dirname, filenames ):
    
    for filename in filenames:
        if re.match('.*\.fit$', filename):
            if args['multiprocessing']:
                work_queue.put([dirname + "/" + filename, args['output_dir'], args['fields']])
            else:
                fits_to_files(dirname + "/" + filename, args['output_dir'], args['fields'])


if __name__ == '__main__':

    #input parameter parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputdir", type=str, required=True, help="Directory containing fits files with spectra. Can have sub directories.")
    parser.add_argument("-o", "--outputdir", type=str, required=True, help="Output directory for plotted spectra icons.")
    parser.add_argument("-l", "--nomultiprocessing", action="store_true", help="Use only one process for computing instead of several")
    parser.add_argument("-p", "--numberofprocesses", type=int, default=4, help="Number of Processes to use when multiprocessing")
    parser.add_argument("-f", "--fields", type=str, default="z", help='comma separated list of fits file fields. e.g. "z,spec_cln,objtype"')
    args = parser.parse_args()    

    if os.path.exists(args.inputdir):
        if os.path.exists(args.outputdir):

            if args.nomultiprocessing:
                os.path.walk( args.inputdir, processDirectory, {"output_dir": args.outputdir, "multiprocessing": False, "fields": args.fields})
            
            else:
                workers = args.numberofprocesses
                work_queue = mp.Queue()
                processes = []
                
                for worker in range(workers):
                    p = mp.Process(target=smp_fits_to_files, args=(work_queue,))
                    p.start()
                    processes.append(p)

                os.path.walk( args.inputdir, processDirectory, {"output_dir": args.outputdir, "multiprocessing": True, "fields": args.fields})

                for worker in range(workers):
                    work_queue.put('STOP')
                    
                for process in processes:
                    process.join()
               
        else:
            sys.exit(''.join(("Output Directory does not exist. Please create: ", args.outputdir)))
    else:
        sys.exit(''.join(("Input directory does not exist: ", args.inputdir, " Please check!")))

    
    
