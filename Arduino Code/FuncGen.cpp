#include "FuncGen.h"
#include <SPI.h>

FuncGenClass FuncGen;

void FuncGenClass::Setup(uint8_t pinPWM, uint8_t pinAD9833_CS, uint8_t pinSelect) {
	PinSelect = pinSelect;
	PinAD9833_CS = pinAD9833_CS;

	pinMode(PinSelect, OUTPUT);
	pinMode(PinAD9833_CS, OUTPUT);

	SPI.setTX(3);
	SPI.setSCK(2);
	SPI.begin();
	SPIini();
	WriteRegister(0x100); /// Reset
	SPIend();
	delay(10);
	
	pinMode(pinPWM, OUTPUT);
	PWM_Signal = new PWMClass(pinPWM);
}

void FuncGenClass::PWM_Set(uint32_t frequency, uint8_t dutycycle) {
	PWM_Signal->SetFrequency(frequency);
	PWM_Signal->SetDutyCycle(dutycycle);
	PWM_Signal->Start();
	
	digitalWrite(PinSelect, 0);
}

void FuncGenClass::AD9833_Set(uint32_t frequency, uint8_t shape) {
	/** AD9833 Control register
	 * 
	 * 	15 Write sequence
	 * 	14 Write sequence
	 * 	13 B28		1: Use 2 consecutive writes to update frequency
	 * 	12 HLB		
	 * 	11 FSELECT	Use FREQ0 or FREQ1 in phase acc
	 * 	10 PSELECT 	Add PHASE0 or PHASE1 to phase acc
	 * 	09 0
	 * 	08 RESET	1: Reset
	 * 	07 SLEEP1	1: MCLK is disabled
	 * 	06 SLEEP12	1: Power down
	 * 	05 OPBITEN	Vout output
	 * 	04 0
	 * 	03 DIV2		Vout output
	 * 	02 0
	 * 	01 MODE		Vout output
	 * 	00 0
	 */
	
	uint32_t FreqWord = (frequency * pow(2,28)) / 25000000.0;
	uint16_t MSB = (uint16_t) ((FreqWord & 0xFFFC000) >> 14);
	uint16_t LSB = (uint16_t)  (FreqWord & 0x3FFF);
	LSB |= 0x4000;
	MSB |= 0x4000; 
  
	SPIini();
	WriteRegister(0x2100);
	WriteRegister(LSB);
	WriteRegister(MSB);
	WriteRegister(0xC000);
	WriteRegister(shape);
	SPIend();

	digitalWrite(PinSelect, 1);
}

void FuncGenClass::Stop(char *which) {
	if (!strcmp(which, "pwm"))		PWM_Signal->Stop(); 
	if (!strcmp(which, "AD9833")) 	AD9833_Set(0,0); 
}

void FuncGenClass::SPIini() {
	SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE2));
	digitalWrite(PinAD9833_CS, LOW);
}

void FuncGenClass::SPIend() {
	digitalWrite(PinAD9833_CS, HIGH);
	SPI.endTransaction();
}

void FuncGenClass::WriteRegister(uint16_t dat) { 
	SPI.transfer(highByte(dat));
	SPI.transfer(lowByte(dat)); 
	delayMicroseconds(10);
}

