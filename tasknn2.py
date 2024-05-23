# -*- coding: utf-8 -*-
"""
Created on Tue Aug 15 11:16:04 2023

@author: vpp
"""

from flask import Flask, render_template, session, redirect, url_for, session, request, jsonify
#from flask_sqlalchemy import SQLAlchemy
#from sqlalchemy import text
#from sqlalchemy import create_engine

import os
import pandas as pd
import numpy as np
import pulp
from spopt.locate import PMedian
# redis cloud loading
from dotenv import load_dotenv
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import time
import io
import csv
import datetime;
import redis
import json
from flask_rq2 import RQ
from rq import Queue
from redis import Redis
from rq import get_current_job
from worker3 import haversine
from io import StringIO

# Load environment variables from .env file
#load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_SSL = os.getenv('REDIS_SSL', 'False') == 'True'

redis_conn = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, ssl=REDIS_SSL)

def pfac_task2(selected_dropdown, P_FACILITIES, uploaded_data_json, facilit,  dm, origins, wei, addresses):
    
    job = get_current_job()
    job_id = job.id
    
    try:
            
        # Retrieve the stored data from session
        selected_option = selected_dropdown
        
        origins = pd.DataFrame(origins)
        
        # Access the uploaded data from the session variable
        #uploaded_json_data = session.get('uploaded_data')
        destinations = pd.read_json(StringIO(uploaded_data_json))
        print(type(destinations))
        print(destinations)
        
        if isinstance(destinations, str):
            destinations = pd.DataFrame(json.loads(destinations))
        
        facilit = pd.read_json(StringIO(facilit))
        if isinstance(facilit, str):
            facilit = pd.DataFrame(json.loads(facilit))
        
        nearest_origin_indexes = facilit[facilit['facility'] == 1].index.tolist()
        print(nearest_origin_indexes)
        
        facilit = facilit["facility"]
        #print(facilit)
        
        # Count the occurrences of each value
        value_counts = facilit.value_counts()
        
        # Get the count for the value 1
        count_of_ones = value_counts.get(1, 0)
        print(count_of_ones)
        
        facility = facilit.to_numpy()
        
        P_FACILITIES = P_FACILITIES+count_of_ones
        print(P_FACILITIES)
            
        weights = pd.DataFrame(wei)
        
        weights = weights.to_numpy()
        
        
        # Measure the start time
        start_time = time.time()
        # ct stores current time
        st = datetime.datetime.now()
        print("start time:-", st)
       
        
        nearest_origins = []
        
        # Selecting nearest indexes and pushing value 1 to facility
        for _, dest_row in destinations.iterrows():
            min_distance = float('inf')
            nearest_origin_index = None
            nearest_origin_coords = None
        
            for idx, orig_row in origins.iterrows():
                dist = haversine(dest_row['Latitude'], dest_row['Longitude'], orig_row['Latitude'], orig_row['Longitude'])
                if dist < min_distance:
                    min_distance = dist
                    nearest_origin_index = idx
                    nearest_origin_coords = (orig_row['Latitude'], orig_row['Longitude'])
        
            nearest_origins.append((nearest_origin_index, nearest_origin_coords))
        
        print(nearest_origins)
        print(type(nearest_origins))
        
        # Create GeoDataFrames
        origins_gdf = gpd.GeoDataFrame(origins, geometry=gpd.points_from_xy(origins.Longitude, origins.Latitude))
        destinations_gdf = gpd.GeoDataFrame(destinations, geometry=gpd.points_from_xy(destinations.Longitude, destinations.Latitude))
        
        
        # Initialize a matrix to store the results
        distance_matrix = np.zeros((len(origins_gdf), len(destinations_gdf)))
        
       
        
        #od_matrix = np.zeros((len(origins_gdf), len(destinations_gdf)))
        od_matrix = pd.DataFrame(distance_matrix)
        # Convert the matrix to a DataFrame for easier viewing and manipulation
        #od_matrix = distance_matrix
        
        
        # Measure the end time
        end_time = time.time()
        # ct stores current time
        et = datetime.datetime.now()
        print("end time:-", et)
        
        # Calculate the time it took
        total_time = end_time - start_time
        
        
        # Estimate the total time
        total_pairs = len(origins_gdf) * len(destinations_gdf)
        estimated_total_time = total_pairs * total_time
        
        #single_pair = total_time/total_pairs
        
        print(f"Total time: {total_time} seconds")
        
        
    #    print(f"Single pair time: {single_pair} seconds")
       
       
    # Print the OD matrix DataFrame
        #print(od_matrix)
        distance_matrix = pd.DataFrame(dm)
        
        distance_matrix[distance_matrix == 0] = 100000
        distance_matrix = distance_matrix.round(decimals = 0)
        
        od_matrix = distance_matrix
        
        od_matrix = od_matrix.to_numpy()
        
        cotwo=0.15
        cm=od_matrix*cotwo
        
        # Extract columns based on indices in nearest_origins
        indices = [i[0] for i in nearest_origins]
        
        
        
        
        
        cost_matrix = cm[:, indices]
        print(f"This is the Cost Matrix: {cost_matrix}")
    
        # Initiating PMedian
        pmedian_from_cm = PMedian.from_cost_matrix(
        cost_matrix,
        weights,
        p_facilities=P_FACILITIES,
        predefined_facilities_arr = facility,
        name="p-median-network-distance"
        )
            
        pmedian = pmedian_from_cm.solve(pulp.PULP_CBC_CMD(msg=False))
            
        # Printing results
        pmp_obj = round(pmedian.problem.objective.value(), 2)
        dis_obj=pmp_obj/cotwo
        dis_obj=round(dis_obj,2)
        pmp_mean = round(pmedian.mean_dist, 2)
        dis_mean = pmp_mean/cotwo
        dis_mean=round(dis_mean,2)
        print(pmp_mean)
        
        facility_list =str(f"Please find your results below <br>")
        
        facility_list += str(f"A total minimized weighted CO2 emissions of {pmp_obj} Kg was observed.  <br>")
        facility_list += str(f"A total minimized weighted distance of {dis_obj} Km was observed.  <br>")
        facility_list += str(f"A mean kg/km CO2 emissions of {pmp_mean} was observed <br>")
        facility_list += str(f"A mean distance of {dis_mean} km was observed  <br>")
        
        
        total_size = 0
        for fac,cli in enumerate(pmedian.fac2cli):
            total_size += len(cli)
    
        print(total_size)
        
        faci=1
        facil = []
        for fac, cli in enumerate(pmedian.fac2cli):
            
            if len(cli) != 0:
                per = (len(cli)/total_size) * 100
                per = round(per,2)
                facility_list += str(f"facility {fac} serving {per}% of customers; <br>")
                facil.append(fac)
                faci=faci+1
                continue
            faci=faci+1
            
    
        print (facil)
        #session['presult'] = facility_list
        presult = facility_list
        
        
        
        addresses3 = []
    
        # Iterate over the indices of addresses
        for idx, address in enumerate(addresses):
            
            # Check if the index exists in facil
            if idx in facil:
                print(idx)
                # Modify the address dictionary to include the idx value
                address["idx"] = idx
                addresses3.append(address)
                
        addresses2=addresses3
        #session['addresses2']=addresses2
        print(addresses2)
        
        # Once your results are ready:
        result_data = {
           "presult": presult,
           "addresses2": addresses2,
           "facil": facil,
           "nearest_origin_indexes": nearest_origin_indexes,
           # ... other data ...
        }
           
        job = get_current_job()
        job_id = job.id
        
        redis_conn.set(f"result_data_for_job_{job_id}", json.dumps(result_data))
    
        #return render_template('pfac.html')
        
        return "Task complete"
    except RuntimeError as e:
        error_message = str("Runtime Error: Please check your input")
        print("This is an run e***************************")
        print(error_message)
        redis_conn.set(f"error_for_job_{job_id}", error_message)
        return "Task failed"

    except Exception as e:
        error_message = f"Unexpected error: There is an exception raised. {str(e)}"
        print("This is an exception***************************")
        redis_conn.set(f"error_for_job_{job_id}", error_message)
        return "Task failed"