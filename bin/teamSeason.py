from peewee import *
import heapq
from swim import Swim

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
	season = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField(null=True)
	division = CharField()
	winnats = FloatField(null=True)
	winconf = FloatField(null=True)
	strengthdual = FloatField(null=True)
	strengthinvite = FloatField(null=True)
	topSwimmers = {}

	class Meta:
		database = db

	def getPrevious(self, yearsBack=1):
		# used to grab same team in
		try:
			return TeamSeason.get(TeamSeason.team==self.team, TeamSeason.gender==self.gender,
						   TeamSeason.division==self.division, TeamSeason.season==self.season-yearsBack)
		except TeamSeason.DoesNotExist:
			return

	def getAllSeasons(self):
		teams = set()
		for team in TeamSeason.get(TeamSeason.team==self.team, TeamSeason.gender==self.gender,
						   TeamSeason.division==self.division):
			teams.add(team)
		return teams

	def getTaperStats(self, weeks=12):
		lastSeason = self.getPrevious()
		for stats in TeamStats.select().where(TeamStats.teamseasonid==lastSeason.id, TeamStats.week >= weeks)\
				.limit(1).order_by(TeamStats.week):
			return stats.mediantaper, stats.mediantaperstd

	def getWinnats(self):
		if self.winnats:
			return self.winnats
		return 0

	def getWinconf(self):
		if not self.conference:
			return ''

		for stats in TeamStats.select(fn.MAX(TeamStats.week), TeamStats.winconf).where(
				TeamStats.teamseasonid==self.id).group_by(TeamStats.winconf):
			if stats.winconf:
				return stats.winconf

		if self.winconf:
			return self.winconf
		return 0

	def getTopSwimmers(self, num=10):
		swimmers = []
		topSwimmers = {}
		for swimmer in Swimmer.select().where(Swimmer.teamid==self.id):
			if 'Relay' in swimmer.name: continue
			heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))

		for (points, swimmer) in heapq.nlargest(num, swimmers):  # take three best times
			topSwimmers[swimmer] = points

		return heapq.nlargest(num, swimmers)

	'''
	def attrition(self):
		teamDrops = 0
		teamSwims = 0
		for team in self.getAllSeasons():
			try:
				# make sure there was a team both years
				seasonID = TeamSeason.get(TeamSeason.team==team, TeamSeason.gender==gender,
										  TeamSeason.season==season).id
				seasonID2 = TeamSeason.get(TeamSeason.team==team, TeamSeason.gender==gender,
										 TeamSeason.season==season+1).id
				for swimmer in Swimmer.select(Swimmer.name, Swimmer.teamid, Swimmer.year).where(
								Swimmer.year!='Senior', Swimmer.teamid==seasonID):
					teamSwims[team] += 1  # total number of swimmers
					try:
						Swimmer.get(Swimmer.name==swimmer.name, Swimmer.season==season+1,
									Swimmer.teamid==seasonID2)  # swam the next year
					except Swimmer.DoesNotExist:
						teamDrops[team] += 1
			except TeamSeason.DoesNotExist:
				pass

		dropRate = {}
		if teamSwims > 0:
			dropRate = float(teamDrops) / float(teamSwims)
		return dropRate
	'''

class Swimmer(Model):
	name = CharField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	year = CharField()
	teamid = ForeignKeyField(TeamSeason, null=True)
	taperSwims = {}

	class Meta:
		database = db

	def getTaperSwims(self, num=3):
		taperSwims = {}
		times = []

		for swim in Swim.raw("WITH topTimes as "
			"(SELECT name, gender, meet, event, time, year, division, swimmer_id, row_number() OVER "
			"(PARTITION BY event, name ORDER BY time) as rnum "
			"FROM Swim WHERE swimmer_id=%s) "
			"SELECT name, event, meet, time, gender, division, year, swimmer_id FROM topTimes WHERE rnum=1",
			self.id):
			if swim.event == '1000 Yard Freestyle' or 'Relay' in swim.event:
				continue
			points = swim.getPPTs()
			# print swim.event, swim.time, points
			# print swim.time, swim.gender, swim.division, swim.event, points
			heapq.heappush(times, (points, swim))

		for (points, swim) in heapq.nlargest(num, times):  # take three best times
			# print self.name, swim.event, points, swim.time
			taperSwims[swim.event] = swim

		return taperSwims

	def getPPTs(self):
		totalPPts = 0
		taperSwims = self.getTaperSwims()
		for event in taperSwims:
			totalPPts += taperSwims[event].getPPTs()

		return totalPPts