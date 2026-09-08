import unittest
from urllib.parse import urlparse, parse_qs

import kurator_update as ku


class StudentTableParserTest(unittest.TestCase):
    def test_cashier_card_uses_fact_amount_only(self):
        self.assertEqual(ku.p_cashier('Student Kassa 0 14 607 000 0'), 14_607_000)

    def test_parses_rows_total_and_pagination(self):
        html = """
        <div>Jami: &nbsp; 2 &nbsp; ta yozuv</div>
        <table><tbody>
          <tr><td>+</td><td>1</td><td><a href="/account/student_list/detail/17015">Nasrullayeva Malikabonu</a></td><td>Senior 12</td><td>Abdulkhakova Fotimabonu</td></tr>
          <tr><td>+</td><td>2</td><td><a href="/account/student_list/detail/10871">Djalgasbaeva Uldai</a></td><td>Junior 23</td><td>Madina Normatova</td><td>05.09.2026 (14:34)</td></tr>
        </tbody></table>
        <a href="/account/index.php?page=student_list&amp;page_action=deleteStudent&amp;item_id=2026-09-01&amp;per_page=50&amp;p=2">2</a>
        """
        rows, pages, total = ku.parse_student_table(html)
        self.assertEqual(total, 2)
        self.assertEqual([row['id'] for row in rows], [17015, 10871])
        self.assertEqual(rows[0]['name'], 'Nasrullayeva Malikabonu')
        self.assertTrue(any('p=2' in page for page in pages))
        self.assertEqual(ku.row_admin_id(rows[0]['cells']), '13799')
        self.assertEqual(ku.row_admin_id(rows[1]['cells']), '16005')
        self.assertEqual(ku.row_action_date(rows[1]['cells']), '2026-09-05')

    def test_fetches_all_pages_and_deduplicates_students(self):
        pages = {
            1: """
              <div>Jami: 3 ta yozuv</div>
              <table><tr><td><a href='/account/student_list/detail/10'>Birinchi O‘quvchi</a></td></tr>
              <tr><td><a href='/account/student_list/detail/20'>Ikkinchi O‘quvchi</a></td></tr></table>
              <a href='/account/index.php?page=student_list&amp;page_action=frozenStudent&amp;item_id=2026-09-01&amp;p=2'>2</a>
            """,
            2: """
              <table><tr><td><a href='/account/student_list/detail/20'>Ikkinchi O‘quvchi</a></td></tr>
              <tr><td><a href='/account/student_list/detail/30'>Uchinchi O‘quvchi</a></td></tr></table>
            """,
        }

        class Response:
            def __init__(self, body):
                self.body = body

            def read(self):
                return self.body.encode()

        class Opener:
            def open(self, url, timeout=60):
                query = parse_qs(urlparse(url).query)
                return Response(pages[int(query.get('p', ['1'])[0])])

        rows = ku.crm_student_rows(Opener(), 'frozenStudent', '2026-09-01')
        self.assertEqual([row['id'] for row in rows], [10, 20, 30])

    def test_rejects_incomplete_pagination(self):
        class Response:
            def read(self):
                return b"<div>Jami: 2 ta yozuv</div><a href='/account/student_list/detail/10'>Bitta</a>"

        class Opener:
            def open(self, url, timeout=60):
                return Response()

        with self.assertRaisesRegex(RuntimeError, 'to.liq olinmadi'):
            ku.crm_student_rows(Opener(), 'deleteStudent', '2026-09-01')


if __name__ == '__main__':
    unittest.main()
