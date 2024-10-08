from i2cdevice import BitField, Device, Register
from i2cdevice.adapter import Adapter, LookupAdapter, U16ByteSwapAdapter
import smbus2
import typing as t
from astropy import units as u
from dataclasses import dataclass
from enum import IntEnum, Enum


class LED(IntEnum):
    LED_1 = 0x01
    LED_2 = 0x02
    LED_4 = 0x04
    LED_3 = 0x08
    ALL = 0x1F


class ChannelEnable(str, Enum):
    A = "A"
    AB = "AB"
    ABC = "ABC"
    ABCD = "ABCD"


CLOCK = 1 << u.MHz

ESTIMATED_WAVELENGTHS = [
    930,
    770,
    760,
    990,
    790,
    895,
    955,
    880,
    825,
    875,
    835,
    845,
    1020,
    950,
    1010,
    995,
    750,
    980,
    780,
    970,
    965,
    860,
    915,
    805,
    820,
    830,
    855,
    830,
    1000,
    1015,
    900,
    1045,
    775,
    920,
    765,
    910,
    975,
    865,
    935,
    885,
    800,
    830,
    850,
    830,
    890,
    1040,
    1005,
    1035,
    755,
    795,
    925,
    785,
    960,
    905,
    940,
    985,
    810,
    840,
    815,
    870,
    1025,
    1050,
    1030,
    945,
]


@dataclass
class MeasumentStatus:
    data_pointer: int
    data_lost: bool
    digital_saturation: bool
    analog_saturation: bool
    temperature_shutdown: bool
    end_of_autozero: bool
    data_available: bool

    def __str__(self):
        return f"Data Pointer: {self.data_pointer}\nData Lost: {self.data_lost}\nDigital Saturation: {self.digital_saturation}\nAnalog Saturation: {self.analog_saturation}\nTemperature Shutdown: {self.temperature_shutdown}\nEnd of Autozero: {self.end_of_autozero}\nData Available: {self.data_available}"

    def __repr__(self):
        return self.__str__()

    def any_set(self):
        return any(
            [
                self.data_lost,
                self.digital_saturation,
                self.analog_saturation,
                self.temperature_shutdown,
                self.end_of_autozero,
                self.data_available,
            ]
        )


class TimeAdapter(Adapter):

    def _decode(self, value: int) -> u.Quantity:
        # Goes low, mid, high bytes
        low = (value >> 16) & 0xFF
        mid = (value >> 8) & 0xFF
        high = (value) & 0xFF

        value = (high << 16) | (mid << 8) | low

        return ((value + 1) / CLOCK).to(u.s)

    def _encode(self, value: u.Quantity) -> int:
        res = max(int((value * CLOCK).decompose()) - 1, 0)
        # Goes low, mid, high bytes
        low = res & 0xFF
        mid = (res >> 8) & 0xFF
        high = (res >> 16) & 0xFF
        res = (low << 16) | (mid << 8) | high
        return res


class AS7421:

    def __init__(self, bus: t.Optional[int] = 1):
        import time

        self.create_device(bus)
        self.reset()
        time.sleep(0.1)
        print("Waiting for reset to complete")
        while self.is_resetting():
            time.sleep(0.01)
        print("Reset complete")

    def is_resetting(self) -> bool:
        return bool(self.device.get("CFG_MISC").SW_RESET)

    def create_device(self, bus):
        self.device = Device(
            0x64,
            i2c_dev=smbus2.SMBus(bus),
            bit_width=8,
            registers=(
                *tuple(
                    Register(
                        f"CFG_RAM_{x}",
                        0x40 + x,
                        fields=(BitField(f"VALUE", 0xFF),),
                    )
                    for x in range(32)
                ),
                Register(
                    "ENABLE",
                    0x60,
                    fields=(
                        BitField("LTF_MODE", 0b11000000),
                        BitField(
                            "LED_AUTO",
                            0b00110000,
                            adapter=LookupAdapter(
                                {
                                    "OFF": 0b00,
                                    "OFF1ON2": 0x01,
                                    "ON1OFF2": 0x02,
                                    "ON": 0x03,
                                }
                            ),
                        ),
                        BitField("SYNC_EN", 0b00001000),
                        BitField("TSD_EN", 0b00000100),
                        BitField("LTF_EN", 0b00000010),
                        BitField("POWERON", 0b00000001),
                    ),
                ),
                Register(
                    "LTF_ITIME",
                    0x61,
                    fields=(BitField("ITIME", 0xFFFFF, adapter=TimeAdapter()),),
                    bit_width=24,
                ),
                Register(
                    "LTF_WTIME",
                    0x64,
                    fields=(BitField("WTIME", 0xFFFFF, adapter=TimeAdapter()),),
                    bit_width=24,
                ),
                Register(
                    "CFG_LTF",
                    0x67,
                    fields=(
                        BitField(
                            "LTF_CYCLE",
                            0b00011000,
                            adapter=LookupAdapter(
                                {
                                    "A": 0b00,
                                    "AB": 0b01,
                                    "ABC": 0b10,
                                    "ABCD": 0b11,
                                }
                            ),
                        ),
                        BitField("CLKMOD", 0b00000111),
                    ),
                ),
                Register(
                    "CFG_LED",
                    0x68,
                    fields=(
                        BitField("SET_LED_ON", 0b10000000),
                        BitField("LED_OFF_EN", 0b01000000),
                        BitField("LED_OFFSET", 0b00110000),
                        BitField(
                            "LED_CURRENT",
                            0b00000111,
                            adapter=LookupAdapter({"50mA": 0, "75mA": 1}),
                        ),
                    ),
                ),
                Register(
                    "CFG_RAM",
                    0x6A,
                    fields=(
                        BitField("REG_BANK", 0b10000000),
                        BitField(
                            "RAM_OFFSET",
                            0b00011111,
                            LookupAdapter(
                                {
                                    "UNSET": 0x00,
                                    "SMUX_A": 0x0C,
                                    "SMUX_B": 0x0D,
                                    "SMUX_C": 0x0E,
                                    "SMUX_D": 0x0F,
                                    "ASETUP_AB": 0x10,
                                    "ASETUP_CD": 0x11,
                                    "COMPDAC": 0x12,
                                }
                            ),
                        ),
                    ),
                ),
                Register(
                    "CFG_AZ",
                    0x6D,
                    fields=(
                        BitField("AZ_ON", 0b10000000),
                        BitField(
                            "AZ_WTIME",
                            0b01100000,
                            adapter=LookupAdapter(
                                {
                                    "32us": 0x00,
                                    "64us": 0x01,
                                    "128us": 0x02,
                                    "256us": 0x03,
                                }
                            ),
                        ),
                        BitField("AZ_EN", 0b00010000),
                        BitField("AZ_CYCLE", 0b00001000),
                        BitField("AZ_ITERATION", 0b00000111),
                    ),
                ),
                Register(
                    "CFG_LED_MULT",
                    0x39,
                    fields=(BitField("LED_MULT", 0xFF),),
                ),
                Register(
                    "LTF_ICOUNT",
                    0x69,
                    fields=(BitField("ICOUNT", 0xFF, bit_width=8),),
                ),
                Register(
                    "CFG_MISC",
                    0x38,
                    fields=(
                        BitField("LED_WAIT_OFF", 0b00000100),
                        BitField("WAIT_CYCLE_ON", 0b00000010),
                        BitField("SW_RESET", 0b00000001),
                    ),
                ),
                Register(
                    "LED_WAIT",
                    0x3D,
                    fields=(BitField("LED_WAIT", 0xFF),),
                ),
                Register(
                    "LTF_CCOUNT",
                    0x3A,
                    fields=(BitField("CCOUNT", 0xFFFF, adapter=U16ByteSwapAdapter()),),
                    bit_width=16,
                ),
                Register(
                    "STATUS_0",
                    0x70,
                    fields=(BitField("DEV_ID", 0b00111111),),
                    read_only=True,
                ),
                Register(
                    "STATUS_1",
                    0x71,
                    fields=(BitField("REV_ID", 0b00111111),),
                    read_only=True,
                ),
                Register(
                    "STATUS_ASAT",
                    0x72,
                    fields=tuple(
                        BitField(f"ASAT_{x}", 0b0000000000000001 << x)
                        for x in range(16)
                    ),
                ),
                Register(
                    "STATUS_6",
                    0x76,
                    fields=(
                        BitField("LTF_READY", 0b00100000),
                        BitField("LTF_BUSY", 0b00010000),
                    ),
                    read_only=True,
                ),
                Register(
                    "STATUS_7",
                    0x77,
                    fields=(
                        BitField("I2C_DATA_POINTER", 0b11000000),
                        BitField("DLOST", 0b00100000),
                        BitField("DSAT", 0b00010000),
                        BitField("ASAT", 0b00001000),
                        BitField("TSD", 0b00000100),
                        BitField("AZ", 0b00000010),
                        BitField("ADATA", 0b00000001),
                    ),
                    read_only=True,
                    volatile=True,
                ),
                Register(
                    "INT_EN",
                    0x67,
                    fields=(
                        BitField("EN_ADATA", 0b00000001),
                        BitField("EN_AZ", 0b00000010),
                        BitField("EN_TSD", 0b00000100),
                        BitField("EN_ASAT", 0b00001000),
                        BitField("EN_DSAT", 0b00010000),
                        BitField("EN_DLOST", 0b00100000),
                    ),
                ),
                *tuple(
                    Register(
                        f"CHANNEL_{ch}",
                        0x80 + 32 * idx,
                        fields=tuple(
                            BitField(
                                f"CH{x}",
                                0xFFFF << 240 - 16 * x,
                                bit_width=16,
                                adapter=U16ByteSwapAdapter(),
                            )
                            for x in range(16)
                        ),
                        read_only=True,
                        bit_width=32 * 8,
                    )
                    for idx, ch in enumerate(["A", "B", "C", "D"])
                ),
                Register(
                    "TEMP",
                    0x78,
                    fields=[
                        BitField(f"TEMP_{x}", 0xFFFF << 48 - 16 * idx, bit_width=16)
                        for idx, x in enumerate(["A", "B", "C", "D"])
                    ],
                    read_only=True,
                    bit_width=64,
                ),
            ),
        )

    def powerup(self):

        self.device.set("ENABLE", POWERON=1)

    def sleep(self):
        self.device.set("CFG_LED", SET_LED_ON=0)
        self.device.set("ENABLE", POWERON=0)

    def print_ram(self):
        for x in range(32):
            ram_value = f"CFG_RAM_{x}"
            # print ram data in hex

            print(f"RAM[{x}] = {self.device.get(ram_value).VALUE:02X}")

    def write_ram_data(self, data: t.List[int], offset: int):
        for idx, value in enumerate(data):
            self.device.set(f"CFG_RAM_{idx + offset}", VALUE=value)

    def configure_gain(self, value: int = 6):
        data = [value] * 32
        self.device.set("CFG_RAM", RAM_OFFSET="ASETUP_AB", REG_BANK=0)
        self.write_ram_data(data, 0)
        # self.print_ram()
        self.device.set("CFG_RAM", RAM_OFFSET="ASETUP_CD", REG_BANK=0)
        self.write_ram_data(data, 0)
        # self.print_ram()

    def zero_smux(self):
        zero_smux = [0] * 32
        for x in ["SMUX_A", "SMUX_B", "SMUX_C", "SMUX_D"]:
            res = self.device.set("CFG_RAM", RAM_OFFSET=x)
            self.write_ram_data(zero_smux, 0)

    def configure_smux(self, smux_data=None):
        default_smux = smux_data
        self.zero_smux()
        zero_smux = [0] * 32
        if default_smux is None:
            default_smux = [0x21, 0x21, 0x21, 0x21, 0x43, 0x43, 0x43, 0x43]
        self.configure_smux_a(default_smux)
        self.configure_smux_b(default_smux)
        self.configure_smux_c(default_smux)
        self.configure_smux_d(default_smux)
        # self.print_ram()

    def _configure_smux(self, smux_data, offset: int, ram_offset: str):
        res = self.device.set("CFG_RAM", RAM_OFFSET=ram_offset)
        self.write_ram_data(smux_data, offset)

    def configure_smux_a(self, smux_data):
        self._configure_smux(smux_data, 0, "SMUX_A")

    def configure_smux_b(self, smux_data):
        self._configure_smux(smux_data, 8, "SMUX_B")

    def configure_smux_c(self, smux_data):
        self._configure_smux(smux_data, 16, "SMUX_C")

    def configure_smux_d(self, smux_data):
        self._configure_smux(smux_data, 24, "SMUX_D")

    def pfn_enable(self):
        self.configure_smux()
        self.configure_gain()
        self.configure_led()

    @property
    def num_measurements(self) -> int:
        return self.device.get("LTF_ICOUNT").ICOUNT

    @num_measurements.setter
    def num_measurements(self, value: int):
        self.device.set("LTF_ICOUNT", ICOUNT=value & 0xFF)

    def configure_led(
        self, current: t.Optional[t.Literal["50mA", "75mA"]] = "50mA", leds:t.Optional[int]=0x1F
    ):  
        leds = int(leds)
        for x in range(4):
            self.device.set("CFG_LED", LED_OFFSET=x)
            self.device.set("CFG_LED_MULT", LED_MULT=leds)
        self.device.set("CFG_LED", LED_OFFSET=0)
        self.device.set("CFG_LED", LED_CURRENT=current)

    def disable_led_wait(self):
        self.device.set("CFG_MISC", LED_WAIT_OFF=1)

    def enable_led_wait(self):
        self.device.set("CFG_MISC", LED_WAIT_OFF=0)

    def reset(self):
        self.device.set("CFG_MISC", SW_RESET=1)

    def switch_on_led(self):
        self.device.set("CFG_LED", SET_LED_ON=1)

    def switch_off_led(self):
        self.device.set("CFG_LED", SET_LED_ON=0)

    def start_measurement(self, with_led: bool = False):
        led_flag = "ON" if with_led else "OFF"
        self.device.set("ENABLE", POWERON=1, LTF_EN=1, TSD_EN=1, LED_AUTO=led_flag)

    def stop_measurement(self):
        self.device.set("ENABLE", LTF_EN=0, TSD_EN=0, LED_AUTO="OFF")

    def measurement_status(self) -> MeasumentStatus:
        reg = self.device.get("STATUS_7")
        return MeasumentStatus(
            data_pointer=reg.I2C_DATA_POINTER,
            data_lost=bool(reg.DLOST),
            digital_saturation=bool(reg.DSAT),
            analog_saturation=bool(reg.ASAT),
            temperature_shutdown=bool(reg.TSD),
            end_of_autozero=bool(reg.AZ),
            data_available=bool(reg.ADATA),
        )

    @property
    def measurement_ready(self):
        measurement_stat = self.measurement_status()
        if measurement_stat.data_available:
            print("-------")
            print(measurement_stat)
            print("-------")
        return measurement_stat.data_available

    @property
    def ltf_busy(self):
        return bool(self.device.get("STATUS_6").LTF_BUSY)

    @property
    def integration_time(self) -> u.Quantity:
        return self.device.get("LTF_ITIME").ITIME

    @integration_time.
    def integration_time(self, value: u.Quantity):
        self.device.set("LTF_ITIME", ITIME=value)

    @property
    def wait_time(self) -> u.Quantity:
        return self.device.get("LTF_WTIME").WTIME

    @wait_time.setter
    def wait_time(self, value: u.Quantity):
        self.device.set("LTF_WTIME", WTIME=value)

    def enable_channels(
        self,
        channels: t.Optional[ChannelEnable] = ChannelEnable.ABCD,
    ):
        self.device.set("CFG_LTF", LTF_CYCLE=channels)

    def channel_data(self, channel_label: t.Literal["A", "B", "C", "D"]) -> t.List[int]:
        reg = self.device.get(f"CHANNEL_{channel_label}")

        return [getattr(reg, f"CH{x}") for x in range(16)]

    def all_channel_data(self) -> t.List[t.List[int]]:
        data = []
        for ch in ["A", "B", "C", "D"]:
            data.extend(self.channel_data(ch))
        return data

    def temperature_data(self, channel_label: t.Literal["A", "B", "C", "D"]) -> int:
        reg = self.device.get("TEMP")
        return getattr(reg, f"TEMP_{channel_label}")

    def all_temperature_data(self) -> t.List[t.List[int]]:
        data = []
        reg = self.device.get("TEMP")
        for ch in ["A", "B", "C", "D"]:
            data.extend([getattr(reg, f"TEMP_{ch}")])
        return data

    def enable_autozero(
        self,
        enable: bool,
        cycle: t.Optional[int] = 0,
        iteration: t.Optional[int] = 0,
        wtime: t.Optional[str] = 0,
    ):
        self.device.set(
            "CFG_AZ",
            AZ_EN=enable,
            AZ_ON=1,
            AZ_CYCLE=int(cycle),
            AZ_ITERATION=int(iteration),
            AZ_WTIME=wtime,
        )

    def wavelengths(self) -> t.List[int]:
        return ESTIMATED_WAVELENGTHS

    def setup_regs(self):
        self.device.set("CFG_MISC", LED_WAIT_OFF=0, WAIT_CYCLE_ON=1)
        self.device.set("LED_WAIT", LED_WAIT=2)
        self.device.set("LTF_CCOUNT", CCOUNT=1023)
        self.device.set("ENABLE", LED_AUTO="OFF")
        self.integration_time = 20 << u.ms
        self.wait_time = 10 << u.ms
        self.num_measurements = 1
        self.device.set("CFG_LTF", LTF_CYCLE="ABCD")
        self.enable_autozero(
            True,
            1,
            0,
            "128us",
        )
        self.enable_led_wait()

    def do_measurement(
        self, with_led: t.Optional[bool] = True, print_timing: t.Optional[bool] = False
    ) -> t.Generator[t.Tuple[float, t.List[int], t.List[int]], None, None]:
        import time

        self.start_measurement(with_led=with_led)
        while self.ltf_busy:
            start = time.perf_counter()
            while not self.measurement_ready:
                pass
            end = time.perf_counter()
            if print_timing:
                print(f"Time to get data: {end,- start}")
            channel_data = self.all_channel_data()
            temperature_data = self.all_temperature_data()
            yield end, channel_data, temperature_data
        self.stop_measurement()
