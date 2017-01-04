import reimport numpy as npimport operatorfrom operator import itemgetterfrom datetime import date, timedeltafrom peewee import *import os, urlparseimport heapqimport time as Timefrom swimdb import Improvement, Team, TeamStats, TeamSeason, Swimmer, Swimfrom swimdb import TempMeet as MeetpointsChampionship = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]pointsDualI = [9, 4, 3, 2, 1]pointsDualR = [11, 4, 2]eventsDualS = ["200 Yard Medley Relay","1000 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay"]eventsDualL = ["400 Yard Medley Relay","1650 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","400 Yard Individual Medley","400 Yard Freestyle Relay"]eventsChamp = ["400 Yard Medley Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","400 Yard Individual Medley","1650 Yard Freestyle","200 Yard Medley Relay","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay"]eventsChamp3 = ['1 mtr Diving','200 Yard Freestyle Relay','','500 Yard Freestyle','200 Yard Individual Medley', '50 Yard Freestyle','','400 Yard Medley Relay','','400 Yard Individual Medley','100 Yard Butterfly','200 Yard Freestyle','100 Yard Breastroke','100 Yard Backstroke','','800 Yard Freestyle Relay','','1650 Yard Freestyle','','200 Yard Medley Relay','','200 Yard Backstroke','100 Yard Freestyle','200 Yard Breastroke','200 Yard Butterfly','','400 Yard Freestyle Relay','3 mtr Diving']#eventsChamp3 = ['500 Yard Freestyle','200 Yard Individual Medley', '50 Yard Freestyle','','400 Yard Individual# Medley','100 Yard Butterfly','200 Yard Freestyle','100 Yard Breastroke','100 Yard Backstroke','','1650 Yard Freestyle','','200 Yard Backstroke','100 Yard Freestyle','200 Yard Breastroke','200 Yard Butterfly']eventsDay1 = ['1 mtr Diving','200 Yard Freestyle Relay','500 Yard Freestyle','200 Yard Individual Medley','50 Yard Freestyle','400 Yard Medley Relay']eventsDay2 = ['400 Yard Individual Medley','100 Yard Butterfly','200 Yard Freestyle','100 Yard Breastroke','100 Yard Backstroke','800 Yard Freestyle Relay']eventsDay3 = ['1650 Yard Freestyle','200 Yard Medley Relay','200 Yard Backstroke','100 Yard Freestyle','200 Yard Breastroke','200 Yard Butterfly','400 Yard Freestyle Relay','3 mtr Diving']allEvents={"400 Yard Medley Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","400 Yard Individual Medley","1650 Yard Freestyle","200 Yard Medley Relay","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay",'1000 Yard Freestyle','100 Yard Breastroke','200 Yard Breastroke'}eventsChampInd={"400 Yard Individual Medley","1650 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley",'100 Yard Breastroke','200 Yard Breastroke'}MIAC = ["Carleton","Augsburg","St. Olaf","Saint Mary's MN","Macalester","Gustavus","Saint Benedict","St. Kate's","Concordia","St. John's","St. Thomas","Hamline"]requiredEvents={"200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly"}eventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay"]#setup database connectiondb_proxy = Proxy()db = Proxy()'''events contained within a relay'''def relayEvents(relay):	dist=str(int(re.findall('\d\d\d',relay)[0])/4)	if re.search('Free',relay):		return [dist+' Yard Freestyle']+[dist+' Yard Freestyle Split']*3	return  [dist+' Yard Backstroke Split',dist+' Yard Breastroke Split',dist+' Yard Butterfly Split',dist+' Yard Freestyle Split']def thisSeason():	today = date.today()	if today.month > 6:		return today.year + 1	return today.yeardef rejectOutliers(dataX, dataY=None, l=5, r=6):	u = np.mean(dataX)	s = np.std(dataX)	if dataY:		data = zip(dataX, dataY)		newList = [i for i in data if (u - l*s < i[0] < u + r*s)]		newX, newY = zip(*newList)		return list(newX), list(newY)	else:		newList = [i for i in dataX if (u - l*s < i < u + r*s)]	return newListdef ECDF(data):	def cdf(num):		d = data		l = float(len(d))		return (sum(1 for i in d if i < num) + sum(.5 for i in d if i==num))/l	return cdfdef getConfs():	confs = {'D1': {'Men': {}, 'Women': {}}, 'D2': {'Men': {}, 'Women': {}}, 'D3': {'Men': {}, 'Women': {}}}	allTeams = {'Men': {'D1': [], 'D2': [], 'D3': []}, 'Women': {'D1': [], 'D2': [], 'D3': []}}	for newTeam in TeamSeason.select(TeamSeason.team, TeamSeason.conference, TeamSeason.division,									 TeamSeason.gender).distinct(TeamSeason.team):		if newTeam.conference not in confs[newTeam.division][newTeam.gender]:			confs[newTeam.division][newTeam.gender][newTeam.conference] = set()		confs[newTeam.division][newTeam.gender][newTeam.conference].add(newTeam.team)		allTeams[newTeam.gender][newTeam.division].append(newTeam.team)		for division in ['D1', 'D2', 'D3']:			allTeams['Men'][division].sort()			allTeams['Women'][division].sort()	return confs, allTeamsdef nextYear(year):	if year=='Freshman':		return 'Sophomore'	if year=='Sophomore':		return 'Junior'	if year=='Junior':		return 'Senior'	return Nonedef grad(f, x, y, h=0.0025):	dx = (f(x, y) - f(x+h, y))/h	dy = (f(x, y) - f(x, y+h))/h	return dx, dydef gradientDescent(f, x0, y0, step=.001):	for i in range(10):		dx, dy = grad(f, x0, y0)		length = ((dx**2 + dy**2) ** .5)		print 'delta:', dx, dy		x0 += step * dx / length		y0 += step * dy / length		if x0 < 0:			x0 = 0.001		if y0 < 0:			y0 = 0.001		#print x0, y0	return x0, y0def frange(x, y, jump):	while x < y:		yield x		x += jumpdef date2week(d):	if d > date.today():		d = date.today()	if d.month > 6:		season = d.year + 1	else:		season = d.year	startDate = date(season - 1, 10, 15)  # use Oct 15 as the start date, prolly good for 2017	weeksIn = int((date - startDate).days / 7)	return weeksIndef week2date(week, season=None):	if not season:		season = thisSeason()	startDate = date(season - 1, 10, 16)  # use Oct 15 as the start date, prolly good for 2017	if week == None:		return date.today()	simDate = startDate + timedelta(weeks=week)	if simDate > date.today():  # can't simulate with future data		simDate = date.today()	return simDate'''conference level information'''class conference:	def __init__(self, name, gender, season, division):		self.conference = name		self.gender = gender		self.season = season		self.teams = set()		self.division = division		for team in TeamSeason.select().where(TeamSeason.gender==gender, TeamSeason.season==season,									TeamSeason.conference==name):			self.teams.add(team)	def meet(self, topTimes=True, date=None, update=False, taper=False, weeksIn=10, nextYear=False):		events = eventsChamp3		swimmerLimit = 17		weeksOut = 16 - weeksIn		base = SwimDatabase('')		conference = base.topTimes(events=events, teams=list(self.teams), season=self.season, gender=self.gender,								   topTimes=topTimes, divisions=self.division, date=date)		season = self.season		if nextYear:			conference.nextYear(self)			season += 1  # update the correct season			weeksOut = '-1'			weeksIn = '-1'		if taper: conference.taper()		conference.topEvents(swimmerLimit)		conference.score()		# update stored win probabilities		if update:			conference.scoreMonteCarlo(weeksOut=weeksOut)			teamProb = conference.getWinProb()			for team in teamProb:				teamSeason = TeamSeason.get(team=team, division=self.division, gender=self.gender, season=season)				try:					stats = TeamStats.get(teamseasonid=teamSeason.id, week=weeksIn)					stats.winconf = teamProb[team]					print team, season, stats.winconf, weeksIn, date, teamSeason.id, stats.id					print stats.save()				except TeamStats.DoesNotExist:					print 'AB:', team, season, teamProb[team], weeksIn, date					print TeamStats.create(teamseasonid=teamSeason.id, week=weeksIn, winconf=teamProb[team], date=date)	def getStats(self):		teamStats = {}		for team in self.teams:			teamStats[team.name] = {}			teamStats[team.name]['winNats'] = team.getWinnats()			teamStats[team.name]['winConf'] = team.getWinconf()			# team development			# print team, session.gender, session.division			try:				stats = Team.get(Team.name==team.name, Team.gender==self.gender, Team.division==self.division)				teamStats[team.name]['strinv'] = stats.strengthinvite				teamStats[team.name]['attrition'] = stats.attrition				teamStats[team.name]['imp'] = stats.improvement			except Team.DoesNotExist:				teamStats[team.name]['strinv'] = None				teamStats[team.name]['attrition'] = None				teamStats[team.name]['imp'] = None			(medtaper, stdtaper) = team.getTaperStats()			teamStats[team.name]['medtaper'] = medtaper			teamStats[team.name]['stdtaper'] = stdtaper	def getTopSwimmers(self, num=10):		swimmers = []		for team in self.teams:			for swimmer in Swimmer.select().where(Swimmer.teamid==team.id):				if 'Relay' in swimmer.name: continue				heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))		return heapq.nlargest(num, swimmers)'''full database methods'''class SwimDatabase:	def __init__(self, database):		global swimDatabase		swimDatabase = self		db_proxy.initialize(database)		self.database = database		self.dist = {}		self.results = {}  # cache dual results		self.teams = {}		self.meetCache = {}		self.eventImpCache = {}		self.topScoreCache = {}		self.topTimesCache = {}		self.conferences, self.allTeams = getConfs()	def topDual(self, season=thisSeason(), events=requiredEvents, debug=False, teams='all', gender='Men'):		if teams == 'all':			teams = self.teams		meets = {}		wins = {}		losses = {}		for team in teams:			if not team in self.teams:				self.teams[team] = Team(team, self)			if not self.teams[team].topDual(season, debug=debug, gender=gender):				continue			meets[team] = self.teams[team].topDual(season, debug=debug, gender=gender)  # its cached			wins[team] = 0			losses[team] = 0			#if debug: print team, '\t\t', meets[team]		if debug: print '-----------'		for team1 in meets:			for team2 in meets:				if team1 == team2:					continue				if not team1 in self.results:					self.results[team1] = {}				if not team2 in self.results:					self.results[team2] = {}				if team2 in self.results[team1] or team1 in self.results[team2]:  # reverse meet already swum					continue				newMeet = self.swimMeet([[team1, meets[team1]], [team2, meets[team2]]], includeEvents=events,									  selectEvents=False)  # should convert to dual form				self.results[team1][team2] = newMeet.winningTeam()				self.results[team2][team1] = newMeet.winningTeam()				if debug: print team1, team2, newMeet.winningTeam()				if self.results[team1][team2] == team1: # team1 wins					wins[team1] += 1					losses[team2] += 1				elif self.results[team1][team2] == team2:  # team2 wins, otherwise no points					wins[team2] += 1					losses[team1] += 1		if debug:			for (index, team) in enumerate(sorted(wins.items(), key=operator.itemgetter(1), reverse=True)):				print str(index)+'.',team[0]+':',team[1],'-',losses[team[0]]		return meets, wins, losses	'''	creates a swim meet with given teams and meets format is [(team1,meet1),(team2,meet2),...]	'''	def swimMeet(self, teamMeets, gender=None, debug=False, includeEvents='all', excludeEvents=set(),				 selectEvents=True, resetTimes=False):		if debug: print teamMeets		meet = Meet()		teams = []		if includeEvents == 'all':			includeEvents = allEvents		commonEvents = allEvents		for teamMeet in teamMeets:			newTeamName = None			newTeam = teamMeet[0]			newMeet = teamMeet[1]			if len(teamMeet) >= 3 and teamMeet[2]:  # maybe pass in new team name				newTeamName = teamMeet[2]			if len(teamMeet) == 4:				season = teamMeet[3]			else:				season = None			if isinstance(newMeet, basestring):  # just a name				newMeet = Meet(name=newMeet, gender=gender, teams=[newTeam], season=season)			commonEvents = commonEvents & set(newMeet.eventSwims.keys())			if debug:				print set(newMeet.eventSwims.keys())				newMeet.printout()			duplicates = None			if not newTeamName:				duplicates = teams.count(newTeam)				teams.append(newTeam)			else:				teams.append(newTeamName)			for swim in newMeet.getSwims(newTeam):				if duplicates:					swim.scoreTeam = swim.getScoreTeam() + ' ' + str(duplicates + 1)				if newTeamName:					swim.scoreTeam = newTeamName				meet.addSwim(swim)		if resetTimes:			for swim in meet.getSwims():				swim.scoreTime = swim.time		if len(meet.teams) == 2:			if selectEvents:				meet.topEvents(25, 3, 4)				'''need to fix event selection for dual meets'''			meet.events = (commonEvents | includeEvents) - excludeEvents			meet.score(dual=True)		else:			if selectEvents:				meet.topEvents()			meet.score()		if debug: meet.printout()		return meet	'''	optimal lineup creator	'''	def lineup(self, teamsSeasons, meet, debug=False, resetTimes=False, events=eventsDualS, gender='Men'):		meet.events = events		teams = []		print teamsSeasons		if debug:			print meet.getEvents(), events		for team in teamsSeasons:			teams.append(team)			if not teamsSeasons[team]:				season = thisSeason()			else:				season = teamsSeasons[team]			# handle duplicate teams			newMeet = self.topTimes(events=events, teams=[team], season=season, gender=gender, topTimes=True).getSwims()			duplicates = teams.count(team) - 1			if debug: print team, season, teams, duplicates			for swim in newMeet:				if duplicates > 0:					swim.scoreTeam = swim.getScoreTeam() + ' ' + str(duplicates + 1)					# print swim.getScoreTeam() + ' ' + str(duplicates + 1)				meet.addSwim(swim)		if resetTimes:			for swim in meet.getSwims():				swim.scoreTime = swim.time		meet.place()		teams = teamsSeasons.keys()		if debug:			meet.printout()		# lineup optimize if creating linup for just one team		if len(teams) == 1:			meet.lineup(teams.pop(), debug=debug)		else:			meet.topEvents(17, indMax=3, totalMax=4)		return meet	'''	top expected score for the whole team	'''	def topTeamScore(self, team, dual=True, season=thisSeason(), gender='Men', division='D3', weeksIn=None):		# conver the week to a date		startDate = date(season - 1, 10, 15)  # use Oct 15 as the start date, prolly good for 2017		endDate = date(season, 2, 15)  # and Feb 15 as an end date, 16 week season		if weeksIn == None:  # can't simulate with future data			simDate = date.today()			weeksIn = int((simDate - startDate).days / 7)		else:			simDate = startDate + timedelta(weeks=weeksIn)		if simDate > date.today():  # can't simulate with future data			simDate = date.today()			weeksIn = int((simDate - startDate).days / 7)		# cache off times?		if dual:			events = eventsDualS		else:			events = eventsChamp		topMeet = self.topTimes(teams=[team], season=season, gender=gender, events=events, divisions=[division],								date=simDate)		topMeet.topEvents(teamMax=17, indMax=3)		if dual:			scores = topMeet.expectedScores(swimmers=6, division=division)		else:			scores = topMeet.expectedScores(swimmers=16, division=division)		if team in scores:			return scores[team]		return 0	'''	returns meet of top times	'''	def topTimes(self, events=None, teams=MIAC, season=None, gender='Men', topTimes=True, meetForm=True,				divisions='all', date=None):		sentinelString = str(events)+str(teams)+str(season)+str(gender)+str(topTimes)+str(divisions)+str(date)		if meetForm and sentinelString in self.topTimesCache:			return self.topTimesCache[sentinelString]		if not events:			events = allEvents		if teams == 'all':			teams = self.teams		if divisions == 'all':			divisions = ['D1', 'D2', 'D3']		if not season:			season = thisSeason()  # use current season		topMeet = Meet(events=events)		swimmers = {}		select = Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason)\				.where(TeamSeason.gender==gender, TeamSeason.team << list(teams), TeamSeason.division << list(divisions),			   	TeamSeason.season==season, Swim.event << list(events))		if topTimes:			if date:				qwery = select.select(Swim.name, Swim.event, fn.Min(Swim.time), Swimmer.team, Swimmer.year).group_by(					Swim.name, Swim.event, Swimmer.team, Swimmer.year).where(Swim.date < date)			else:				qwery = select.select(Swim.name, Swim.event, fn.Min(Swim.time), Swimmer.team, Swimmer.year).group_by(Swim.name,					Swim.event, Swimmer.team, Swimmer.year)		else:  # mean time for the season			qwery = select.select(Swim.name, Swim.event, fn.Avg(Swim.time), Swimmer.team, Swimmer.year).group_by(Swim.name,				Swim.event, Swimmer.team, Swimmer.year)		for swim in qwery:			if topTimes:				time = swim.min			else:				time = swim.avg			newSwim = Swim(name=swim.name, event=swim.event, time=time, gender=gender, team=swim.swimmer.team,									  season=season, year=swim.swimmer.year, swimmer=swim.swimmer)			if meetForm:				topMeet.addSwim(newSwim)			else:				if not swim.team in swimmers:					swimmers[swim.team] = {}				if not swim.name in swimmers[swim.team]:						swimmers[swim.team][swim.name] = {}				swimmers[swim.team][swim.name][swim.event] = newSwim		if meetForm:			topMeet.place()			self.topTimesCache[sentinelString] = topMeet			return topMeet		return swimmers	def conference(self, teams=MIAC, season=None, topTimes=True, gender='Men', divisions='D3', date=None,				   update=False, taper=False, weeksIn=10, nextYear=False, nats=False):		events = eventsChamp3		if not season:			season = thisSeason()  # use current season		conference = self.topTimes(events=events, teams=teams, season=season, gender=gender, topTimes=topTimes,								   divisions=[divisions], date=date)		if nextYear:			conference.nextYear(self)			season += 1  # update the correct season		if taper:			conference.taper()		swimmerLimit = 17		conference.topEvents(swimmerLimit)		conference.score()		# update stored win probabilities		weeksOut = 16 - weeksIn		if nextYear:			weeksOut = '-1'			weeksIn = '-1'		if update:			conference.scoreMonteCarlo(weeksOut=weeksOut)			teamProb = conference.getWinProb()			for team in teamProb:				teamSeason = TeamSeason.get(team=team, division=divisions, gender=gender, season=season)				try:					stats = TeamStats.get(teamseasonid=teamSeason.id, week=weeksIn)					if nats:						stats.winnats = teamProb[team]					else:						stats.winconf = teamProb[team]					print 'Existing:', team, season, stats.winconf, weeksIn, date, teamSeason.id, stats.id					print stats.save()				except TeamStats.DoesNotExist:					print 'New:', team, season, teamProb[team], weeksIn, date					if nats:						TeamStats.create(teamseasonid=teamSeason.id, week=weeksIn, winnats=teamProb[team], date=date)					else:						TeamStats.create(teamseasonid=teamSeason.id, week=weeksIn, winconf=teamProb[team], date=date)		return conference	# simulate a national swim meet, will update the db with win probs if update	def nationals(self, season=None, topTimes=True, gender='Men', division='D3', simDate=None, update=False,				  nextYear=False, weeksIn=4):		teams = self.allTeams[gender][division]		print season		startDate = date(season - 1, 10, 15)  # use Oct 15 as the start date, prolly good for 2017		print startDate		if weeksIn:			simDate = week2date(weeksIn, season)		print simDate		meet = self.conference(teams=teams, season=season, topTimes=topTimes, gender=gender, divisions=division,							   date=simDate, nextYear=nextYear, nats=True, update=update, weeksIn=weeksIn)		meet.scoreMonteCarlo(dual=False, weeksOut=16-weeksIn)		# update db with win probs		print meet.getWinProb()		if update:			teamProb = meet.getWinProb()			for team in teamProb:				print team, teamProb[team]				TeamSeason.update(winnats=teamProb[team]).where(TeamSeason.team==team, TeamSeason.season==season+1,											TeamSeason.gender==gender, TeamSeason.division==division).execute()		return meet	'''	returns top 25 teams and caches ranking data	'''	def teamRank(self, division='D3', gender='Men', season=2016, num=25):		teamScores = {}		for team in TeamSeason.select().where(TeamSeason.gender==gender, TeamSeason.division==division,								TeamSeason.season==season):			teamScores[team.team] = team		return sorted(teamScores.values(), key=lambda t: t.getStrength(), reverse=True)[:25]	# update the probabilities of winning conference	def updateConferenceProbs(self, division='D3', gender='Women', season=2017, weeksIn=None, forceUpdate=False):		simDate = week2date(weeksIn, season)		startDate = week2date(0, season)		print simDate		for team in TeamSeason.select().where(TeamSeason.division==division, TeamSeason.gender==gender,					TeamSeason.season==season):			try:				stats = TeamStats.get(teamseasonid=team.id, week=weeksIn)				if stats.winconf is not None and not forceUpdate:  # we already have data					continue				print stats.winconf, team.team				teams = self.conferences[division][gender][team.conference]				if weeksIn == -1:  # pre-season					self.conference(teams=teams, gender=gender, season=season-1, divisions=division, update=True,								nextYear=True, date=startDate)				self.conference(teams=teams, gender=gender, season=season, divisions=division, update=True,								weeksIn=weeksIn, date=simDate)			except TeamStats.DoesNotExist:				teams = self.conferences[division][gender][team.conference]				if weeksIn == -1:  # pre-season					self.conference(teams=teams, gender=gender, season=season-1, divisions=division, update=True,								nextYear=True, date=startDate)				self.conference(teams=teams, gender=gender, season=season, divisions=division, update=True,								weeksIn=weeksIn, date=simDate)	def updateTeamStrength(self, division='D3', gender='Women', season=2017, weeksIn=None, update=True):		simDate = week2date(weeksIn, season)		print simDate		for team in TeamSeason.select().where(TeamSeason.division==division, TeamSeason.gender==gender,					TeamSeason.season==season):			try:				stats = TeamStats.get(teamseasonid=team.id, week=weeksIn)				if stats.strengthinvite is None or update:					scoreInv = team.topTeamScore(dual=False, weeksIn=weeksIn)					stats.strengthinvite = scoreInv					print team.team, scoreInv				if stats.strengthdual is None or update:					scoreDual = team.topTeamScore(dual=True, weeksIn=weeksIn)					stats.strengthdual = scoreDual					print team.team, scoreDual				stats.save()			except TeamStats.DoesNotExist:				scoreInv = team.topTeamScore(dual=False, weeksIn=weeksIn)				scoreDual = team.topTeamScore(dual=True, weeksIn=weeksIn)				TeamStats.create(teamseasonid=team.id, week=weeksIn, strengthinvite=scoreInv, strengthdual=scoreDual,								 date=simDate)	def updateTeamStats(self, division='D3', gender='Women', week=6):		if week2date(week) > date.today():			return  # would be a future week		database.nationals(nextYear=False, gender=gender, division=division, season=2017, update=True, weeksIn=week)		database.updateConferenceProbs(division=division, gender=gender, season=2017, weeksIn=week)		database.updateTeamStrength(division=division, gender=gender, season=2017, weeksIn=week, update=True)	def conferencePlace(self, division, gender, newSwims, year=2014):		newEvents = set()		for swim in newSwims:			newEvents.add(swim[0])		confMeets = {}		with open('./data/' + division + gender + '.csv') as meetFile:			for line in meetFile:				(meetName, confName) = re.split('\t', line.strip())				if confName=='UAA' and confName in confMeets:  # combine that stupid UAA meet					confMeets[confName].addSwims(Meet(name=meetName, events=newEvents, gender=gender,													  topSwim=True).getSwims())				else:					confMeets[confName] = Meet(name=meetName, events=newEvents, gender=gender, topSwim=True,											   season=year)		confScores = {}		for conference in confMeets:			confMeet = confMeets[conference]			for swim in newSwims:				newSwim = Swim(event=swim[0], name='you', team='self', time=swim[1], gender=gender)				confMeet.addSwim(newSwim)			confMeet.place(storePlace=True)			confMeet.score()			confScores[conference] = {}			for swim in confMeet.getSwims():				if swim.name=='you':					confScores[conference][swim.event] = swim.place			confMeet.removeSwimmer('you')		return confScores	def taperMeets(self, year=2015, gender='Women', division='D1'):  #find meets where most best times come from		teamMeets = {}		#teams=['Univ of Utah', 'Stanford', 'California', 'Arizona', 'Southern Cali', 'Arizona St']		teams = self.allTeams[gender][division]		for team in teams:			for swim in Swim.raw("WITH topTimes AS (SELECT name, event, meet, time, row_number() OVER (PARTITION BY event,name "					 "ORDER BY time) AS rnum "					 "FROM Swim "					 "WHERE team=%s AND season=%s AND date > '%s-02-01' AND gender=%s) "					 "SELECT name,event,meet,time FROM topTimes WHERE rnum=1",					 team, year, year, gender):				if not team in teamMeets:					teamMeets[team] = []				teamMeets[team].append(swim.meet)		#print teamMeets.keys()		taperMeets = {}		for team in teamMeets:			taperMeet = max(set(teamMeets[team]), key=teamMeets[team].count)			#print team, taperMeet			if taperMeet not in taperMeets:				taperMeets[taperMeet] = 0			taperMeets[taperMeet] += 1		bigTaperMeets = [i for i in taperMeets if taperMeets[i]>2]		return bigTaperMeets	def taperSwims(self, teams, gender, conference, season=None, numTimes=3):		if season == None:			season = thisSeason()		teamSwims = {}		for team in teams:			teamSwims[team] = {}			for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(TeamSeason.team==team,					TeamSeason.gender==gender, TeamSeason.conference==conference, TeamSeason.season==season):					teamSwims[team][swimmer.name] = {}					times = []					#print team, gender					#print swimmer.name, swimmer.team					for swim in Swim.raw("WITH topTimes as "							"(SELECT name, gender, meet, event, time, year, division, swimmer_id, row_number() OVER "							"(PARTITION BY event, name ORDER BY time) as rnum "							"FROM Swim WHERE swimmer_id=%s) "							"SELECT name, event, meet, time, gender, division, year, swimmer_id FROM topTimes WHERE "										 "rnum=1",							swimmer.id):						if swim.event == '1000 Yard Freestyle': continue						cdf = self.getTimeCDF(gender, swim.division, swim.event, 100)						points = 1 - cdf(swim.time)						#print swim.time, swim.gender, swim.division, swim.event, points						heapq.heappush(times, (points, swim))					for (points, swim) in heapq.nlargest(numTimes, times):  #take three best times						#print team, swimmer.name, swim.event, points, swim.time						teamSwims[team][swimmer.name][swim.event] = swim		return teamSwims	def taperStats(self, division='D1', gender='Women', season=2016, weeks=10):		print weeks		drops = []		teamDrops = {}		startDate = date(season-1, 10, 15)  # use Oct 15 as a hard-coded start date		newDate = startDate + timedelta(weeks=weeks)		for conference in self.conferences[division][gender]:			for team in self.conferences[division][gender][conference]:				taperSwims = set()				#if not team in 'Carleton':				#	continue				topTimes = self.taperSwims(teams=[team], gender=gender, season=season, conference=conference)				for team in topTimes:					for swimmer in topTimes[team]:						for event in topTimes[team][swimmer]:							taperSwims.add(topTimes[team][swimmer][event])							#print event, swimmer				for taperSwim in taperSwims:					#print taperSwim.swimmer.season					for earlySwim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==taperSwim.swimmer,							Swim.event==taperSwim.event, Swim.date < newDate):						if earlySwim.min:							dropPer = 100 * (earlySwim.min - taperSwim.time)/taperSwim.time							drops.append(dropPer)							if team not in teamDrops:								teamDrops[team] = []							teamDrops[team].append(dropPer)							#print taperSwim.event, taperSwim.swimmer.name, earlySwim.min, taperSwim.time, dropPer		#print np.mean(drops), np.std(drops)		allStats = []		for team in teamDrops:			meanDrop = np.mean(teamDrops[team])			stdDrop = np.std(teamDrops[team])			#print team, round(meanDrop, 2), round(stdDrop, 2), len(teamDrops[team])			#print gender, division, team			try:				oldTeam = TeamSeason.get(TeamSeason.gender==gender, TeamSeason.division==division, TeamSeason.team==team,									 TeamSeason.season==season)				newStats = {'week': weeks, 'date': newDate, 'teamseasonid': oldTeam.id,						'toptaper': meanDrop, 'toptaperstd': stdDrop}				allStats.append(newStats)			except:				pass		print allStats		if len(allStats)==0:			return		# now insert into database		db_proxy.connect()		with db_proxy.transaction():			TeamStats.insert_many(allStats).execute()	# returns improvemnt data from db, from season1 to season2	def getImprovement(self, gender='Men', teams=MIAC, season1=thisSeason()-1, season2=thisSeason()-2):		posSeasons = [2016, 2015, 2014, 2013, 2012, 2011]		#print season1, season2		if season1 > season2 and season1 in posSeasons and season2 in posSeasons:			seasons = range(season2, season1)			#print seasons		teamImprovement = {}		for swim in Improvement.select().where(Improvement.fromseason << seasons, Improvement.gender==gender,									   Improvement.team << list(teams)):			if swim.team not in teamImprovement:				teamImprovement[swim.team] = []			teamImprovement[swim.team].append(swim.improvement)		if len(teams)==1 and teams[0] in teamImprovement:			return teamImprovement[teams[0]]		return teamImprovementif __name__ == "__main__":	# database setup	urlparse.uses_netloc.append("postgres")	if "DATABASE_URL" in os.environ:  # production		url = urlparse.urlparse(os.environ["DATABASE_URL"])		db = PostgresqlDatabase(database=url.path[1:],								user=url.username,								password=url.password,								host=url.hostname,								port=url.port)	else:		db = PostgresqlDatabase('swimdb', user='hallmank')	database = SwimDatabase(db)	for division in ['D1', 'D2', 'D3']:		for gender in ['Women', 'Men']:			database.updateTeamStats(division=division, gender=gender, week=11)			#for year in {2016, 2015, 2014, 2013, 2012}:			#	print division, gender, year			#	database.updateTeamStrength(division=division, gender=gender, season=year, weeksIn=20, update=False)