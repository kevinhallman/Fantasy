__author__ = 'hallmank'

from peewee import *
import os
import re
from datetime import date as Date
import time

db = PostgresqlDatabase('swimdb', user='hallmank')

class Swim(Model):
	name = CharField()
	event = CharField()
	date = DateField()
	time = FloatField()
	season = IntegerField()
	team = CharField()
	meet = CharField()
	gender = CharField()
	conference = CharField()
	division = CharField()
	relay = BooleanField()
	year = CharField()

	class Meta:
		database = db
		indexes = ('name', 'meet')

class Meet(Model):
	name = CharField()
	startDate = DateField()
	endDate = DateField()



def seasonString(dateString):
	dateParts = re.split('/', dateString)
	year = int(dateParts[2])
	month = int(dateParts[0])
	day = int(dateParts[1])
	date = Date(year, month, day)

	if date > Date(date.year, 6, 1):
		year = date.year + 1
	else:
		year = date.year
	return year, date

def toTime(time):
	if time[0]=="X" or time[0]=="x":
		time=time[1:]
	if re.match(".*:.*",time) == None:
		return float(time)
	return float(re.split(":",time)[0])*60 +float(re.split(":",time)[1])

def getConfs(confFile):
	with open(confFile,'r') as file:
		teams = {}
		for line in file:
			parts = re.split('\t', line.strip())
			division = parts[0]
			conf = parts[1]
			team = parts[2]
			if not team in teams:
				teams[team] = (conf, division)
	return teams

def load():
	#load the swims
	swims = []
	lineNum = 0
	root = './swimData'
	teams = getConfs('bin/conferences.txt')
	for swimFileName in os.listdir(root):
		if swimFileName[0]=='.' or '14' in swimFileName:
			continue  # don't use ref files
		with open(root + '/' + swimFileName) as swimFile:
			for line in swimFile:
				lineNum += 1
				#if lineNum > 300:
				#	break
				swimArray = re.split('\t', line)
				meet = swimArray[0].strip()
				d = swimArray[1]
				(season, swimDate) = seasonString(d)
				name = swimArray[2]
				year = swimArray[3]
				team = swimArray[4]
				gender = swimArray[5]
				event = swimArray[6]
				time = toTime(swimArray[7])
				if team in teams:
					conference = teams[team][0]
					division = teams[team][1]
				else:
					conference = ''
					division = ''
				if 'Relay' in event:
					relay = True
				else:
					relay = False

				if relay:
					name = team + ' Relay'

				newSwim = {'meet': meet, 'date': swimDate, 'season': season, 'name': name, 'year': year, 'team': team,
					   'gender': gender, 'event': event, 'time': time, 'conference': conference, 'division':
					division, 'relay': relay}

				try:
					swim = Swim.get(Swim.name==name, Swim.time<time+.01, Swim.time > time-.01, Swim.event==event,
								   Swim.date==swimDate)
					#print swim.name, swim.time, swim.event, swim.date
					#print name, time, event, swimDate
				except Swim.DoesNotExist:
					#print 'nope'
					swims.append(newSwim)

	#print swims

	db.connect()
	with db.transaction():
		Swim.insert_many(swims).execute()

if __name__ == '__main__':
	#db.get_indexes(Swim)
	#swims = {}

	start = time.time()
	load()
	#db.create_index(Swim, (Swim.meet, Swim.gender))
	#db.create_index(Swim, (Swim.gender, Swim.season, Swim.event, Swim.team, Swim.name, Swim.time))
	#events = ['100 Yard Freestyle', '200 Yard Freestyle']
	#for event in events:
	#	swims[event] = set()
	#for swim in Swim.select(Swim.name, Swim.event, fn.Min(Swim.time)).where(Swim.gender=='Women', Swim.season==2013,
	#										Swim.event << events).group_by(Swim.name, Swim.event):
	#	swims[swim.event].add(swim)
	#for swim in Swim.select().where(Swim.division==''):
	#	print swim.team, swim.conference, swim.name
	stop = time.time()
	#for event in swims:
	#	for swim in swims[event]:
	#		print swim.name, swim.min
	print stop - start
