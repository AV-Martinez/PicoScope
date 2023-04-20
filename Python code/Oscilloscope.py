import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import time
import math

import matplotlib.pyplot 	as plt
import matplotlib.animation as animation
import matplotlib.ticker 	as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

import Globals

""" 
SIGNAL DISPLAY ACROSS THE HORIZONTAL AXIS

	Definitions
		microsPerSample: Time needed by the sourcing hardware to get a sample.
		timeDiv: Units of time per division on the x axis
		
	Description:
		The display media across the x axis is characterized as follows:
			* Samples-wise, its size must be equal to the number of samples (samples_per_frame). This is
			  the optimal situation, alternatively:
					If more samples are gathered, they will overlap when displayed.
					If less samples are gathered, the signal shape will deteriorate if changing fast enough.
			* Time-wise, it size is equal to timeDiv times the number of divisions (which equals 10)
	
	To display a signal frame, we need to capture samples_per_frame samples in timeDiv*10 millis. This imposes 
	a limit to the maximum number of samples that can be shown on a given display width. The sourcing
	hardware will deliver samples at a maximum rate of microsPerSample, so
	
							timeDiv*10 / numSamples > microsPerSample
							
	The highest frequency of the signal displayable using this approach is limited by the microsPerSample value.
	This can be overcome by using ETS. The ETS (Equivalent Time Sampling) approach is based on the following:

		1. Wait for a trigger point in the input signal.
		2. Take samples at an increasing delay until all the needed samples are gathered.
		
	This works because a precise small delay can be accomplished by just executing nops in the sourcing 
	hardware. See CaptureETS() in Oscilloscope.cpp
	
SIGNAL DISPLAY ACROSS THE VERTICAL AXIS

	The input stage consists of a compensated attenuator which allows measurement of signals larger than
	3.3 volts.

	The response of an ideal compensated attenuator should not be dependent on  the signal frequency, 
	but in reality it is. The calibration process determines the transfer function by measuring input
	voltages from a known source at different frequencies.
"""

class OscilloscopeChannel():

	def __init__(self, parent, channel_number, osc_instance, *args, **kwargs):
		self.channel_number = channel_number
		self.osc_instance   = osc_instance
		
		""" tkinter variables """
		self.frame = tk.LabelFrame(parent, text=" Channel {}: ".format(channel_number), padx=5, pady=5)

		offset_frame = tk.Frame(self.frame)
		self.offset_slide = tk.Scale(offset_frame, from_=-5, to=+5, resolution=0.1, orient="horizontal", showvalue=False, command=self.on_offset_change)
		self.offset_value = tk.Label(offset_frame)
		self.offset_slide.pack(side="left")
		self.offset_value.pack(side="left")
		
		self.enabled 	= tk.BooleanVar()
		self.enabled_cb = tk.Checkbutton(self.frame, text="Enabled: ", variable=self.enabled, command=self.on_checkbox) 
		self.color		= ttk.Combobox(self.frame, state="readonly", values=["Yellow","Blue","Red","Black"], width=10) 
		self.volts_div 	= ttk.Combobox(self.frame, state="readonly", values=["0.1 V","0.2 V","0.5 V","1 V","2 V"], width=10)
		self.info		= tk.Label(self.frame, text="")
		self.info_cb	= ttk.Combobox(self.frame, state="readonly", width=6, values=["Freq:","Volts:","Vpp:"]); 
		self.enabled_cb								.grid(row=0, column=0, sticky="e")
		tk.Label(self.frame, text="Volts/Div: ")	.grid(row=1, column=0, sticky="e")
		tk.Label(self.frame, text="Offset: ")		.grid(row=2, column=0, sticky="e")
		self.info_cb								.grid(row=3, column=0, sticky="e")
		self.color									.grid(row=0, column=1, sticky="w")
		self.volts_div								.grid(row=1, column=1, sticky="w")
		offset_frame								.grid(row=2, column=1, sticky="news", pady=5)
		self.info									.grid(row=3, column=1, sticky="w")
		
		""" set initial values for widgets """
		self.volts_div.set(Globals.config["Osc-Ch{}".format(channel_number)]["VerticalDivision"])
		self.color.set(Globals.config["Osc-Ch{}".format(channel_number)]["Color"])
		self.offset_slide.set(Globals.config["Osc-Ch{}".format(channel_number)]["Offset"]); self.on_offset_change(None)
		self.enabled.set(True if Globals.config["Osc-Ch{}".format(channel_number)]["Enabled"] == "True" else False)
		self.on_checkbox()
		self.info_cb.set("Freq:")
		
		""" input stage transfer function """
		self.tr_func = eval(Globals.config["Osc-Ch{}".format(channel_number)]["InputStageTrFunc"])
		self.tr_func_avg = 0
		for freq,attenuation in self.tr_func.items():
			self.tr_func_avg += attenuation
			if attenuation == 0:
				messagebox.showinfo(message="Channel {} requires calibration.".format(channel_number), title="Warning", parent=parent)
				break
		self.tr_func_avg = self.tr_func_avg / len(self.tr_func)
		
		""" matplotlib variables """
		self.plot_data = None
		
	def on_checkbox(self):
		self.osc_instance.on_channel_enabled(self.channel_number)
		if self.enabled.get() == False:
			self.info.configure(text="")
			Globals.board.send_command("led ch{} off".format(self.channel_number))
		else:
			Globals.board.send_command("led ch{} on".format(self.channel_number))
	
	def on_offset_change(self, event):
		self.offset_value.configure(text="{:+.1f}".format(self.offset_slide.get()))
		
	def sample_to_volts(self, sample_value, attenuation):
		return sample_value * 0.000805861 * attenuation # 0.000805861 = 3.3/4095
		
	def current_attenuation(self, period_info):
		if period_info == None:
			return self.tr_func_avg
		if period_info[1] == 0:
			return self.tr_func_avg
		if period_info[0] >= 3:
			return self.tr_func_avg
		f = int(1000000/period_info[1])
		min_freq = min(self.tr_func.keys())
		max_freq = max(self.tr_func.keys())
		if f <= min_freq: return self.tr_func[min_freq]
		if f >= max_freq: return self.tr_func[max_freq]
		f1 = None
		for freq,attenuation in self.tr_func.items():
			if freq == f: return self.tr_func[freq]
			if f1 != None:
				if f <= freq:
					f2   = freq
					att2 = self.tr_func[freq]
					break
			f1   = freq
			att1 = self.tr_func[freq]
		att = att1 + ((att2-att1)/(f2-f1))*(f-f1)
		return att
			
	def draw_frame(self, samples, period_info, operating_mode):
		volts_div = float(self.volts_div.get()[:-2])
		offset 	  = (self.offset_slide.get())*10
		
		att = self.current_attenuation(period_info)
		
		volts = [self.sample_to_volts(s,att) for s in samples]
		data  = [10*v/volts_div + offset for v in volts]
	
		if operating_mode == "Oscilloscope":
			x = np.linspace(0, 100, len(data))
			y = np.asarray(data)
		else:
			if len(data)%2 != 0: data = data[1:] # Need an even number of points for FFT 
			nsamples = len(data)
			ft = np.fft.fft(data) / nsamples
			ft = ft[range(int(nsamples/2))]
			x = np.arange(nsamples/2)
			y = abs(ft) + self.offset_slide.get()*10
		
		self.plot_data.set_data(x,y)
		self.plot_data.set_color(self.color.get())

		if self.info_cb.get() == "Freq:":
			if period_info == None:
				self.info.configure(text="No trigger", fg="black")
			else:
				status = period_info[0]
				value  = period_info[1]
				if status < 3 and value != 0:
					self.info.configure(text="{} Hz".format(int(1000000/value)))
					if   status == 0:	self.info.configure(fg="green")
					elif status == 1:	self.info.configure(fg="green3")
					else:				self.info.configure(fg="green3")
				elif status == 3:
					self.info.configure(text=">100 KHz", fg="red")
				elif status == 4:
					self.info.configure(text="Non-periodic", fg="black")
				elif status == 100 and value != 0:
					self.info.configure(text="{} KHz (ETS)".format(int(1000000/value)), fg="black")
				elif status == 101:
					self.info.configure(text="ETS timeout", fg="red")
		elif self.info_cb.get() == "Volts:":
			self.info.configure(fg="black",text="{:.2f}...{:.2f} Volts".format(self.sample_to_volts(min(samples),att), self.sample_to_volts(max(samples),att)))
		elif self.info_cb.get() == "Vpp:":
			self.info.configure(fg="black",text="{:.2f} Volts".format(self.sample_to_volts(max(samples)-min(samples),att)))

class Oscilloscope(tk.Frame):
	
	def __init__(self, parent, *args, **kwargs):
		tk.Frame.__init__(self, parent, *args, **kwargs)
		self.parent = parent
		parent.protocol("WM_DELETE_WINDOW", self.on_close_window)

		parent.tk.call('wm', 'iconphoto', parent._w, tk.PhotoImage(file="Oscilloscope.png"))
		parent.geometry("+{}+{}".format(Globals.config["Osc-Window"]["xpos"], Globals.config["Osc-Window"]["ypos"]))
		parent.title("Oscilloscope")

		parent.rowconfigure(0,weight=1)
		parent.columnconfigure(0,weight=1)
		
		mdpi = int(Globals.config["Settings-Osc-Display"]["DPI"])
		fw	 = int((parent.winfo_screenwidth()  * int(Globals.config["Settings-Osc-Display"]["CanvasWidth"][:-1]))  / 100)
		fh	 = int((parent.winfo_screenheight() * int(Globals.config["Settings-Osc-Display"]["CanvasHeight"][:-1])) / 100)
		
		self.window_width      = fw
		self.samples_per_frame = self.window_width
		
		""" signal showing canvas """
		self.fig, self.axis = plt.subplots(figsize=(fw/mdpi,fh/mdpi),dpi=mdpi)
		self.axis.set_xlim(0,100)
		self.axis.set_ylim(-50,+50)
		gls = self.axis.get_ygridlines()								# mark 0 volts line
		gls[6].set_color("white")										# in this color
		self.axis.set_facecolor((0.5,0.5,0.5)) 							# background color
		self.fig.patch.set_facecolor((0.6,0.6,0.6))						# rounding color
		self.axis.xaxis.set_major_locator(ticker.MultipleLocator(10)) 	# 10 x 10 grid
		self.axis.yaxis.set_major_locator(ticker.MultipleLocator(10)) 	# 10 x 10 grid
		plt.grid() 													  	# show grid
		plt.xticks(color=(0.6,0.6,0.6)) 								# No units in x 
		self.fig.tight_layout() 										# Smaller area around figure
		self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
		self.canvas.get_tk_widget().grid(column=0, row=0, sticky="nswe")
		
		tools_frame = tk.Frame(parent)
		
		mode_frame = tk.LabelFrame(tools_frame, text=" Mode: ", padx=5, pady=5)
		self.operating_mode = tk.StringVar()
		tk.Radiobutton(mode_frame, text="Oscilloscope", variable=self.operating_mode, value="Oscilloscope", command=self.on_mode_changed).pack(anchor='w')
		tk.Radiobutton(mode_frame, text="Spectrometer", variable=self.operating_mode, value="Spectrometer", command=self.on_mode_changed).pack(anchor='w')
		self.operating_mode.set(Globals.config["Osc-HorizontalAxis"]["Mode"])
		
		performance_frame = tk.Frame(mode_frame)
		self.perf_show = tk.BooleanVar()
		tk.Checkbutton(performance_frame, text="Perf:", variable=self.perf_show, command=self.on_perf_show).pack(anchor="w", side="left")
		self.perf_sps = tk.Label(performance_frame)
		self.perf_fps = tk.Label(performance_frame)
		self.perf_sps.pack(side="left")
		self.perf_fps.pack(side="left")
		performance_frame.pack(anchor="w")
		
		time_frame = tk.LabelFrame(tools_frame, text=" Horizontal axis: ", padx=5, pady=5)
		self.horizontal_units_label = tk.Label(time_frame, text="Time/Div: ")	
		self.horizontal_units_label.grid(row=0, column=0, sticky="e")
		tk.Label(time_frame, text="Trigger: ")	.grid(row=1, column=0, sticky="e")
		tk.Label(time_frame, text="Extent: ")	.grid(row=2, column=0, sticky="e")
		self.horiz_div    	 = ttk.Combobox(time_frame, state="readonly", values=self.horizontal_unit_values(self.operating_mode.get()), width=10)
		self.use_ets 		 = tk.BooleanVar()
		self.use_ets_cb  	 = tk.Checkbutton(time_frame, text="ETS", variable=self.use_ets, command=self.on_use_ets) 
		self.trigger_channel = ttk.Combobox(time_frame, state="readonly", values=["Ch 1","Ch 2"], width=10)
		self.horiz_div_info	 = tk.Label(time_frame, text="")
		self.horiz_div		.bind('<<ComboboxSelected>>', self.on_horiz_div_changed)
		self.use_ets_cb		.grid(row=0, column=2, sticky="w")
		self.horiz_div		.grid(row=0, column=1, sticky="w")
		self.trigger_channel.grid(row=1, column=1, sticky="w", columnspan=2)
		self.horiz_div_info	.grid(row=2, column=1, sticky="w", columnspan=2)
		
		self.CH1 			 = OscilloscopeChannel(tools_frame, 1, self)
		self.CH2 			 = OscilloscopeChannel(tools_frame, 2, self)
		self.CH1.plot_data,  = self.axis.plot([], [], lw=1, marker='') #  marker='o' marker='|', ls="" 
		self.CH2.plot_data,  = self.axis.plot([], [], lw=1, marker='')

		mode_frame			.grid(row=0, column=0, sticky="we")
		time_frame			.grid(row=1, column=0, sticky="we")
		self.CH1.frame		.grid(row=2, column=0, sticky="we")
		self.CH2.frame		.grid(row=3, column=0, sticky="we")
		
		tools_frame.grid(row=0, column=1, sticky="nw", padx=5, pady=5)
		
		""" timing parameters for sampling """
		self.micros_needed_for_1sample  	= Globals.board.get_value("osc get_micros_needed_for_1sample", 2)
		self.micros_needed_for_2sample  	= Globals.board.get_value("osc get_micros_needed_for_2sample", 2)
		self.max_samples 					= Globals.board.get_value("osc get_max_samples", 2)
		self.nanos_per_sample_in_ets_mode 	= Globals.board.get_value("osc get_nanos_per_sample_in_ets_mode", 2)
		
		""" set initial values for widgets """
		self.trigger_channel.set(Globals.config["Osc-HorizontalAxis"]["Trigger"])
		self.on_mode_changed(False)
		self.on_channel_enabled(None)
		self.on_horiz_div_changed(None)
		self.time_at_last_frame = None

		""" don't start animation until this point in which the board is ok """
		self.ani = animation.FuncAnimation(self.fig, self.animation_get_data, init_func=self.animation_init, frames=1, interval=100, blit=True)		
		
		parent.resizable(False,False)
		
	def animation_init(self):
		self.CH1.plot_data.set_data([], [])
		self.CH2.plot_data.set_data([], [])
		return self.CH1.plot_data, self.CH2.plot_data,
    
	def animation_get_data(self,i):
		if self.time_at_last_frame != None:
			if self.perf_show.get():
				self.perf_fps.configure(text=" {} fps".format(int(1/(time.time()-self.time_at_last_frame))))
		self.time_at_last_frame = time.time()
		
		""" channels on show -- only one channel possible in ETS mode """
		if   not self.CH1.enabled.get() and not self.CH2.enabled.get(): return self.CH1.plot_data, self.CH2.plot_data,
		elif 	 self.CH1.enabled.get() and not self.CH2.enabled.get(): showing = 1
		elif not self.CH1.enabled.get() and     self.CH2.enabled.get(): showing = 2
		else:                                                           
			if self.use_ets.get(): return self.CH1.plot_data, self.CH2.plot_data,
			showing = 3		
		
		""" sampling parameters """
		time_span_in_micros = int(10*self.horizontal_unit_in_micros(self.horiz_div.get()))
		if self.use_ets.get():
			time_between_samples = self.nanos_per_sample_in_ets_mode # nanoseconds
			potential_samples    = int((time_span_in_micros*1000) / time_between_samples)
			samples_to_show      = potential_samples
		else:
			min_micros_per_sample = self.micros_needed_for_1sample if showing == 1 or showing == 2 else self.micros_needed_for_2sample
			potential_samples 	  = int(time_span_in_micros/min_micros_per_sample)
			samples_to_show       = potential_samples if potential_samples < self.window_width else self.window_width
			time_between_samples  = int(time_span_in_micros/samples_to_show) # microseconds
			if time_between_samples < min_micros_per_sample:
				print("Internal error 1", time_between_samples, "<", min_micros_per_sample)
				return self.CH1.plot_data, self.CH2.plot_data,

		if samples_to_show > self.max_samples:
			print("Internal error 2", samples_to_show, ">", self.max_samples)
			return self.CH1.plot_data, self.CH2.plot_data,

		""" update info on the time axis """
		if self.operating_mode.get() == "Oscilloscope":
			if time_span_in_micros < 1: 
				time_extent_units = "ns"
				time_extent_value = time_span_in_micros*1000
			elif time_span_in_micros >= 1000:
				time_extent_units = "ms"
				time_extent_value = int(time_span_in_micros/1000)
			else:
				time_extent_units = "us"
				time_extent_value = time_span_in_micros
			self.horiz_div_info.configure(text="{} samples {} {}".format(samples_to_show, time_extent_value, time_extent_units))
		else:
			freq_extent_units = "KHz" if time_span_in_micros < 1000 else "Hz"
			freq_extent_value = int(100000/time_span_in_micros) if time_span_in_micros < 1000 else int(100000000/time_span_in_micros)
			self.horiz_div_info.configure(text="{} samples {} {}".format(samples_to_show, freq_extent_value, freq_extent_units))

		""" get samples and draw frame """
		t0 = time.time()
		trigger_channel = 1 if self.trigger_channel.get() == "Ch 1" else 2
		(samples,period_status,period_value) = Globals.board.osc_get_samples(showing, samples_to_show, time_between_samples, trigger_channel, self.use_ets.get())
		if self.perf_show.get():
			self.perf_sps.configure(text=" {} Ksps ".format(int((samples_to_show/1000)/(time.time()-t0))))
		period_info = (period_status,period_value)
		if showing == 1:
			self.CH1.draw_frame(samples, period_info, self.operating_mode.get())
		elif showing == 2:
			self.CH2.draw_frame(samples, period_info, self.operating_mode.get())
		else:
			samples1 = samples[1::2]
			samples2 = samples[2::2]
			self.CH1.draw_frame(samples1, period_info if trigger_channel==1 else None, self.operating_mode.get())
			self.CH2.draw_frame(samples2, period_info if trigger_channel==2 else None, self.operating_mode.get())
		
		return self.CH1.plot_data, self.CH2.plot_data,
    
	def horizontal_unit_values(self, mode):
		if mode == "Oscilloscope":
			return ["1 us", "2 us",   "5 us",   "10 us",  "20 us", "50 us", "0.1 ms","0.2 ms","0.5 ms","1 ms", "2 ms",  "5 ms",  "10 ms", "20 ms","50 ms"]
		else:
			return ["1 MHz","500 KHz","200 KHz","100 KHz","50 KHz","20 KHz","10 KHz","5 KHz", "2 KHz", "1 KHz","500 Hz","200 Hz","100 Hz","50 Hz","20 Hz"]
			
	def horizontal_unit_in_micros(self, value):
		if value[-2:] == "ms":
			return float(value[:-3])*1000
		elif value[-2:] == "us":
			return float(value[:-3])
		elif value[-3] == "MHz":
			return 1/float(value[:-4])
		elif value[-3:] == "KHz":
			return 1000/float(value[:-4])
		elif value[-2:] == "Hz":
			return 1000000/float(value[:-3])
			
	def on_use_ets(self):
		try: # On first call, the CHx objects are not yet created
			if self.use_ets.get() and self.CH1.enabled.get() and self.CH2.enabled.get():
				messagebox.showinfo(message="ETS mode available only for single channel.", title="Warning", parent=self.parent)
				self.use_ets.set(False)
		except:
			pass
			
	def on_perf_show(self):
		if not self.perf_show.get():
			self.perf_sps.configure(text="")
			self.perf_fps.configure(text="")
		
	def on_channel_enabled(self,ch_num):
		try: # On first call, the CHx objects are not yet created
			if 	 self.CH1.enabled.get() == True  and self.CH2.enabled.get() == True:
				if self.use_ets.get():
					messagebox.showinfo(message="ETS mode available only for single channel.", title="Warning", parent=self.parent)
					if ch_num == 1:
						self.CH1.enabled.set(False)
					else:
						self.CH2.enabled.set(False)
					return
				self.trigger_channel.configure(state="readonly")
			elif self.CH1.enabled.get() == True  and self.CH2.enabled.get() == False:
				self.trigger_channel.set("Ch 1")
				self.trigger_channel.configure(state="disabled")
			elif self.CH1.enabled.get() == False and self.CH2.enabled.get() == True:
				self.trigger_channel.set("Ch 2")
				self.trigger_channel.configure(state="disabled")
			elif self.CH1.enabled.get() == False and self.CH2.enabled.get() == False:
				self.trigger_channel.configure(state="disabled")
				if self.perf_show.get():
					self.perf_sps.configure(text="")
					self.perf_fps.configure(text="")
		except:
			pass
			
	def on_mode_changed(self, save_current = True):
		if self.operating_mode.get() == "Oscilloscope":
			self.horizontal_units_label.configure(text="Time/Div: ")
			if save_current: Globals.config["Osc-HorizontalAxis"]["FreqDiv"] = self.horiz_div.get()
			self.horiz_div.configure(values=self.horizontal_unit_values("Oscilloscope"))
			self.horiz_div.set(Globals.config["Osc-HorizontalAxis"]["TimeDiv"])
			self.trigger_channel.configure(state="readonly")
		else:
			self.horizontal_units_label.configure(text="Freq./Div: ")
			if save_current: Globals.config["Osc-HorizontalAxis"]["TimeDiv"] = self.horiz_div.get()
			self.horiz_div.configure(values=self.horizontal_unit_values("Spectrometer"))
			self.horiz_div.set(Globals.config["Osc-HorizontalAxis"]["FreqDiv"])
			self.trigger_channel.configure(state="disabled")

	def on_horiz_div_changed(self, event):
		if self.horizontal_unit_in_micros(self.horiz_div.get()) <= 50:
			self.use_ets_cb.configure(state="normal")
		else:
			self.use_ets.set(False)
			self.use_ets_cb.configure(state="disabled")
		
	def on_close_window(self):
		g = self.parent.geometry().split("+")
		Globals.config["Osc-Window"]["xpos"] 				= str(g[1])
		Globals.config["Osc-Window"]["ypos"] 				= str(g[2])
		Globals.config["Osc-HorizontalAxis"]["Mode"]		= self.operating_mode.get()
		if self.operating_mode.get() == "Oscilloscope":
			Globals.config["Osc-HorizontalAxis"]["TimeDiv"]	= self.horiz_div.get()
		else:
			Globals.config["Osc-HorizontalAxis"]["FreqDiv"]	= self.horiz_div.get()
		Globals.config["Osc-HorizontalAxis"]["Trigger"]		= self.trigger_channel.get()
		Globals.config["Osc-Ch1"]["VerticalDivision"] 		= self.CH1.volts_div.get()
		Globals.config["Osc-Ch1"]["Color"] 					= self.CH1.color.get()
		Globals.config["Osc-Ch1"]["Offset"] 				= str(self.CH1.offset_slide.get())
		Globals.config["Osc-Ch1"]["Enabled"]				= "True" if self.CH1.enabled.get() == True else "False"
		Globals.config["Osc-Ch2"]["VerticalDivision"]	 	= self.CH2.volts_div.get()
		Globals.config["Osc-Ch2"]["Color"] 					= self.CH2.color.get()
		Globals.config["Osc-Ch2"]["Offset"] 				= str(self.CH2.offset_slide.get())
		Globals.config["Osc-Ch2"]["Enabled"]				= "True" if self.CH2.enabled.get() == True else "False"
		Globals.save_config()
		
		Globals.board.send_command("led ch1 off")
		Globals.board.send_command("led ch2 off")
		
		Globals.toplevel_windows["Oscilloscope"].parent.destroy()
		Globals.toplevel_windows["Oscilloscope"] = None

