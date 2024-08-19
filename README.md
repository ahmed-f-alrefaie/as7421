# Python library for AS7421

This is a Python library for the [AS7421](https://ams.com/en/as7421) 64-channel NIR sensor.

The library is based on the datasheet and some reverse engineering to determine the correct register settings and
interpretation of the data. Considering both production and support has been dropped I felt it is useful to have a library
to interface with the sensor

## Installation

```bash
git clone https://github.com/ahmed-f-alrefaie/as7421.git
cd as7421
pip install .
```

The python file ``examples/basic.py`` includes a basic example of how to use the library.

## Calibration file

There is also a calibration file parser included in the library under calibration. Again it is a best guess as to what is actually included.



## Limitations

As this is a reverse engineered library, there are some limitations:

### SMUX configuration

The smux configuration is only partially known. Each of the RAM ragisters for a particular channel is assigned to two pixels and a nibble is used
to select which ADC is connected to the pixel. There are 4 ADCs that can be assigned for each integration channels ``A``, ``B``, ``C`` and ``D``.
For example, setting RAM location 0 as 0x21 will map two photodiodes to ADC 2 and ADC 1. At least thats how it looks. However, the actual
mapping of photodiodes to each of the RAM locations is not known. The library assumes that the mapping is the same as the datasheet but this
does not appear to be true.

### Wavelength assignment

As the datasheet does not provide the wavelength assignment for each of the channels, an educated guess was made based on switching on each of the LEDs
and recording the data. The data was then compared to the expected spectrum and the closest match was used. This is not perfect but it is the best
that can be done for now. The LED spectrum after this wavelength assignment is given below:

![alt text](https://github.com/ahmed-f-alrefaie/as7421/blob/master/led.png?raw=true)

Again this is biased and is probably only 60% correct.

### Calibration

The sensor does require some form of calibration to maximise data and unfortunately this procedure is not known. The calibration file included is a best guess
as to what is included based on the calibration documents and other available data for sensors.

### License

This library is licensed under the MIT license. See [LICENSE.md](LICENSE.md) for more details.
