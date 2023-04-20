#include "main.h"
#include "Wire.h"

// ******************************************************************************************************
/// For Raspberry Pi Pico (select this device, not a generic one. Otherwise, overclocking does not work)
/// https://arduino-pico.readthedocs.io/en/latest/
/// Overclock to 250 MHz. THIS IS CRITICAL for the ETS timing -- see CaptureETS() in Oscilloscope.cpp
// ******************************************************************************************************

/** Pending:
 * 		Do not provide nanos between samples in Capture ETS, or provide a new initial read parameter
 * 		to provide this value (as MicrosNeededFor_Sample), ie. "NanosPerSampleInETS"
 * 
 * 		Stickers.
 *
*/ 

#define PIN_LED_ACTIVITY 15

#include "Oscilloscope.h"
#define OSC_CH1_CHANNEL_ADC 	1 	
#define OSC_CH2_CHANNEL_ADC	 	2	
#define OSC_CH1_GPIO_TRIGGER 	29
#define OSC_CH2_GPIO_TRIGGER	14

#include "FuncGen.h"
#define PIN_FUNCGEN_PWM   	8
#define PIN_FUNCGEN_AD9833 	1
#define PIN_FUNCGEN_SOURCE 	7

#include "LED.h"

void Setup() {
	Serial.begin();

	Oscilloscope.Setup(OSC_CH1_CHANNEL_ADC, OSC_CH2_CHANNEL_ADC, OSC_CH1_GPIO_TRIGGER, OSC_CH2_GPIO_TRIGGER);
	FuncGen.Setup(PIN_FUNCGEN_PWM, PIN_FUNCGEN_AD9833, PIN_FUNCGEN_SOURCE);
	LED.Setup();
	
	LED.Set(LED_OSC_CH1, true);
	LED.Set(LED_OSC_CH2, true);
	LED.Set(LED_FUN_GEN, true);
	LED.BreatheNP((char *)"red",   1);
	LED.BreatheNP((char *)"green", 1);
	LED.BreatheNP((char *)"blue",  1);
	LED.Set(LED_OSC_CH1, false);
	LED.Set(LED_OSC_CH2, false);
	LED.Set(LED_FUN_GEN, false);

	pinMode(PIN_LED_ACTIVITY, OUTPUT);
	rp2040.wdt_begin(5000);
}

void Loop() {
	rp2040.wdt_reset();

	if (Oscilloscope.TestWaitForTrigger) { /// Trigger calibration
		static uint32_t ticks = millis();
		if (millis()-ticks > 2000) {
			ticks = millis();
			uint32_t f[] = {1000000, 200000, 100000, 50000,20000,10000,5000,2000,1000,500,200,100,50,20,10,0};
			static uint8_t fix = 0;
			FuncGen.AD9833_Set(f[fix], AD9833_SHAPE_SINE);
			Serial.print("\nF="); Serial.println(f[fix]);
			fix++; if (f[fix] == 0) fix = 0;
			delay(100);
			uint16_t periodStatus, periodValue;
			Oscilloscope.WaitForTrigger(OSC_CH1_GPIO_TRIGGER, &periodStatus, &periodValue);
			FuncGen.Stop((char *)"AD9833");
		}
		return;
	}
	
	char txBuffer[10];
	
	static char sCmd[100];
	static uint8_t sIx = 0;
	if (Serial.available()) 
		while (Serial.available()) {
			char c = Serial.read();
			if (c == '\n' || sIx == 99) {
				sCmd[sIx] = '\0';
				digitalWrite(PIN_LED_ACTIVITY, HIGH);
				char *tool = strtok(sCmd, " ");
				char *cmd  = strtok(NULL, " ");
				if (!strcmp(tool, "osc")) { /// Oscilloscope commands 
					if (!strcmp(cmd, "get_samples")) {
						char *channel              = strtok(NULL, " ");
						char *numSamples   		   = strtok(NULL, " ");
						char *microsBetweenSamples = strtok(NULL, " ");
						char *triggerChannel	   = strtok(NULL, " ");
						Oscilloscope.CaptureBasic(atoi(channel), atoi(numSamples), atoi(microsBetweenSamples), atoi(triggerChannel)); 
					}
					else if (!strcmp(cmd, "get_samples_ets")) {
						char *channel              = strtok(NULL, " ");
						char *numSamples   		   = strtok(NULL, " ");
						char *nanosBetweenSamples  = strtok(NULL, " ");
						char *triggerChannel	   = strtok(NULL, " ");
						Oscilloscope.CaptureETS(atoi(channel), atoi(numSamples), atoi(nanosBetweenSamples), atoi(triggerChannel)); 
					}
					else if (!strcmp(cmd, "get_micros_needed_for_1sample")) { 
						memcpy(txBuffer, &Oscilloscope.MicrosNeededFor1Sample, 2);
						Serial.write(txBuffer, 2);
					}
					else if (!strcmp(cmd, "get_micros_needed_for_2sample")) { 
						memcpy(txBuffer, &Oscilloscope.MicrosNeededFor2Sample, 2);
						Serial.write(txBuffer, 2);
					}
					else if (!strcmp(cmd, "get_max_samples")) { 
						uint16_t maxs = OSC_MAX_SAMPLES;
						memcpy(txBuffer, &maxs, 2);
						Serial.write(txBuffer, 2);
					}
				}
				else if (!strcmp(tool, "funcgen")) { /// Function Generator commands
					if (!strcmp(cmd, "pwm_set")) {
						char *frequency	= strtok(NULL, " ");
						char *dutycycle = strtok(NULL, " ");
						FuncGen.PWM_Set(atol(frequency), atoi(dutycycle));
					}
					else if (!strcmp(cmd, "AD9833_set")) {
						char *frequency = strtok(NULL, " ");
						char *shape  = strtok(NULL, " ");
						uint8_t shapeId;
						if 		(!strcmp(shape, "Sine"))	 shapeId = AD9833_SHAPE_SINE;
						else if (!strcmp(shape, "Triangle")) shapeId = AD9833_SHAPE_TRIANGLE;
						else if (!strcmp(shape, "Square")) 	 shapeId = AD9833_SHAPE_SQUARE;
						FuncGen.AD9833_Set(atol(frequency), shapeId);
					}
					else if (!strcmp(cmd, "stop")) {
						char *which = strtok(NULL, " ");
						FuncGen.Stop(which);
					}
				}
				else if (!strcmp(tool, "led")) { /// LED commands
					char *param = strtok(NULL, " "); 
					if 		(!strcmp(cmd, "ch1"))     LED.Set(LED_OSC_CH1, !strcmp(param, "on"));
					else if (!strcmp(cmd, "ch2"))     LED.Set(LED_OSC_CH2, !strcmp(param, "on"));
					else if (!strcmp(cmd, "fgen"))    LED.Set(LED_FUN_GEN, !strcmp(param, "on"));
					else if (!strcmp(cmd, "breathe")) LED.BreatheNP(param,2);
				}
				digitalWrite(PIN_LED_ACTIVITY, LOW);
				sIx = 0;
			}
			else 
				sCmd[sIx++] = c;
	}
	
}

