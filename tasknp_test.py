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
from multiprocessing import Pool, cpu_count
from worker import calculate_path
from io import StringIO

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_SSL = os.getenv('REDIS_SSL', 'False') == 'True'

redis_conn = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, ssl=REDIS_SSL)


def recommend_task(selected_dropdown, P_FACILITIES, origins, wei, addresses):
    
    job = get_current_job()
    job_id = job.id
    
    try:
        
            
        # Retrieve the stored data from session
        selected_option = selected_dropdown
        print(selected_dropdown)
        
        P_FACILITIES = P_FACILITIES
        
        origins = pd.DataFrame(origins)
        
        destinations = origins
        
        weights = pd.DataFrame(wei)
        
        weights = weights.to_numpy()
        
        #G = nx.from_dict_of_dicts(G_d["G"], create_using=nx.MultiDiGraph())
        # Load the road network graph
        #G = ox.io.load_graphml('sweden_road_network.graphml')
        #G = ox.io.load_graphml('Borlänge_road_network.graphml')
        #G = ox.io.load_graphml(f'{selected_option}.graphml')
        G = ox.graph_from_place(selected_option, network_type='drive')
        
        
        # Measure the start time
        start_time = time.time()
        # ct stores current time
        st = datetime.datetime.now()
        print("start time:-", st)
       
        # Create GeoDataFrames
    
        origins_gdf = gpd.GeoDataFrame(origins, geometry=gpd.points_from_xy(origins.Longitude, origins.Latitude))
        destinations_gdf = gpd.GeoDataFrame(destinations, geometry=gpd.points_from_xy(destinations.Longitude, destinations.Latitude))
        """  
        distance_matrix = np.zeros((len(origins_gdf), len(destinations_gdf)))
        
        # For each pair of origin and destination, find the shortest path
        for i in range(len(origins_gdf)):
            for j in range(len(destinations_gdf)):
                orig_point = origins_gdf.iloc[i].geometry
                dest_point = destinations_gdf.iloc[j].geometry
        
                # Get the nearest nodes to the points
                orig_node = ox.distance.nearest_nodes(G, orig_point.x, orig_point.y)
                dest_node = ox.distance.nearest_nodes(G, dest_point.x, dest_point.y)
        
                # Calculate the shortest path length
                try:
                    path_length = nx.shortest_path_length(G, orig_node, dest_node, weight='length')
                    print(path_length)
                except nx.NetworkXNoPath:
                    print(f"No path found between ")
                    path_length = 10000
        
                # Store the result in the matrix
                distance_matrix[i, j] = path_length
        """ 
        distance_matrix = np.zeros((len(origins_gdf), len(destinations_gdf)))
    
        for i in range(len(origins_gdf)):
            for j in range(len(destinations_gdf)):
                orig_point = origins_gdf.iloc[i].geometry
                dest_point = destinations_gdf.iloc[j].geometry
        
                weight = 'length'
        
                # Get the nearest nodes to the points
                orig_node = ox.distance.nearest_nodes(G, orig_point.x, orig_point.y)
                dest_node = ox.distance.nearest_nodes(G, dest_point.x, dest_point.y)
        
                try:
                    # Get the shortest path using OSMnx
                    path = ox.distance.shortest_path(G, orig_node, dest_node, weight=weight, cpus=2)  # Removed cpus argument
                    
                    # Calculate the path length based on the edges in the path
                    path_edges = list(zip(path[:-1], path[1:]))
                    path_length = sum([G[u][v][0][weight] for u, v in path_edges])
                    #print(path_length)
                except nx.NetworkXNoPath:
                    print(f"No path found for origin {i} and destination {j}")
                    path_length = 10000
                except Exception as e:  # A general exception to catch other unexpected issues
                    print(f"Error for origin {i} and destination {j}: {e}")
                    path_length = 10000
        
                distance_matrix[i, j] = path_length
    
         
          
        distance_matrix[distance_matrix == 0] = 100000
        distance_matrix = distance_matrix.round(decimals = 0)
        od_matrix = pd.DataFrame(distance_matrix)
        # Convert the matrix to a DataFrame for easier viewing and manipulation
        #od_matrix = distance_matrix
        
        print(f"This is the OD Matrix: {od_matrix}")
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
        
        od_matrix = od_matrix.to_numpy()
        od_matrix=od_matrix/1000
        #np.fill_diagonal(od_matrix, 10000)
        cotwo=0.15
        cost_matrix=od_matrix*cotwo
        
        
        
        # Initiating PMedian
        pmedian_from_cm = PMedian.from_cost_matrix(
        cost_matrix,
        weights,
        p_facilities=P_FACILITIES,
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
        
       
                
        nearest_origin_indexes = []
        #session['addresses2']=addresses2
        #print(addresses2)
        
        # Once your results are ready:
        result_data = {
           "presult": presult,
           "addresses": addresses,
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
 
 