import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import Globals

class FrequencyDigit(tk.Label):
	
	def __init__(self, parent, *args, **kwargs):
		tk.Label.__init__(self, parent, *args, **kwargs)

		self.parent = parent
		self.set_value(0)
		self.configure(font=("Arial",25))
		self.bind("<Button-4>", self.on_mousewheel_up) # <MouseWheel> in Windows
		self.bind("<Button-5>", self.on_mousewheel_down)
		
	def set_value(self, value):
		self.value = value
		self.configure(text="{}".format(self.value))
		
	def on_mousewheel_up(self, event):
		if self.value == 9:
			self.value = 0
		else:
			self.value += 1
		self.configure(text="{}".format(self.value))
		self.parent.updated()
		
	def on_mousewheel_down(self, event):
		if self.value == 0: 
			self.value = 9
		else:
			self.value -= 1
		self.configure(text="{}".format(self.value))
		self.parent.updated()


class FrequencyDisplay(tk.Frame):
	
	def __init__(self, parent, owner, *args, **kwargs):
		tk.Frame.__init__(self, parent, *args, **kwargs)

		self.owner = owner
		self.digit = [FrequencyDigit(self) for i in range(0,6)]
		for i in range(0,6):
			self.digit[i].grid(row=0,column=i)
		tk.Label(self,text=" Hz",font=("Arial",25)).grid(row=0,column=7)
		
	def updated(self):
		value = 0
		for i in range(0,6):
			value += self.digit[i].value * pow(10,(5-i))
		self.owner.freq.delete(0,tk.END)
		self.owner.freq.insert(0,value)
		self.owner.on_freq_updated(None)
		
	def set_value(self,value):
		v = "{:06d}".format(value)
		for i in range(0,6):
			self.digit[i].set_value(int(v[i]))
			

class FuncGen(tk.Frame):
	
	def __init__(self, parent, *args, **kwargs):
		tk.Frame.__init__(self, parent, *args, **kwargs)
		
		self.parent = parent
		self.running = False
		parent.protocol("WM_DELETE_WINDOW", self.on_close_window)
		
		parent.tk.call('wm', 'iconphoto', parent._w, tk.PhotoImage(file="FuncGen.png"))
		parent.geometry("+{}+{}".format(Globals.config["FuncGen"]["xpos"], Globals.config["FuncGen"]["ypos"]))
		parent.title("Function Generator")

		frame_params = tk.Frame(parent)
		tk.Label(frame_params, text="Frequency: ").grid(row=0, column=0, sticky="e", padx=5, pady=2)
		self.freq = tk.Entry(frame_params)
		self.freq.bind("<FocusOut>", self.on_freq_updated)
		self.freq.bind("<Return>", self.on_freq_updated)
		self.freq.grid(row=0, column=1, sticky="w", padx=5, pady=2)
		
		tk.Label(frame_params, text="Mode: ").grid(row=1, column=0, sticky="e", padx=5, pady=2)
		self.mode = ttk.Combobox(frame_params, state="readonly", values=["PWM", "AD9833"], width=10); self.mode.bind('<<ComboboxSelected>>', self.on_mode_changed)
		self.mode.grid(row=1, column=1, sticky="w", padx=5, pady=2)
		
		self.lbl_dutycycle = tk.Label(frame_params, text="Duty cycle: ")
		self.lbl_dutycycle.grid(row=2, column=0, sticky="e", padx=5, pady=2)
		frame_dutycycle = tk.Frame(frame_params)
		self.dutycycle_slide = tk.Scale(frame_dutycycle, from_=0, to=100, resolution=1, length=140, orient="horizontal", showvalue=False, command=self.on_dutycycle_changed)
		self.dutycycle_value = tk.Label(frame_dutycycle)
		self.dutycycle_slide.pack(side="left")
		self.dutycycle_value.pack(side="left")
		frame_dutycycle.grid(row=2, column=1, sticky="w", padx=5, pady=2)

		self.lbl_shape = tk.Label(frame_params, text="Shape: ")
		self.lbl_shape.grid(row=3, column=0, sticky="e", padx=5, pady=2)
		self.shape = ttk.Combobox(frame_params, state="readonly", values=["Sine", "Triangle", "Square"], width=10); self.shape.bind('<<ComboboxSelected>>', self.on_shape_changed)
		self.shape.grid(row=3, column=1, sticky="w", padx=5, pady=2)

		self.frequency_display = FrequencyDisplay(parent, self)
		self.frequency_display.pack()

		frame_params.pack(expand=True, padx=5, pady=5)

		frame_buttons = tk.Frame(parent)
		self.button_start = tk.Button(frame_buttons, text="Start", command=self.on_button_start)
		self.button_stop  = tk.Button(frame_buttons, text="Stop", command=self.on_button_stop)
		self.button_stop .pack(side="left")
		self.button_start.pack(side="left")
		frame_buttons.pack(expand=True, padx=5, pady=5)

		""" set initial values for widgets """
		self.freq				.insert(0,Globals.config["FuncGen"]["Frequency"])
		self.dutycycle_slide	.set(Globals.config["FuncGen"]["DutyCycle"]); self.on_dutycycle_changed(None)
		self.shape				.set(Globals.config["FuncGen"]["Shape"]); self.on_shape_changed(None)
		self.mode				.set(Globals.config["FuncGen"]["Mode"]); self.on_mode_changed(None)
		self.button_stop		.configure(state="disabled")
		if self.validate_freq_value():
			self.frequency_display.set_value(int(self.freq.get()))
		
		parent.resizable(False,False)
		
	def validate_freq_value(self):
		try:
			v = int(self.freq.get())
		except:
			messagebox.showinfo(message="Invalid charaters", title="Bad frequency value", parent=self.parent)
			return False
		if v >= 1000000 or v <= 0:
			messagebox.showinfo(message="Range is (0,1000000)", title="Bad frequency value", parent=self.parent)
			return False
		return True
		
	def on_freq_updated(self,event):
		if self.validate_freq_value():
			self.frequency_display.set_value(int(self.freq.get()))
			if self.running:
				if self.mode.get() == "PWM":
					Globals.board.send_command("funcgen pwm_set {} {}".format(self.freq.get(), self.dutycycle_slide.get()))
				else:
					Globals.board.send_command("funcgen AD9833_set {} {}".format(self.freq.get(), self.shape.get()))
			return True
		return False
		
	def on_mode_changed(self,event):
		if self.mode.get() == "PWM":
			self.shape			.configure(state="disabled")
			self.lbl_shape		.configure(state="disabled")
			self.dutycycle_slide.configure(state="normal")
			self.lbl_dutycycle	.configure(state="normal")
			if self.running:
				Globals.board.send_command("funcgen AD9833_set {} {}".format(self.freq.get(), self.shape.get()))
		else:
			self.shape			.configure(state="readonly")
			self.lbl_shape		.configure(state="normal")
			self.dutycycle_slide.configure(state="disabled")
			self.lbl_dutycycle	.configure(state="disabled")
			if self.running:
				Globals.board.send_command("funcgen pwm_set {} {}".format(self.freq.get(), self.dutycycle_slide.get()))
		
	def on_dutycycle_changed(self,event):
		if self.running:
			self.dutycycle_value.config(text="{}%".format(self.dutycycle_slide.get()))
			Globals.board.send_command("funcgen pwm_set {} {}".format(self.freq.get(), self.dutycycle_slide.get()))
		
	def on_shape_changed(self,event):
		if self.running:
			Globals.board.send_command("funcgen AD9833_set {} {}".format(self.freq.get(), self.shape.get()))
		
	def on_button_start(self):
		if not self.on_freq_updated(None): return
		
		if self.mode.get() == "PWM":
			Globals.board.send_command("funcgen pwm_set {} {}".format(self.freq.get(), self.dutycycle_slide.get()))
		else:
			Globals.board.send_command("funcgen AD9833_set {} {}".format(self.freq.get(), self.shape.get()))
		Globals.board.send_command("led fgen on")
		self.running = True
		self.button_stop .configure(state="normal")
		self.button_start.configure(state="disabled")

	def on_button_stop(self):
		if self.mode.get() == "PWM":
			Globals.board.send_command("funcgen stop pwm")
		else:
			Globals.board.send_command("funcgen stop AD9833")
		Globals.board.send_command("led fgen off")
		self.running = False
		self.button_stop .configure(state="disabled")
		self.button_start.configure(state="normal")

	def on_close_window(self):
		g = self.parent.geometry().split("+")
		Globals.config["FuncGen"]["xpos"] 		= str(g[1])
		Globals.config["FuncGen"]["ypos"] 		= str(g[2])
		Globals.config["FuncGen"]["Frequency"] 	= self.freq.get()
		Globals.config["FuncGen"]["Mode"] 		= self.mode.get()
		if self.mode.get() == "PWM":
			Globals.config["FuncGen"]["DutyCycle"] 	= str(int(self.dutycycle_slide.get()))
		else:
			Globals.config["FuncGen"]["Shape"] 		= self.shape.get()
		Globals.save_config()
		
		Globals.board.send_command("funcgen stop pwm")
		Globals.board.send_command("funcgen stop AD9833")
		Globals.board.send_command("led fgen off")

		Globals.toplevel_windows["FuncGen"].parent.destroy()
		Globals.toplevel_windows["FuncGen"] = None
		
