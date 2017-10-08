allevents = ['1650 Free', '1500 Free', '1000 Free', '800 Free', '500 Free', '400 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM', '400 IM']

ageGroupsChamp = ['10-', '11-12', '13-14', '15-18', '19+']
ageGroupsAll = ['8-', '9-10', '11-12', '13-14', '15-16', '17-18', '19-22', '22+']

allEventsSCY = ['1650 Free', '1000 Free', '500 Free', '400 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM', '400 IM']

eventsSCY = {}
eventsSCY['11-12'] = eventsSCY['10-'] = ['50 Free', '100 Free', '200 Free', '500 Free'
				'50 Fly', '100 Fly',
				'50 Back', '100 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM']
eventsSCY['13-14'] = ['1650 Free', '500 Free', '200 Free', '100 Free', '50 Free',
				'100 Fly', '200 Fly',
				'100 Back', '200 Back',
				'100 Breast', '200 Breast',
				'200 IM', '400 IM']
eventsSCY['19+'] = eventsSCY['15-18'] = eventsSCY['13-14']

eventConvert = {'1650 Free':'1650 Yard Freestyle',
				'500 Free': '500 Yard Freestyle',
				'200 Free':'200 Yard Freestyle',
				'100 Free':'100 Yard Freestyle',
			 	'50 Free':'50 Yard Freestyle',
				'100 Fly':'100 Yard Butterfly',
				'200 Fly':'200 Yard Butterfly',
				'100 Back':'100 Yard Backstroke',
				'200 Back':'200 Yard Backstroke',
				'100 Breast': '100 Yard Breastroke',
			   	'200 Breast': '200 Yard Breastroke',
				'200 IM': '200 Yard Individual Medley',
			   	'400 IM': '400 Yard Individual Medley'}


SCMfactor = {'Men':
			{'50 Free': 1.023590926,
			'100 Free': 1.029557805,
			'200 Free': 1.024409523,
			'400 Free': 0.917095814,
			'800 Free': 0.920460079,
			'1500 Free': 0.991358102,
			'50 Back': 1.026385618,
			'100 Back': 1.015631027,
			'200 Back': 1.022796962,
			'50 Breast': 1.023463317,
			'100 Breast': 1.009632222,
			'200 Breast': 1.010580528,
			'50 Fly': 1.025226574,
			'100 Fly': 1.030784375,
			'200 Fly': 1.027486823,
			'200 IM': 1.024460257,
			'400 IM': 1.026097941},
		'Women':
			 {'50 Free': 1.023852327,
			'100 Free': 1.026297279,
			'200 Free': 1.028988581,
			'400 Free': 0.909249615,
			'800 Free': 0.916659786,
			'1500 Free': 0.990508763,
			'50 Back': 1.030394157,
			'100 Back': 1.018476035,
			'200 Back': 1.01748535,
			'50 Breast': 1.028831003,
			'100 Breast': 1.018742229,
			'200 Breast': 1.021378194,
			'50 Fly': 1.030428254,
			'100 Fly': 1.024434017,
			'200 Fly': 1.038638242,
			'200 IM': 1.020100494,
			'400 IM': 1.028537708}
			 }
eventtoSCY = {'1500 Free': '1650 Free',
				'400 Free': '500 Free',
				'200 Free': '200 Free',
				'100 Free': '100 Free',
			 	'50 Free': '50 Free',
			  	'50 Fly': '50 Fly',
				'100 Fly': '100 Fly',
				'200 Fly': '200 Fly',
			  	'50 Back': '50 Fly',
				'100 Back': '100 Back',
				'200 Back': '200 Back',
				'100 Breast': '100 Breast',
			   	'200 Breast': '200 Breast',
				'200 IM': '200 IM',
			   	'400 IM': '400 IM'}

eventsSCM = ['1500 Free', '400 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM', '400 IM']

eventsLCM = ['1500 Free', '400 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'200 IM', '400 IM']