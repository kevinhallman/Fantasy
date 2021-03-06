import time as Time
from datetime import date as Date
from swimdb import Swim, TeamSeason, Swimmer, toTime, Meet, seasonString, TeamStats
from sqlmeets import update_weekly_stats, date2week
import re
import os
import urlparse
import peewee
import playhouse.migrate as mig
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
	with open('bin/newconferences.txt', 'r') as file:
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
def load(year=2019):
	db.execute_sql('CREATE TEMP TABLE stage_team AS '
		'SELECT DISTINCT team, gender, division, season, conference FROM swimstaging WHERE season=2019 and new=True')

	print 'inserting teams'
	db.execute_sql('INSERT INTO teamseason (gender, division, team, season, conference) '
		'SELECT st.gender, st.division, st.team, 2019, st.conference FROM stage_team st '
		'LEFT OUTER JOIN teamseason ts ON ts.team=st.team and ts.gender=st.gender and ts.season=2019 '
		'WHERE ts.id IS NULL')

	print 'inserting swimmers'
	db.execute_sql('CREATE TEMP TABLE stage_swimmer AS '
		'SELECT season, name, team, gender, division, year, rank FROM '
		'(SELECT DISTINCT season, name, team, gender, division, year, rank() OVER '
		'(PARTITION BY name, team, gender, division ORDER BY date) '
		'FROM swimstaging) AS s WHERE s.rank=1 order by name')

	db.execute_sql('INSERT INTO swimmer (name, season, gender, year, team_id) '
		'SELECT ss.name, 2019, ss.gender, ss.year, ts.id as team_id FROM stage_swimmer ss '
		'INNER JOIN teamseason ts ON ss.team=ts.team and ss.division=ts.division and ss.gender=ts.gender and '
			 'ss.season=ts.season '
		'LEFT OUTER JOIN swimmer sw on sw.name=ss.name and sw.team_id=ts.id where sw.id IS NULL')

	
	db.execute_sql('CREATE TEMP TABLE stage_swim AS '
		'SELECT * FROM swimstaging WHERE season=2019 and new=True')

	print 'wipe powerpoints'
	db.execute_sql('UPDATE swimmer SET ppts=null '
		'FROM '
		'(SELECT sr.id FROM stage_swim ss '
		'INNER JOIN teamseason ts ON ss.team=ts.team and ss.division=ts.division and ss.gender=ts.gender and '
		'ss.season=ts.season '
		'INNER JOIN swimmer sr ON ss.name=sr.name and ts.id=sr.team_id '
		'LEFT OUTER JOIN swim sw on sw.name=ss.name and sw.event=ss.event and sw.time=ss.time and sw.date=ss.date where sw.id IS NULL '
		') AS s '
		'WHERE s.id=swimmer.id ')

	print 'inserting swims'
	db.execute_sql('INSERT INTO swim (name, event, date, time, season, team, meet, gender, division, relay, '
				   'swimmer_id) '
		'SELECT ss.name, ss.event, ss.date, ss.time, ss.season, ss.team, ss.meet, ss.gender, ss.division, ss.relay, '
				   'sr.id FROM stage_swim ss '
		'INNER JOIN teamseason ts ON ss.team=ts.team and ss.division=ts.division and ss.gender=ts.gender and '
				   'ss.season=ts.season '
		'INNER JOIN swimmer sr ON ss.name=sr.name and ts.id=sr.team_id '
		'LEFT OUTER JOIN swim sw on sw.name=ss.name and sw.event=ss.event and sw.time=ss.time and sw.date=ss.date where sw.id IS NULL')

	print 'fixing duplicates'
	fixDupSwimmers(year)

	print 'Updating powerpoints'
	updatePowerpoints(year)

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
									team=targetTeam)
			mergeSwimmers(swimmer, targetSwimmer)
		except Swimmer.DoesNotExist:
			swimmer.save()

		# update their swims
		for swim in Swim.select().where(Swim.swimmer==swimmer.id):
			swim.team = targetTeam.team
			swim.season = targetTeam.season
			if swim.relay:  # change relay names
				swim.name = targetTeam.team + ' Relay'

			query = Swim.select(Swim.name==swim.name, Swim.event==swim.event, Swim.date==swim.date,
								Swim.time==swim.time)

			if query.exists():
				print 'delete', swim.name, swim.event, swim.date, swim.time
				swim.delete()
			else:
				swim.save()

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
			Swimmer).join(TeamSeason).where(Swimmer.name.endswith('Relay'), Swim.relay==True):
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

def fix_dup_teams():
	# find teams that have more than three matching swimmers, three trasnfers to same team unlikely
	teams_merged = set()
	for team in TeamSeason.raw('SELECT s.count,s.team1, ts1.strengthinvite as str1, s.team2,ts2.strengthinvite as str2 '
		'FROM ( '
			'SELECT count(s1.id), s1.team_id AS team1, s2.team_id AS team2 '
			'FROM swimmer s1, swimmer s2 '
			'WHERE s1.team_id!=s2.team_id and s1.name=s2.name and s1.season=s2.season and s1.gender=s2.gender '
			'GROUP BY s1.team_id, s2.team_id '
			') AS s '
		'INNER JOIN teamseason ts1 ON S.team1 = ts1.id '
		'INNER JOIN teamseason ts2 ON S.team2 = ts2.id '
		'WHERE count>2 ORDER BY count DESC'):

		# make sure we don't try and delete the reverse
		print teams_merged
		print team.team1, team.str1, team.team2, team.str2
		if team.team1 in teams_merged or team.team2 in teams_merged:
			continue
		teams_merged.add(team.team1)
		teams_merged.add(team.team2)


		# merge into the team with higher score
		if team.str1 > team.str2:
			mergeTeams(team.team2, team.team1)
		elif team.str1 < team.str2:
			mergeTeams(team.team1, team.team2)
		else:  # same score, use higher id meaning newer
			if team.team1 > team.team2:
				mergeTeams(team.team2, team.team1)
			else:
				mergeTeams(team.team1, team.team2)

def delete_nulls():
	pass
	'''
	DELETE from swimmer sw WHERE sw.id IN
	(SELECT r.id FROM swimmer r
	LEFT OUTER JOIN swim m ON m.swimmer_id=r.id WHERE m.id IS NULL);

	DELETE from teamstats ts WHERE ts.teamseasonid_id IN
	(SELECT r.id FROM teamseason r
	LEFT OUTER JOIN swimmer m ON m.team_id=r.id WHERE m.id IS NULL);

	DELETE from teammeet tm WHERE tm.team_id IN
	(SELECT r.id FROM teamseason r
	LEFT OUTER JOIN swimmer m ON m.team_id=r.id WHERE m.id IS NULL);

	DELETE from teamseason ts WHERE ts.id IN
	(SELECT r.id FROM teamseason r
	LEFT OUTER JOIN swimmer m ON m.team_id=r.id WHERE m.id IS NULL);
	'''

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
		load(year=args['load'])

	if args['stats']:
		if int(args['stats']) == 0:
			week = date2week(Date.today())
		else:
			week = int(args['stats'])
		
		for division in ['D1', 'D2', 'D3']:
			for gender in ['Men' , 'Women']:
				print division, gender
				#for week in [-1, 5, 10, 15, 20, 25]:
				update_weekly_stats(week=week, season=2019, division=division, gender=gender)

	stop = Time.time()
	print stop - start