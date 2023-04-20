import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import time

import Globals

class Settings(tk.Frame):
	
	def __init__(self, parent, *args, **kwargs):
		tk.Frame.__init__(self, parent, *args, **kwargs)
		self.parent = parent

		parent.protocol("WM_DELETE_WINDOW", self.on_close_window)
		parent.geometry("+{}+{}".format(Globals.config["Settings-Window"]["xpos"], Globals.config["Settings-Window"]["ypos"]))
		parent.title("Settings")
		
		self.tab_control  = ttk.Notebook(parent)
		tab_board   	  = ttk.Frame(self.tab_control)
		tab_osc_screen    = ttk.Frame(self.tab_control)
		tab_osc_calibrate = ttk.Frame(self.tab_control)
		self.tab_control.add(tab_board, 		text=" Board ")
		self.tab_control.add(tab_osc_screen, 	text=" Oscilloscope Display ")
		self.tab_control.add(tab_osc_calibrate, text=" Oscilloscope Calibration ")
		self.tab_control.pack(expand=True, fill="both", padx=5, pady=5)
		
		tk.Label(tab_board, text="Port: ").grid(row=0, column=0, sticky="e", padx=5, pady=10)
		self.board_port	= tk.Entry(tab_board)
		self.board_port.grid(row=0, column=1, sticky="w")
		tk.Label(tab_board, text="Wakeup color: ").grid(row=1, column=0, sticky="e", padx=5, pady=2)
		self.wakeup_color = ttk.Combobox(tab_board, state="readonly", values=["Red","Green","Blue"], width=6)
		self.wakeup_color.grid(row=1, column=1, sticky="w")

		tk.Label(tab_osc_screen, text="Display resolution: ")	.grid(row=0, column=0, sticky="e", padx=5, pady=2)
		tk.Label(tab_osc_screen, text="Canvas width: ")		.grid(row=1, column=0, sticky="e", padx=5, pady=2)
		tk.Label(tab_osc_screen, text="Canvas height: ")		.grid(row=2, column=0, sticky="e", padx=5, pady=2)
		self.osc_display_dpi	= tk.Entry(tab_osc_screen, width=6)
		self.osc_canvas_width   = ttk.Combobox(tab_osc_screen, state="readonly", values=["25%","33%","50%","75%"], width=6)
		self.osc_canvas_height  = ttk.Combobox(tab_osc_screen, state="readonly", values=["25%","33%","50%","75%"], width=6)
		self.osc_display_dpi	.grid(row=0, column=1, sticky="w", padx=5, pady=2)
		self.osc_canvas_width	.grid(row=1, column=1, sticky="w", padx=5, pady=2)
		self.osc_canvas_height	.grid(row=2, column=1, sticky="w", padx=5, pady=2)
		tk.Label(tab_osc_screen, text="dpi")		.grid(row=0, column=2, sticky="w", pady=2)
		tk.Label(tab_osc_screen, text="of screen")	.grid(row=1, column=2, sticky="w", pady=2)
		tk.Label(tab_osc_screen, text="of screen")	.grid(row=2, column=2, sticky="w", pady=2)
		
		self.button_calibrate = tk.Button(tab_osc_calibrate, command=self.on_osc_calibrate, text="Calibrate input stage")
		self.button_calibrate.pack(pady=5)
		self.progress_var = tk.DoubleVar()
		self.progress_bar = ttk.Progressbar(tab_osc_calibrate, variable=self.progress_var, maximum=100)
		self.progress_bar.pack(fill="both", pady=5, padx=30)
		
		frame_buttons = tk.Frame(parent)
		self.button_cancel = tk.Button(frame_buttons, text="Close", command=self.on_cancel)
		self.button_ok  = tk.Button(frame_buttons, text="Ok", command=self.on_ok)
		self.button_cancel.pack(side="left")
		self.button_ok.pack(side="left")
		frame_buttons.pack(expand=True, padx=5, pady=5)

		parent.resizable(False,False)

		""" set initial values for widgets """
		self.board_port.insert(0, Globals.config["Settings-Board"]["Port"])
		self.osc_display_dpi.insert(0, Globals.config["Settings-Osc-Display"]["DPI"])
		self.osc_canvas_width .set(Globals.config["Settings-Osc-Display"]["CanvasWidth"])
		self.osc_canvas_height.set(Globals.config["Settings-Osc-Display"]["CanvasHeight"])
		self.wakeup_color.set(Globals.config["Settings-Board"]["WakeUpColor"])
		
	def on_osc_calibrate(self):
		"""
		Input stage is a compensated attenuator which attenuation should be independent of
		the signal frequency, but in reality it is not.

		AD9833 measured specs:
			Sine 630mV Vpp
			Square 3.64V Vpp
		"""
		self.button_calibrate	.config(state="disabled")
		self.button_ok			.config(state="disabled")
		self.button_cancel		.config(state="disabled")
		min_micros_per_sample = Globals.board.get_value("osc get_micros_needed_for_1sample", 2)
		print("ch freq   samples us/sample cycles att")
		print("-- ------ ------- --------- ------ ----")
		for channel in range(1,3):
			rc = messagebox.askokcancel(message="Connect 3.3v AD9833 output to channel {}, then click Ok.".format(channel), title="Calibrate input stage", parent=self.parent)
			if not rc: continue
			tr_func = eval(Globals.config["Osc-Ch{}".format(channel)]["InputStageTrFunc"])
			i = 1
			freqs = Globals.input_stage_testing_frequencies
			for freq in freqs:
				self.progress_var.set(i*100/len(freqs)); self.update()
				i += 1
				Globals.board.send_command("funcgen AD9833_set {} {}".format(freq, "Sine"))
				t0 = time.time()
				while time.time()-t0 < 0.2: pass # stabilize signal
				micros_between_samples = min_micros_per_sample
				num_cycles = 5
				num_samples = (num_cycles * 1000000 / freq) / micros_between_samples
				while num_samples >= 5000:
					micros_between_samples += min_micros_per_sample
					num_samples = (num_cycles * 1000000 / freq) / micros_between_samples
				if micros_between_samples == min_micros_per_sample:
					while num_samples < 5000:
						num_cycles += 5
						num_samples = (num_cycles * 1000000 / freq) / micros_between_samples
				num_samples = int(num_samples)
				samples = Globals.board.osc_get_samples(channel, num_samples, micros_between_samples, channel, False)
				vpp = (max(samples[0])-min(samples[0]))*3.3/4095
				attenuation = 0.630/vpp
				tr_func[freq] = attenuation
				print("{0: <2} {1: <6} {2: <7} {3: <9} {4: <6} {5:.2f}".format(channel,freq, num_samples,micros_between_samples,num_cycles,attenuation))
			Globals.config["Osc-Ch{}".format(channel)]["InputStageTrFunc"] = str(tr_func)
		Globals.save_config()

		Globals.board.send_command("funcgen stop AD9833")
		self.progress_var.set(0)		
		self.button_calibrate	.config(state="normal")
		self.button_ok			.config(state="normal")
		self.button_cancel		.config(state="normal")
		messagebox.showinfo(message="Calibration done.\nRestart oscilloscope.", title="Calibrate input stage", parent=self.parent)
			
	def on_ok(self):
		if self.osc_display_dpi.get() != Globals.config["Settings-Osc-Display"]["DPI"] or self.osc_canvas_width.get()  != Globals.config["Settings-Osc-Display"]["CanvasWidth"] or self.osc_canvas_height.get() != Globals.config["Settings-Osc-Display"]["CanvasHeight"]:
			messagebox.showinfo(message="Restart oscilloscope to apply changes", title="Information", parent=self.parent)
			   
		Globals.config["Settings-Board"]["Port"]				= self.board_port.get()
		Globals.config["Settings-Board"]["WakeUpColor"] 		= self.wakeup_color.get()
		Globals.config["Settings-Osc-Display"]["DPI"] 			= self.osc_display_dpi.get()
		Globals.config["Settings-Osc-Display"]["CanvasWidth"]   = self.osc_canvas_width.get()+"%"
		Globals.config["Settings-Osc-Display"]["CanvasHeight"]  = self.osc_canvas_height.get()+"%"
		self.on_close_window()
		
	def on_cancel(self):
		self.on_close_window()

	def on_close_window(self):
		g = self.parent.geometry().split("+")
		Globals.config["Settings-Window"]["xpos"] = str(g[1])
		Globals.config["Settings-Window"]["ypos"] = str(g[2])

		Globals.toplevel_windows["Settings"].parent.destroy()
		Globals.toplevel_windows["Settings"] = None
		
