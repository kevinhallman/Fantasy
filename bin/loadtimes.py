import time as Time
from swimdb import Swim, TeamMeet, TeamSeason, Swimmer, toTime, getConfs, Meet, seasonString, TeamStats
import re
import os
import urlparse
from peewee import *

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

def getNewConfs():
	confTeams = {}
	with open('data/newconferences.txt', 'r') as file:
		for line in file:
			parts = re.split('\t', line.strip())
			division = parts[0]
			gender = parts[1]
			year = '20' + parts[2]
			conf = parts[3]
			team = parts[4]
			if not division in confTeams:
				confTeams[division] = {}
			if not gender in confTeams[division]:
				confTeams[division][gender] = {}
			if not year in confTeams[division][gender]:
				confTeams[division][gender][year] = {}
			if not conf in confTeams[division][gender][year]:
				confTeams[division][gender][year][team] = conf
	return confTeams

'''
load in new swim times
can load in to all SQL tables if params are true
'''
def load(loadMeets=False, loadTeams=False, loadSwimmers=False, loadSwims=False, loadTeamMeets=False, loadyear=17):
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
		match = re.search('(\D+)(\d+)([mf])new', swimFileName)
		if not match:
			continue
		div, year, gender = match.groups()

		if not (int(year) == loadyear):
			continue
		if not 'new' in swimFileName:
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

				if not team in divisions:
					divisions[team] = division

				if team in teams:
					conference = teams[team][0]
				else:
					conference = ''


				if team == 'Connecticut':
					if division=='D1':
						conference = 'American Athletic Conf'
					else:
						conference = 'NESCAC'

				if 'Relay' in event: relay = True
				else: relay = False

				if relay:
					name = team + ' Relay'

				if loadTeams:
					key = str(season) + team + gender + conference + division
					if not key in teamKeys:  # try each team once
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
					if not key in meetKeys:
						meetKeys.add(key)  # try each meet once
						try:  # don't double add for meets not loaded yet
							meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						except Meet.DoesNotExist:
							newMeet = {'season': season, 'gender': gender, 'meet': meet, 'date': swimDate}
							meets.append(newMeet)

				if loadSwimmers:
					key = str(season) + name + year + team + gender
					if not key in swimmerKeys:
						swimmerKeys.add(key)
						try:
							swimmerID = Swimmer.get(Swimmer.season==season, Swimmer.name==name, Swimmer.team==team,
													Swimmer.gender==gender).id
						except Swimmer.DoesNotExist:
							teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
							newSwimmer = {'season': season, 'name': name, 'year': year, 'team': team, 'gender':
								gender, 'teamid': teamID}
							swimmers.append(newSwimmer)

				if loadTeamMeets:
					key = str(season) + meet + gender + team
					if not key in teamMeetKeys:
						teamMeetKeys.add(key)
						meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
						try:
							teamMeetID = TeamMeet.get(TeamMeet.meet==meetID, TeamMeet.team==teamID).id
						except TeamMeet.DoesNotExist:
							newTeamMeet = {'meet': meetID, 'team': teamID}
							teamMeets.append(newTeamMeet)

				if loadSwims:
					try:
						Swim.get(Swim.name==name, Swim.time<time+.01, Swim.time > time-.01, Swim.event==event,
							Swim.date==swimDate)  # floats in SQL and python different precision
					except Swim.DoesNotExist:
						swimmerID = Swimmer.get(Swimmer.season==season, Swimmer.name==name, Swimmer.team==team,
												Swimmer.gender==gender).id
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

def deleteDups():
	# cleanup for duplicate swims
	'''print Swim.raw('DELETE FROM Swim WHERE id IN (SELECT id FROM (SELECT id, '
        'ROW_NUMBER() OVER (partition BY meet, name, event, time, season ORDER BY id) AS rnum '
        'FROM Swim) t '
        'WHERE t.rnum > 1)').execute()'''

	print TeamStats.raw('DELETE FROM TeamStats WHERE id IN (SELECT id FROM (SELECT id, '
        'ROW_NUMBER() OVER (partition BY week, teamseasonid_id ORDER BY id) AS rnum '
        'FROM TeamStats) t '
        'WHERE t.rnum > 1)').execute()

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
	for swim in Swim.select(Swim.team, Swim.season, Swim.conference, Swim.gender, Swim.id).where(Swim.relay==True,
																		Swim.swimmer==None):
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

def mergeTeams(sourceTeamId, targetTeamId):
	sourceTeam = TeamSeason.get(id=sourceTeamId)
	targetTeam = TeamSeason.get(id=targetTeamId)

	# clear teamstats
	TeamStats.delete().where(TeamStats.teamseasonid==sourceTeam.id).execute()

	# find swimmers and update their info
	for swimmer in Swimmer.select().where(Swimmer.teamid==sourceTeam.id):
		swimmer.teamid = targetTeam.id
		swimmer.team = targetTeam.team
		swimmer.save()
		for swim in Swim.select().where(Swim.swimmer==swimmer.id):
			swim.division = targetTeam.division
			swim.conference = targetTeam.conference
			swim.team = targetTeam.team
			swim.season = targetTeam.season
			swim.save()

	# now switch the meet linking table
	for teammeet in TeamMeet.select().where(TeamMeet.team==sourceTeam.id):
		teammeet.team = targetTeam.id
		teammeet.save()

	TeamSeason.delete().where(TeamSeason.id==sourceTeamId).execute()

def mergeSwimmers(sourceSwimmerId, targetSwimmerId):
	sourceSwimmer = Swimmer.get(id=sourceSwimmerId)
	targetSwimmer = Swimmer.get(id=targetSwimmerId)
	targetTeam = TeamSeason.get(id=targetSwimmer.teamid)
	print targetTeam.team
	for swim in Swim.select().where(Swim.swimmer==sourceSwimmer):
		print swim.id
		swim.team = targetTeam.team
		swim.division = targetTeam.division
		swim.conference = targetTeam.conference
		swim.season = targetTeam.season
		swim.swimmer = targetSwimmer
		swim.save()

	Swimmer.delete().where(Swimmer.id==sourceSwimmerId).execute()

def fixRelays():
	'''
	count = 0
	for swim in Swim.select(Swim.name, Swim.id, Swim.relay, Swimmer.name, Swimmer.teamid, TeamSeason.team,
							TeamSeason.season, TeamSeason.team, TeamSeason.gender).join(
			Swimmer).join(TeamSeason).where(~Swimmer.name.endswith('Relay'), Swim.relay==True):
		print swim.id, swim.swimmer.name, swim.name, swim.swimmer.teamid.team, swim.swimmer.teamid.id
		try:
			relay = Swimmer.get(Swimmer.teamid==swim.swimmer.teamid.id, Swimmer.name.endswith('Relay'))
			if relay.name != swim.name:
				continue
			swim.swimmer = relay.id
			swim.save()
		except Swimmer.DoesNotExist:
			team = swim.swimmer.teamid
			name = team.team + ' Relay'
			relay = Swimmer.create(teamid=team.id, gender=team.gender, season=team.season, team=team.team, name=name)
			if relay.name != swim.name:
				continue
			swim.swimmer = relay.id
			swim.save()

		count +=1
		if count%1000==0: print count
	print count
	'''
	count=0
	for swim in Swim.select().join(Swimmer).where(Swimmer.gender=='Men', Swim.gender=='Women'):
		count += 1
		try:
			newswimmer = Swimmer.get(Swimmer.season==swim.season, Swimmer.name==swim.name, Swimmer.team==swim.team,
							  Swimmer.gender==swim.gender)
			swim.swimmer = newswimmer.id
			swim.save()
		except Swimmer.DoesNotExist:
			try:
				team = TeamSeason.get(TeamSeason.season==swim.season, TeamSeason.gender==swim.gender,
							   TeamSeason.team==swim.team)
				n=Swimmer.create(teamid=team.id, gender=team.gender, season=team.season, team=team.team, name=swim.name)
				swim.swimmer = n.id
				swim.save()
			except TeamSeason.DoesNotExist:
				print swim.event, swim.name, swim.team, swim.season, swim.gender

	print count

def fixConfs():
	newConfs = getNewConfs()
	for team in TeamSeason.select().where(TeamSeason.season>2010):
		try:
			conf = newConfs[team.division][team.gender][str(team.season)][team.team]
			if conf != team.conference:
				print 'nope', team.id, team.team, team.conference, conf
				team.conference = conf
				team.save()
		except:
			pass
			#print 'huh', team.id, team.team, team.division, team.gender, team.season

def fixDupTeams():
	confTeams = getNewConfs()

	for team in TeamSeason.raw('SELECT id, team, conference, gender, division, season FROM '
							'(SELECT id, gender, team, division, conference, season, ROW_NUMBER() '
	 						'OVER (partition BY season, gender, team, division ORDER BY id) '
							'AS rnum FROM teamseason) t WHERE t.rnum > 1'):
		print team.id, team.team, team.conference, team.division
		try:
			conf = confTeams[team.division][team.gender][str(team.season)][team.team]
			print conf
			if not team.conference:
				newTeam = TeamSeason.get(team=team.team, conference=conf, division=team.division,
							   gender=team.gender, season=team.season)
				if newTeam.id!=team.id:
					mergeTeams(team.id, newTeam.id)

		except KeyError:
			pass

def fixDivision():
	for swim in Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason).where(Swim.division=='D1',
																	TeamSeason.division=='D3'):
		try:
			newTeam = TeamSeason.get(team=swim.team, division=swim.division, season=swim.season, gender=swim.gender)
			if newTeam.id != swim.swimmer.teamid.id:
				print newTeam.team, newTeam.division, newTeam.season
			newSwimmer = Swimmer(name=swim.name, teamid=newTeam.id)
			print newSwimmer.name
			swim.swimmer = newSwimmer.id
			swim.save()
		except TeamSeason.DoesNotExist:
			pass

if __name__ == '__main__':
	start = Time.time()
	fixDivision()
	fixDupTeams()
	#mergeSwimmers(294608, 285526)
	#mergeSwimmers(293514, 280998)
	#mergeTeams(8533, 8377)
	#mergeTeams(8545, 8239)
	#mergeTeams(7625, 8435)
	#mergeTeams(6785, 8453)
	#fixRelays()
	#safeLoad()
	# fixConfs()
	# deleteDups()
	# migrateImprovement()
	# addRelaySwimmers()
	stop = Time.time()
	print stop - start
		#print swim.team

# select from Swimmer,Swim where Swim.swimmer_id=Swimmer.id and Swim.relay='t' and Swimmer.name not like '%Relay'