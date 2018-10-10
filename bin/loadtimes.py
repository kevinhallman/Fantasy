import time as Time
from swimdb import Swim, TeamMeet, TeamSeason, Swimmer, toTime, Meet, seasonString, TeamStats, Improvement
from sqlmeets import update_weekly_stats
import re
import os
import urlparse
import peewee
import argparse
from events import badEventMap, eventConvert

urlparse.uses_netloc.append("postgres")
if "DATABASE_URL" in os.environ:  # production
	url = urlparse.urlparse(os.environ["DATABASE_URL"])
	db = peewee.PostgresqlDatabase(database=url.path[1:],
    	user=url.username,
    	password=url.password,
    	host=url.hostname,
    	port=url.port)
else:
	db = peewee.PostgresqlDatabase('swimdb', user='hallmank')

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
def load(loadMeets=False, loadTeams=False, loadSwimmers=False, loadSwims=False, loadTeamMeets=False, loadyear=2015,
		 type='new'):
	swims = []
	swimmers = []
	swimmerKeys = set()
	newTeams = []
	teamKeys = set()
	meets = []
	meetKeys = set()
	teamMeets = []
	teamMeetKeys = set()
	swimKeys = set()
	root = 'data/ncaa/' + str(loadyear)
	#root = 'data/hs'

	for swimFileName in os.listdir(root):
		print swimFileName, type
		if type == 'reload':
			match = re.search('(\D+)(\d+)([mf])', swimFileName)
		elif type == 'best':
			match = re.search('(\D+)(\d+)([mf])best', swimFileName)
		elif type=='new':
			match = re.search('(\D+)(\d+)([mf])new', swimFileName)

		if not match:
			continue
		print 'match'
		div, fileyear, gender = match.groups()
		print fileyear, loadyear
		if not (int(fileyear) == int(loadyear)) - 2000:
			continue

		confTeams = getNewConfs()

		with open(root + '/' + swimFileName) as swimFile:
			if div == 'DI':
				division = 'D1'
			elif div == 'DII':
				division = 'D2'
			elif div == 'DIII':
				division = 'D3'

			for idx, line in enumerate(swimFile):
				swimArray = re.split('\t', line)
				if len(swimArray) > 8:
					continue
				meet = swimArray[0].strip()
				d = swimArray[1]
				(season, swimDate) = seasonString(d)
				name = swimArray[2]
				year = swimArray[3]
				team = swimArray[4]
				gender = swimArray[5]
				event = swimArray[6]
				time = toTime(swimArray[7])

				# data validation
				if name == '&nbsp;' or team=='&nbsp;':  # junk data
					continue

				# convert bad event names
				if event in badEventMap:
					event = badEventMap[event]
				convert = dict([[v, k] for k,v in eventConvert.items()])
				convert['50 Yard Medley Relay'] = '200 Medley Relay'
				convert['50 Yard Freestyle Relay'] = '200 Free Relay'
				if event in convert:
					event = convert[event]
				if 'Yard' in event:
					print event
					print 'yard'
					continue

				if season and swimDate and name and team and gender and event and time:
					pass
				else:  # missing some information
					print season, swimDate, name, year, team, gender, event, time
					continue

				try:
					conference = confTeams[division][gender][str(season)][team]
				except KeyError:
					try:
						# try last year if not found yet
						conference = confTeams[division][gender][str(season - 1)][team]
					except KeyError:
						conference = ''

				if 'Relay' in event: relay = True
				else: relay = False

				if relay:
					name = team + ' Relay'
					year = ''

				# now check for existance and load in chunks for performance
				if loadTeams:
					key = str(season) + team + gender + division
					if not key in teamKeys:  # try each team once
						teamKeys.add(key)
						query = TeamSeason.select().where(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.division==division)
						if not query.exists():
							newTeam = {'season': season, 'conference': conference, 'team': team, 'gender':
								gender, 'division': division}
							newTeams.append(newTeam)

				if loadMeets:
					key = str(season) + meet + gender
					if not key in meetKeys:
						meetKeys.add(key)  # try each meet once

						query = Meet.select().where(Meet.meet==meet, Meet.season==season, Meet.gender==gender)
						if not query.exists():
							newMeet = {'season': season, 'gender': gender, 'meet': meet, 'date': swimDate}
							meets.append(newMeet)

				if loadSwimmers:
					key = str(season) + name + str(team) + gender
					if not key in swimmerKeys:
						swimmerKeys.add(key)
						teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.division==division).id

						query = Swimmer.select().where(Swimmer.season==season, Swimmer.name==name,
													  Swimmer.team==teamID, Swimmer.gender==gender)
						if not query.exists():
							newSwimmer = {'season': season, 'name': name, 'year': year, 'gender':
								gender, 'team': teamID}
							swimmers.append(newSwimmer)
						elif not relay:
							for swimmer in query:
								if swimmer.year != year:
									print swimmer.year, year, swimmer.id
									swimmer.year = year
									swimmer.save()

				if loadTeamMeets:
					key = str(season) + meet + gender + team
					if not key in teamMeetKeys:
						teamMeetKeys.add(key)
						meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.division==division).id
						query = TeamMeet.select().where(TeamMeet.meet==meetID, TeamMeet.team==teamID)

						if not query.exists():
							newTeamMeet = {'meet': meetID, 'team': teamID}
							teamMeets.append(newTeamMeet)

				if loadSwims:
					key = name + event + str(time) + str(swimDate)
					if not key in swimKeys:
						swimKeys.add(key)

						query = Swim.select().where(Swim.name==name, Swim.time<time + .01, Swim.time > time - .01,
									Swim.event==event, Swim.date==swimDate)  # floats in SQL and python different
						if not query.exists():
							teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.division==division).id
							swimmer = Swimmer.get(Swimmer.name==name, Swimmer.team==teamID)
							newSwim = {'meet': meet, 'date': swimDate, 'season': season, 'name': name, 'team': team,
					   			'gender': gender, 'event': event, 'time': time, 'division':
								division, 'relay': relay, 'swimmer': swimmer.id}
							swims.append(newSwim)

							# wipe powerpoints for that swimmer
							swimmer.ppts = None
							swimmer.save()

						# incremental load
						if len(swims) > 999:
							print 'Swims: ', len(swims)
							print Swim.insert_many(swims).execute()
							swims = []

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
loads into tables in order
'''
def safeLoad(year=2018, type='new'):
	print 'loading teams...'
	load(loadTeams=True, loadyear=year, type=type)
	print 'loading meets and swimmers...'
	load(loadMeets=True, loadSwimmers=True, loadyear=year, type=type)
	print 'loading teamMeets and swims...'
	load(loadTeamMeets=True, loadSwims=True, loadyear=year, type=type)

	print 'Updating powerpoints'
	updatePowerpoints(year)

	print 'fixing duplicates'
	fixDupSwimmers(year)

	print 'refresh view'
	db.execute_sql("REFRESH MATERIALIZED VIEW top_swim")


def updatePowerpoints(year):
	for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.ppts.is_null(),
																			  Swimmer.season==int(year)):
		swimmer.getPPTs()


'''
The following functions are all meant for data correction

merge: helper functions to merge two teams or swimmers into the same
fix: these go through existing data and clean up the various parts
'''
def mergeTeams(sourceTeamId, targetTeamId):
	sourceTeam = TeamSeason.get(id=sourceTeamId)
	targetTeam = TeamSeason.get(id=targetTeamId)

	# clear teamstats
	TeamStats.delete().where(TeamStats.teamseasonid==sourceTeam.id).execute()

	# find swimmers and update their info
	for swimmer in Swimmer.select().where(Swimmer.team==sourceTeam.id):
		swimmer.team = targetTeam.id
		try:
			targetSwimmer = Swimmer.get(gender=targetTeam.gender, season=targetTeam.season, name=swimmer.name,
									teamid=targetTeam)
			mergeSwimmers(swimmer, targetSwimmer)
		except Swimmer.DoesNotExist:
			swimmer.save()

		# update their swims
		for swim in Swim.select().where(Swim.swimmer==swimmer.id):
			swim.team = targetTeam.team
			swim.season = targetTeam.season
			if swim.relay:  # change relay names
				swim.name = targetTeam.team + ' Relay'
			swim.save()

	# now switch the meet linking table
	for teammeet in TeamMeet.select().where(TeamMeet.team==sourceTeam.id):
		teammeet.team = targetTeam.id
		teammeet.save()

	TeamSeason.delete().where(TeamSeason.id==sourceTeamId).execute()


def mergeSwimmers(sourceSwimmerId, targetSwimmerId):
	sourceSwimmer = Swimmer.get(id=sourceSwimmerId)
	targetSwimmer = Swimmer.get(id=targetSwimmerId)
	targetTeam = TeamSeason.get(id=targetSwimmer.team)
	print targetTeam.team
	for swim in Swim.select().where(Swim.swimmer==sourceSwimmer):
		swim.team = targetTeam.team
		swim.division = targetTeam.division
		swim.season = targetTeam.season
		swim.swimmer = targetSwimmer.id
		swim.name = targetSwimmer.name
		try:
			print swim.name, swim.event, swim.time, swim.date
			Swim.get(name=swim.name, event=swim.event, date=swim.date)
			# should mean the swims already exist
			print 'delete', swim.id
			Swim.delete().where(Swim.id==swim.id).execute()
		except Swim.DoesNotExist:
			print 'move', swim.id
			swim.save()

	Swimmer.delete().where(Swimmer.id==sourceSwimmerId).execute()


def fixRelays():
	'''finds relays that are attached to non-relay swimmers'''
	count = 0
	for swim in Swim.select(Swim.name, Swim.id, Swim.relay, Swimmer.name, Swimmer.team, TeamSeason.team,
							TeamSeason.season, TeamSeason.team, TeamSeason.gender).join(
			Swimmer).join(TeamSeason).where(~Swimmer.name.endswith('Relay'), Swim.relay==True):
		print swim.id, swim.swimmer.name, swim.name, swim.swimmer.team.team, swim.swimmer.team.id
		try:
			relay = Swimmer.get(Swimmer.team==swim.swimmer.team.id, Swimmer.name.endswith('Relay'))
			if relay.name != swim.name:
				continue
			swim.swimmer = relay.id
			swim.save()
		except Swimmer.DoesNotExist:
			team = swim.swimmer.team
			name = team.team + ' Relay'
			relay = Swimmer.create(teamid=team.id, gender=team.gender, season=team.season, team=team.team, name=name)
			if relay.name != swim.name:
				continue
			swim.swimmer = relay.id
			swim.save()

		count +=1
		if count % 1000 == 0: print count
	print count

	'''now fix ones with gender mismatch'''
	count = 0
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
				print team.id, team.team, team.conference, conf
				team.conference = conf
				team.save()
		except:
			pass


def normalizeData():
	for team in TeamSeason().select():
		for swimmer in Swimmer.select().where(Swimmer.team==team):
			if swimmer.season != team.season:
				print swimmer.name, swimmer.season, team.season, team.team, swimmer.id, team.id
			if swimmer.gender != team.gender:
				print swimmer.name, team.id, swimmer.gender, team.gender


# guess duplicate swimmers as people who tied in more than two races
def fixDupSwimmers(season=2018):
	swimmers_merged = set()
	for swim in Swim.raw('select s.count, s.swimmer1, s.swimmer2 from '
		'(select count(s1.id),s1.swimmer_id as swimmer1, s2.swimmer_id as swimmer2 from swim s1, swim s2 '
		'where s1.swimmer_id!=s2.swimmer_id and s1.time=s2.time and s1.event=s2.event and s1.date=s2.date and '
		's1.team=s2.team and s2.season=%s group by s1.swimmer_id, s2.swimmer_id) as s '
		'where count>3 order by count desc', season):

		# make sure we don't try and delete the reverse
		print swimmers_merged
		print swim.swimmer1, swim.swimmer2
		if swim.swimmer1 in swimmers_merged or swim.swimmer2 in swimmers_merged:
			continue
		swimmers_merged.add(swim.swimmer1)
		swimmers_merged.add(swim.swimmer2)

		count1 = Swim.select().where(Swim.swimmer==swim.swimmer1).count()
		count2 = Swim.select().where(Swim.swimmer==swim.swimmer2).count()

		# merge into the swimmer with more swims
		if count1 > count2:
			mergeSwimmers(swim.swimmer2, swim.swimmer1)
		elif count1 > count2:
			mergeSwimmers(swim.swimmer1, swim.swimmer2)
		else:  # same number of swims, use higher id meaning newer
			if swim.swimmer1 > swim.swimmer2:
				mergeSwimmers(swim.swimmer2, swim.swimmer1)
			else:
				mergeSwimmers(swim.swimmer1, swim.swimmer2)


def fixMeetNames():
	for char in ['+', '@', '&']:
		searchStr = '%' + char + '%'
		for meet in Meet.select().where(Meet.meet % searchStr):
			print meet.meet
			if char == '+':
				newName = meet.meet.replace('+', ' ')
			elif char == '@':
				newName = meet.meet.replace('@', 'at')
			else:
				newName = meet.meet.replace('&', 'and')

			print newName
			Swim.update(meet=newName).where(Swim.meet==meet.meet).execute()

			meet.meet = newName
			meet.save()


def badTimes():
	for event in eventConvert:
		if event=='1000 Free': continue
		for swim in Swim.select().where(Swim.event==event).order_by(Swim.time).limit(100):
			ppts = swim.getPPTs(raw=True)
			if ppts > 1300 or ppts < 5:
				print swim.event, swim.time, swim.gender, ppts, swim.name, swim.team, swim.division
				swim.delete_instance()


def fixTeams():
	for swim in Swim.select().join(Swimmer).join(TeamSeason).where(Swim.team != TeamSeason.team):
		swim.team = swim.swimmer.team.team
		swim.save()

if __name__ == '__main__':
	start = Time.time()

	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--dups', help='year to remove duplicate swimmers for')
	parser.add_argument('-l', '--load', help='year to load in new times')
	parser.add_argument('-b', '--best', help='year to load in best times')
	parser.add_argument('-a', '--all', help='year to load in all times')
	parser.add_argument('-s', '--stats', help='week to update team stats')
	parser.add_argument('-p', '--points', help='year to update powerpoints')

	args = vars(parser.parse_args())

	if args['dups']:
		fixDupSwimmers(args['dups'])

	if args['points']:
		updatePowerpoints(args['points'])

	if args['load']:
		safeLoad(year=args['load'])

	if args['best']:
		safeLoad(year=args['best'], type='best')

	if args['all']:
		safeLoad(year=args['load'], type='all')

	if args['stats']:
		for division in ['D1', 'D2', 'D3']:
			for gender in ['Men', 'Women']:
				print division, gender
				update_weekly_stats(week=int(args['stats']), season=2019, division=division, gender=gender)


	# fixConfs()
	# fixDivision()
	# fixRelays())
	stop = Time.time()
	print stop - start