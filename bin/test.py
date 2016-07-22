import re

with open('data/CollegeswimmingHSTimesMen827.txt') as file:
	for line in file:
		parts = line.split('|')
		name = parts[1]
		if not re.search('[a-z]', name):
			nameP = re.match('(.)(.*), (.)(.*)?', name)
			if nameP:
				if ' ' in nameP.group(4):
					lastName = nameP.group(4)[:-2].lower()
				else:
					lastName = nameP.group(4).lower()
				newName = nameP.group(1) + nameP.group(2).lower() + ', ' + nameP.group(3) + lastName
				#print newName
		else:
			if name[-2] == ' ':
				newName = name[:-2]  #strip mi
			else:
				newName = name

		team = parts[0].strip()
		time = parts[5].strip()
		year = parts[2]
		event = parts[4]
		if ' L ' in event: #no long course times
			continue
		event = event.replace('Free', 'Freestyle')
		event = event.replace('Breast', 'Breastroke')
		event = event.replace('Fly', 'Butterfly')
		event = event.replace('Back', 'Backstroke')
		event = event.replace('IM', 'Individual Medley')
		event = event.replace(' Y ', ' Yard ')
		team = team.replace('&amp;', '&')
		team = team.replace('&#39;', '\'')
		newName = newName.replace('&#39;', '\'')
		print team + '|' + newName + '|' + year + '|' + event + '|' + time + '|' + 'Men'
		'''
		if '&' in team:
			print team
		if '&' in newName:
			print newName
		'''