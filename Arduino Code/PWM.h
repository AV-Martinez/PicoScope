#ifndef _PWM_H_
#define _PWM_H_

#include <Arduino.h>

class PWMClass {
public:
	PWMClass(uint8_t gpio);
	
	void Start();
	void Stop();
	void SetFrequency(uint32_t f);
	void SetDutyCycle(uint8_t dc);
	
	uint32_t MaxPWMFrequency = 62000000L; 

private:
	void Set();
	void DoInit();

	uint8_t Gpio;
	uint8_t Slice, Channel;
	uint8_t Duty;
	uint32_t Frequency;
	
	bool Init;
	
};

#endif
