# swimulator application

A web.py application to display swimming analysis and simulations.

swiddb is the associated postgres database
bin/appsql.py is the web application. Run via python bin/appsql.py
bin/clubdb.py, swimdb.py, and sqlmeets.py contain the data models and analysis
bin/loadtimes.py loads new times into the database
/templates contains the html templates

data folder contains swimming data to be loaded in bia loadtimes.py, worlddb.py, and clubbd.py corresponding to college meets, international meets, and USA club meets respectively

Instructions to run app after downloading repo:
1. Create a local database named swimdb 
2. cd to pyweb/scripts and run "./db_build.sh"  This will load in the tables and indexes without data
3. Change the  db username is explicitly referenced and needs to be changed: swimdb.py, loadtimes.py, fantasy.py to whatever user you ran the .sh with
example: db = PostgresqlDatabase('swimdb', user='hallmank')

4. You will want to maybe load in some data. From the root folder, run:
python bin/staging_collegeScraper.py   --this will load times from USAswimming into the staging table
python bin/loadtimes.py --load 2019    --this loads in all the 2019 times from the staging table to the database
Feel free to re-run every week or so to get new times. It will automatically check and delete duplicate times.
5. from the root folder, run bin/appfan.py

-----Fantasy Swimming-----
bin/appfan.py  -- main web app, run from root with python bin/appfan.py
bin/fantasy.py -- db definitions for fantasy swimming

TODOs for fantasy:
1. modify the joinleague page to allow for creating a new league
2. Create a page to set a team's lineup and database tables to store that lineup (maybe I did the db tables already?)
3. Make code to set competition for a fantasy season