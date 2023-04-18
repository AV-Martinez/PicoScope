import tkinter as tk
from tkinter import messagebox

import Globals
import Oscilloscope
import Settings

class LaunchItem():

	def __init__(self, parent, name, row, internal_name, *args, **kwargs):
		
		self.internal_name = internal_name
		try:
			self.image = tk.PhotoImage(file=self.internal_name+".png")
		except:
			self.image = None
		
		self.icon = tk.Label(parent, image=self.image)
		self.icon.grid(row=row, column=0, sticky="w")
		tk.Button(parent, text=name, command=self.on_click).grid(row=row, column=1, sticky="news")

	def on_click(self):
		if Globals.toplevel_windows[self.internal_name] == None:
			class_ = getattr(__import__(self.internal_name),self.internal_name)
			Globals.toplevel_windows[self.internal_name] = class_(tk.Toplevel())
		else:
			Globals.toplevel_windows[self.internal_name].parent.attributes("-topmost", True)

class Main(tk.Frame):
	
	def __init__(self, parent, *args, **kwargs):
		tk.Frame.__init__(self, parent, *args, **kwargs)
		self.parent = parent
		parent.protocol("WM_DELETE_WINDOW", self.on_close_window)

		parent.tk.call('wm', 'iconphoto', parent._w, tk.PhotoImage(file="PicoScope.png"))
		parent.geometry("+{}+{}".format(Globals.config["PicoScope-Window"]["xpos"], Globals.config["PicoScope-Window"]["ypos"]))
	
		self.settings   = LaunchItem(parent, "Settings",						1, "Settings")
		self.osc  		= LaunchItem(parent, "Oscilloscope", 					2, "Oscilloscope")
		self.funcgen	= LaunchItem(parent, "Function Generator",				3, "FuncGen")

		if not Globals.board.ok:
			messagebox.showinfo(message="Board not found.\nReconnect USB.", title="Error")
			exit(0)
		Globals.board.send_command("led breathe {}".format(Globals.config["Settings-Board"]["WakeUpColor"].lower()))
		
		parent.resizable(False,False)
		
	def on_settings(self):
		dialog = Settings.Settings(self.parent)
		self.parent.wait_window(dialog.top)

	def on_close_window(self):
		for w in Globals.toplevel_windows:
			if Globals.toplevel_windows[w] != None:
				Globals.toplevel_windows[w].on_close_window()

		g = self.parent.geometry().split("+")
		Globals.config["PicoScope-Window"]["xpos"] = str(g[1])
		Globals.config["PicoScope-Window"]["ypos"] = str(g[2])
		Globals.save_config()

		self.quit()

if __name__ == "__main__":

	root = tk.Tk()
	root.title("PicoScope")
	Main(root)

	root.mainloop()

