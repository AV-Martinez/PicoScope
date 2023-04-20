import serial # pip3 install pySerial
import time
import threading

import Globals

class Board():
	def __init__(self, port):
		try:
			self.serial = serial.Serial(port, 1, timeout=0) # USB CDC, speed is auto adjusted to max value
			self.ok = True
			self.semaphore = threading.Semaphore()
		except: 
			self.ok = False

	def close(self):
		self.serial.close()
		
	""" 
	Returns num_samples taken every time_between_samples (in micros if use_ets==False, in nanos if use_ets==True)
	if channel==3, data for both channels is gathered simultaneously. The returned list contains
	one channel in even positions and the other channel in odd positions.
	Following the samples taken two additional 2-byte integers are expected:
		For non-ets mode:
			The period calculation status: A value <=2 marks a valid period value
			The period value: In microseconds
		For ets mode:
			The period calculation status: 100:ok 101:timeout
			The period value: In nanoseconds
	"""
	def osc_get_samples(self, channel, num_samples, time_between_samples, trigger_channel, use_ets):
		self.semaphore.acquire()
		if not use_ets:
			cmd = "osc get_samples {} {} {} {}".format(channel, num_samples, time_between_samples, trigger_channel)
		else:
			cmd = "osc get_samples_ets {} {} {} {}".format(channel, num_samples, time_between_samples, trigger_channel)
		self.serial.write(bytes(cmd+"\n", "utf-8"))
		if channel == 3: num_samples = num_samples*2
		num_samples += 2 # returned data will include samples plus period_status and period_value
		
		data = []
		two_bytes = []
		t0 = time.time()
		while len(data) != num_samples and time.time()-t0 < 5.0:
			buff = self.serial.read(self.serial.in_waiting or 1) # in_waiting needed for >115200bps. Learnt from Python's miniterm
			if buff: 
				for i in range(0,len(buff)):
					two_bytes.append(buff[i])
					if len(two_bytes) == 2:
						data.append(two_bytes[0]*256+two_bytes[1])
						two_bytes = []
		self.semaphore.release()
		if len(data) != num_samples:
			print("Error: osc_get_samples timeout. num_samples:", num_samples, "len(data):", len(data))
			while len(data) != num_samples:
				data.append(0)
		return (data[:-2],data[-2],data[-1])
		
	def send_command(self, command):
		self.semaphore.acquire()
		self.serial.write(bytes(command+"\n", "utf-8"))
		self.semaphore.release()
		
	def get_value(self, command, ilength):
		self.semaphore.acquire()
		self.serial.write(bytes(command+"\n", "utf-8"))
		value = self._receive_integer(ilength)
		self.semaphore.release()
		return value
		
	def _receive_integer(self, num_bytes):
		data = []
		t0 = time.time()
		while len(data) != num_bytes and time.time()-t0 < 5.0:
			buff = self.serial.read(self.serial.in_waiting or 1) # in_waiting needed for >115200bps. Learnt from Python's miniterm
			if buff: 
				for i in range(0,len(buff)):
					data.append(buff[i])
		if len(data) != num_bytes:
			print("Error: receive_integer timeout")
			return 0
		value = 0
		for n in range(0,num_bytes):
			value = value + data[n] * pow(2,n*8)
		return value
		
