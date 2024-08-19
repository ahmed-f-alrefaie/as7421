from as7421 import AS7421, LED, ChannelEnable
from astropy import units as u

dev = AS7421(bus=1)

dev.setup_regs()
dev.integration_time = 65.5 << u.ms
dev.wait_time = 5 << u.ms

dev.powerup()
dev.configure_smux()
dev.configure_led(current="50mA", leds=LED.LED_1 | LED.LED_2 | LED.LED_3 | LED.LED_4)
dev.enable_channels(ChannelEnable.ABCD)

dev.num_measurements = 10

time = []
spectra = []
temperature = []

try:
    for t, s, temp in dev.do_measurement(with_led=True, print_timing=True):
        time.append(t)
        spectra.append(s)
        temperature.append(temp)
except KeyboardInterrupt:
    pass

wavelengths = dev.wavelengths

dev.sleep()

print("Timestamp", time)
print("Spectra", spectra)
print("Temperature", temperature)
