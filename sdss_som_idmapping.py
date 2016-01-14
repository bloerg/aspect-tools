#!/usr/bin/python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import json
import os
from shutil import copyfile
import argparse
import sys


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



if __name__ == '__main__':

#input parameter parsing
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--inputfile", type=str, required=True, help="input file like full0_0.html generated by ASPECT")
parser.add_argument("-o", "--outputfile", type=str, help="output file (defaults to standard output)")
exclusive_output_options = parser.add_mutually_exclusive_group(required = True)
exclusive_output_options.add_argument("-c", "--csv", action="store_true", help="output format is csv (default)")
parser.add_argument("-d", "--delimiter", type=str, help='csv output delimiter (defaults to ";")')
exclusive_output_options.add_argument("-j", "--json", action="store_true",  help="output format is json")
args = parser.parse_args()

if not args.delimiter:
    delimiter = ";"
else:
    delimiter = args.delimiter

if os.path.exists(args.inputfile):

    if args.outputfile:
        if os.path.exists(args.outputfile):
            exit(''.join(("Error: output file already exists: ", args.outputfile, "\n", "I wont overwrite.")))
        else:
            try:
                output_file = open(args.outputfile, 'w')
            except IOError:
                sys.exit("Error: could not open output file for writing.")

    
    with open(args.inputfile, 'r') as input_file:
        plain_html = input_file.read()

    if args.csv:
        output_string = delimiter.join( ( "som_x", "som_y" , "mjd", "plateid", "fiberid", "link\n") )
        if args.outputfile:
            output_file.write(output_string)
        else:
            sys.stdout.write(output_string)

    html_content = BeautifulSoup(plain_html, "lxml")
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
                    sys.stderr.write("Don't know how to scrape ids from fits.png filename. Using empty values...")
                    mjd = -1
                    plateid = -1
                    fiberid = -1                
                
            if args.json:
                output_object = {"mjd": int(mjd), "plateid":int(plateid), "fiberid": int(fiberid), "som_x": int(som_x), "som_y": int(som_y), "link": str(link)}
                if args.outputfile:
                    json.dump(output_object, output_file)
                else:
                    print json.dumps(output_object)
            
            if args.csv:
                output_string = delimiter.join( ( str(som_x), str(som_y), str(mjd), str(plateid), str(fiberid), ''.join(('"',str(link), '"', "\n")) ) )
                if args.outputfile:
                    output_file.write(output_string)
                else:
                    sys.stdout.write(output_string)


            som_x = som_x +1
        som_y = som_y + 1
    if args.outputfile:
        output_file.close()
    
else:
    sys.exit(''.join(("Error: input file does not exist: ", args.inputfile, "\n")))


