#include "LED.h"

class LEDclass LED;

void LEDclass::Setup() {
	pinMode(LED_OSC_CH1, OUTPUT);
	pinMode(LED_OSC_CH2, OUTPUT);
	pinMode(LED_FUN_GEN, OUTPUT);
	OnBoardNeoPixel = new Adafruit_NeoPixel(1,LED_NEOPIXEL);
	OnBoardNeoPixel->begin();
}

void LEDclass::Set(uint8_t which, uint8_t status) {
	digitalWrite(which, status);
}

void LEDclass::SetNeoPixel(uint8_t red, uint8_t green, uint8_t blue) {
	OnBoardNeoPixel->setPixelColor(0, OnBoardNeoPixel->Color(red, green, blue));
	OnBoardNeoPixel->show();
}

void LEDclass::BreatheNP(char *color, uint8_t delayms) {
	if (!strcmp(color, "red")) {
		for (int16_t i = 0; i <= 255;  i++) { LED.SetNeoPixel(0,i,0);	delay(delayms); }
		for (int16_t i = 255; i >= 0; i--)  { LED.SetNeoPixel(0,i,0);	delay(delayms); }
	}
	if (!strcmp(color, "green")) {
		for (int16_t i = 0; i <= 255;  i++) { LED.SetNeoPixel(i,0,0);	delay(delayms); }
		for (int16_t i = 255; i >= 0; i--)  { LED.SetNeoPixel(i,0,0);	delay(delayms); }
	}
	if (!strcmp(color, "blue")) {
		for (int16_t i = 0; i <= 255;  i++) { LED.SetNeoPixel(0,0,i);	delay(delayms); }
		for (int16_t i = 255; i >= 0; i--)  { LED.SetNeoPixel(0,0,i);	delay(delayms); }
	}
}
