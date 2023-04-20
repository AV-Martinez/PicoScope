#include "Oscilloscope.h"

#include "hardware/pwm.h"
#include "hardware/adc.h"
#include "hardware/dma.h"

OscilloscopeClass Oscilloscope;

volatile uint8_t  TriggerGpio;
#define MAX_TRIGGER_EVENTS 50
struct {
	uint32_t MicsSincePrevCall;
	uint32_t Events;
} TriggerEvents[MAX_TRIGGER_EVENTS];
volatile uint8_t  TriggerIx;
volatile uint32_t TriggerMicsAtLastCall;
volatile uint8_t  TriggerCaptureMode;
volatile uint32_t TriggerMinMicros;
void __not_in_flash_func(TriggerIRQ)(uint gpio, uint32_t events) {
	if (gpio != TriggerGpio) return;
	if (TriggerCaptureMode == 0) { /// Non-ETS, get data
		uint32_t now = micros();
		if (TriggerMicsAtLastCall == 0 || now-TriggerMicsAtLastCall < 5) { /// See docs at WaitForTrigger
			TriggerMicsAtLastCall = now;
			return;
		}
		if (TriggerIx < MAX_TRIGGER_EVENTS) {
			TriggerEvents[TriggerIx].MicsSincePrevCall = now - TriggerMicsAtLastCall;
			TriggerEvents[TriggerIx].Events = events;
			TriggerIx++;
		}
		TriggerMicsAtLastCall = now;
	}
	else if (TriggerCaptureMode == 1) { /// Non-ETS, wait for trigger
		uint32_t now = micros();
		if (events == 4 /**falling*/ || TriggerMicsAtLastCall == 0 || now-TriggerMicsAtLastCall < 5) { /// See docs at WaitForTrigger
			TriggerMicsAtLastCall = now;
			return;
		}
		if (TriggerMinMicros == 0) 
			TriggerIx++;
		else {
			if (now-TriggerMicsAtLastCall > TriggerMinMicros) TriggerIx++;
		}
		TriggerMicsAtLastCall = now;
	}
	else if (TriggerCaptureMode == 2) { /// ETS mode, wait for trigger
		if (events != 4 /**rising*/) TriggerIx++;
	}
}

void __not_in_flash_func(TriggerIRQ_ForETS)(uint gpio, uint32_t events) {
	if (gpio != TriggerGpio) return;
	TriggerIx++;
}

volatile bool TriggerTimeout;
bool TriggerTimeoutHandler(struct repeating_timer *t) {
	TriggerTimeout = true;
	return true;
}

void OscilloscopeClass::Setup(uint8_t ch1_adcChannel,  uint8_t ch2_adcChannel, 
							  uint8_t ch1_gpioTrigger, uint8_t ch2_gpioTrigger) {
	Ch1_adcChannel = ch1_adcChannel;
	Ch2_adcChannel = ch2_adcChannel;
	
	Ch1_gpioTrigger = ch1_gpioTrigger;
	Ch2_gpioTrigger = ch2_gpioTrigger;

	pinMode(Ch1_gpioTrigger, INPUT);
	gpio_set_irq_enabled_with_callback(Ch1_gpioTrigger, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, true, &TriggerIRQ);
	gpio_set_irq_enabled(Ch1_gpioTrigger, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, false);

	pinMode(Ch2_gpioTrigger, INPUT);
	gpio_set_irq_enabled_with_callback(Ch2_gpioTrigger, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, true, &TriggerIRQ);
	gpio_set_irq_enabled(Ch2_gpioTrigger, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, false);

	MicrosNeededFor1Sample = 2;	/// As per ADC DMA reading limit
	MicrosNeededFor2Sample = 4; /// As per ADC DMA reading limit

	analogReadResolution(12);	
	
}

void OscilloscopeClass::CaptureBasic(uint8_t channel, uint16_t numSamples, uint16_t microsBetweenSamples, uint8_t triggerChannel) {
	uint8_t  gpio;
	uint16_t periodValue;
	uint16_t periodStatus;
	if (channel == 1 || (channel == 3 && triggerChannel == 1)) gpio = Ch1_gpioTrigger; 
	if (channel == 2 || (channel == 3 && triggerChannel == 2)) gpio = Ch2_gpioTrigger;

	/// Wait for trigger
	WaitForTrigger(gpio, &periodStatus, &periodValue);

	/// Capture and send samples
	GetSamplesByDMA(channel, numSamples, microsBetweenSamples, Samples);
	uint16_t bix = 0;
	uint16_t noSamples = channel == 1 || channel == 2 ? numSamples : numSamples*2;
	for (uint16_t s = 0; s < noSamples; s++) {
		TxBuffer[bix++] = (Samples[s] & 0x0F00) >> 8;
		TxBuffer[bix++] = (Samples[s] & 0x00FF);
	}
	Serial.write(TxBuffer, bix);
	
	/// Send period calculation status and value
	TxBuffer[0] = (periodStatus & 0xFF00) >> 8;
	TxBuffer[1] = (periodStatus & 0x00FF);
	TxBuffer[2] = (periodValue & 0xFF00) >> 8;
	TxBuffer[3] = (periodValue & 0x00FF);
	Serial.write(TxBuffer, 4);
}

void OscilloscopeClass::CaptureETS(uint8_t channel, uint16_t numSamples, uint16_t nanosBetweenSamples, uint8_t triggerChannel) {

	adc_init();
	uint8_t captureChannel = (channel == 1) ? Ch1_adcChannel : Ch2_adcChannel;
		adc_gpio_init(26 + captureChannel); 	/// Prepare GPIO
		adc_select_input(captureChannel);

	uint8_t gpio = (channel == 1) ? Ch1_gpioTrigger : Ch2_gpioTrigger;

	uint16_t bix = 0;
	uint16_t sampleCount = 0;
	uint32_t t0 = millis();
	const uint32_t timeoutValue = 4000;
	while (sampleCount != numSamples && millis()-t0 < timeoutValue) {
		
		TriggerCaptureMode = 2; TriggerTimeout = false; TriggerIx = 0;
		add_repeating_timer_ms(50, TriggerTimeoutHandler, NULL, &TriggerTimeoutTimer);	
		gpio_set_irq_enabled(gpio, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, true);
		while (!TriggerTimeout && TriggerIx < 1); 
		gpio_set_irq_enabled(gpio, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, false);
		cancel_repeating_timer(&TriggerTimeoutTimer); 
		if (TriggerTimeout) continue;

		/// The number of nops is adjusted so that the frequency of a known source is properly displayed in ETS mode
		/// These values adjusted for 100ns delay for F_CPU = 250 MHz (4ns/nop)
		for (uint16_t c = 0; c < sampleCount; c++) {
			asm volatile("nop"); asm volatile("nop"); asm volatile("nop"); asm volatile("nop");
			asm volatile("nop"); asm volatile("nop"); asm volatile("nop"); asm volatile("nop");
			asm volatile("nop"); asm volatile("nop"); asm volatile("nop"); asm volatile("nop");
			asm volatile("nop"); asm volatile("nop"); asm volatile("nop"); asm volatile("nop");
			asm volatile("nop"); asm volatile("nop"); asm volatile("nop");
		}
		
		/** Filtering out signal spikes
		 * 	When showing a signal in ETS mode, occasional spikes are rendered in the drawn signal.
		 *  Note that ETS is heavily dependant on a very precise trigger, and these spikes can probably
		 *  be traced to inaccuracies in the triggering circuit. 
		 *  They are filtered out here by a crude comparison with the last value (i.e., no large variations are expected
		 *  in the input signal)
		 */
		uint16_t sample = adc_read();
		Samples[sampleCount] = sample;
		static uint16_t lastSample = 0xFFFF;
		if (lastSample != 0xFFFF) {
			if (abs(sample-lastSample) > 10) {
				lastSample = sample;
				continue;
			}
		}
		lastSample = sample;
		TxBuffer[bix++] = (sample & 0x0F00) >> 8;
		TxBuffer[bix++] = (sample & 0x00FF);
		sampleCount++;
	}
	bool timedOut = !(millis()-t0 < timeoutValue);
	
	/// Send data, calculating signal period
	uint16_t period = 0;
	if (!timedOut) {
		Serial.write(TxBuffer, bix);
		/// Calculate period
		uint32_t avg = 0; uint16_t min = 0xFFFF, max = 0;
		for (uint16_t s = 0; s < sampleCount; s++) {
			avg += Samples[s]; 
			if (Samples[s] < min) min = Samples[s];
			if (Samples[s] > max) max = Samples[s];
		}
		avg /= sampleCount;
		uint16_t mpDetect = ((max-min)*10)/100;
		uint16_t s1, s2;
		for (s1 = 1; s1 < sampleCount; s1++) if (Samples[s1-1] <= avg && Samples[s1] >= avg) break;
		if (s1 < sampleCount) {
			for (s2 = s1+3; s2 < sampleCount; s2++) if (Samples[s2-1] <= avg && Samples[s2] >= avg) break;
			if (s2 < sampleCount) 
				period = (s2-s1)*nanosBetweenSamples;
		}
	}
	else { /// Timedout
		for (uint16_t b = 0; b < numSamples*2; b++) TxBuffer[b] = 0;
		Serial.write(TxBuffer, numSamples*2);
	}
	/// Send extra info
	TxBuffer[0] = ((timedOut ? 101:100) & 0xFF00) >> 8;
	TxBuffer[1] = ((timedOut ? 101:100) & 0x00FF);
	TxBuffer[2] = (period & 0xFF00) >> 8;
	TxBuffer[3] = (period & 0x00FF);
	Serial.write(TxBuffer, 4);
	
}

void OscilloscopeClass::WaitForTrigger(uint8_t triggerGpio, uint16_t *periodStatus, uint16_t *periodValue) {
	/** Trigger detection strategy
	 * 
	 * 	At low frequencies (less than about 3 KHz) the triggering hardware does not create a clean
	 * 	square signal in sync with the signal average value detection. Instead, some rapid low-high
	 *  transitions may happen at the average value detection point. This is probably due to the inherent 
	 * 	inaccuracy of the LM311 comparator, some ripple at the R-C averaging circuit and/or some instability
	 * 	in the input signal itself. When measured, these events turn into IRQ calls around 2-3 us.
	 * 
	 * 	The first approach to implement the trigger detection is to call an ISR on the either falling or
	 * 	rising edges of the triggering signal. If doing so, and due to the effect described above, some fake
	 * 	calls will happen at mid-period point. The solution is to call the ISR on *both* the falling and
	 * 	rising edges, and multiplying the measured period value by 2.
	 * 
	 *  At high frequencies, the signal's period time challenges the time resolution of the microcontroller.
	 * 	Assuming a 1us maximum resolution, any period value below 10us will have more than 10% error. 
	 * 	For this reaqson, 10us is chosen as the smallest directly measurable period (f=100KHz). This turns
	 *  into 5us for the minimum valid time between ISR calls (since the ISR is called at both the falling
	 * 	and rising edge) => MAX FREQUENCY is 100KHz
	 * 
	 * 	Combining the two limits above, any ISR call that happens less than 5us after the last one is
	 *  disregarded. For very low frequencies (less than about 100 Hz), the ISR may still be triggered
	 * 	with transitions of more than 5 us. In these cases, a full review of the captured triggers
	 *  is needed.
	 * 
	 * 	The trigger detection must be subject to a timeout in case no periodic signal is fed. This is
	 * 	chosen as 200ms => MIN FREQUENCY is 5Hz
	 * 
	 * 	The algorithm will always return F=100KHz as the frequency of the signal for any signal with
	 * 	frequency >= 100KHz. To detect a *true* frequency larger than 100KHz, the event types must be analyzed. 
	 * 	Proper <= 100KHz signals will not show any event type == 12 (i.e. 4+8, i.e. both a rising(8) and a falling(4)
	 * 	edges in the same ISR call are reported)
	 * 
	*/
	TriggerGpio = triggerGpio;
	const uint16_t timeoutMaxMillis = 500; /// 200ms theoretical

	uint32_t start;
	if (TestWaitForTrigger) start = micros();

	/// Take 20 triggers
	TriggerCaptureMode = 0; TriggerTimeout = false; TriggerIx = TriggerMicsAtLastCall = 0;
	add_repeating_timer_ms(timeoutMaxMillis, TriggerTimeoutHandler, NULL, &TriggerTimeoutTimer);	
	gpio_set_irq_enabled(triggerGpio, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, true);
	while (!TriggerTimeout && TriggerIx < 20); 
	gpio_set_irq_enabled(triggerGpio, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, false);
	cancel_repeating_timer(&TriggerTimeoutTimer); 
	if (TriggerTimeout) {
		*periodStatus = 4; /// Timeout
		*periodValue  = 0;
		return;
	}

	/// Analyze triggers
	uint32_t min = 0xFFFFFFFF, max = 0, avg = 0;
	char line[100];
	if (TestWaitForTrigger) { snprintf(line, 100, "Timeout:%d N:%d\n", TriggerTimeout, TriggerIx); Serial.print(line); }
	for (uint8_t i = 0; i < TriggerIx; i++) {
		if (false && TestWaitForTrigger) { snprintf(line, 100, "Tr:%2d %+5ldus type:%ld\n", i, TriggerEvents[i].MicsSincePrevCall, TriggerEvents[i].Events);  Serial.print(line); }
		if (TriggerEvents[i].MicsSincePrevCall < min) min = TriggerEvents[i].MicsSincePrevCall;
		if (TriggerEvents[i].MicsSincePrevCall > max) max = TriggerEvents[i].MicsSincePrevCall;
		avg += TriggerEvents[i].MicsSincePrevCall;
	}
	avg /= TriggerIx;
	uint32_t q = max/min;	/// Quality factor. 1=ok
	uint8_t  events12 = 0;	/// Number of events of type 12 (fast rising and falling edges)
	if (q == 1) {			/// All values very similar
		/// Check there are no fake transitions that may point to a very high frequency (> 100KHz)
		for (uint8_t i = 0; i < TriggerIx; i++)	if (TriggerEvents[i].Events == 12) events12++;
		if (events12 < (TriggerIx*2)/3) { /// Mostly good 8-4-8 (proper rise/fall edges) events
			*periodValue = avg*2; 
			if (events12 == 0) *periodStatus = 0; else *periodStatus = 1;
		}
		else  {/// Suspect this is a very high frequency signal
			*periodStatus = 3;
			*periodValue  = 0; 
		}
	}
	else { /// Some fake transitions have been captured
		/// Calculate the avg of the largest values to calculate the frequency
		uint32_t avg_of_max = 0; uint8_t n = 0;
		for (uint8_t i = 0; i < TriggerIx; i++)
			if (TriggerEvents[i].MicsSincePrevCall > avg) { 
				avg_of_max += TriggerEvents[i].MicsSincePrevCall;
				n++;
			}
		avg = avg_of_max/n;
		*periodValue  = avg*2; 
		*periodStatus = 2;
	}
	if (TestWaitForTrigger) { snprintf(line, 100, "max:%ld min:%ld avg:%ld q:%ld evts12:%d f:%ld pStat:%d pValue:%d\n", max, min, avg, q, events12, *periodValue != 0 ? 1000000L/(*periodValue) : 0L, *periodStatus, *periodValue); Serial.print(line); }
	
	/// Finally, wait for a trigger point and return
	if (q == 1) 
		TriggerMinMicros = 0;
	else 
		TriggerMinMicros = *periodValue/4;
	TriggerCaptureMode = 1; TriggerTimeout = false; TriggerIx = TriggerMicsAtLastCall = 0;
	add_repeating_timer_ms(timeoutMaxMillis, TriggerTimeoutHandler, NULL, &TriggerTimeoutTimer);	
	gpio_set_irq_enabled(triggerGpio, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, true);
	while (!TriggerTimeout && TriggerIx < 2); /// Wait for two edges, which will mark the start of a period
	gpio_set_irq_enabled(triggerGpio, GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL, false);
	cancel_repeating_timer(&TriggerTimeoutTimer); 
	if (TriggerTimeout) {
		*periodStatus = 4; /// Timeout
		*periodValue  = 0;
		return;
	}
	
	if (TestWaitForTrigger) { snprintf(line, 100, "Triggered %ld. Done in %ld us\n", TriggerMinMicros, micros()-start); Serial.print(line); }
	
}

/// Reference: https://vanhunteradams.com/Pico/VGA/FFT.html 
/// Reference: https://github.com/raspberrypi/pico-examples/blob/master/adc/dma_capture/dma_capture.c
void OscilloscopeClass::GetSamplesByDMA(uint8_t channel, uint16_t numSamples, uint16_t microsBetweenSamples, uint16_t *outputBuffer) {
	
	/// Set up ADC -----------------------------------------------------
	if (channel == 1 || channel == 2) {
		uint8_t captureChannel = (channel == 1) ? Ch1_adcChannel : Ch2_adcChannel;
		
		adc_gpio_init(26 + captureChannel); 	/// Prepare GPIO
		adc_init();								/// Init ADC
		adc_select_input(captureChannel);		/// Select input
		adc_fifo_setup(							/// Configure ADC FIFO
			true,		/// Write each completed conversion to the sample FIFO
			true,		/// Enable DMA data request (DREQ)
			1,	   		/// DREQ (and IRQ) asserted when at least 1 sample present
			false,  	/// We won't see the ERR bit because of 8 bit reads; disable.
			false 		/// Using 16-bit samples
		);
		/// 96 clock cycles are needed for 1 sample. ADC clock runs at 48Mhz. 
		/// 96 clock cycles are needed for a 2us sample (minimum time between samples)
		adc_set_clkdiv((96.0*microsBetweenSamples)/2.0);
	}
	else {
		adc_gpio_init(26+Ch1_adcChannel);
		adc_gpio_init(26+Ch2_adcChannel);		/// Prepare GPIO
		adc_init();								/// Init ADC
		adc_set_round_robin(0b00000110);		/// Select input (channels 1 and 2)
		adc_fifo_setup(							/// Configure ADC FIFO
			true,		/// Write each completed conversion to the sample FIFO
			true,		/// Enable DMA data request (DREQ)
			1,	   		/// DREQ (and IRQ) asserted when at least 1 sample present
			false,  	/// We won't see the ERR bit because of 8 bit reads; disable.
			false 		/// Using 16-bit samples
		);
		/// To keep the requested microsBetweenSamples, samples must be gathered 
		/// twice as fast when in round robin mode
		adc_set_clkdiv((96.0*(microsBetweenSamples/2.0))/2.0);
	}

	/// Set up DMA channel ---------------------------------------------
	uint dma_channel = 2; /// Alternatively; dma_claim_unused_channel(true);
	dma_channel_config cfg = dma_channel_get_default_config(dma_channel);
	channel_config_set_transfer_data_size	(&cfg, DMA_SIZE_16); /// Using 16-bit samples
	channel_config_set_read_increment		(&cfg, false);
	channel_config_set_write_increment		(&cfg, true);
	channel_config_set_dreq					(&cfg, DREQ_ADC);
	dma_channel_configure(dma_channel, &cfg,
		outputBuffer,	/// Destination
		&adc_hw->fifo,  /// Source
		channel == 1 || channel == 2 ? numSamples : numSamples*2, /// Will capture twice as many samples in round robin mode (2 inputs)
		true			/// Start immediately
	);

	/// Get samples ----------------------------------------------------
	adc_run(true); 										/// Start ADC
	dma_channel_wait_for_finish_blocking(dma_channel);	/// Wait for completion
	adc_run(false);										/// Stop ADC
	adc_fifo_drain();									/// Clean up fifo

}

