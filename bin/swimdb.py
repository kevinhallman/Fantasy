from peewee import *
import os
import re
from datetime import date as Date
import time as Time
import urlparse
from playhouse.migrate import *


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

class TeamSeason(Model):
	#name = CharField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField(null=True)
	division = CharField()

	class Meta:
		database = db

class Swimmer(Model):
	name = CharField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	year = CharField()
	teamid = ForeignKeyField(TeamSeason, null=True)

	class Meta:
		database = db

class Swim(Model):
	swimmer = ForeignKeyField(Swimmer, null=True)
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
	place = None
	score = None
	scoreTeam = None
	scoreTime = None
	split = False

	def getScoreTeam(self):
		if self.scoreTeam:
			return self.scoreTeam
		if self.team:
			return self.team
		return ''

	def getScoreTime(self):
		if self.scoreTime:
			return	self.scoreTime
		return self.time

	def getScore(self):
		if self.score:
			return self.score
		return 0

	def printScore(self, br='\t', gender=True):
		time = swimTime(self.getScoreTime())
		if gender:
			genderStr = br + self.gender
		else:
			genderStr = ''
		if self.relay:
			name = 'Relay'
		else:
			name = self.name
		if self.meet:
			meet = str(self.meet)
		else:
			meet = ''
		return name+br+self.getScoreTeam()+genderStr+br+self.event+br+time+br+meet

	def __str__(self):
		return self.name+self.team+self.event+str(toTime(self.time))

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
	swimmer = ForeignKeyField(Swimmer, null=True)
	name = CharField()
	event = CharField()
	improvement = FloatField()
	fromtime = FloatField()
	totime = FloatField()
	fromseason = IntegerField()
	toseason = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField()
	division = CharField()
	fromyear = CharField()
	toyear = CharField()

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

#make time look nice
def swimTime(time):
	(seconds, point) = re.split("\.", str(time))
	if int(seconds) < 60:
		time = round(time, 2)
		time = str(time)
		while len(time) < 5:
			time += '0'
		return time
	minutes = str(int(seconds) / 60)
	seconds = str(int(seconds) % 60)
	while len(seconds) < 2:
		seconds = '0' + seconds
	while len(point) < 2:
		point = point + '0'
	return  minutes + ":" + seconds + "." + point[:2]

#turn time into seconds, round to two digits
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


'''
load in new swim times
can load in to all SQL tables if params are true
'''
def load(loadMeets=False, loadTeams=False, loadSwimmers=False, loadSwims=False, loadTeamMeets=False):
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
		div, year, gender = match.groups()

		#if not (int(year) == 16):  #and gender=='m'):
		#	continue
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

				if 'Relay' in event: relay = True
				else: relay = False

				if relay:
					name = team + ' Relay'

				#clear old values
				teamID = None
				meetID = None
				swimmerID = None

				if loadTeams:
					key = str(season) + team + gender + conference + division
					if not relay and not key in teamKeys:  # try each team once
						teamKeys.add(key)
						try:  # don't double add for teams not loaded yet
							teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
						except TeamSeason.DoesNotExist:
							newTeam = {'season': season, 'conference': conference, 'team': team, 'gender':
								gender, 'division': division}
							newTeams.append(newTeam)

				if loadMeets:
					key = str(season) + meet + gender
					if not relay and not key in meetKeys:
						meetKeys.add(key)  # try each meet once
						try:  # don't double add for meets not loaded yet
							meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						except Meet.DoesNotExist:
							newMeet = {'season': season, 'gender': gender, 'meet': meet, 'date': swimDate}
							meets.append(newMeet)

				if loadSwimmers:
					key = str(season) + name + year + team + gender
					if not relay and not key in swimmerKeys:
						swimmerKeys.add(key)
						try:
							swimmerID = Swimmer.get(Swimmer.season==season, Swimmer.name==name, Swimmer.team==team).id
						except Swimmer.DoesNotExist:
							if not teamID:
								teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
							newSwimmer = {'season': season, 'name': name, 'year': year, 'team': team, 'gender':
								gender, 'teamid': teamID}
							swimmers.append(newSwimmer)

				if loadTeamMeets:
					key = str(season) + meet + gender + team
					if not relay and not key in teamMeetKeys:
						teamMeetKeys.add(key)
						if not meetID:
							meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						if not teamID:
							teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
						try:
							teamMeetID = TeamMeet.get(TeamMeet.meet==meetID, TeamMeet.team==teamID).id
						except TeamMeet.DoesNotExist:
							newTeamMeet = {'meet': meetID, 'team': teamID}
							teamMeets.append(newTeamMeet)

				if loadSwims:
					try:
						Swim.get(Swim.name==event, Swim.time<time+.01, Swim.time > time-.01, Swim.event==event,
							Swim.date==swimDate)  # floats in SQL and python evidently different precision
					except Swim.DoesNotExist:
						if not swimmerID and not relay:
							swimmerID = Swimmer.get(Swimmer.season==season, Swimmer.name==name, Swimmer.team==team).id
						newSwim = {'meet': meet, 'date': swimDate, 'season': season, 'name': name, 'year': year, 'team': team,
					   		'gender': gender, 'event': event, 'time': time, 'conference': conference, 'division':
							division, 'relay': relay, 'swimmer': swimmerID}
						swims.append(newSwim)

	db.connect()
	if loadTeams and len(newTeams) > 0:
		print 'Teams:', len(newTeams)
		TeamSeason.insert_many(newTeams).execute()

	if loadMeets and len(meets) > 0:
		print 'Meets:', len(meets)
		Meet.insert_many(meets).execute()

	if loadSwimmers and len(swimmers) > 0:
		print 'Swimmers:', len(swimmers)
		Swimmer.insert_many(swimmers).execute()

	if loadTeamMeets and len(teamMeets) > 0:
		print 'Team Meets:', len(teamMeets)
		TeamMeet.insert_many(teamMeets).execute()

	if loadSwims and len(swims) > 0:
		print 'Swims: ', len(swims)
		Swim.insert_many(swims).execute()
	'''
	for i in range(len(newSwims) / 100):
		print i
		with db.transaction():
			print newSwims[i*100:(i+1)*100]
			Swim.insert_many(newSwims[i*100:(i+1)*100]).execute()
	'''

	''' cleanup for duplicate swims
	Swim.raw('DELETE FROM Swim WHERE id IN (SELECT id FROM (SELECT id, '
        'ROW_NUMBER() OVER (partition BY meet, name, event, time ORDER BY id) AS rnum '
        'FROM Swim) t '
        'WHERE t.rnum > 1)')
    '''
	#return divisions

def migrateImprovement():

	migrator = PostgresqlMigrator(db)
	with db.transaction():
		migrate(
			#migrator.add_column('improvement', 'swimmer_id', Improvement.swimmer)
			#migrator.add_column('swimmer', 'teamid_id', Swimmer.teamid)
			#migrator.add_column('swim', 'swimmer_id', Swim.swimmer)
		)
	count = 0
	'''
	for swimmer in Swimmer.select(Swimmer.name, Swimmer.season, Swimmer.team):
		try:

			team = TeamSeason.select().where(TeamSeason.team==swimmer.team, TeamSeason.season==swimmer.season).get()
			#print team.id, swimmer.name
			Swimmer.update(teamid=team.id).where(Swimmer.name==swimmer.name,
								Swimmer.season==swimmer.season).execute()
			count += 1
			if count %100==0:
				print count
		except Swimmer.DoesNotExist:
			pass
	'''
	for swim in Swim.select(Swim.name, Swim.season, Swim.team, Swim.relay, Swim.id).where(Swim.swimmer >> None):

		try:
			#print swim.team
			if swim.relay: continue
			swimmer = Swimmer.select().where(Swimmer.team==swim.team, Swimmer.season==swim.season,
										  Swimmer.name==swim.name).get()
			#print swimmer.id, swimmer.name, swim.id
			Swim.update(swimmer=swimmer.id).where(Swim.id==swim.id).execute()
			count += 1
			if count %100==0:
				print count
		except Swimmer.DoesNotExist:
			pass

def safeLoad():
	print 'loading teams...'
	load(loadTeams=True)
	print 'loading meets and swimmers...'
	load(loadMeets=True, loadSwimmers=True)
	print 'loading teamMeets and swims...'
	load(loadTeamMeets=True, loadSwims=True)

def addRelaySwimmers():
	'''
	relaySwimmers = []
	for swim in Swim.select(Swim.team, Swim.season, Swim.conference, Swim.gender).distinct().where(Swim.relay==True):
		try:
			teamID = TeamSeason.get(TeamSeason.season==swim.season, TeamSeason.team==swim.team,
										   TeamSeason.gender==swim.gender, TeamSeason.conference==swim.conference).id
		except TeamSeason.DoesNotExist:
			print swim.team
		relayName = swim.team + ' Relay'
		newSwim = {'season': swim.season, 'name': relayName, 'year': None, 'team': swim.team, 'gender': swim.gender,
				   'teamid': teamID}
		relaySwimmers.append(newSwim)
	print 'Swimmers: ' + str(len(relaySwimmers))
	Swimmer.insert_many(relaySwimmers).execute()
	'''
	#print relaySwimmers
	swimmers = {}
	i=0
	for swim in Swim.select(Swim.team, Swim.season, Swim.conference, Swim.gender, Swim.id).where(Swim.relay==True):
		i+=1
		if i%1000==0:
			print i
		key = swim.team + str(swim.season) + swim.gender
		if not key in swimmers:
			try:
				swimmerID = Swimmer.get(Swimmer.team==swim.team, Swimmer.season==swim.season,
									Swimmer.gender==swim.gender).id
				swimmers[key] = swimmerID
			except Swimmer.DoesNotExist:
				print swim.team, swim.season, swim.conference
				continue
		else:
			swimmerID = swimmers[key]

		Swim.update(swimmer=swimmerID).where(Swim.id==swim.id).execute()



if __name__ == '__main__':
	'''
	for teamMeet in TeamMeet.select(Meet, TeamMeet, TeamSeason).join(Meet).switch(TeamMeet).join(TeamSeason):
		print teamMeet.meet.meet, teamMeet.team.team, teamMeet.team.season, teamMeet.team.gender, \
			teamMeet.team.conference
	'''
	#db.get_indexes(Swim)
	#swims = {}

	#db.drop_tables([TeamSeason, Swimmer])
	#db.create_tables([TeamSeason, Swimmer])
	start = Time.time()
	#load(loadTeams)
	#safeLoad()
	#migrateImprovement()
	addRelaySwimmers()
	stop = Time.time()
	print stop - start
