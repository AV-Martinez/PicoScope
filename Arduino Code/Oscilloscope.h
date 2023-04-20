#ifndef _OSCILLOSCOPE_H_
#define _OSCILLOSCOPE_H_

#include <Arduino.h>

#define OSC_MAX_SAMPLES 10000

class OscilloscopeClass {
public:
	void Setup			(uint8_t ch1_adcChannel, uint8_t ch2_adcChannel, uint8_t ch1_gpioTrigger, uint8_t ch2_gpioTrigger); 
	void CaptureBasic 	(uint8_t channel/**1,2,3*/, uint16_t numSamples, uint16_t microsBetweenSamples, uint8_t triggerChannel);
	void CaptureETS 	(uint8_t channel/**1,2*/,   uint16_t numSamples, uint16_t nanosBetweenSamples,  uint8_t triggerChannel);
	void WaitForTrigger	(uint8_t triggerGpio, uint16_t *periodStatus, uint16_t *periodValue);
								/// *periodStatus:
								///		0: Good value in *periodValue, best quality
								///		1: Good value in *periodValue, though lesser quality
								///		2: Good value in *periodValue, though lesser quality
								///		3: *periodValue unknown but less than 1us (f>100KHz)
								///		4: Timeout, probably non-periodic signal
	const bool TestWaitForTrigger = false;	/// Dump triggering info on Serial. Can't communicate with Python in this mode

	uint16_t MicrosNeededFor1Sample;			/// Microseconds needed to get one sample
	uint16_t MicrosNeededFor2Sample;			/// Microseconds needed to get two samples

	uint8_t Ch1_gpioTrigger, Ch2_gpioTrigger;	/// Trigger input gpio for channel 1 and 2

private:
	uint8_t Ch1_adcChannel, Ch2_adcChannel;		/// ADC channel for oscilloscope channel 1 and 2
	struct repeating_timer TriggerTimeoutTimer;	/// Trigger timeout management
	uint16_t Samples[OSC_MAX_SAMPLES];			/// Samples buffer
	uint8_t  TxBuffer[OSC_MAX_SAMPLES*2];		/// Byte buffer containing samples or any other data to be sent
	
	void GetSamplesByDMA (uint8_t channel, uint16_t numSamples, uint16_t microsBetweenSamples, uint16_t *outputBuffer);

};

extern OscilloscopeClass Oscilloscope;

#endif
