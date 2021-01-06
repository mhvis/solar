from decimal import Decimal
from unittest import TestCase

from samil.pvoutput import aggregate_statuses


class AggregateStatusesTestCase(TestCase):

    def setUp(self) -> None:
        self.status = {
            'pv1_voltage': Decimal('442.8'),
            'pv2_voltage': Decimal('460.9'),
            'grid_voltage': Decimal('228.5'),
            'internal_temperature': Decimal('21.1'),
            'output_power': Decimal('170'),
            'energy_today': Decimal('5.67'),
            'operation_mode': "Normal",
        }

    def test_non_normal_operation_mode(self):
        self.status['operation_mode'] = "Not normal"
        result = aggregate_statuses([self.status])
        self.assertIsNone(result)

    def test_one(self):
        r = aggregate_statuses([self.status])
        self.assertEqual({
            'energy_gen': 5670,
            'power_gen': 170,
            'temp': Decimal('21.1'),
            'voltage': Decimal('228.5'),
        }, r)

    def test_two(self):
        status2 = dict(self.status)
        status2['internal_temperature'] = Decimal('22.1')
        status2['grid_voltage'] = Decimal('229.5')

        r = aggregate_statuses([self.status, status2])
        self.assertEqual({
            'energy_gen': 11340,
            'power_gen': 340,
            'temp': Decimal('21.6'),
            'voltage': Decimal('229.0'),
        }, r)

    def test_three_phase(self):
        status = dict(self.status)
        del status['grid_voltage']
        status['grid_voltage_r_phase'] = Decimal('228.6')
        status['grid_voltage_s_phase'] = Decimal('229.6')
        status['grid_voltage_t_phase'] = Decimal('229.5')
        r = aggregate_statuses([status])
        self.assertEqual({
            'energy_gen': 5670,
            'power_gen': 170,
            'temp': Decimal('21.1'),
            'voltage': Decimal('229.2'),
        }, r)

    def test_dc(self):
        r = aggregate_statuses([self.status], dc_voltage=True)
        self.assertEqual({
            'energy_gen': 5670,
            'power_gen': 170,
            'temp': Decimal('21.1'),
            'voltage': Decimal('451.8'),
        }, r)
