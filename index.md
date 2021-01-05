---
title: Samil Power inverter communication protocol
---

This document describes my findings on the communication protocol used for
talking with a Samil Power inverter over the network.
A Python implementation can be found on [GitHub](https://github.com/mhvis/solar).

Contents:

* [Relevant inverters](#relevant-inverters)
* [Discovery](#discovery)
* [Messages](#messages)
* [Packet data samples](#packet-data-samples)
* [Other resources](#other-resources)


## Relevant inverters

* SolarRiver TL series
* SolarRiver TL-D series
* SolarLake TL series

This is based on the notion that the
[SolarPower Browser V3](https://web.archive.org/web/20190720131520/http://www.samilpower.com/service.php)
software supports these inverters according to the Samil Power website.

The following inverters have been confirmed to work with the protocol:

* SolarRiver 3400 TL-D
* SolarRiver 4500 TL-D
* SolarRiver 5200 TL-D
* SolarLake 17K

## Discovery

The following message is broadcasted over UDP port 1300 to discover inverters in
the network:

```
0000   55 aa 00 40 02 00 0b 49 20 41 4d 20 53 45 52 56  U..@...I AM SERV
0010   45 52 04 3a                                      ER.:
```

The message format is explained later, the payload here is `I AM SERVER`.
Inverters will respond by opening a TCP connection to the host on port 1200.

## Messages

When a TCP connection is made, the server (you) can make requests. The inverter
will send a response for your request. For me the time between a request and
response was typically 1.5 seconds.

All messages have the following format, in order:

* 2 bytes, always 0x55 0xaa.
* 2 bytes which seem to be an identifier for the type of request/response.
* 1 byte which I don't know, the value does not seem to matter.
* 2 bytes: an integer denoting the payload length.
* The payload.
* 2 bytes at the end, the checksum, a sum of the previous bytes.

Integers in messages are always 2 bytes and big endian unless stated
otherwise. Normally they are unsigned, except for when the value can
become negative (e.g. for internal temperature).

Strings are null-terminated if they are shorter than their space in the
packet, which is determined by the protocol.
Bytes after the 0 byte are ignored.
It seems that an ASCII encoding is used, non-ASCII characters such as `é` are not supported.


### Model/version info

Request has identifier `01 03 02` (hex), empty payload and checksum `01 05`.

Response has identifier `01 83 00`. Payload:

```
0x00   31 20 20 34 35 30 30 56 31 2e 33 30 52 69 76 65  1  4500V1.30Rive
0x10   72 20 34 35 30 30 54 4c 2d 44 00 20 53 61 6d 69  r 4500TL-D. Sami
0x20   6c 50 6f 77 65 72 00 20 20 20 20 20 44 57 34 31  lPower.     DW41
0x30   33 42 38 30 38 30 00 00 00 00 00 00 56 31 2e 33  3B8080......V1.3
0x40   30 56 31 2e 33 30 32                             0V1.302
```

The payload will be of exactly length 71 and consists (only) of
possibly null-terminated strings. The meaning and offset of each string:

* 0x00 Device type:
  * "1" = Single-phase inverter
  * "2" = Three-phase inverter
  * "3" = SolarEnvi Monitor
  * "4" = R-phase inverter of the three combined single-phase ones (?)
  * "5" = S-phase inverter of the three combined single-phase ones (?)
  * "6" = T-phase inverter of the three combined single-phase ones (?)
* 0x01 VA rating ("  4500")
* 0x07 Firmware version ("V1.30")
* 0x0c Model name ("River 4500TL-D")
* 0x1c Manufacturer ("SamilPower")
* 0x2c Serial number ("DW413B8080")
  * This value seems to have influence on how status values should be interpreted
* 0x3c Communication version ("V1.30")
* 0x41 Other version ("V1.30")
* 0x46 General (?, protocol version??) ("2")
  * This also seems to influence on how status values should be interpreted, in a minor way

Source: [ID Info](#dataid-infodw413b8080csv).


### Status data format

This requests the inverter for the specification of the data types that are present in the status data response, and also in which order they will appear in that response.

Request identifier: `01 00 02`, checksum: `01 02`, empty payload.

Response identifier: `01 80 00`. Each byte in the payload specifies a type of data that will appear in the status data response according to the list below. The order of the type specifications as they appear in the payload will be the same as the order in which the data values will appear in the status response. Each status value in the status response will always be 2 bytes long, which results in that the payload length of the status response will effectively be always twice the length of this format response. An example payload for this format response is `00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34 35 36`. The known data types that can appear in the list are given here, note that these are not offsets but a possible value of a byte in the payload.

* 0x00 Internal temperature in tenths of degrees Celcius, two's complement number (375 = 37.5 degrees Celcius)
* 0x01 PV1 voltage in decivolts (2975 = 297.5 V)
* 0x02 PV2 voltage in decivolts
* 0x04 PV1 current in deciampere
* 0x05 PV2 current in deciampere
* 0x07 Energy total in tenths of kWh first part
* 0x08 Energy total second part
* 0x09 Total operation time in hours first part big endian
* 0x0a Total operation time in hours last part
* 0x0b Output power in watt
* 0x0c Operation mode, 0=wait, 1=normal, 2=fault, 3=permanent fault, 4=check, 5=PV power off
* 0x11 Energy produced today in hundreds of kWh (474 = 4.74 kWh)
* 0x17
* 0x18
* 0x19
* 0x1a
* 0x1b
* 0x1c ? These unknown types 0x17 till 0x22 may be for indicating fault codes but I have not looked into it
* 0x1d
* 0x1e
* 0x1f
* 0x20
* 0x21
* 0x22
* 0x27 PV1 input power in watt
* 0x28 PV2 input power in watt
* 0x2f Heatsink temperature in tenths of degrees Celcius
* 0x31 Single phase inverter or R-phase of a three-phase inverter: current to grid in tenths of ampere
* 0x32 Single phase inverter or R-phase of a three-phase inverter: grid voltage in tenths of volts
* 0x33 Single phase inverter or R-phase of a three-phase inverter: grid frequency in hundreds of hertz (4998 = 49.98 Hz)
* 0x34 Output power in watt
* 0x35 Total energy produced first part, in hectowatt hour (114649 = 11464.9 kWh)
* 0x36 Total energy produced second part
* 0x51 Three-phase inverter only, S phase: current to grid in tenths of ampere
* 0x52 Three-phase inverter only, S phase: grid voltage in tenths of volts
* 0x53 Three-phase inverter only, S phase: grid frequency in hundreds of hertz
* 0x71 Three-phase inverter only, T phase: current to grid in tenths of ampere
* 0x72 Three-phase inverter only, T phase: grid voltage in tenths of volts
* 0x73 Three-phase inverter only, T phase: grid frequency in hundreds of hertz


### Status data (voltage, temperature, et cetera)

Request identifier: `01 02 02`, empty payload and checksum `01 04`.

Response identifier: `01 82` and an inconsistent third byte which is usually 0. The payload is a list of integer values where each value is 2 bytes long and big endian. The values that you can expect in the payload are documented in the earlier section on the status data format. An example payload:

```
0000   01 77 0b 9f 0b f6 00 15 00 14 00 00 28 40 00 01
0010   01 da 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0020   00 00 00 00 00 00 02 88 02 6f 00 37 09 14 13 86
0030   04 ee 00 01 b1 cc
```

* 0x00 Internal temperature 0x01 0x77 = 375 = 37.5 degrees Celcius
* 0x02 PV1 voltage of 297.5 V
* ...
* 0x0a Total operation time 0x00 0x00 0x28 0x40 = 10304 hours
* ...

### Historical data

Request identifier: `06 01 02`. The payload has length 2 and consists of two integers with length 1 to specify the period for which you want to receive data. The first integer indicates the last two digits of the start year, the second integer indicates the last two digits of the end year.

The server responds with multiple messages until all requested data is
transferred. The identifier of each message is `06 61 00`.
For each day of the year a number of packets is sent.
These packets have a data string with them which must be concatenated with the other packets of the same day,
to form the data for a complete day.
The data for a complete day is a CSV formatted string.
Explanation of the payload of a single packet:

* 0x00 Last two digits of the year of current packet (0-99)
* 0x01 Month number (1-12)
* 0x02 Day number (1-31)
* 0x03 ? for me it is always `00 00 01 38`
* 0x07 4-byte integer: specifies the number of data packets that will be sent for the current day
* 0x0b 4-byte integer: sequence number of the data packet for the current day
* 0x0f One of the parts of a textual ASCII csv encoding
for the complete day, which looks like shown below in the example.
The CSV values are separated by CR+LF newlines (\r\n, `0x0d0a`).

Example of the payloads for a full day, in 3 packets:

```
      YY MM DD ?? ?? ?? ??|Data count |Sequence nr|Start of text
      \/ \/ \/            |\/ \/ \/ \/|\/ \/ \/ \/|\/
0000  11 03 16 00 00 01 38|00 00 00 03|00 00 00 00|30   ......8........0
0010  30 3a 30 30 2c 2d 2d 2d 33 33 0d 0a 30 31 3a 30   0:00,---33..01:0
0020  30 2c 30 2e 30 30 20 0d 0a 30 32 3a 30 30 2c 30   0,0.00 ..02:00,0
0030  2e 30 30 20 0d 0a 30 33 3a 30 30 2c 30 2e 30 30   .00 ..03:00,0.00
0040  20 0d 0a 30 34 3a 30 30 2c 30 2e 30 30 20 0d 0a    ..04:00,0.00 ..
0050  30 35 3a 30 30 2c 30 2e 30 30 20 0d 0a 30 36 3a   05:00,0.00 ..06:
0060  30 30 2c 30 2e 30 30 20 0d 0a 30 37 3a 30 30 2c   00,0.00 ..07:00,
0070  30 2e 30 33 20 0d 0a 30 38 3a 30 30 2c 30 2e 32   0.03 ..08:00,0.2
0080  32 20 0d 0a 30 39 3a 30 30 2c 31 2e 31 36 20      2 ..09:00,1.16 

                                                   Continuation of text
                                                   \/
0000  11 03 16 00 00 01 38 00 00 00 03 00 00 00 01 0d   ......8.........
0010  0a 31 30 3a 30 30 2c 32 2e 36 31 20 0d 0a 31 31   .10:00,2.61 ..11
0020  3a 30 30 2c 33 2e 32 30 20 0d 0a 31 32 3a 30 30   :00,3.20 ..12:00
0030  2c 33 2e 32 30 20 0d 0a 31 33 3a 30 30 2c 32 2e   ,3.20 ..13:00,2.
0040  31 37 20 0d 0a 31 34 3a 30 30 2c 31 2e 39 37 20   17 ..14:00,1.97 
0050  0d 0a 31 35 3a 30 30 2c 30 2e 37 31 20 0d 0a 31   ..15:00,0.71 ..1
0060  36 3a 30 30 2c 30 2e 38 35 20 0d 0a 31 37 3a 30   6:00,0.85 ..17:0
0070  30 2c 30 2e 36 37 20 0d 0a 31 38 3a 30 30 2c 30   0,0.67 ..18:00,0
0080  2e 31 32 20 0d 0a 31 39 3a 30 30 2c 30 2e 30      .12 ..19:00,0.0

                                                   Continuation of text
                                                   \/
0000  11 03 16 00 00 01 38 00 00 00 03 00 00 00 02 30   ......8........0
0010  20 0d 0a 32 30 3a 30 30 2c 30 2e 30 30 20 0d 0a    ..20:00,0.00 ..
0020  32 31 3a 30 30 2c 30 2e 30 30 20 0d 0a 32 32 3a   21:00,0.00 ..22:
0030  30 30 2c 30 2e 30 30 20 0d 0a 32 33 3a 30 30 2c   00,0.00 ..23:00,
0040  30 2e 30 30 20 0d 0a                              0.00 ..

```

When all data is transferred, the inverter sends a closing packet to notify this.
This packet has identifier `06 81 00` and empty payload.


### Unknown message 2

Request identifier: `01 09 02`, checksum: `01 0b`, empty payload.

Response identifier: `01 89 00`, payload was for me `55 0c 00 00`.

### Unknown message 3

Request identifier: `04 00 02`, checksum: `01 05`, empty payload.

Response identifier: `04 80 00`. The payload was for me a
byte with value 2 followed by a long sequence of bytes with value 0 (160 bytes).

## Packet data samples

This is a collection of packets I used for determining the protocol.
The inverter used is SolarRiver 4500 TL-D, which connected to an installation of the official
[SolarPower Browser V3](https://web.archive.org/web/20190720131520/http://www.samilpower.com/service.php)
client.

Aside from these samples, I also used a script for simulating an inverter,
by having the official SolarPower Browser V3 software tricked into connecting to that fake inverter,
to test different inverter types or extreme values.

***

Request: `55 aa 01 03 02 00 00 01 05`

Response after 2 seconds:
```
0000   55 aa 01 83 00 00 47 31 20 20 34 35 30 30 56 31  U.....G1  4500V1
0010   2e 33 30 52 69 76 65 72 20 34 35 30 30 54 4c 2d  .30River 4500TL-
0020   44 00 20 53 61 6d 69 6c 50 6f 77 65 72 00 20 20  D. SamilPower.  
0030   20 20 20 44 57 34 31 33 42 38 30 38 30 00 00 00     DW413B8080...
0040   00 00 00 56 31 2e 33 30 56 31 2e 33 30 32 11 88  ...V1.30V1.302..
```

Bytes:
```
0x00: 55 aa 01, same as request
0x03: 83 00, message type identifier?
0x05: payload length, 0x47 = 71 bytes, payload end: 0x7+0x47=0x4e
0x07: payload start, 0x31? length?
0x08: "  4500"
0x0e: "V1.30"
0x13: "River 4500TL-D"
0x21: 00 20
0x23: "SamilPower"
0x2d: 00 20 20 20 20 20
0x33: "DW413B8080"
0x3d: 00 00 00 00 00 00
0x43: "V1.30V1.30"
0x4d: 32?
0x4e: 11 88, checksum
```

***

Request: `55 aa 01 00 02 00 00 01 02`, response after 2 seconds:

```
0000   55 aa 01 80 00 00 1b 00 01 02 04 05 09 0a 0c 11  U...............
0010   17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34  ....... !"'(1234
0020   35 36 04 7e                                      56.~
```

Bytes:
```
0x00: 55 aa 01, same as request
0x03: 80 00
0x05: 00 1b, payload length, 0x1b = 27 bytes
0x07: unknown payload, decimal byte values: 0 1 2 4 5 9 10 12 17 23 24 27 28 29 30 31 32 33 34 39 40 49 50 51 52 53 54?
0x22: checksum
```

***

Request: `55 aa 01 09 02 00 00 01 0b`.

Response after 2 seconds: `55 aa 01 89 00 00 04 55 0c 00 00 01 ee`

Bytes:
```
0x00: 55 aa 01, same as request
0x03: 89 00?
0x05: 00 04, payload length (4 bytes)
0x07: 55 0c 00 00? unknown payload
0x0b: checksum
```

***

Request: `55 aa 04 00 02 00 00 01 05`.

Response after 2 seconds:
```
0000   55 aa 04 80 00 00 a1 02 00 00 00 00 00 00 00 00  U...............
0010   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0030   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0040   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0050   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0060   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0070   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0080   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0090   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00a0   00 00 00 00 00 00 00 00 02 26                    .........&
```

Bytes:
```
0x00: 55 aa 04, same as request
0x03: 80 00
0x05: 00 a1 = 161, length of payload
0x07: payload, all zeros?
0xa8: 02 26, end
```

***

Request: `55 aa 01 02 02 00 00 01 04`. Response after 2 seconds:

```
0000   55 aa 01 82 00 00 36 01 77 0b ac 0b e1 00 15 00  U.....6.w.......
0010   14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00  ...(@...........
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02  ................
0030   76 00 38 09 1b 13 86 04 fb 00 01 b1 cc 09 b8     v.8............
```

Request (283): `55 aa 01 02 02 00 00 01 04`. Response after 2 seconds:

```
0000   55 aa 01 82 00 00 36 01 77 0b ac 0b e4 00 15 00  U.....6.w.......
0010   14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00  ...(@...........
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02  ................
0030   75 00 38 09 16 13 86 04 f8 00 01 b1 cc 09 b2     u.8............
```

Request (291): `55 aa 01 02 02 00 00 01 04`. Response (294) after 2 seconds:

```
0000   55 aa 01 82 00 00 36 01 77 0b a3 0b f3 00 15 00  U.....6.w.......
0010   14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00  ...(@...........
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 02 8a 02  ................
0030   72 00 37 09 14 13 86 04 f5 00 01 b1 cc 09 ad     r.7............
```

A couple more...

Response 309:
```
0000   55 aa 01 82 00 00 36 01 77 0b 9f 0b f6 00 15 00  U.....6.w.......
0010   14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00  ...(@...........
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 02 88 02  ................
0030   6f 00 37 09 14 13 86 04 ee 00 01 b1 cc 09 a0     o.7............
```
Bytes, offset is in hexadecimal, values are received big endian:
```
0x00: 55 aa 01, same as request
0x03: 82 00, message identifier?
0x05: 0x0 0x36, payload length (0x07+0x36 = 0x3d)
0x07: internal temperature in decicelcius (375 = 37.5 degrees Celcius)
0x09: PV1 voltage in decivolts (0x0b9f = 2975 = 297.5 V)
0x0b: PV2 voltage in decivolts (0x0bf6 = 3062 = 306.2V)
0x0d: PV1 current in deciampere (0x0015 = 21 = 2.1 A)
0x0f: PV2 current in deciampere
0x11: ? 0
0x13: total operation hours (0x2840 = 10304 hours)
0x15: ? 1
0x17: energy today in decawatt hour (0x1da = 474 = 4.74 kW h)
0x19: ? a lot of zeros
0x2d: PV1 input in watt (0x288 = 648 W)
0x2f: PV2 input in watt
0x31: single phase grid in deciampere
0x33: single phase grid in decivolts
0x35: single phase grid in centihertz (0x1386 = 4998 = 49.98 Hz)
0x37: output power in watt
0x39: ? 1
0x3b: ? 0xb1cc = 45516
0x3d: checksum
```
SolarPower Browser values after above response:
```
Operation mode: normal
Total operation hour: 10304 h

ID info
Device type: single phase inverter
VA rating: 4500
Model name: River 4500TL-D
Manufacturer: SamilPower
Serial number: DW413B8080

Input data
PV1 input: 648 W
PV2 input: 623 W
PV1 voltage: 297.5 V
PV2 voltage: 306.2 V
PV1 current: 2.1 A
PV2 current: 2.0 A

Output data
Output power: 1262 W
Energy today: 4.74 kWh
Energy total: 11105.2 kWh

Single phase
Grid: 232.4 V
Grid: 5.5 A
Grid: 49.98 Hz

Other data
Internal: 37.5 deg C
Heatsink: 0.0 deg C
Reduced: 11071.884 kg
Reduced: 333.156 kg
Reduced: 2976.194 kg
Reduced: 4442.080 kg
```
A couple more...

***

Request for historical data: `55 aa 06 01 02 00 02 10 10 01 2a`.

Bytes:
```
0x00: 55 aa 06, message identifier?
0x03: 01 02?
0x05: payload length, 2 bytes
0x07: last two digits of start year (0x10 = 16 -> 2016)
0x08: last two digits of end year (0x10 = 16 -> 2016)
0x09: end, 01 2a
```

The server responses with multiple packets:

```
0000   55 aa 06 61 00 00 8f 10 01 01 00 00 01 38 00 00  U..a.........8..
0010   00 03 00 00 00 00 30 30 3a 30 30 2c 2d 2d 2d 39  ......00:00,---9
0020   32 0d 0a 30 31 3a 30 30 2c 30 2e 30 30 20 0d 0a  2..01:00,0.00 ..
0030   30 32 3a 30 30 2c 30 2e 30 30 20 0d 0a 30 33 3a  02:00,0.00 ..03:
0040   30 30 2c 30 2e 30 30 20 0d 0a 30 34 3a 30 30 2c  00,0.00 ..04:00,
0050   30 2e 30 30 20 0d 0a 30 35 3a 30 30 2c 30 2e 30  0.00 ..05:00,0.0
0060   30 20 0d 0a 30 36 3a 30 30 2c 30 2e 30 30 20 0d  0 ..06:00,0.00 .
0070   0a 30 37 3a 30 30 2c 30 2e 30 33 20 0d 0a 30 38  .07:00,0.03 ..08
0080   3a 30 30 2c 30 2e 32 34 20 0d 0a 30 39 3a 30 30  :00,0.24 ..09:00
0090   2c 30 2e 34 30 20 17 88                          ,0.40 ..

0000   55 aa 06 61 00 00 8f 10 01 01 00 00 01 38 00 00  U..a.........8..
0010   00 03 00 00 00 01 0d 0a 31 30 3a 30 30 2c 31 2e  ........10:00,1.
0020   30 33 20 0d 0a 31 31 3a 30 30 2c 31 2e 31 37 20  03 ..11:00,1.17 
0030   0d 0a 31 32 3a 30 30 2c 30 2e 36 38 20 0d 0a 31  ..12:00,0.68 ..1
0040   33 3a 30 30 2c 30 2e 33 31 20 0d 0a 31 34 3a 30  3:00,0.31 ..14:0
0050   30 2c 30 2e 30 35 20 0d 0a 31 35 3a 30 30 2c 30  0,0.05 ..15:00,0
0060   2e 30 30 20 0d 0a 31 36 3a 30 30 2c 30 2e 30 30  .00 ..16:00,0.00
0070   20 0d 0a 31 37 3a 30 30 2c 30 2e 30 30 20 0d 0a   ..17:00,0.00 ..
0080   31 38 3a 30 30 2c 30 2e 30 30 20 0d 0a 31 39 3a  18:00,0.00 ..19:
0090   30 30 2c 30 2e 30 17 5d                          00,0.0.]

0000   55 aa 06 61 00 00 47 10 01 01 00 00 01 38 00 00  U..a..G......8..
0010   00 03 00 00 00 02 30 20 0d 0a 32 30 3a 30 30 2c  ......0 ..20:00,
0020   30 2e 30 30 20 0d 0a 32 31 3a 30 30 2c 30 2e 30  0.00 ..21:00,0.0
0030   30 20 0d 0a 32 32 3a 30 30 2c 30 2e 30 30 20 0d  0 ..22:00,0.00 .
0040   0a 32 33 3a 30 30 2c 30 2e 30 30 20 0d 0a 0a de  .23:00,0.00 ....

...
```

### Samples at night (no PV output)

Current values:
```
0000   55 aa 01 82 00 00 36 00 00 00 00 00 00 00 00 00  U.....6.........
0010   00 00 00 29 9f 00 05 07 ef 00 00 00 00 00 00 00  ...)............
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0030   00 00 00 00 00 00 00 00 00 00 01 bf 4f 04 8a     ............O..
```
Model info:
```
0000   55 aa 01 83 00 00 47 31 20 20 34 35 30 30 56 31  U.....G1  4500V1
0010   2e 33 30 52 69 76 65 72 20 34 35 30 30 54 4c 2d  .30River 4500TL-
0020   44 00 20 53 61 6d 69 6c 50 6f 77 65 72 00 20 20  D. SamilPower.  
0030   20 20 20 44 57 34 31 33 42 38 30 38 30 00 00 00     DW413B8080...
0040   00 00 00 56 31 2e 33 30 56 31 2e 33 30 32 11 88  ...V1.30V1.302..
```
Unknown 1:
```
0000   55 aa 01 80 00 00 1b 00 01 02 04 05 09 0a 0c 11  U...............
0010   17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34  ....... !"'(1234
0020   35 36 04 7e                                      56.~
```
Unknown 2:
```
0000   55 aa 01 89 00 00 04 55 0c 00 00 01 ee           U......U.....
```
Unknown 3:
```
0000   55 aa 04 80 00 00 a1 02 00 00 00 00 00 00 00 00  U...............
0010   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0020   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0030   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0040   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0050   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0060   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0070   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0080   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0090   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00a0   00 00 00 00 00 00 00 00 02 26                    .........&
```

## Other resources

These are files that are saved by SamilPower Browser V3.

### ~/Data/ID Info/DW413B8080.csv

```
Serial number,Device Type,VA rating,Firmware Ver,Model Name,Manufacturer,Communication Ver,Other Ver,General
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V .  ,V .  ,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V .  ,V .  ,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
DW413B8080,1,  4500,V1.30,River 4500TL-D,SamilPower,V1.30,V1.30,2
```

### ~/Data/Daily/2016-5-26/DW413B8080.csv

```
Time,Temperature,PV1 Voltage[V],PV2 Voltage[V],PV1 Current[A],PV2 Current[A],Total energy[KW.Hr],Total operation hours[Hr],Total AC Power[W],Mode,Daily Energy[KW.Hr],PV1 Input Power[W],PV2 Input Power[W],Heatsink Temperature,Current to grid (R Phase)[A],Grid voltage(R Phase)[V],Grid frequency(R Phase)[Hz],Current to grid (S Phase)[A],Grid voltage(S Phase)[V],Grid frequency(S Phase)[Hz],Current to grid (T Phase)[A],Grid voltage(T Phase)[V],Grid frequency(T Phase)[Hz],Reduced amount of CO2[KG],Reduced amount of SO2[KG],Reduced amount of Oil[KG],Reduced amount of Coal[KG]
2016-5-26 20:15:25,31.4,273.1,285.4,0.5,0.4,11317.9,10506,272,Normal,25.70,157,130,0.0,1.6,227.3,49.99,0.0,0.0,0.00,0.0,0.0,0.00,11283.946,339.537,3033.197,4527.160
2016-5-26 20:40:41,30.5,324.5,326.0,0.0,0.0,11318.0,10506,0,Wait,25.78,0,0,0.0,0.0,224.8,49.97,0.0,0.0,0.00,0.0,0.0,0.00,11284.046,339.540,3033.224,4527.200
```
