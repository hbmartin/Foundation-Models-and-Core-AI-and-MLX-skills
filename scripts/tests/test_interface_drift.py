import unittest
from scripts.interface_drift import compare


class InterfaceDriftTests(unittest.TestCase):
    def test_reordered_types_and_attributes_do_not_remove_declarations(self):
        a = '@available(tvOS, unavailable)\n@available(iOS 27.0, *)\npublic struct A {\n public var x: Int {\n get\n }\n}\npublic struct B {\n}\n'
        b = 'public struct B {\n}\n@available(iOS 27.0, *)\n@available(tvOS, unavailable)\npublic struct A {\n public var x: Int {\n get\n }\n}\n'
        self.assertEqual(compare(a, b), [])

    def test_protocol_requirement_without_public_and_accessor_change_are_visible(self):
        a = 'public protocol P {\n var data: Int { get set }\n}\n'
        b = 'public protocol P {\n var name: String { get }\n var data: Int { get }\n}\n'
        changes = compare(a, b)
        self.assertEqual({c['kind'] for c in changes}, {'added', 'modified'})
        self.assertTrue(all(c['owner'] == 'P' for c in changes))

    def test_inlined_body_change_and_convenience_initializer_are_visible(self):
        a = 'extension M.Messages {\n @_alwaysEmitIntoClient public var reaction: String {\n get { "Tapback" }\n }\n}\n'
        b = a.replace('Tapback', 'CustomReaction').replace('\n}\n', '\n convenience public init(inputConnectionBehavior: Behavior)\n}\n')
        changes = compare(a, b)
        self.assertEqual(len(changes), 2)
        self.assertTrue(any('CustomReaction' in c.get('after', {}).get('body', '') for c in changes))

    def test_namespace_printing_is_normalized_but_platform_availability_is_kept(self):
        a = 'extension M::Policy {\n public static let persistent: M::Policy\n}\n'
        b = a.replace('::', '.').replace(' public static', ' @available(tvOS, unavailable)\n public static')
        changes = compare(a, b)
        self.assertEqual(len(changes), 1)
        self.assertIn('@available(tvOS, unavailable)', changes[0]['after']['attributes'])

    def test_changed_type_conformance_is_modified_not_removed(self):
        before = "public struct Loader<T> : Loading {\n}\n"
        after = "public struct Loader<T> : Loading, ExpressibleByArrayLiteral {\n}\n"
        changes = compare(before, after)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["kind"], "modified")

    def test_data_declarations_have_scoped_context(self):
        a = 'extension M.Transcript {\n public enum Entry {\n case text(String)\n }\n}\n'
        b = a.replace(' case text(String)', ' case text(String)\n @available(iOS 27.2, *)\n case data(M.Transcript.DataEntry)')
        change = compare(a, b)[0]
        self.assertEqual(change['owner'], 'M.Transcript.Entry')
        self.assertIn('DataEntry', change['after']['declaration'])
