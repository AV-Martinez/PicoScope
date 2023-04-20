import configparser
config = configparser.ConfigParser()

def save_config():
	with open("PicoScope.ini", "w") as configfile:
		config.write(configfile)

"""
Given the minimum of 2 microseconds to take one sample, and considering that the 
shape of a sine requires at least 5 samples for a minimum valid approximation (triangle),
then the minimum period is 2us/sample * 5samples = 10us => 100KHz
"""
input_stage_testing_frequencies = [10,20,50,100,200,500,1000,2000,5000,10000,20000,50000,100000]
	
import os.path
if not os.path.exists("PicoScope.ini"):
	config["PicoScope-Window"]		 = {"xpos":10, "ypos":10}
	config["Settings-Window"]		 = {"xpos":20, "ypos":20}
	config["Settings-Board"]		 = {"Port":"/dev/ttyACM0", "WakeUpColor":"Red" }
	config["Settings-Osc-Display"]	 = {"DPI":96, "CanvasWidth":"25%%", "CanvasHeight":"25%%"}
	config["Osc-HorizontalAxis"]  	 = {"Mode":"Oscilloscope", "TimeDiv":"10 ms", "FreqDiv":"100 Hz", "Trigger":"Ch 1"}
	config["Osc-Ch1"] 				 = {"VerticalDivision":"1 V", "Offset":"0", "Color":"Yellow","Enabled":"True",  "InputStageTrFunc":"" }
	config["Osc-Ch2"] 				 = {"VerticalDivision":"1 V", "Offset":"0", "Color":"Blue",  "Enabled":"False", "InputStageTrFunc":"" }
	config["Osc-Window"]			 = {"xpos":100, "ypos":100}
	config["FuncGen"]				 = {"xpos":110, "ypos":110, "Mode":"PWM", "Frequency":100, "DutyCycle":50, "Shape":"Sine"}
	config["FuncGen-AD9833"]		 = {"xpos":110, "ypos":110, "Frequency":100, "Shape":"Sine"}
	
	tf_dict = {}
	for f in input_stage_testing_frequencies:
		tf_dict[f] = 0
		
	config["Osc-Ch1"]["InputStageTrFunc"] = str(tf_dict)
	config["Osc-Ch2"]["InputStageTrFunc"] = str(tf_dict)
			
	save_config()

config.read("PicoScope.ini")

import Board
board = Board.Board(config["Settings-Board"]["Port"])

toplevel_windows = {"Settings":			None,
					"Oscilloscope":		None, 
					"FuncGen":			None,
					"FrequencyMeter":	None }

