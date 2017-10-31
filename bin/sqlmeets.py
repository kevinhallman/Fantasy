import reimport numpy as npimport operatorfrom operator import itemgetterfrom datetime import date as Date, timedeltafrom peewee import *import os, urlparseimport heapqimport time as time#simport matplotlib.pyplot as pltfrom swimdb import Improvement, Team, TeamStats, TeamSeason, Swimmer, Swimfrom swimdb import TempMeet as MeetpointsChampionship = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]pointsDualI = [9, 4, 3, 2, 1]pointsDualR = [11, 4, 2]eventsDualS = ["200 Yard Medley Relay","1000 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay"]eventsDualL = ["400 Yard Medley Relay","1650 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","400 Yard Individual Medley","400 Yard Freestyle Relay"]eventsChamp = ["400 Yard Medley Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","400 Yard Individual Medley","1650 Yard Freestyle","200 Yard Medley Relay","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay"]eventsChamp3 = ['1 mtr Diving','200 Yard Freestyle Relay','','500 Yard Freestyle','200 Yard Individual Medley', '50 Yard Freestyle','','400 Yard Medley Relay','','400 Yard Individual Medley','100 Yard Butterfly','200 Yard Freestyle',				'100 Yard Breastroke','100 Yard Backstroke','','800 Yard Freestyle Relay','','1650 Yard Freestyle','','200 Yard Medley Relay','','200 Yard Backstroke','100 Yard Freestyle','200 Yard Breastroke','200 Yard Butterfly','','400 Yard Freestyle Relay','3 mtr Diving']#eventsChamp3 = ['500 Yard Freestyle','200 Yard Individual Medley', '50 Yard Freestyle','','400 Yard Individual# Medley','100 Yard Butterfly','200 Yard Freestyle','100 Yard Breastroke','100 Yard Backstroke','','1650 Yard Freestyle','','200 Yard Backstroke','100 Yard Freestyle','200 Yard Breastroke','200 Yard Butterfly']eventsDay1 = ['1 mtr Diving','200 Yard Freestyle Relay','500 Yard Freestyle','200 Yard Individual Medley','50 Yard Freestyle','400 Yard Medley Relay']eventsDay2 = ['400 Yard Individual Medley','100 Yard Butterfly','200 Yard Freestyle','100 Yard Breastroke','100 Yard Backstroke','800 Yard Freestyle Relay']eventsDay3 = ['1650 Yard Freestyle','200 Yard Medley Relay','200 Yard Backstroke','100 Yard Freestyle','200 Yard Breastroke','200 Yard Butterfly','400 Yard Freestyle Relay','3 mtr Diving']allEvents = {"400 Yard Medley Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","400 Yard Individual "			"Medley","1650 Yard Freestyle","200 Yard Medley Relay","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay",'1000 Yard Freestyle','100 Yard Breastroke','200 Yard Breastroke'}eventsChampInd={"400 Yard Individual Medley","1650 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley",'100 Yard Breastroke','200 Yard Breastroke'}MIAC = ["Carleton","Augsburg","St. Olaf","Saint Mary's MN","Macalester","Gustavus","Saint Benedict","St. Kate's","Concordia","St. John's","St. Thomas","Hamline"]requiredEvents={"200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly"}eventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay"]indEventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle", "1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley"]# setup database connectiondb_proxy = Proxy()db = Proxy()'''events contained within a relay'''def relayEvents(relay):	dist=str(int(re.findall('\d\d\d',relay)[0])/4)	if re.search('Free',relay):		return [dist+' Yard Freestyle']+[dist+' Yard Freestyle Split']*3	return  [dist+' Yard Backstroke Split',dist+' Yard Breastroke Split',dist+' Yard Butterfly Split',dist+' Yard Freestyle Split']def thisSeason():	today = Date.today()	if today.month > 6:		return today.year + 1	return today.yeardef rejectOutliers(dataX, dataY=None, l=5, r=6):	u = np.mean(dataX)	s = np.std(dataX)	if dataY:		data = zip(dataX, dataY)		newList = [i for i in data if (u - l*s < i[0] < u + r*s)]		newX, newY = zip(*newList)		return list(newX), list(newY)	else:		newList = [i for i in dataX if (u - l*s < i < u + r*s)]	return newListdef ECDF(data):	def cdf(num):		d = data		l = float(len(d))		return (sum(1 for i in d if i < num) + sum(.5 for i in d if i==num))/l	return cdfdef getConfs():	confs = {'D1': {'Men': {}, 'Women': {}}, 'D2': {'Men': {}, 'Women': {}}, 'D3': {'Men': {}, 'Women': {}}}	allTeams = {'Men': {'D1': [], 'D2': [], 'D3': []}, 'Women': {'D1': [], 'D2': [], 'D3': []}}	for newTeam in TeamSeason.select(TeamSeason.team, TeamSeason.conference, TeamSeason.division,									 TeamSeason.gender).distinct(TeamSeason.team):		if newTeam.conference not in confs[newTeam.division][newTeam.gender]:			confs[newTeam.division][newTeam.gender][newTeam.conference] = set()		confs[newTeam.division][newTeam.gender][newTeam.conference].add(newTeam.team)		allTeams[newTeam.gender][newTeam.division].append(newTeam.team)		for division in ['D1', 'D2', 'D3']:			allTeams['Men'][division].sort()			allTeams['Women'][division].sort()	return confs, allTeamsdef nextYear(year):	if year=='Freshman':		return 'Sophomore'	if year=='Sophomore':		return 'Junior'	if year=='Junior':		return 'Senior'	return Nonedef grad(f, x, y, h=0.0025):	dx = (f(x, y) - f(x+h, y))/h	dy = (f(x, y) - f(x, y+h))/h	return dx, dydef gradientDescent(f, x0, y0, step=.001):	for i in range(10):		dx, dy = grad(f, x0, y0)		length = ((dx**2 + dy**2) ** .5)		print 'delta:', dx, dy		x0 += step * dx / length		y0 += step * dy / length		if x0 < 0:			x0 = 0.001		if y0 < 0:			y0 = 0.001		#print x0, y0	return x0, y0def frange(x, y, jump):	while x < y:		yield x		x += jumpdef date2week(d):	if d > Date.today():		d = Date.today()	if d.month > 6:		season = d.year + 1	else:		season = d.year	startDate = Date(season - 1, 10, 15)  # use Oct 15 as the start date, prolly good for 2017	weeksIn = int((d - startDate).days / 7)	return weeksIndef week2date(week, season=None):	if not season:		season = thisSeason()	startDate = Date(season - 1, 10, 16)  # use Oct 15 as the start date, prolly good for 2017	if week == None:		return Date.today()	simDate = startDate + timedelta(weeks=week)	if simDate > Date.today():  # can't simulate with future data		simDate = Date.today()	return simDate'''conference level information'''class Conference:	def __init__(self, name, gender, season, division):		self.conference = name		self.gender = gender		self.season = season		self.teams = set()		self.division = division		for team in TeamSeason.select().where(TeamSeason.gender==gender, TeamSeason.season==season,									TeamSeason.conference==name):			self.teams.add(team)	def meet(self, topTimes=True, date=None, update=False, taper=False, weeksIn=10, nextYear=False):		events = eventsChamp3		swimmerLimit = 17		weeksOut = 16 - weeksIn		base = SwimDatabase('')		conference = base.topTimes(events=events, teams=list(self.teams), season=self.season, gender=self.gender,								   topTimes=topTimes, divisions=self.division, date=date)		season = self.season		if nextYear:			conference.nextYear(self)			season += 1  # update the correct season			weeksOut = '-1'			weeksIn = '-1'		if taper: conference.taper()		conference.topEvents(swimmerLimit)		conference.score()		# update stored win probabilities		if update:			conference.scoreMonteCarlo(weeksOut=weeksOut)			teamProb = conference.getWinProb()			for team in teamProb:				teamSeason = TeamSeason.get(team=team, division=self.division, gender=self.gender, season=season)				try:					stats = TeamStats.get(teamseasonid=teamSeason.id, week=weeksIn)					stats.winconf = teamProb[team]					print team, season, stats.winconf, weeksIn, date, teamSeason.id, stats.id					print stats.save()				except TeamStats.DoesNotExist:					print 'AB:', team, season, teamProb[team], weeksIn, date					print TeamStats.create(teamseasonid=teamSeason.id, week=weeksIn, winconf=teamProb[team], date=date)	def getStats(self):		teamStats = {}		for team in self.teams:			teamStats[team.name] = {}			teamStats[team.name]['winNats'] = team.getWinnats()			teamStats[team.name]['winConf'] = team.getWinconf()			# team development			# print team, session.gender, session.division			try:				stats = Team.get(Team.name==team.name, Team.gender==self.gender, Team.division==self.division)				teamStats[team.name]['strinv'] = stats.strengthinvite				teamStats[team.name]['attrition'] = stats.attrition				teamStats[team.name]['imp'] = stats.improvement			except Team.DoesNotExist:				teamStats[team.name]['strinv'] = None				teamStats[team.name]['attrition'] = None				teamStats[team.name]['imp'] = None			(medtaper, stdtaper) = team.getTaperStats()			teamStats[team.name]['medtaper'] = medtaper			teamStats[team.name]['stdtaper'] = stdtaper	def getTopSwimmers(self, num=10):		swimmers = []		for team in self.teams:			for swimmer in Swimmer.select().where(Swimmer.teamid==team.id):				if 'Relay' in swimmer.name: continue				heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))		return heapq.nlargest(num, swimmers)'''full database methods'''class SwimDatabase:	def __init__(self, database):		global swimDatabase		swimDatabase = self		db_proxy.initialize(database)		self.database = database		self.dist = {}		self.results = {}  # cache dual results		self.teams = {}		self.meetCache = {}		self.eventImpCache = {}		self.topScoreCache = {}		self.topTimesCache = {}		self.teamRankCache = {}		self.swimmerRankCache = {}		self.conferences, self.allTeams = getConfs()	def topDual(self, season=thisSeason(), events=requiredEvents, debug=False, teams='all', gender='Men'):		if teams == 'all':			teams = self.teams		meets = {}		wins = {}		losses = {}		for team in teams:			if not team in self.teams:				self.teams[team] = Team(team, self)			if not self.teams[team].topDual(season, debug=debug, gender=gender):				continue			meets[team] = self.teams[team].topDual(season, debug=debug, gender=gender)  # its cached			wins[team] = 0			losses[team] = 0			#if debug: print team, '\t\t', meets[team]		if debug: print '-----------'		for team1 in meets:			for team2 in meets:				if team1 == team2:					continue				if not team1 in self.results:					self.results[team1] = {}				if not team2 in self.results:					self.results[team2] = {}				if team2 in self.results[team1] or team1 in self.results[team2]:  # reverse meet already swum					continue				newMeet = self.swimMeet([[team1, meets[team1]], [team2, meets[team2]]], includeEvents=events,									  selectEvents=False)  # should convert to dual form				self.results[team1][team2] = newMeet.winningTeam()				self.results[team2][team1] = newMeet.winningTeam()				if debug: print team1, team2, newMeet.winningTeam()				if self.results[team1][team2] == team1: # team1 wins					wins[team1] += 1					losses[team2] += 1				elif self.results[team1][team2] == team2:  # team2 wins, otherwise no points					wins[team2] += 1					losses[team1] += 1		if debug:			for (index, team) in enumerate(sorted(wins.items(), key=operator.itemgetter(1), reverse=True)):				print str(index)+'.',team[0]+':',team[1],'-',losses[team[0]]		return meets, wins, losses	'''	creates a swim meet with given teams and meets format is [(team1,meet1),(team2,meet2),...]	'''	def swimMeet(self, teamMeets, gender=None, includeEvents='all', excludeEvents=set(),				 selectEvents=True, resetTimes=False):		meet = Meet()		teams = []		if includeEvents == 'all':			includeEvents = allEvents		commonEvents = allEvents  # start with all events and whittle down		for teamMeet in teamMeets:			newTeam = teamMeet['team']			newMeet = teamMeet['meet']			if 'season' in teamMeet:				season = teamMeet['season']			else:				season = None			if isinstance(newMeet, basestring):  # just a name				newMeet = Meet(name=newMeet, gender=gender, teams=[newTeam], season=season)			commonEvents = commonEvents & set(newMeet.eventSwims.keys())			# resolve duplicate names, first try season, then a number			newTeamName = None			if teams.count(newTeam) > 0:				newTeamName = newTeam + ' ' + season				if teams.count(newTeamName) > 0:					newTeamName += ' ' + str(teams.count(newTeamName))			if newTeamName:				teams.append(newTeamName)			else:				teams.append(newTeam)			# now apply to existing swims			for swim in newMeet.getSwims(newTeam):				if newTeamName:					swim.scoreTeam = newTeamName				meet.addSwim(swim)		meet.reset(times=resetTimes)		if len(meet.teams) == 2:			if selectEvents:				meet.topEvents(25, 3, 4)				'''need to fix event selection for dual meets'''			meet.events = (commonEvents | includeEvents) - excludeEvents			meet.score(dual=True)		else:			if selectEvents:				meet.topEvents()			meet.score()		return meet	'''	optimal lineup creator	'''	def lineup(self, teams, meet, resetTimes=False, events=eventsDualS, gender='Men'):		meet.events = events		teamNames = []		for teamName in teams:			division = teams[teamName]['division']			if not 'season' in teams[teamName]:				season = thisSeason()			else:				season = teams[teamName]['season']			# add each team's top times to meet			team = TeamSeason.get(season=season, team=teamName, gender=gender, division=division)  # need division			topTimesMeet = team.topTimes(events=events)			# resolve duplicate names, first try season, then a number			newTeamName = None			if teamNames.count(teamName) > 0:				newTeamName = teamName + ' ' + season				if teamNames.count(newTeamName) > 0:					newTeamName += ' ' + str(teamNames.count(newTeamName))			if newTeamName:				teamNames.append(newTeamName)			else:				teamNames.append(teamName)			for swim in topTimesMeet.getSwims():				if newTeamName:					swim.scoreTeam = newTeamName				meet.addSwim(swim)		meet.reset(times=resetTimes)		meet.place()		# lineup optimize if creating lineup for just one team		if len(teamNames) == 1:			meet.lineup(teamNames.pop())		else:			meet.topEvents(17, indMax=3, totalMax=4)		return meet	'''	top expected score for the whole team	'''	def topTeamScore(self, teamName, dual=True, season=thisSeason(), gender='Men', division='D3', weeksIn=None):		# conver the week to a date		simDate = week2date(weeksIn, season)		# cache off times?		if dual:			events = eventsDualS		else:			events = eventsChamp		team = TeamSeason.get(season=season, team=teamName, gender=gender, division=division)  # need division		topMeet = team.topTimes(events=events, dateStr=simDate)		topMeet.topEvents(teamMax=17, indMax=3)		if dual:			scores = topMeet.expectedScores(swimmers=6, division=division)		else:			scores = topMeet.expectedScores(swimmers=16, division=division)		if team in scores:			return scores[team]		return 0	'''	returns meet of average times	'''	def averageTimes(self, conf, season=None, gender='Men', division=None, date=None):		if type(date) == type(str):			date = Date(date)		if not season:			season = thisSeason()  # use current season		if not date:			date = Date.today()		topMeet = Meet()		if conf=='Nationals':			select = Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason)\				.where(TeamSeason.gender==gender, TeamSeason.division==division, TeamSeason.season==season, Swim.date < date)		else:			select = Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason)\				.where(TeamSeason.gender==gender, TeamSeason.conference==conf, TeamSeason.season==season, Swim.date < date)		qwery = select.select(Swim.name, Swim.event, fn.Avg(Swim.time), Swimmer.team, Swimmer.year).group_by(Swim.name,				Swim.event, Swimmer.team, Swimmer.year)		for swim in qwery:			time = swim.avg			if swim.event != '1000 Yard Freestyle':				newSwim = Swim(name=swim.name, event=swim.event, time=time, gender=gender, team=swim.swimmer.team,									  season=season, year=swim.swimmer.year, swimmer=swim.swimmer)				topMeet.addSwim(newSwim)		topMeet.place()		return topMeet	'''	returns meet of average times	'''	def topTimesNew(self, season, gender, conf, division=None, dateStr=None, events=None):		if not dateStr:			meetDate = Date.today()			dateStr = str(meetDate.year) + '-' + str(meetDate.month) + '-' + str(meetDate.day)		newMeet = Meet()		if conf == 'Nationals':			for swim in Swim.raw("SELECT event, time, rank, name, meet, team, year, swimmer_id FROM "					"(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, rank() "					"OVER (PARTITION BY swim.name, event ORDER BY time) "					"FROM (swim "					"INNER JOIN swimmer sw "					"ON swim.swimmer_id=sw.id "					"INNER JOIN teamseason ts "					"ON sw.teamid_id=ts.id and ts.season=%s and ts.gender=%s and ts.division=%s) "					"WHERE swim.date < %s) AS a "					"WHERE a.rank=1", season, gender, division, dateStr):				newMeet.addSwim(swim)		else:			for swim in Swim.raw("SELECT event, time, rank, name, meet, team, year, swimmer_id FROM "					"(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, rank() "					"OVER (PARTITION BY swim.name, event ORDER BY time) "					"FROM (swim "					"INNER JOIN swimmer sw "					"ON swim.swimmer_id=sw.id "					"INNER JOIN teamseason ts "					"ON sw.teamid_id=ts.id and ts.season=%s and ts.gender=%s and ts.conference=%s) "					"WHERE swim.date < %s) AS a "					"WHERE a.rank=1", season, gender, conf, dateStr):				newMeet.addSwim(swim)		if '1000 Yard Freestyle' in newMeet.eventSwims:			del(newMeet.eventSwims['1000 Yard Freestyle'])		return newMeet	# simulates conference or national meet, must be real conference	def conference(self, season, gender, conf, division=None, dateStr=None, topTimes=True, update=False, taper=False,				   nextYear=False):		#print conf		if not season:			season = thisSeason()  # use current season		if topTimes:			conference = self.topTimesNew(conf=conf, season=season, gender=gender, division=division, dateStr=dateStr)		else:  # use avg times			conference = self.averageTimes(conf=conf, season=season, gender=gender, division=division, date=dateStr)		if nextYear:  # estimate next year's results			conference.nextYear(self)			season += 1  # update the correct season		conference.events = eventsChamp3		#print conference.getEvents()		#conference.printout()		conference.topEvents(teamMax=17)		conference.score()		if taper:			conference.taper()		if update:			weeksIn = date2week(dateStr)			#print weeksIn			if conf == 'Nationals':				nats = True			else:				nats = False			conference.update(weeksIn=weeksIn, division=division, gender=gender, season=season, nats=nats)		return conference	'''	returns top 25 teams and caches ranking data	'''	def teamRank(self, division='D3', gender='Men', season=2016, num=25):		sentinelStr = division + gender + str(season) + str(num)		if sentinelStr in self.teamRankCache:			return self.teamRankCache[sentinelStr]		teamScores = {}		for team in TeamSeason.select().where(TeamSeason.gender==gender, TeamSeason.division==division,								TeamSeason.season==season):			teamScores[team.team] = team		teams = sorted(teamScores.values(), key=lambda t: t.getStrength(), reverse=True)[:num]		self.teamRankCache[sentinelStr] = teams		return teams	'''	Returns top swimmers in a conference	'''	def swimmerRank(self, division='D3', gender='Men', season=2017, num=25, conference=None):		sentinelStr = division + gender + str(season) + str(num) + str(conference)		if sentinelStr in self.swimmerRankCache:			return self.swimmerRankCache[sentinelStr]		swimmerScores = {}		if not conference:  # all conferences			for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.gender==gender,									TeamSeason.division==division, TeamSeason.season==season):				swimmerScores[swimmer.name] = swimmer		else:			for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.gender==gender,						TeamSeason.division==division, TeamSeason.season==season, TeamSeason.conference==conference):				swimmerScores[swimmer.name] = swimmer		# return sorted list of top swimmers		swimmers = sorted(swimmerScores.values(), key=lambda s: s.getPPTs(), reverse=True)[:num]		self.swimmerRankCache[sentinelStr] = swimmers		return swimmers	# update the probabilities of winning conference	def updateConferenceProbs(self, division='D3', gender='Women', season=2017, weeksIn=None):		simDate = week2date(weeksIn, season)		if weeksIn == -1:  # pre-season			nextYear = True		else:			nextYear = False		print simDate		for conference in self.conferences[division][gender]:			if conference == '':				continue			self.conference(conf=conference, gender=gender, season=season, division=division, update=True,								dateStr=simDate, nextYear=nextYear)	def updateTeamStrength(self, division='D3', gender='Women', season=2017, weeksIn=None, update=True):		simDate = week2date(weeksIn, season)		print simDate		for team in TeamSeason.select().where(TeamSeason.division==division, TeamSeason.gender==gender,					TeamSeason.season==season):			try:				stats = TeamStats.get(teamseasonid=team.id, week=weeksIn)				if stats.strengthinvite is None or update:					scoreInv = team.topTeamScore(dual=False, weeksIn=weeksIn)					stats.strengthinvite = scoreInv					print team.team, scoreInv				if stats.strengthdual is None or update:					scoreDual = team.topTeamScore(dual=True, weeksIn=weeksIn)					stats.strengthdual = scoreDual					print team.team, scoreDual				stats.save()			except TeamStats.DoesNotExist:				scoreInv = team.topTeamScore(dual=False, weeksIn=weeksIn)				scoreDual = team.topTeamScore(dual=True, weeksIn=weeksIn)				TeamStats.create(teamseasonid=team.id, week=weeksIn, strengthinvite=scoreInv, strengthdual=scoreDual,								 date=simDate)	def updateTeamStats(self, division='D3', gender='Women', week=6):		simDate = week2date(week)		if simDate > Date.today():			return  # would be a future week		database.conference(conf='Nationals', gender=gender, division=division, season=2018, update=True,							dateStr=simDate)		database.updateConferenceProbs(division=division, gender=gender, season=2018, weeksIn=week)		database.updateTeamStrength(division=division, gender=gender, season=2018, weeksIn=week, update=True)	def conferencePlace(self, division, gender, newSwims, year=2014):		newEvents = set()		for swim in newSwims:			newEvents.add(swim[0])		confMeets = {}		with open('./data/' + division + gender + '.csv') as meetFile:			for line in meetFile:				(meetName, confName) = re.split('\t', line.strip())				if confName=='UAA' and confName in confMeets:  # combine that stupid UAA meet					confMeets[confName].addSwims(Meet(name=meetName, events=newEvents, gender=gender,													  topSwim=True).getSwims())				else:					confMeets[confName] = Meet(name=meetName, events=newEvents, gender=gender, topSwim=True,											   season=year)		confScores = {}		for conference in confMeets:			confMeet = confMeets[conference]			for swim in newSwims:				newSwim = Swim(event=swim[0], name='you', team='self', time=swim[1], gender=gender)				confMeet.addSwim(newSwim)			confMeet.place(storePlace=True)			confMeet.score()			confScores[conference] = {}			for swim in confMeet.getSwims():				if swim.name=='you':					confScores[conference][swim.event] = swim.place			confMeet.removeSwimmer('you')		return confScores	def taperMeets(self, year=2015, gender='Women', division='D1'):  #find meets where most best times come from		teamMeets = {}		#teams=['Univ of Utah', 'Stanford', 'California', 'Arizona', 'Southern Cali', 'Arizona St']		teams = self.allTeams[gender][division]		for team in teams:			for swim in Swim.raw("WITH topTimes AS (SELECT name, event, meet, time, row_number() OVER (PARTITION BY event,name "					 "ORDER BY time) AS rnum "					 "FROM Swim "					 "WHERE team=%s AND season=%s AND date > '%s-02-01' AND gender=%s) "					 "SELECT name,event,meet,time FROM topTimes WHERE rnum=1",					 team, year, year, gender):				if not team in teamMeets:					teamMeets[team] = []				teamMeets[team].append(swim.meet)		#print teamMeets.keys()		taperMeets = {}		for team in teamMeets:			taperMeet = max(set(teamMeets[team]), key=teamMeets[team].count)			#print team, taperMeet			if taperMeet not in taperMeets:				taperMeets[taperMeet] = 0			taperMeets[taperMeet] += 1		bigTaperMeets = [i for i in taperMeets if taperMeets[i]>2]		return bigTaperMeets	# returns improvemnt data from db, from season1 to season2	def getImprovement(self, gender='Men', teams=MIAC, season1=thisSeason()-1, season2=thisSeason()-2):		posSeasons = [2017, 2016, 2015, 2014, 2013, 2012, 2011]		#print season1, season2		if season1 > season2 and season1 in posSeasons and season2 in posSeasons:			seasons = range(season2, season1)			#print seasons		teamImprovement = {}		for swim in Improvement.select().where(Improvement.fromseason << seasons, Improvement.gender==gender,									   Improvement.team << list(teams)):			if swim.team not in teamImprovement:				teamImprovement[swim.team] = []			teamImprovement[swim.team].append(swim.improvement)		if len(teams)==1 and teams[0] in teamImprovement:			return teamImprovement[teams[0]]		return teamImprovement	def storeImprovement(self):		season = 2017		swims = []		for team in TeamSeason.select().where(TeamSeason.season==season):			preTeam = team.getPrevious()			if not preTeam:				continue			top1 = team.getTaperSwims(structured=True)			top2 = preTeam.getTaperSwims(structured=True)			for swimmer in top1:				if not swimmer in top2:					continue				for event in top1[swimmer]:					if not event in top2[swimmer]:						continue					swim1 = top1[swimmer][event]					swim2 = top2[swimmer][event]					time1 = swim1.time					time2 = swim2.time					drop = (time2-time1) / ((time1+time2) / 2) * 100					#print swimmer, event, time1, time2					if abs(drop) > 10:  # toss outliers						continue					newSwim = {'fromseason': season-1, 'toseason': season, 'name': swim1.name,							   'fromyear': swim2.year, 'toyear': swim1.year,							   'team': team.team, 'gender': team.gender, 'event': event,							   'improvement': drop,  # positive=faster							   'fromtime': swim2.time, 'totime': swim1.time,							   'conference': team.conference, 'division': team.division}					#print newSwim					swims.append(newSwim)		print len(swims)		db_proxy.connect()		for i in range(len(swims) / 100):			print i			with db_proxy.transaction():				Improvement.insert_many(swims[i*100:(i+1)*100]).execute()	def timedrops(self):		timeDrops = {'Men': {}, 'Women': {}}		dropDif = {'Men': {}, 'Women': {}}		for season in [2008, 2009, 2010]:			for rank in [1, 16, 200]:				for swim in Swim.raw('SELECT event, time, gender, rank, name, meet, team, division, year FROM '					'(SELECT name, time, event, meet, team, year, gender, division, rank() '					'OVER (PARTITION BY gender, event, division ORDER BY time, name, meet) '					'FROM swim '					'WHERE swim.season = %s) AS a '					'WHERE a.rank=%s order by gender, event ', season, rank):					if swim.division != 'D3': continue					if swim.event not in timeDrops[swim.gender]:						timeDrops[swim.gender][swim.event] = {}						dropDif[swim.gender][swim.event] = {}					if str(rank) not in timeDrops[swim.gender][swim.event]:						timeDrops[swim.gender][swim.event][str(rank)] = {}						dropDif[swim.gender][swim.event][str(rank)] = {}					if str(season) not in timeDrops[swim.gender][swim.event][str(rank)]:						timeDrops[swim.gender][swim.event][str(rank)][str(season)] = {}					timeDrops[swim.gender][swim.event][str(rank)][str(season)] = swim.time				#print timeDrops		improvements = []		impStroke = {'Breastroke': [], 'Backstroke': [], 'Butterfly': [], 'Freestyle': [], 'IM': []}		impGender = {'Men': [], 'Women': []}		impDistance = {'50': [], '100': [], '200': [], 'distance': []}		impRank = {'1': [], '16': [], '200': []}		for gender in timeDrops:			for event in timeDrops[gender]:				for rank in timeDrops[gender][event]:					time7 = timeDrops[gender][event][rank]['2008']					time8 = timeDrops[gender][event][rank]['2009']					time9 = timeDrops[gender][event][rank]['2010']					perImp = ((time8 - (time7 + time9) / 2.0) / time8) * 100					dropDif[gender][event][rank] = perImp					improvements.append(perImp)					if 'Breastroke' in event:						impStroke['Breastroke'].append(perImp)					elif 'Backstroke' in event:						impStroke['Backstroke'].append(perImp)					elif 'Butterfly' in event:						impStroke['Butterfly'].append(perImp)					elif 'Freestyle' in event:						impStroke['Freestyle'].append(perImp)					elif 'Individual Medley' in event:						impStroke['IM'].append(perImp)					impGender[gender].append(perImp)					impRank[str(rank)].append(perImp)					if '100' in event:						impDistance['100'].append(perImp)					elif '200' in event:						impDistance['200'].append(perImp)					elif event == '50 Yard Freestyle':						impDistance['50'].append(perImp)					elif '500 Yard' in event or '1650 Yard' in event or '400 Yard Individual Medley' in event:						impDistance['distance'].append(perImp)				print gender + ',' + event + ',' + str(round(np.mean(dropDif[gender][event].values()), 3))		print np.mean(improvements)		for gender in impGender:			print gender, np.mean(impGender[gender])		for stroke in impStroke:			print stroke, np.mean(impStroke[stroke])		for distance in impDistance:			print distance, np.mean(impDistance[distance])		for rank in impRank:			print rank, np.mean(impRank[rank])	def timeHistograms(self):		times = {'2008':[], '2009':[], '2010':[]}  # 2016 is the only season with all the times		#times = {}		#for season in range(2008, 2017):		#	times[str(season)] = []		for season in times:			for swim in Swim.select(Swim.time).where(Swim.division=='D1', Swim.gender=='Women',				Swim.event=='100 Yard Freestyle', Swim.season==int(season)).limit(3000).order_by(Swim.time):				times[season].append(swim.time)		#print len(times[season])		plt.hist(times['2009'], 30, alpha=0.5, label='2009')		plt.hist(times['2010'], 30, alpha=0.5, label='2010')		plt.hist(times['2008'], 30, alpha=0.5, label='2008')		plt.legend(loc='upper right')		plt.show()	def timePlacePPts(self, place=100, division='D1', gender='Women', season=2011):		points = {}		for season in [2011, 2012, 2013, 2014]:			points[season] = {}			for divGen in [('Men', 'D1'), ('Men', 'D3'), ('Women', 'D1'), ('Women', 'D3')]:				gender = divGen[0]				division = divGen[1]				points[season][division + gender] = {}				for event in indEventOrder:					for swim in Swim.raw("select * from swim where event=%s and season=%s and division=%s and gender=%s order "								 "by time limit 1 offset %s",							 event, season, division, gender, place):						print event, season, division, gender, place, swim.getPPTs()						points[season][division + gender][event] = swim.getPPTs()		print indEventOrder		for season in points:			for divGen in points[season]:				output = str(season) + ',' + divGen				for event in indEventOrder:					output += ',' + str(round(points[season][divGen][event], 2))				print outputif __name__ == "__main__":	# database setup	urlparse.uses_netloc.append("postgres")	if "DATABASE_URL" in os.environ:  # production		url = urlparse.urlparse(os.environ["DATABASE_URL"])		db = PostgresqlDatabase(database=url.path[1:],								user=url.username,								password=url.password,								host=url.hostname,								port=url.port)	else:		db = PostgresqlDatabase('swimdb', user='hallmank')	database = SwimDatabase(db)	#database.timePlacePPts()	#database.timedrops()	#print database.storeImprovement()	#database.updateConferenceProbs(weeksIn=14)	for division in ['D1', 'D2', 'D3']:		for gender in ['Men', 'Women']:			print division, gender			database.updateTeamStats(division=division, gender=gender, week=1)			database.updateTeamStats(division=division, gender=gender, week=2)