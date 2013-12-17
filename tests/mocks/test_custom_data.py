from unittest import TestCase, main
try:
    from mock import MagicMock, patch
except ImportError:
    from unittest.mock import MagicMock, patch

from stormpath.resource.custom_data import CustomData


class TestCustomData(TestCase):

    def setUp(self):
        self.props = {
            'href': 'test/resource',
            'createdAt': 123,
            'foo': 1,
            'bar': '2',
            'baz': ['one', 'two', 'three'],
            'quux': {'key': 'value'}
        }

    def test_custom_data_created_with_properties(self):
        d = CustomData(MagicMock(), properties=self.props)

        self.assertTrue(d.is_materialized())
        self.assertEqual(d['foo'], 1)

    def test_readonly_properties_are_not_exposed_in_dict(self):
        d = CustomData(MagicMock(), properties=self.props)

        self.assertEqual(d.href, 'test/resource')
        self.assertFalse('href' in d)

    def test_readonly_properties_are_not_camels(self):
        d = CustomData(MagicMock(), properties=self.props)

        with self.assertRaises(AttributeError):
            self.createdAt
        self.assertEqual(d.created_at, 123)

    def test_custom_data_implements_dict_protocol(self):
        d = CustomData(MagicMock(), properties=self.props)

        self.assertTrue('foo' in d)
        self.assertEqual(d['foo'], 1)
        self.assertEqual(d.get('foo'), 1)
        self.assertEqual(d.get('nonexistent'), None)
        self.assertEqual(d.get('nonexistent', 42), 42)

        with self.assertRaises(KeyError):
            d['nonexistent']

        keys = set(sorted(d.keys(), key=str))
        self.assertEqual(keys, set(d))
        self.assertEqual(keys, {'bar', 'baz', 'foo', 'quux'})
        values = sorted(list(d.values()), key=str)

        keys_from_items = {k for k, v in d.items()}
        values_from_items = sorted([v for k, v in d.items()], key=str)

        self.assertEqual(keys, keys_from_items)
        self.assertEqual(values, values_from_items)

    def test_non_readonly_properties_can_be_set(self):
        d = CustomData(MagicMock(), properties=self.props)

        d['whatever'] = 42
        self.assertEqual(d['whatever'], 42)

    def test_readonly_properties_cant_be_set(self):
        d = CustomData(MagicMock(), properties=self.props)

        with self.assertRaises(KeyError):
            d['meta'] = 'i-am-so-meta'

    def test_del_properties_doesnt_trigger_resource_delete(self):
        ds = MagicMock()
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)

        del d['foo']
        self.assertFalse('foo' in d)

        self.assertFalse(ds.delete_resource.called)

    def test_serializing_props_only_serializes_custom_data(self):
        d = CustomData(MagicMock(), properties=self.props)

        del self.props['href']
        del self.props['createdAt']

        self.assertEqual(d._get_properties(), self.props)

    def test_manually_set_property_has_precedence(self):
        props = {
            'href': 'test/resource',
            'bar': '2',
            'baz': ['one', 'two', 'three'],
            'quux': {'key': 'value'}
        }

        d = CustomData(MagicMock(), properties=props)

        d['quux'] = 'a-little-corgi'
        d._set_properties(props)

        quux = d.data.pop('quux')
        props.pop('quux')
        props.pop('href')

        # quux property is as set
        self.assertEqual(quux, 'a-little-corgi')
        self.assertEqual(d.data, props)

    @patch('stormpath.resource.base.Resource._ensure_data')
    def test_non_materialized_property_is_ensured(self, _ensure_data):
        d = CustomData(MagicMock(), href='test/resource')

        self.assertFalse(d.is_materialized())
        d.get('corge')
        self.assertTrue(_ensure_data.called)

    def test_del_delays_deletion_until_save(self):
        ds = MagicMock()
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)
        del d['foo']
        del d['bar']

        self.assertEqual(d.__dict__['_deletes'],
            set(['test/resource/foo', 'test/resource/bar']))
        self.assertFalse(ds.delete_resource.called)
        d.save()
        ds.delete_resource.assert_any_call('test/resource/foo')
        ds.delete_resource.assert_any_call('test/resource/bar')
        self.assertEqual(ds.delete_resource.call_count, 2)

    @patch('stormpath.resource.base.Resource.is_new')
    def test_del_doesnt_delete_if_new_resource(self, is_new):
        is_new.return_value = True
        ds = MagicMock()
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)
        del d['foo']
        self.assertEqual(d.__dict__['_deletes'], set())

    def test_save_empties_delete_list(self):
        ds = MagicMock()
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)
        del d['foo']
        d.save()
        self.assertEqual(d.__dict__['_deletes'], set())

    def test_setitem_removes_from_delete_list(self):
        ds = MagicMock()
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)
        del d['foo']
        self.assertEqual(d.__dict__['_deletes'],
            set(['test/resource/foo']))
        d['foo'] = 'i-was-never-even-gone'
        self.assertEqual(d.__dict__['_deletes'], set())
        self.assertFalse(ds.delete_resource.called)

    def test_del_then_read_doesnt_set_deleted(self):
        props = {
            'href': 'test/resource',
            'bar': '2',
            'baz': ['one', 'two', 'three'],
            'quux': {'key': 'value'}
        }
        ds = MagicMock()
        ds.get_resource.return_value = self.props
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=props)
        del d['foo']
        with self.assertRaises(KeyError):
            d['foo']
        self.assertTrue('test/resource/foo' in d.__dict__['_deletes'])

    def test_doesnt_schedule_del_if_new_property(self):
        ds = MagicMock()
        ds.get_resource.return_value = self.props
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)
        with self.assertRaises(KeyError):
            del d['corge']
        self.assertFalse('test/resource/corge' in d.__dict__['_deletes'])

    def test_dash_not_allowed_at_beggining_of_key(self):
        ds = MagicMock()
        client = MagicMock(data_store=ds)

        d = CustomData(client, properties=self.props)
        with self.assertRaises(KeyError):
            d['-'] = 'dashing'



if __name__ == '__main__':
    main()
