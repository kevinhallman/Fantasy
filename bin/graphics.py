import plotly.plotly as py
import plotly.graph_objs as go
import plotly.offline as offline

dataMatrix = [['200 Yard Backstroke 200 Yard Freestyle 500 Yard Freestyle', 148, 0.64]
['100 Yard Backstroke 100 Yard Butterfly 200 Yard Butterfly', 158, 0.6],
['100 Yard Breastroke 100 Yard Butterfly 200 Yard Breastroke', 160, 0.46],
['1650 Yard Freestyle 200 Yard Butterfly 500 Yard Freestyle', 162, 0.58]
['100 Yard Breastroke 200 Yard Breastroke 400 Yard Individual Medley', 191, 0.53],
['100 Yard Backstroke 200 Yard Backstroke 200 Yard Freestyle', 211, 0.6],
['100 Yard Backstroke 200 Yard Backstroke 500 Yard Freestyle', 225, 0.5],
['200 Yard Backstroke 200 Yard Individual Medley 400 Yard Individual Medley', 247, 0.71],
['100 Yard Butterfly 200 Yard Butterfly 50 Yard Freestyle', 247, 0.59],
['200 Yard Breastroke 200 Yard Individual Medley 400 Yard Individual Medley', 264, 0.75],
['100 Yard Butterfly 200 Yard Butterfly 500 Yard Freestyle', 276, 0.54],
['200 Yard Butterfly 200 Yard Individual Medley 400 Yard Individual Medley', 282, 0.72],
['100 Yard Breastroke 100 Yard Freestyle 50 Yard Freestyle', 300, 0.55],
['100 Yard Breastroke 200 Yard Breastroke 50 Yard Freestyle', 371, 0.5],
['100 Yard Backstroke 200 Yard Backstroke 50 Yard Freestyle', 373, 0.57],
['100 Yard Backstroke 100 Yard Butterfly 200 Yard Backstroke', 403, 0.6],
['1650 Yard Freestyle 400 Yard Individual Medley 500 Yard Freestyle', 444, 0.63],
['100 Yard Backstroke 100 Yard Freestyle 50 Yard Freestyle', 474, 0.63],
['100 Yard Freestyle 200 Yard Freestyle 500 Yard Freestyle', 602, 0.65],
['100 Yard Butterfly 200 Yard Butterfly 200 Yard Individual Medley', 604, 0.6],
['100 Yard Backstroke 200 Yard Backstroke 200 Yard Individual Medley', 647, 0.63],
['100 Yard Butterfly 100 Yard Freestyle 50 Yard Freestyle', 893, 0.64],
['1650 Yard Freestyle 200 Yard Freestyle 500 Yard Freestyle', 1211, 0.61],
['100 Yard Freestyle 200 Yard Freestyle 50 Yard Freestyle', 1301, 0.64],
['100 Yard Breastroke 200 Yard Breastroke 200 Yard Individual Medley', 1562, 0.59]]


offline.plot({
			"data": [
				go.Scatter(
					x=timesX,
					y=dif,
					mode='markers',
					name='Men'
				),
				go.Scatter(
					x=timesXW,
					y=difW,
					mode='markers',
					name='Women'
				),
				go.Scatter(
					x=[timeStart, timeEnd],
					y=[fit_fn(timeStart), fit_fn(timeEnd)],
					mode='line',
					name='Men Fit'
				),
				go.Scatter(
					x=[timeStartW, timeEndW],
					y=[fit_fnW(timeStartW), fit_fnW(timeEndW)],
					mode='line',
					name='Women Fit'
				)
			],
    		"layout": go.Layout(title=event)
		},
		filename=event)