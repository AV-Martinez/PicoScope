#ifndef _FUNCGEN_H_
#define _FUNCGEN_H_

#include <Arduino.h>
#include "PWM.h"

#define AD9833_SHAPE_SINE 		0b00000000
#define AD9833_SHAPE_TRIANGLE 	0b00000010
#define AD9833_SHAPE_SQUARE		0b00101000

class FuncGenClass {

public:

	void Setup(uint8_t pinPWM, uint8_t pinAD9833_CS, uint8_t pinSelect);

	void PWM_Set	(uint32_t frequency, uint8_t dutycycle);
	void AD9833_Set	(uint32_t frequency, uint8_t waveform);
	void Stop		(char *which);
	
private:

	PWMClass *PWM_Signal;

	uint8_t PinAD9833_CS;
	uint8_t PinSelect;
	
	void SPIini();
	void SPIend();
	void WriteRegister(uint16_t dat);
};

extern FuncGenClass FuncGen;

#endif
