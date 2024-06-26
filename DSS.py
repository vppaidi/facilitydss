from flask import Flask, render_template, session, redirect, url_for, session, request, jsonify, flash

from flask_wtf import FlaskForm
from wtforms import (StringField, BooleanField, DateTimeField,
                     RadioField,SelectField,
                     TextAreaField,SubmitField)
from wtforms.validators import DataRequired
import urllib.parse
import sys
import gc
import subprocess
from subprocess import run,PIPE
import os
import pandas as pd
import numpy as np #(You are here)
import requests
import pulp
from spopt.locate import PMedian
from flask import send_from_directory
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import time
import io
import csv
import datetime;
import json
import copy
from rq import Queue
from redis import Redis
from rq.job import Job
# This is used to explore only for newly available locations
from tasknp_test import redis_conn, recommend_task

# This is used to explore only with pre-loaded datasets
from tasknp2 import redis_conn, recommend_task2

# This is to explore with existing locations
from tasknp3 import redis_conn, recommend_task3

# This is to use pre-loaded datasets and with existing locations
from tasknp4 import redis_conn, recommend_task4

#This is used to exploit using given facilities
from tasknn import redis_conn, pfac_task

#This is used to exploit using given facilities when pre loaded data
from tasknn2 import redis_conn, pfac_task2

from rq.exceptions import NoSuchJobError


app = Flask(__name__)



queue = Queue(connection=redis_conn)

# Configure a secret SECRET_KEY
app.config['SECRET_KEY'] = 'mysecretkey'

# Define the expected header name
EXPECTED_HEADER_NAME = 'dest'

# Define the expected header name
EXPECTED_HEADER_NAME2 = 'facility'

addresses = []
addresses2 = []
addr = []
radius = 0

#Loading data
#locations = pd.read_csv('datacsv.csv')

# Fixed parameters from the provided URL
username = "vppaidi"
repository = "facilitydss"
branch = "main"

# Construct the GitHub raw URL
base_url = "https://raw.githubusercontent.com"

file_name = "datacsv"
file_path = f"{base_url}/{username}/{repository}/{branch}/{file_name}.csv"
locations = pd.read_csv(file_path)

predata = ['Sweden','Stockholms','Göteborg', 'Kalmar', 'Dalarnas', 'Södermanlands', 'Östergötlands', 'Jönköpings', 'Skåne', 'Kronobergs', 'Örebro', 'Värmlands', 'Hallands', 'Västra Götalands', 'Västerbottens', 'Norbottens', 'Uppsala', 'Stockholm', 'Linköping', 'Göteborg', 'Stockholms']
# Now create a WTForm Class
# Lots of fields available:
# http://wtforms.readthedocs.io/en/stable/fields.html
class InfoForm(FlaskForm):
    '''
    This general class gets a lot of form about puppies.
    Mainly a way to go through many of the WTForms Fields.
    '''

@app.route('/', methods=['GET', 'POST'])
def index():
    
    
    # Create instance of the form.
    
    form = InfoForm()
    data = None  # Initialize 'data' with a default value
    options = 'Borlänge'  # The options for the dropdown menu
   

        
    if request.method == 'POST':

        
        selected_radio = request.form.get('radio')
        session['selected_radio']= selected_radio
        #selected_dropdown  = request.form.get('dropdown' + selected_radio[-1])
        if selected_radio[-1] == '3':
            selected_dropdown = request.form.get('city')
        else:
            selected_dropdown  = request.form.get('dropdown' + selected_radio[-1])

        
        session['s_option'] = selected_dropdown
        
        # Print the selected options
        print("Selected Radio Option:", selected_radio)
        print("Selected Dropdown Option:", session.get('s_option'))
        
        option = request.form.get('option')
        # Now option contains the value of the selected radio button
        # Do something with the option here
        print(option)
        
        if option == 'option10':
            return render_template('upload.html')
        
        elif option == 'option11':
            return render_template('recommend.html')

        
    return render_template('index.html', form=form, options=options, data=data)

@app.route('/upload', methods=['GET','POST'])
def upload():
    
        
    #selected_dropdown = "default_value"
    selected_dropdown =session.get('s_option')
    
    uploaded_data_json = '{""}'
    facilit = '{""}'
    P_FACILITIES = 0
    
    selected_option = request.form.get('fileOption')
    print(selected_option)
    
    if request.method == 'POST':
        
        
        selected_option = request.form.get('fileOption')
        print(selected_option)
    
        if selected_option == 'optionA':
            file = request.files['fileA']
            
            P_FACILITIES = request.form.get('facilities')  # Get the input value

            try:
                P_FACILITIES = int(P_FACILITIES)
                
                if not (0 <= P_FACILITIES <= 100):  # Check if the value is within the desired range
                    raise ValueError("Value out of range")
            
            except ValueError as e:
                # Handle the error appropriately, e.g., return an error response
                return f"Invalid input: {e}"
            
            session['P_FACILITIES']= P_FACILITIES
            print(P_FACILITIES)
            
            
            #file = request.files['file']
            if not file:
                return {"error": "No file"}
            
            
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)

            addresses = []
        
            for row in csv_input:
                # Removing the BOM character
                print(row)
                address = row['\ufeffAddress'.strip()]  # Use the header name to access the correct field
                
                # Photon API endpoint
                url = 'https://photon.komoot.io/api/?q=' + address
            
                response = requests.get(url)
                
                if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type'):
                    data = response.json()
                    
                    # Check if results are available
                    if data and 'features' in data and len(data['features']) > 0:
                        latitude = data['features'][0]['geometry']['coordinates'][1]  # Photon's order is [lon, lat]
                        longitude = data['features'][0]['geometry']['coordinates'][0]
                        addresses.append({'address': address, 'lat': latitude, 'lon': longitude})
                    else:
                        print(f"No results found for address: {address}")
                else:
                    print(f"Failed request for address: {address}. Status: {response.status_code}. Response: {response.text}")
                # Delay for one second
                time.sleep(1)  # Add this line to introduce a delay
            #print(addresses)                    
           
            df = pd.DataFrame(addresses)
            df = df.rename(columns={'lat': 'Latitude', 'lon': 'Longitude'})
            print(df.head())
            uploaded_data =df[['Latitude','Longitude']]
            df = df[['Latitude','Longitude']]
            
            
            file.seek(0)
            dff = pd.read_csv(file)
            facilit = dff
            print(facilit)
            
            if len(df) != len(dff):
                return jsonify({"message": "All Addresses are not identified. Try to upload coordinates using the alternate option", "status": "error"})

            facilit = facilit.to_json() 
            

            uploaded_data_json = uploaded_data.to_json()
            
            
            session['uploaded_data_json'] = uploaded_data_json
            session['facilit'] = facilit
            session['addresses'] = addresses
            
            return render_template('pfac.html', addresses = addresses)
        
        else:
            file = request.files['fileB']
            P_FACILITIES = request.form.get('facilities')  # Get the selected option
            P_FACILITIES = int(P_FACILITIES)
            session['P_FACILITIES']= P_FACILITIES
            print(P_FACILITIES)
            
            
            #file = request.files['file']
            if not file:
                return {"error": "No file"}
            addresses = []  # Initialize the addresses list here
            
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
        
            for row in csv_input:
                # Assuming your CSV columns are named 'Latitude', 'Longitude', and 'Address'
                #print(row)
                latitude = row['\ufeffLatitude'].strip() 
                longitude = row['Longitude'].strip()
                            
                addresses.append({'lat': latitude, 'lon': longitude})
                
            df = pd.DataFrame(addresses)
            df = df.rename(columns={'lat': 'Latitude', 'lon': 'Longitude'})
            #print(df.head())
            uploaded_data =df[['Latitude','Longitude']]
            df = df[['Latitude','Longitude']]
                
            
            file.seek(0)
            dff = pd.read_csv(file)
            facilit = dff

            facilit = facilit.to_json() 
            
            uploaded_data_json = uploaded_data.to_json()
           
            session['uploaded_data_json'] = uploaded_data_json
            session['facilit'] = facilit
            session['addresses'] = addresses
                  
            return render_template('pfac.html', addresses = addresses)
  
@app.route('/download_example')
def download_example():

    # Send the example file for download
    return send_from_directory('static', 'examples/dest.csv', as_attachment=True)

@app.route('/download_example4')
def download_example4():

    # Send the example file for download
    return send_from_directory('static', 'examples/dest4.csv', as_attachment=True)


@app.route('/download_example3')
def download_example3():

    # Send the example file for download
    return send_from_directory('static', 'examples/coordinates.csv', as_attachment=True)    

@app.route('/pfac', methods=['GET','POST'])
def pfac():
    
    P_FACILITIES = session.get('P_FACILITIES')
    selected_dropdown = session.get('s_option')
    facilit = session.get('facilit')
    print("This is selected option", selected_dropdown)
    uploaded_data_json = session.get('uploaded_data_json')
    origins = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
    
    print(type(origins))    
    
    print(origins.head(5))
    origins = origins.to_dict(orient='records')
    
    if selected_dropdown in predata:
        
        print(selected_dropdown)
        file_name = selected_dropdown
        encoded_file_name = urllib.parse.quote(file_name)  # URL encoding
        file_path = f"{base_url}/{username}/{repository}/{branch}/{encoded_file_name}.csv"
        print(file_path)
        result = pd.read_csv(file_path, header=None)
        
        #print(result.head(5))
        dm = result.to_dict(orient='records')
        addresses = session.get('addresses')
        
        
        wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
        #print(wei.head(5))
        wei = wei.to_dict(orient='records')
        job = queue.enqueue(pfac_task2, selected_dropdown, P_FACILITIES, uploaded_data_json, facilit,  dm, origins, wei, addresses, job_timeout=97200)
        return jsonify({"message": "Task queued!", "job_id": job.get_id()}), 200
    
    else:
            
                       
            
            wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
            
            
            print(wei.head(5))
            wei = wei.to_dict(orient='records')
            
            addresses = session.get('addresses')
              
            
            #G_d = dict(G=nx.to_dict_of_dicts(G))
                
            #job = pfac_task.queue(selected_dropdown, uploaded_data_json, facilit, P_FACILITIES, origins, wei, addresses)
            job = queue.enqueue(pfac_task, selected_dropdown, uploaded_data_json, facilit, P_FACILITIES, origins, wei, addresses, job_timeout=97200)
            return jsonify({"message": "Task queued!", "job_id": job.get_id()}), 200


@app.route('/recommend', methods=['GET', 'POST'])
def recommend():

    #P_FACILITIES = session.get('P_FACILITIES')
    selected_dropdown = session.get('s_option')
   # facilit = session.get('facilit')
    print("This is selected option", selected_dropdown)
    #uploaded_data_json = session.get('uploaded_data_json')
    
    file = request.files.get('csvFile', None)  # Use .get() to safely retrieve the file
    P_FACILITIES = request.form.get('facilities')  # Get the input value
    
    try:
        P_FACILITIES = int(P_FACILITIES)
        
        if not (0 <= P_FACILITIES <= 100):  # Check if the value is within the desired range
            raise ValueError("Value out of range")
    
    except ValueError as e:
        # Handle the error appropriately, e.g., return an error response
        return f"Invalid input: {e}"
    session['P_FACILITIES']= P_FACILITIES
    print(P_FACILITIES)
    # If only P_Facilities were selected without upload
    if not file:
        if selected_dropdown in predata:
                     
            
                          
            file_name = selected_dropdown
            encoded_file_name = urllib.parse.quote(file_name)  # URL encoding
            file_path = f"{base_url}/{username}/{repository}/{branch}/{encoded_file_name}.csv"
            result = pd.read_csv(file_path, header=None)
            
            #print(result.head(5))
            dm = result.to_dict(orient='records')
            
            
            res = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
                       
            addresses = []
            addr = []
                                
            for idx, (latitude, longitude) in enumerate(res.values):
                latitude_str = str(latitude).strip()
                longitude_str = str(longitude).strip()
                
                addresses.append({'index': idx, 'lat': latitude_str, 'lon': longitude_str})
                
                
            #origins = pd.DataFrame(res, columns=['Latitude', 'Longitude'])
            #session['addresses'] = addresses
            #print(addresses)
            
            
            wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
            #print(wei.head(5))
            wei = wei.to_dict(orient='records')
            job = queue.enqueue(recommend_task2, selected_dropdown, P_FACILITIES, dm, wei, addresses, job_timeout=97200)
            return jsonify({"message": "Task queued!", "job_id": job.get_id(),"addr": addr}), 200
        else:
          
            origins = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
                
            addresses = []
            addr = []
            
            for idx, (latitude, longitude) in enumerate(origins.values):
                latitude_str = str(latitude).strip()
                longitude_str = str(longitude).strip()
                addresses.append({'index': idx, 'lat': latitude_str, 'lon': longitude_str})
            
            print(addresses) 
           # Converting origins to make it serializable
            origins = origins.to_dict(orient='records')
            

            wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
            
            wei = wei.to_dict(orient='records')
            
          
            job = queue.enqueue(recommend_task, selected_dropdown, P_FACILITIES, origins, wei, addresses, job_timeout=97200)
            return jsonify({"message": "Task queued!", "job_id": job.get_id(),"addr": addr}), 200
    # when file is uploaded
    else:
        print("file uploaded")
        # Retrieve the csv type
        csv_type = request.form['csvType']
        
        # Based on csv_type you can take different actions
        if csv_type == "csv_c":
            # Handle CSV C type processing
                    
            if selected_dropdown in predata:
               #print(selected_dropdown) 
               
               file_name = selected_dropdown
               encoded_file_name = urllib.parse.quote(file_name)  # URL encoding
               file_path = f"{base_url}/{username}/{repository}/{branch}/{encoded_file_name}.csv"
               result = pd.read_csv(file_path, header=None)
               
               #print(result.head(5))
               dm = result.to_dict(orient='records')
               
               addresses = []
               stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
               csv_input = csv.DictReader(stream)
               
               idx = 0  # Initialize index counter outside the loop

               for row in csv_input:
                   # Removing the BOM character
                   address = row['\ufeffAddress'.strip()]  # Use the header name to access the correct field
                                
                   # Photon API endpoint
                   url = 'https://photon.komoot.io/api/?q=' + address
                
                   response = requests.get(url)
                    
                   if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type'):
                       data = response.json()
                        
                       # Check if results are available
                       if data and 'features' in data and len(data['features']) > 0:
                           latitude = data['features'][0]['geometry']['coordinates'][1]  # Photon's order is [lon, lat]
                           longitude = data['features'][0]['geometry']['coordinates'][0]
                           addresses.append({'index': idx, 'lat': latitude, 'lon': longitude})  # Add index to the dictionary
                           
                           idx += 1  # Increment the index counter
                       else:
                           print(f"No results found for address: {address}")
                   else:
                       print(f"Failed request for address: {address}. Status: {response.status_code}. Response: {response.text}")
                    
                    # Delay for one second
                   time.sleep(1)
               
               addr=copy.deepcopy(addresses)  
               print(addresses)
               df = pd.DataFrame(addresses)
               num_rows=len(df)
               df = df.rename(columns={'lat': 'Latitude', 'lon': 'Longitude'})
               #print(df.head())
               uploaded_data =df[['Latitude','Longitude']]
               df = df[['Latitude','Longitude']]
               
               file.seek(0)
               dff = pd.read_csv(file)
               facilit = dff
               #print(facilit)
               facilit = facilit.to_json() 
               
               uploaded_data_json = uploaded_data.to_json()
               
               wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
               #print(wei.head(5))
               wei = wei.to_dict(orient='records')
               
               addresses = []
               origins = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
               for idx, (latitude, longitude) in enumerate(origins.values):
                   latitude_str = str(latitude).strip()
                   longitude_str = str(longitude).strip()
                   #idx=idx+num_rows
                   addresses.append({'index': idx, 'lat': latitude_str, 'lon': longitude_str})
                   #idx=idx-num_rows
               print(addresses)
               origins = origins.to_dict(orient='records')
               
               job = queue.enqueue(recommend_task4, selected_dropdown, P_FACILITIES, dm, uploaded_data_json, facilit, origins, wei, addresses, job_timeout=97200)
               return jsonify({"message": "Task queued!", "job_id": job.get_id(),"addr": addr}), 200
            else:
                addr=[]    
                addresses = []
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                idx = 0  # Initialize index counter outside the loop

                for row in csv_input:
                    # Removing the BOM character
                    address = row['\ufeffAddress'.strip()]  # Use the header name to access the correct field
                                 
                    # Photon API endpoint
                    url = 'https://photon.komoot.io/api/?q=' + address
                 
                    response = requests.get(url)
                     
                    if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type'):
                        data = response.json()
                         
                        # Check if results are available
                        if data and 'features' in data and len(data['features']) > 0:
                            latitude = data['features'][0]['geometry']['coordinates'][1]  # Photon's order is [lon, lat]
                            longitude = data['features'][0]['geometry']['coordinates'][0]
                            addresses.append({'index': idx, 'lat': latitude, 'lon': longitude})  # Add index to the dictionary
                            #print(addresses)
                            idx += 1  # Increment the index counter
                        else:
                            print(f"No results found for address: {address}")
                    else:
                        print(f"Failed request for address: {address}. Status: {response.status_code}. Response: {response.text}")
                     
                     # Delay for one second
                    time.sleep(1)
                
                addr=copy.deepcopy(addresses) 
                print(f"This will be printed: {addr}")
                df = pd.DataFrame(addresses) 
                num_rows=len(df)
                df = df.rename(columns={'lat': 'Latitude', 'lon': 'Longitude'})
                #print(df.head())
                uploaded_data =df[['Latitude','Longitude']]
                df = df[['Latitude','Longitude']]
                
                
                file.seek(0)
                dff = pd.read_csv(file)
                facilit = dff
                #print(facilit)
                facilit = facilit.to_json() 
                
                uploaded_data_json = uploaded_data.to_json()
                        
                            
                
                res = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
                
                for idx, (latitude, longitude) in enumerate(res.values):
                    latitude_str = str(latitude).strip()
                    longitude_str = str(longitude).strip()
                    idx=idx+num_rows
                    addresses.append({'index': idx, 'lat': latitude_str, 'lon': longitude_str})
                    idx=idx-num_rows
                
               
                
                session['uploaded_data_json'] = uploaded_data_json
                session['facilit'] = facilit
                #session['addresses'] = addresses
                
                
                origins = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
                #print(origins.head(5))
                origins = origins.to_dict(orient='records')
               
                wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
                #print(wei.head(5))
                wei = wei.to_dict(orient='records')
                
                job = queue.enqueue(recommend_task3, selected_dropdown, uploaded_data_json, facilit, P_FACILITIES, origins, wei, addresses, job_timeout=97200)
                return jsonify({"message": "Task queued!", "job_id": job.get_id(),"addr": addr}), 200

         # When coordinates csv file is uploaded
         
        elif csv_type == "csv_d":
            
            if selected_dropdown in predata:
               #print(selected_dropdown) 
               
               file_name = selected_dropdown
               encoded_file_name = urllib.parse.quote(file_name)  # URL encoding
               file_path = f"{base_url}/{username}/{repository}/{branch}/{encoded_file_name}.csv"
               result = pd.read_csv(file_path, header=None)
               
               #print(result.head(5))
               dm = result.to_dict(orient='records')
               
                 
               addresses = []  # Initialize the addresses list here
               
               stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
               csv_input = csv.DictReader(stream)
               
               idx = 0
               for row in csv_input:
                   # Assuming your CSV columns are named 'Latitude', 'Longitude', and 'Address'
                   #print(row)
                   latitude = row['\ufeffLatitude'].strip() 
                   longitude = row['Longitude'].strip()
                               
                   addresses.append({'index': idx, 'lat': latitude, 'lon': longitude})  # Add index to the dictionary
                   
                   idx += 1  # Increment the index counter
               addr=copy.deepcopy(addresses)     
               df = pd.DataFrame(addresses)
               num_rows=len(df)
               df = df.rename(columns={'lat': 'Latitude', 'lon': 'Longitude'})
               #print(df.head())
               uploaded_data =df[['Latitude','Longitude']]
               df = df[['Latitude','Longitude']]
               
               
               
               file.seek(0)
               dff = pd.read_csv(file)
               facilit = dff
               #print(facilit)
               facilit = facilit.to_json() 
               
               uploaded_data_json = uploaded_data.to_json()
               
               wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
               #print(wei.head(5))
               wei = wei.to_dict(orient='records')
               
               addresses = []
               origins = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
               for idx, (latitude, longitude) in enumerate(origins.values):
                   latitude_str = str(latitude).strip()
                   longitude_str = str(longitude).strip()
                   #idx=idx+num_rows
                   addresses.append({'index': idx, 'lat': latitude_str, 'lon': longitude_str})
                   #idx=idx-num_rows
               print(addresses)
               origins = origins.to_dict(orient='records')
               
               job = queue.enqueue(recommend_task4, selected_dropdown, P_FACILITIES, dm, uploaded_data_json, facilit, origins, wei, addresses, job_timeout=97200)
               return jsonify({"message": "Task queued!", "job_id": job.get_id(),"addr": addr}), 200
            else:
                    
                addresses = []
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                idx = 0
                for row in csv_input:
                    # Assuming your CSV columns are named 'Latitude', 'Longitude', and 'Address'
                    #print(row)
                    latitude = row['\ufeffLatitude'].strip() 
                    longitude = row['Longitude'].strip()
                                
                    addresses.append({'index': idx, 'lat': latitude, 'lon': longitude})  # Add index to the dictionary
                    
                    idx += 1  # Increment the index counter
                
                addr=copy.deepcopy(addresses)   
                df = pd.DataFrame(addresses)
                num_rows=len(df)
                df = df.rename(columns={'lat': 'Latitude', 'lon': 'Longitude'})
                #print(df.head())
                uploaded_data =df[['Latitude','Longitude']]
                df = df[['Latitude','Longitude']]
                
                
                file.seek(0)
                dff = pd.read_csv(file)
                facilit = dff
                #print(facilit)
                facilit = facilit.to_json() 
                
                uploaded_data_json = uploaded_data.to_json()
                        
                            
                
                res = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
                
                for idx, (latitude, longitude) in enumerate(res.values):
                    latitude_str = str(latitude).strip()
                    longitude_str = str(longitude).strip()
                    idx=idx+num_rows
                    addresses.append({'index': idx, 'lat': latitude_str, 'lon': longitude_str})
                    idx=idx-num_rows
                
               
                
                session['uploaded_data_json'] = uploaded_data_json
                session['facilit'] = facilit
                #session['addresses'] = addresses
                
                
                origins = locations[locations['Name'] == selected_dropdown][['Latitude', 'Longitude']].reset_index(drop=True)
                #print(origins.head(5))
                origins = origins.to_dict(orient='records')
               
                wei = locations[locations['Name'] == selected_dropdown][['Weights']].reset_index(drop=True)
                #print(wei.head(5))
                wei = wei.to_dict(orient='records')
                
                job = queue.enqueue(recommend_task3, selected_dropdown, uploaded_data_json, facilit, P_FACILITIES, origins, wei, addresses, job_timeout=97200)
                return jsonify({"message": "Task queued!", "job_id": job.get_id(),"addr": addr}), 200 # This is sent to HTML
            
        
@app.route('/download_example2')
def download_example2():

    # Send the example file for download
    return send_from_directory('static', 'examples/coordinates2.csv', as_attachment=True)    
    

@app.route('/task-status/<job_id>', methods=['GET'])
def get_task_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)  # Use the established Redis connection here.

        if job.is_failed:
            response = {"state": "failed", "message": str(job.exc_info)}
        elif job.is_finished:
            response = {"state": "finished", "result": job.result}
        else:
            response = {"state": job.get_status()}
    except NoSuchJobError:  # If the job doesn't exist, catch the exception.
        response = {"state": "unknown", "message": "Job not found"}

    return jsonify(response), 200

@app.route('/fetch-error/<job_id>', methods=['GET'])
def fetch_error(job_id):
    error_message = redis_conn.get(f"error_for_job_{job_id}").decode('utf-8') if redis_conn.get(f"error_for_job_{job_id}") else None
    return jsonify({'error_message': error_message})

@app.route('/result/<job_id>')
def result(job_id):
    
    #redis_conn = Redis()
    error_message = redis_conn.get(f"error_for_job_{job_id}")
    if error_message:
        return jsonify({"error": error_message}), 500
    
    result_data_json = redis_conn.get(f"result_data_for_job_{job_id}")
    if result_data_json is None:
        return "No results found", 404
    
    if result_data_json:
        
        result_data = json.loads(result_data_json)
        
        presult=result_data["presult"] 
        addresses2=result_data["addresses2"]
        nearest_origin_indexes = result_data["nearest_origin_indexes"]
        #print(addresses2)
        data = presult
        addresses2 = addresses2
    
        selected_radio = session.get('selected_radio')
        if selected_radio == 'option3':
            radius = 1000
        elif selected_radio =='option2':
            radius = 5000
        elif selected_radio == 'option1':
            radius = 20000
        print(radius)
        session.clear()
        # Your result displaying code here
        return render_template('result.html', data = data, addresses2=addresses2, radius=radius,nearest_origin_indexes=nearest_origin_indexes)
    else:
        return jsonify({"error": "No result or error found for the given job ID."}), 404
    
@app.route('/result2/<job_id>')
def result2(job_id):
    
    #redis_conn = Redis()
    error_message = redis_conn.get(f"error_for_job_{job_id}")
    if error_message:
        return jsonify({"error": error_message.decode('utf-8')}), 500
    
    result_data_json = redis_conn.get(f"result_data_for_job_{job_id}")
    if result_data_json is None:
        return "No results found", 404

    if result_data_json:
        
        result_data = json.loads(result_data_json)
        presult=result_data["presult"] 
        facil=result_data["facil"]
        addresses = result_data["addresses"]
        
        # This is used to identify explored locations
        nearest_origin_indexes = result_data["nearest_origin_indexes"]
        
        #addresses = session.get('addresses')
        addresses3 = []
        
        for address in addresses:
            #print(address['index'])
           # print(address)
            # Check if the index exists in facil
            if address['index'] in facil:
                # Avoid adding 'idx' to addresses3
                updated_address = address.copy()
                if 'idx' in updated_address:
                    del updated_address['idx']
                addresses3.append(updated_address)
        
        #print(addresses3)
        
        addresses2 = addresses3
        
        data = presult
        facil = facil
        
        selected_radio = session.get('selected_radio')
        if selected_radio == 'option3':
            radius = 1000
        elif selected_radio =='option2':
            radius = 5000
        elif selected_radio == 'option1':
            radius = 20000
        
        print(radius)
        session.clear()
        # Your result displaying code here
        return render_template('result2.html', data = data, addresses2=addresses2, radius=radius, nearest_origin_indexes=nearest_origin_indexes)
    
    else:
        return jsonify({"error": "No result or error found for the given job ID."}), 404
        
@app.route('/browser-closing', methods=['POST'])
def browser_closing():
  
    gc.collect()

    
    return "Cleanup done", 200

if __name__ == '__main__':
   
    app.run(host="0.0.0.0", port=8000)

