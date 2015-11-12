__author__ = 'hallmank'

from peewee import *
import os
import re
from datetime import date as Date
import time
import urlparse

urlparse.uses_netloc.append("postgres")
if "DATABASE_URL" in os.environ:  # production
	url = urlparse.urlparse(os.environ["DATABASE_URL"])
	db = PostgresqlDatabase(database=url.path[1:],
    	user=url.username,
    	password=url.password,
    	host=url.hostname,
    	port=url.port)
else:
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

class HSSwim(Model):
	name = CharField()
	event = CharField()
	time = FloatField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	year = CharField()

	class Meta:
		database = db

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

def loadHS():
	file = 'data/HStimesMen827.txt'

	#swimmers = Swim.where(Swim.)

	with open(file) as swimFile:
		swims = []
		for line in swimFile:
			parts = line.split('|')
			print parts
			(team, name, year, event, time, gender) = (parts[0].strip(), parts[1], int(parts[2]), parts[3], parts[4],
													   parts[5].strip())
			time = toTime(time)
			newSwim = {'season': year, 'name': name, 'team': team, 'year': 'HS',
					   'gender': gender, 'event': event, 'time': time}
			swims.append(newSwim)

	print swims

	db.connect()
	with db.transaction():
		HSSwim.insert_many(swims).execute()

def normalizeTeams():
	teamMap = {}
	for swimTeam in Swim.select(Swim.team).distinct():
		teamMap[swimTeam.team] = []
		print len(teamMap)
		for swimmer in Swim.select(Swim.name).where(swimTeam.team==Swim.team).distinct():
			#print swimmer.name
			for swim in HSSwim.select(HSSwim.team, fn.MIN(HSSwim.time)).where(HSSwim.name==swimmer.name).group_by(
					HSSwim.team):
				teamMap[swimTeam.team].append(swim.team)
	teamMap2 = {}
	for team in teamMap:
		if len(teamMap[team]) > 2:
			teamMap2[max(set(teamMap[team]), key=teamMap[team].count)] = team
	print teamMap2

	for team in teamMap2:
		q = HSSwim.update(team=teamMap2[team]).where(HSSwim.team==team)
		print q.execute()

def load():
	#load the swims
	swims = []
	root = 'data'
	teams = getConfs('data/conferences.txt')
	divisions = {}
	for swimFileName in os.listdir(root):
		match = re.search('(\D+)(\d+)([mf])', swimFileName)
		if not match:
			continue
		#print match.groups()
		div, year, gender = match.groups()

		if not int(year) == 16:
			continue
		with open(root + '/' + swimFileName) as swimFile:
			if div == 'DI':
				division = 'D1'
			elif div == 'DII':
				division = 'D2'
			elif div == 'DIII':
				division = 'D3'
			print division, swimFileName

			for line in swimFile:
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

				if swimDate < Date(2015, 2, 15):
					continue

				if not team in divisions:
					divisions[team] = division

				if team in teams:
					conference = teams[team][0]
				else:
					conference = ''


				if team=='Connecticut':
					if division=='D1':
						conference = 'American Athletic Conf'
					else:
						conference = 'NESCAC'
				

				if 'Relay' in event:
					relay = True
				else:
					relay = False

				if relay:
					name = team + ' Relay'

				newSwim = {'meet': meet, 'date': swimDate, 'season': season, 'name': name, 'year': year, 'team': team,
					   'gender': gender, 'event': event, 'time': time, 'conference': conference, 'division':
					division, 'relay': relay}
				swims.append(newSwim)
				'''try:
					swim = Swim.get(Swim.name==name, Swim.time<time+.01, Swim.time > time-.01, Swim.event==event,
								   Swim.date==swimDate)
					print swim.name, swim.time, swim.event, swim.date
					print name, time, event, swimDate
				except Swim.DoesNotExist:
					#print 'nope'
					swims.append(newSwim)'''

	print len(swims)

	db.connect()
	with db.transaction():
		Swim.insert_many(swims).execute()

	#return divisions

'''
for new, old in [("50 Yard Freestyle", '50 Freestyle'), ("100 Yard Freestyle", '100 Freestyle'), ("200 Yard "
																									  "Freestyle",
																									  '200 Freestyle'),
					 ("500 Yard Freestyle", '500 Freestyle'), ("1000 Yard Freestyle", '1000 Freestyle'), ("1650 Yard "
																										  "Freestyle", '1650 Freestyle'), ("100 Yard Butterfly", '100 Butterfly'), ("200 Yard Butterfly", '200 Butterfly'), ("100 Yard Backstroke", '100 Backstroke'), ("200 Yard Backstroke", '200 Backstroke'), ("100 Yard Breastroke", '100 Breastroke'), ("200 Yard Breastroke", '200 Breastroke'), ("200 Yard Individual Medley", '200 IM'), ("400 Yard Individual Medley", '400 IM'), ("200 Yard Medley Relay", '200 Medley Relay'), ("400 Yard Medley Relay", '400 Medley Relay'), ("200 Yard Freestyle Relay", '200 Freestyle Relay'), ("400 Yard Freestyle Relay", '400 Freestyle Relay'), ("800 Yard Freestyle Relay",'800 Freestyle Relay')]:
'''

if __name__ == '__main__':
	#db.get_indexes(Swim)
	#swims = {}
	#db.drop_tables([HSSwim])
	#db.create_tables([HSSwim])
	start = time.time()
	#for swim in HSSwim.select():
	#	print swim
	#for team in HSSwim.select(HSSwim.team).where(HSSwim.team=='Carleton'):
	#	print team.team
	#q = HSSwim.update(team='Carleton').where(HSSwim.team=='Carleton College')
	#print q.execute()
	load()
	#for swim in Swim.select().where(Swim.name=='St. Thomas Relay', Swim.season==2016):
	#	print swim.name, swim.date, swim.event, swim.time
	#normalizeTeams()
	#divisions = load()
	#db.connect()
	#for team in divisions:
	#	q = Swim.update(division=divisions[team]).where(Swim.team==team, Swim.division=='')
	#	print team, q.execute()
	stop = time.time()
	print stop - start

#dq = Swim.delete().where(Swim.team=='Connecticut')
