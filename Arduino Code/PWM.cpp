#include "PWM.h"

/// https://www.i-programmer.info/programming/hardware/14849-the-pico-in-c-basic-pwm.html?start=1
/// https://www.i-programmer.info/programming/hardware/14849-the-pico-in-c-basic-pwm.html?start=2

#include "hardware/pwm.h"

PWMClass::PWMClass(uint8_t gpio) {
	Gpio = gpio;
	Init = false;
}

void PWMClass::Start() { 
	if (!Init) DoInit();
	gpio_set_function(Gpio, GPIO_FUNC_PWM);
	pwm_set_enabled(Slice, true); 
}
	
void PWMClass::Stop() { 
	if (!Init) DoInit();
	digitalWrite(Gpio, LOW);
	pwm_set_enabled(Slice, false); 
}

void PWMClass::SetFrequency(uint32_t f) { 
	if (!Init) DoInit();
	Frequency = f; 
	Set(); 
}
	
void PWMClass::SetDutyCycle(uint8_t dc) { 
	if (!Init) DoInit();
	Duty = dc; 
	Set(); 
}

void PWMClass::Set() {
	uint32_t clock = F_CPU;
	uint32_t divider16 = clock / Frequency / 4096 + (clock % (Frequency * 4096) != 0);
	if (divider16 / 16 == 0) divider16 = 16;
	uint32_t wrap = clock * 16 / divider16 / Frequency - 1;
	pwm_set_clkdiv_int_frac(Slice, divider16/16, divider16 & 0xF);
	pwm_set_wrap(Slice, wrap);
	pwm_set_chan_level(Slice, Channel, wrap * Duty / 100);		
}

void PWMClass::DoInit() {
	gpio_set_function(Gpio, GPIO_FUNC_PWM);
	Slice = pwm_gpio_to_slice_num(Gpio);
	Channel = pwm_gpio_to_channel(Gpio);
	Init = true;
}

