import peewee as pw
from playhouse.migrate import PostgresqlMigrator, migrate
from swimdb import Swimmer, Meet, Swim, TeamSeason, TeamStats
from datetime import date, timedelta
from events import eventsDualS, eventsChamp
import heapq
import urlparse
import os
import datetime, random

#  setup database
urlparse.uses_netloc.append("postgres")
if "DATABASE_URL" in os.environ:  # production
	url = urlparse.urlparse(os.environ["DATABASE_URL"])
	db = pw.PostgresqlDatabase(database=url.path[1:],
    	user=url.username,
    	password=url.password,
    	host=url.hostname,
    	port=url.port)
else:
	db = pw.PostgresqlDatabase('swimdb', user='hallmank')

class FantasyConference(pw.Model):
	name = pw.CharField()
	gender = pw.CharField()
	conference = pw.CharField(null=True)
	division = pw.CharField()
	season = pw.IntegerField()
	team_limit = pw.IntegerField(default=10)
	team_size_limit = pw.IntegerField(default=17)
	dates = None

	def __init__(self, **kwargs):
		pw.Model.__init__(self, **kwargs)

	# fantasy competition dates
	def getDates(self):
		if self.dates:
			return self.dates
		# this will give us the first Monday after the hard-coded start date
		onDay = lambda date, day: date + datetime.timedelta(days=(day - date.weekday() + 7) % 7)
		month = datetime.timedelta(weeks=4)
		day = datetime.timedelta(days=1)

		start = onDay(date=date(self.season - 1, 11, 01), day=0)  # 0 for Monday
		month1 = onDay(start + month, 0)
		month2 = onDay(month1 + month, 0)
		month3 = onDay(month2 + month, 0)
		month4 = onDay(month3 + month, 0)

		months = dict()
		months[0] = (start, month1 - day)  # Nov-Dec
		months[1] = (month1, month2 - day)  # Dec-Jan
		months[2] = (month2, month3 - day)  # Jan-Feb
		months[3] = (month3, month4 - day)  # Feb-March

		self.dates = months
		return months

	def teams(self):
		for team in FantasyTeam.select().where(FantasyTeam.conference==self):
			if team.name != 'freeagent':
				yield team

	# create schedule for conference
	def schedule(self):
		meets = self.getDates().keys()
		teamsWeeks = {}
		for meet in meets:
			teams = []
			for team in self.teams():
				teams.append(team)
			teamsWeeks[meet] = random.shuffle(teams)
		for week in teamsWeeks:
			teams = teamsWeeks[week]
			while len(teams) > 1:
				team1 = teams.pop()
				team2 = teams.pop()
				newScore = FantasyScore(team1=team1, team2=team2, week=int(week), status='new')
				newScore.save()

	# get scores for that month
	def getScores(self, month=0):
		scores = []
		for score in FantasyScore.select().where(FantasyScore.conference==self, FantasyScore.week==month):
			scores.append((score.team1, score.team2, score.score1, score.score2))
		return scores

	def score(self, month=0):
		for score in FantasyScore.select().where(FantasyScore.conference==self, FantasyScore.week==month):
			pass

	# return dummy team of free agents and create if it does not exist
	def freeAgentTeam(self):
		try:
			team = FantasyTeam.get(conference=self, name='freeagent')
		except FantasyTeam.DoesNotExist:
			team = FantasyTeam(conference=self, name='freeagent')
			team.save()
		return team

	# auto-add all swimmers in that conference
	def addSwimmers(self):
		# create the free agent team if it doesn't exist
		free = self.freeAgentTeam()
		if not free:
			free = FantasyTeam(name='freeagent', owner='system', conference=self)
			free.save()
		print free, self.gender, self.season, self.name
		for swimmer in Swimmer.select().join(TeamSeason).where(TeamSeason.conference==self.conference,
												Swimmer.gender==self.gender, TeamSeason.season==self.season):
			if 'Relay' not in swimmer.name:  # no relays, add to free agentss
				newSwimmer = FantasyTeamSwimmer(team=free, swimmer=swimmer, conference=self)
				newSwimmer.save()

	def freeAgents(self):
		for swimmer in self.freeAgentTeam().swimmers():
			yield swimmer

	def swimmers(self):
		for swimmer in FantasyTeamSwimmer.select().where(FantasyTeamSwimmer.conference==self):
			yield swimmer

	indexes = (
            (('conference', 'season', 'gender', 'name'), True),
        )

	class Meta:
		database = db

class FantasyOwner(pw.Model):
	name = pw.CharField()
	password = pw.CharField()

	class Meta:
		database = db

class FantasyTeam(pw.Model):
	name = pw.CharField()
	owner = pw.ForeignKeyField(FantasyOwner, null=True)
	conference = pw.ForeignKeyField(FantasyConference)

	# add to team and remove from free agency
	def addSwimmer(self, swimmer):
		if swimmer.conference != self.conference:
			return 'wrong conference'
		if swimmer.team == self.conference.freeAgentTeam():
			try:
				swimmer.team = self
				swimmer.save()
				return 'success'
			except:
				return 'error'

	def dropSwimmer(self, swimmer):
		if swimmer.conference != self.conference:
			return 'wrong conference'
		if swimmer.team == self:
			try:
				swimmer.team = self.conference.freeAgentTeam()
				swimmer.save()
				return 'success'
			except:
				return 'error'

	'''top expected score for the whole team'''
	def topTeamScore(self, dual=True, month=None):

		if dual:
			events = eventsDualS
		else:
			events = eventsChamp
		topMeet = self.topTimes(events=events, month=month)

		topMeet.topEvents(teamMax=17, indMax=3)
		if dual:
			scores = topMeet.expectedScores(swimmers=6, division=self.division)
		else:
			scores = topMeet.expectedScores(swimmers=16, division=self.division)

		if self.team in scores:
			return scores[self.team]
		return 0

	def swimmers(self):
		for swimmer in FantasyTeamSwimmer.select().where(FantasyTeamSwimmer.team==self):
			yield swimmer

	def getTopSwimmers(self, num=10):
		swimmers = []
		for swimmer in self.swimmers():
			heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))

		return heapq.nlargest(num, swimmers)

	def topTimes(self, month=None, events=None, verbose=False):
		months = self.conference.getDates()
		if month in months:
			startDate, endDate = months[month]
		else:  # use the whole year
			endDate = str(self.conference.season) + '-4-1'
			startDate = str(self.conference.season - 1) + '-10-1'

		newMeet = Meet()
		if verbose: print startDate, endDate
		for fanswimmer in self.swimmers():
			swimmer = fanswimmer.swimmer
			for swim in Swim.raw("WITH topTimes as "
				"(SELECT date, name, gender, meet, event, time, division, swimmer_id, row_number() OVER "
				"(PARTITION BY event, name ORDER BY time) as rnum "
				"FROM Swim WHERE swimmer_id=%s and swim.date<%s and swim.date>%s) "
				"SELECT date, name, event, meet, time, gender, division, swimmer_id FROM topTimes WHERE rnum=1",
				swimmer.id, endDate, startDate):
				swim.gender = swimmer.gender
				swim.season = swimmer.season
				swim.year = swimmer.year
				if verbose: print swim, swim.date
				if events:
					if swim.event in events:
						newMeet.addSwim(swim)
				else:
					newMeet.addSwim(swim)

		return newMeet

	# dual another team and optionally save the stored result
	def dual(self, team2=None, month=0, lineup1=None, lineup2=None, verbose=False, save=True):
		# check to see if the score exists, if not create it
		try:
			score = FantasyScore.get(team_one=self, week=month, conference=self.conference)
		except:
			try:
				score = FantasyScore.get(team_one=team2, week=month, conference=self.conference)
			except:
				if not team2:  # we don't know who they are swimming yet so return
					return None, None
				score = FantasyScore(team_one=self, team_two=team2, week=month, conference=self.conference)

		if not team2:
			team2 = score.team_two

		meet = Meet()
		bench = Meet()
		if lineup1:  # get swims from lineup
			meet.addSwims(lineup1.getSwims(), newTeamName=self.name)
		else:  # if the meet exists use those
			if score.has_swims(self):
				for swim in score.get_swims(self, status='active'):
					swim.scoreTeam = self.name
					meet.addSwim(swim)
				for swim in score.get_swims(self, status='inactive'):
					swim.scoreTeam = self.name
					bench.addSwim(swim)
			# otherwise use top times
			else:
				top_times = self.topTimes(events=eventsDualS, month=month)
				drops1 = top_times.topEvents(teamMax=17, indMax=3)
				bench.addSwims(drops1, newTeamName=self.name)
				meet.addSwims(top_times.getSwims(), newTeamName=self.name)
				if save:
					score.save_times(top_times, self)
					score.save_times(drops1, self, status='inactive')

		if lineup2:  # get swims from lineup
			meet.addSwims(lineup2.getSwims(), newTeamName=team2.name)
		else:  # if the meet exists use those
			if score.has_swims(team2):
				for swim in score.get_swims(team2, status='active'):
					swim.scoreTeam = team2.name
					meet.addSwim(swim)
				for swim in score.get_swims(team2, status='inactive'):
					swim.scoreTeam = team2.name
					bench.addSwim(swim)
			else:
				top_times = team2.topTimes(events=eventsDualS, month=month)
				drops2 = top_times.topEvents(teamMax=17, indMax=3)
				bench.addSwims(drops2, newTeamName=team2.name)
				meet.addSwims(top_times.getSwims(), newTeamName=team2.name)
				if save:
					score.save_times(top_times, team2)
					score.save_times(drops2, team2, status='inactive')

		meet.score()
		if verbose: print meet

		if self.name in meet.scores and team2.name in meet.scores:
			score1 = meet.scores[self.name]
			score2 = meet.scores[team2.name]
		else:
			return None, None

		if save:
			score.team_one_score = score1
			score.team_two_score = score2
			if lineup1:
				score.save_times(lineup1, self)
			if lineup2:
				score.save_times(lineup2, team2)
			score.save()

		return meet, bench

	indexes = (
            (('name', 'conference'), True),
        )

	class Meta:
		database = db


class FantasyTeamSwimmer(pw.Model):
	team = pw.ForeignKeyField(FantasyTeam)
	swimmer = pw.ForeignKeyField(Swimmer)
	conference = pw.ForeignKeyField(FantasyConference)

	# unique index
	indexes = (
            (('conference', 'swimmer'), True),
        )

	class Meta:
		database = db


class FantasyScore(pw.Model):
	conference = pw.ForeignKeyField(FantasyConference)
	team_one = pw.ForeignKeyField(FantasyTeam, related_name='team_one')
	team_one_score = pw.IntegerField(null=True)
	team_two = pw.ForeignKeyField(FantasyTeam, related_name='team_two')
	team_two_score = pw.IntegerField(null=True)
	week = pw.IntegerField()
	#status = pw.CharField()

	# two unique indexes
	indexes = (
            (('team_one', 'week'), True),
            (('team_two', 'week'), True),
        )

	def has_swims(self, team):
		if team != self.team_one and team != self.team_two:
			return False
		try:
			FantasySwim.get(meet=self, team=team)
			return True
		except FantasySwim.DoesNotExist:
			return False

	def get_swims(self, team, status='active'):
		for swim in FantasySwim.select().where(FantasySwim.meet==self, FantasySwim.team==team,
											   FantasySwim.status==status):
			yield swim.swim

	def save_times(self, meet, team, status='active'):
		print meet
		for swim in meet.getSwims():
			# partition functions don't grab full swim info
			db_swim = swim.sync()
			newSwim = FantasySwim(meet=self, swim=db_swim, status=status, team=team)
			newSwim.save()

	class Meta:
		database = db


class FantasySwim(pw.Model):
	meet = pw.ForeignKeyField(FantasyScore)
	swim = pw.ForeignKeyField(Swim)
	status = pw.CharField()
	team = pw.ForeignKeyField(FantasyTeam)


	# two unique indexes
	indexes = (
            (('meet', 'swim'), True),
        )

	class Meta:
		database = db

if __name__== '__main__':
	#db.create_tables([FantasySwim])
	migrator = PostgresqlMigrator(db)
	with db.transaction():
		migrate(
			#migrator.add_column('fantasyscore', 'status', FantasyScore.status),
			#migrator.add_column('fantasyconference', 'team_size_limit', FantasyConference.team_size_limit),
			#migrator.add_column('teamseason', 'improvement', TeamSeason.improvement)
			#migrator.adsd_column('swimmer', 'teamid_id', Swimmer.teamid)
			#migrator.add_column('swim', 'powerpoints', Swim.powerpoints)
		)

	#db.drop_tables([FantasyTeam, FantasyConference])
	#db.create_tables([FantasyTeam, FantasyTeamSwimmer, FantasyConference, FantasyScore])
	#miac = FantasyConference(name='MIACtest', division='D3', conference='MIAC', gender='Men', season=2017)
	#miac.save()
	#miac = FantasyConference.get(name='MIACtest')
	#miac.addSwimmers()
	#newowner = FantasyOwner(name='Kevin', password='Kevin')
	#newowner.save()
	#newteam = FantasyTeam(name='Kevin', conference=miac, owner=newowner)
	#newteam.save()
	newteam = FantasyTeam.get(name='Kevin')
	newteam2 = FantasyTeam.get(name="Team Eric")
	meet = newteam.topTimes(month=2)

	newteam.dual(newteam2, save=True, month=2, verbose=True, lineup1=meet)
	#print miac.getDates()
