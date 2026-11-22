import unittest
from scripts.interface_drift import compare, declarations


class InterfaceDriftTests(unittest.TestCase):
    def test_blank_lines_and_indentation_do_not_change_client_bodies(self):
        before = '@inlinable public func f() -> Int {\n let x = 1\n return x\n}\n'
        self.assertEqual(compare(before, before.replace('\n return', '\n\n\n    return')), [])
        self.assertTrue(compare(before, before.replace('1', '2')))
        self.assertTrue(compare('public func f() { print("a b") }', 'public func f() { print("a  b") }'))

    def test_keyword_parameter_labels_do_not_pair_unrelated_functions(self):
        for label in ('operator', 'macro', 'import', 'precedencegroup', 'class'):
            before = f'public func a({label} value: Int)\n'
            after = before.replace('func a', 'func b')
            self.assertEqual({change['kind'] for change in compare(before, after)}, {'added', 'removed'})

    def test_malformed_attributes_and_type_headers_have_local_diagnostics(self):
        for text, message in (
            ('@available(*, message: "unclosed)\npublic func f()\n', 'unterminated Swift attribute'),
            ('@available(*, deprecated\npublic func f()\n', 'unterminated Swift attribute'),
            ('public protocol P\npublic func f()\npublic struct Q {}\n', 'missing opening brace'),
            ('public struct P\n', 'missing opening brace'),
        ):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, f'line 1: {message}'):
                declarations(text)

    def test_declaration_keywords_inside_literals_do_not_change_scope(self):
        text = 'public func f(_ text: String = "extension T; macro m")\n'
        record = declarations(text)[0]
        self.assertEqual(record['declaration'], text.strip())
        self.assertEqual(record['owner'], '<module>')
        self.assertEqual({change['kind'] for change in compare(text, text.replace('macro m', 'macro n'))}, {'added', 'removed'})

    def test_previously_omitted_declaration_kinds(self):
        for declaration in ('import XCTest', 'public import UniformTypeIdentifiers',
                            'public macro m() = #externalMacro(module: "M", type: "T")',
                            'infix operator +++ : AdditionPrecedence',
                            'precedencegroup Custom {\n associativity: left\n}',
                            'extension M.T : CustomStringConvertible {\n}'):
            with self.subTest(declaration=declaration):
                self.assertEqual(len(compare('', declaration)), 1)

    def test_extension_conformances_constraints_and_multiline_headers(self):
        before = 'extension M.T : P where Element : Equatable {\n public func f()\n}\n'
        for after in (before.replace(' : P ', ' : Q '), before.replace('Equatable', 'Hashable')):
            self.assertEqual(compare(before, after)[0]['kind'], 'modified')
        self.assertEqual(compare(before, before.replace(' where ', '\n where ').replace(' {', '\n {')), [])

    def test_nested_and_escaped_attribute_strings_retain_availability(self):
        attribute = '@available(*, deprecated, renamed: "bar(_:)", message: "Use \\"bar()\\" instead")'
        for separator in ('\n', ' '):
            with self.subTest(separator=separator):
                before = attribute + separator + 'public func f()\n'
                record = declarations(before)[0]
                self.assertEqual(record['attributes'], [attribute])
                self.assertEqual(record['declaration'], 'public func f()')
                changes = compare(before, before.replace('instead', 'now'))
                self.assertEqual(len(changes), 1)
                self.assertEqual(changes[0]['kind'], 'modified')
        multiline = attribute.replace(', message:', ',\n message:') + '\npublic func f()\n'
        self.assertEqual(compare(attribute + '\npublic func f()\n', multiline), [])

    def test_precedence_and_macro_payload_changes_are_visible(self):
        before = 'precedencegroup Custom {\n associativity: left\n}\n'
        self.assertEqual(compare(before, before.replace('left', 'right'))[0]['kind'], 'modified')
        before = 'public macro m() = #externalMacro(module: "M", type: "T")\n'
        self.assertEqual(compare(before, before.replace('"T"', '"U"'))[0]['kind'], 'modified')

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
