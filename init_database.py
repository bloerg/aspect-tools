# -*- coding: utf-8 -*-
import psycopg2
import pyfits
import string
import os
import re



##Configuration

#Database
with open('../../etc/config.json') as json_data_file:
    config = json.load(json_data_file)
server_name = config['postgresql']['host']
db_name = config['postgresql']['database']
user_name = config['postgresql']['user']
db_password = config['postgresql']['password']


#SOM
#SOM_dimension is the edge length of the map. It is one terminated.
som_dimension = 1104

def make_SOM_table(dimension):
    db_cursor.execute('CREATE TABLE som (SOM_X integer, SOM_Y integer, CHECK (SOM_X >= 0), CHECK (SOM_X < %s), CHECK (SOM_Y >= 0), CHECK (SOM_Y < %s), PRIMARY KEY (SOM_X, SOM_Y));', (dimension, dimension))
    for som_x in range(som_dimension):
        for som_y in range(som_dimension):
            db_cursor.execute('INSERT INTO SOM (SOM_X, SOM_Y) VALUES (%s, %s)', (som_x, som_y))

def make_specobject_metadata_table():
    db_cursor.execute("""CREATE TABLE specobject_metadata (
        MJD integer, CHECK (MJD >= 0),
        PLATEID integer, CHECK (PLATEID >= 0),
        FIBERID integer, CHECK (FIBERID >= 0),
        tai real, 
        ra real, 
        dec real, 
        equinox real, 
        az real, 
        alt real,
        quality varchar(20), 
        radeg real, 
        decdeg real, 
        tileid integer, 
        cartid integer, 
        mapid integer, 
        name varchar(20), 
        objid varchar(30), 
        objtype varchar(20), 
        spec_cln integer, 
        raobj real, 
        decobj real, 
        z real, 
        z_err real,
        z_conf real,
        z_status real,
        z_warnin real,
        PRIMARY KEY (MJD, PLATEID, FIBERID));""")
    db_connection.commit()
        
def make_specobject_equivalent_width_table():
    db_cursor.execute("""CREATE TABLE specobject_equivalentwidths (
        MJD integer,
        PLATEID integer,
        FIBERID integer,
        FOREIGN KEY (MJD, PLATEID, FIBERID) REFERENCES  specobject_metadata (MJD, PLATEID, FIBERID) ON DELETE CASCADE,
        PRIMARY KEY (MJD, PLATEID, FIBERID)
        );""")
    db_connection.commit()

def make_specobject_spectra_table():
    db_cursor.execute("""CREATE TABLE specobject_spectra (
        MJD integer,
        PLATEID integer,
        FIBERID integer,
        spectrum real[],
        FOREIGN KEY (MJD, PLATEID, FIBERID) REFERENCES  specobject_metadata (MJD, PLATEID, FIBERID) ON DELETE CASCADE,
        PRIMARY KEY (MJD, PLATEID, FIBERID)
        );""")
    db_connection.commit()

def make_user_defined_layer_table():
    db_cursor.execute("""CREATE TABLE user_defined_layers (
        LAYERNAME varchar(256),
        color varchar(20) NOT NULL,
        alpha real DEFAULT 0.5,
        remark varchar(1000),
        PRIMARY KEY (LAYERNAME)
        );""")
    db_connection.commit()


def make_user_defined_selection_table():
    db_cursor.execute("""CREATE TABLE user_defined_selections (
        MJD integer,
        PLATEID integer,
        FIBERID integer,
        LAYERNAME varchar(256) NOT NULL,
        FOREIGN KEY (MJD, PLATEID, FIBERID) REFERENCES  specobject_metadata (MJD, PLATEID, FIBERID) ON DELETE CASCADE,
        FOREIGN KEY (LAYERNAME) REFERENCES user_defined_layers (LAYERNAME) ON DELETE CASCADE,
        PRIMARY KEY (MJD, PLATEID, FIBERID, LAYERNAME)
        );""")
    db_connection.commit()
        
def make_spec_object_spectra_width_256_view():
    #the following function was inspired by http://stackoverflow.com/questions/13804281/aggregate-functions-over-arrays
    db_cursor.execute("""CREATE OR REPLACE FUNCTION public.downsize_spectrum (
            a_spectrum real [], new_size integer
            )
            RETURNS real [] AS
            $body$
            DECLARE
              dim_start int = array_length(a_spectrum, 1); --size of input array
              dim_end int = new_size; -- size of output array
              dim_step int = dim_start / dim_end; --avg batch size
              tmp_sum NUMERIC; --sum of the batch
              result_spectrum real[]; -- resulting array
            BEGIN

              FOR i IN 1..dim_end LOOP --from 1 to new_size.
                tmp_sum = 0;

                FOR j IN (1+(i-1)*dim_step)..i*dim_step LOOP --from 1 to 3, 4 to 6, ...
                  tmp_sum = tmp_sum + a_spectrum[j];  
                END LOOP; 

                result_spectrum[i] = tmp_sum / dim_step;
              END LOOP; 

              RETURN result_spectrum;
            END;
            $body$
            LANGUAGE 'plpgsql'
            IMMUTABLE
            RETURNS NULL ON NULL INPUT;""")
    db_connection.commit()

    db_cursor.execute("""CREATE MATERIALIZED VIEW specobject_spectra_width256
        AS
        SELECT mjd, plateid, fiberid, downsize_spectrum(specobject_spectra.spectrum, %s) as spectrum FROM
            specobject_spectra NATURAL 
            JOIN som_specobject_identification 
    ;""", (256,))
    db_connection.commit()
    db_cursor.execute("""create index on specobject_spectra_width256 (MJD, PLATEID, FIBerID)""")
    db_connection.commit()

def fits_to_db ( filename ):
    fits_file_name = filename
    fits_file = pyfits.open(fits_file_name)
    
#    print fits_file_name
    
    ##Die Daten aus dem ersten HDU
    data_fields = ['tai', 'ra', 'dec', 'equinox', 'az', 'alt', 'mjd', 'quality', 'radeg', 'decdeg', 'plateid', 'tileid', 'cartid', 'mapid', 'name', 'objid', 'objtype', 'raobj', 'decobj', 'fiberid', 'z', 'z_err', 'z_conf', 'z_status', 'z_warnin', 'spec_cln']
    data = dict()
    value_string = ""
    for data_field in data_fields:
        data[data_field] = fits_file[0].header[data_field]
        value_string = value_string + "%(" + data_field + ")s, "
    value_string = string.rstrip(value_string,', ') 
    
    db_cursor.execute("INSERT INTO specobject_metadata" + " (" + string.join(data_fields,',') + ") VALUES (" + value_string + ");", data)

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
        db_cursor.execute("CREATE TABLE IF NOT EXISTS " + "ew_" +  restWave + """ (
            MJD integer,
            PLATEID integer,
            FIBERID integer,
            equivalent_width numeric,
            FOREIGN KEY (MJD, PLATEID, FIBERID) REFERENCES  specobject_metadata (MJD, PLATEID, FIBERID) ON DELETE CASCADE,
            PRIMARY KEY (MJD, PLATEID, FIBERID)
            );""")
        db_cursor.execute("INSERT INTO " + "ew_" + restWave + " (MJD, PLATEID, FIBERID, equivalent_width) VALUES (%s, %s, %s, %s)", (data['mjd'], data['plateid'], data['fiberid'], ew + 0))
        #equivalent_width_data['ew_'+restWave] = ew + 0
        #equivalent_width_data_fields.append('ew_'+restWave)
        #equivalent_width_value_string = equivalent_width_value_string + ", %(ew_"+restWave+")s"
        ewcount = ewcount+1
    
    spectrum=fits_file[0].data[0]
    db_cursor.execute("INSERT into specobject_spectra (MJD, PLATEID, Fiberid, spectrum) VALUES (%s,%s,%s,%s);", (data['mjd'], data['plateid'], data['fiberid'], spectrum.tolist()))
    
    db_connection.commit()
    fits_file.close


def processDirectory (args, dirname, filenames ):
    #print dirname
    for filename in filenames:
        if re.match('.*\.fit$', filename):
            fits_to_db(dirname + "/" + filename)
            

def Kohonen_Fits_Mapping(filename):
    db_cursor.execute("""CREATE TABLE som_specobject_identification (
            SOM_X integer,
            SOM_Y integer,
            MJD integer,
            PLATEID integer,
            FIBERID integer,
            FOREIGN KEY (MJD, PLATEID, FIBERID) REFERENCES  specobject_metadata (MJD, PLATEID, FIBERID) ON DELETE CASCADE,
            FOREIGN KEY (SOM_X, SOM_Y) REFERENCES SOM (SOM_X, SOM_Y),
            PRIMARY KEY (SOM_X, SOM_Y, MJD, PLATEID, FIBERID)
            );""")
    mapping_data_file = csv.DictReader(open(filename, "rb"), delimiter=";")
    for row in mapping_data_file:
        data = dict()
        data = row
        db_cursor.execute("INSERT INTO som_specobject_identification (som_x, som_y, mjd, plateid, fiberid) VALUES (%s, %s, %s, %s, %s);", (int(data['x']), int(data['y']), int(data['MJD']), int(data['plateID']), int(data['fibID'])))
    db_connection.commit()

def make_spectra_metadata_table():
    db_cursor.execute('CREATE TABLE spectrametadata')

if __name__ == '__main__':

    #Create Database
    connect_string = "dbname=postgres" + " user=" + user_name + " host="+ server_name + " password=" + db_password
    db_connection = psycopg2.connect(connect_string)
    db_cursor = db_connection.cursor()
    db_connection.autocommit=True
    db_cursor.execute('CREATE DATABASE ' + db_name)
    db_connection.close()

    #Database Connection
    connect_string = "dbname=" + db_name + " user=" + user_name + " host="+ server_name + " password=" + db_password
    db_connection = psycopg2.connect(connect_string)
    db_cursor = db_connection.cursor()
    db_connection.autocommit=False

    #initialize the tables in the database
    make_SOM_table(som_dimension)
    make_specobject_metadata_table()
    #make_specobject_equivalent_width_table()
    make_specobject_spectra_table()
    db_connection.commit()
    base_dir = "./spectra/sub/spectra.txt"
    os.path.walk( base_dir, processDirectory, None )
    #compute reduced spectra with width of 256
    #this may take another while
    make_spec_object_spectra_width_256_view()
    #insert the Tablef or the SOM - Spectra - Mapping
    Kohonen_Fits_Mapping('./zuordnung.dat')

    db_cursor.close()
    db_connection.close()    
    
    
