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

class Improvement(Model):
	name = CharField()
	event = CharField()
	improvement = FloatField()
	fromTime = FloatField()
	toTime = FloatField()
	fromSeason = IntegerField()
	toSeason = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField()
	division = CharField()
	fromYear = CharField()
	toYear = CharField()

	class Meta:
		database = db

class Swimmer(Model):
	name = CharField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	year = CharField()

	class Meta:
		database = db

class TeamSeason(Model):
	#name = CharField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField(null=True)
	division = CharField()

	class Meta:
		database = db

class Meet(Model):
	season = IntegerField()
	meet = CharField()
	gender = CharField()
	date = DateField()

	class Meta:
		database = db

class TeamMeet(Model):
	team = ForeignKeyField(TeamSeason)
	meet = ForeignKeyField(Meet)

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
	num = float(re.split(":",time)[0])*60 +float(re.split(":",time)[1])
	return int(num) + round(num%1, 2)  # round to two decimals

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
	swimmers = []
	swimmerKeys = set()
	newTeams = []
	teamKeys = set()
	meets = []
	meetKeys = set()
	teamMeets = []
	teamMeetKeys = set()
	root = 'data'

	teams = getConfs('data/conferences.txt')
	divisions = {}
	for swimFileName in os.listdir(root):
		match = re.search('(\D+)(\d+)([mf])', swimFileName)
		if not match:
			continue
		#print match.groups()
		div, year, gender = match.groups()

		if not (int(year) == 16):  #and gender=='m'):
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


				try:
					swim = Swim.get(Swim.name==name, Swim.time<time+.01, Swim.time > time-.01, Swim.event==event,
								   Swim.date==swimDate)
					#print swim.name, swim.time, swim.event, swim.date
					#print name, time, event, swimDate
				except Swim.DoesNotExist:
					#print newSwim
					swims.append(newSwim)

				'''
				key = str(season) + name + year + team + gender
				if not relay and not key in swimmerKeys:
					newSwimmer = {'season': season, 'name': name, 'year': year, 'team': team, 'gender': gender}
					swimmers.append(newSwimmer)
					swimmerKeys.add(key)
				'''
				'''
				key = str(season) + team + gender + conference + division
				if not relay and not key in teamKeys:
					newTeam = {'season': season, 'conference': conference, 'team': team, 'gender':
						gender, 'division': division}
					newTeams.append(newTeam)
					teamKeys.add(key)
				'''
				'''
				key = str(season) + meet + gender + str(swimDate)
				if not relay and not key in meetKeys:
					newMeet = {'season': season, 'gender': gender, 'meet': meet, 'date': swimDate}
					meets.append(newMeet)
					meetKeys.add(key)
				'''
				'''
				key = str(season) + meet + gender + team

				if not relay and not key in teamMeetKeys:
					newTeamMeet = {'season': season, 'gender': gender, 'meet': meet, 'team': team}
					teamMeets.append(newTeamMeet)
					teamMeetKeys.add(key)
				'''

	#print len(teamMeets)
	#for meet in teamMeets:
	#	print meet

	#db.connect()
	#Meet.insert_many(meets).execute()
	db.connect()
	#print len(swims)
	#print Swim.insert_many(swims).execute()
	'''
	for i in range(len(newSwims) / 100):
		print i
		with db.transaction():
			print newSwims[i*100:(i+1)*100]
			Swim.insert_many(newSwims[i*100:(i+1)*100]).execute()
	'''

	'''
	Swim.raw('DELETE FROM Swim WHERE id IN (SELECT id FROM (SELECT id, '
        'ROW_NUMBER() OVER (partition BY meet, name, event, time ORDER BY id) AS rnum '
        'FROM Swim) t '
        'WHERE t.rnum > 1)')
    '''
	#return divisions



if __name__ == '__main__':
	#db.get_indexes(Swim)
	#swims = {}

	#db.drop_tables([TeamSeason])
	#db.create_tables([TeamMeet])
	start = time.time()
	load()
	stop = time.time()
	print stop - start
