#ifndef _LED_H_
#define _LED_H_

#include "Adafruit_NeoPixel.h"


#define LED_OSC_CH1  4
#define LED_OSC_CH2  6
#define LED_FUN_GEN  5
#define LED_NEOPIXEL 16

#include <Arduino.h>

class LEDclass {
public:
	void Setup();
	void Set(uint8_t which, uint8_t status);
	void SetNeoPixel(uint8_t red, uint8_t green, uint8_t blue);
	void BreatheNP(char *color, uint8_t delay);
	
private:
	Adafruit_NeoPixel *OnBoardNeoPixel;
};

extern LEDclass LED;

#endif
