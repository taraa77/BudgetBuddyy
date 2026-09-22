import csv
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import MonthlyData, Expense


class CsvExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test_korisnik",
            password="Test-lozinka-123!",
        )
        cls.other_user = User.objects.create_user(
            username="drugi_korisnik",
            password="Druga-lozinka-123!",
        )

        cls.month = MonthlyData.objects.create(
            user=cls.user,
            month="2025-04",
            income=Decimal("1000.00"),
            goal=Decimal("200.00"),
        )
        Expense.objects.create(
            monthly_data=cls.month,
            category="smjestaj",
            amount=Decimal("500.00"),
        )
        Expense.objects.create(
            monthly_data=cls.month,
            category="hrana",
            amount=Decimal("280.00"),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("export_csv", args=[self.month.pk])

    def read_rows(self, response):
        text = response.content.decode("utf-8-sig")
        return list(csv.reader(StringIO(text), delimiter=";"))

    def test_csv_sadrzaj_i_izracuni(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "text/csv; charset=utf-8",
        )
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))

        rows = self.read_rows(response)

        self.assertEqual(
            rows[0],
            ["Mjesec", "Vrsta zapisa", "Opis", "Iznos (EUR)"],
        )
        self.assertTrue(all(len(row) == 4 for row in rows))
        self.assertIn(
            ["2025-04", "Trošak", "Smještaj", "500,00"], rows
        )
        self.assertIn(
            ["2025-04", "Sažetak", "Ukupni troškovi", "780,00"],
            rows,
        )
        self.assertIn(
            ["2025-04", "Sažetak", "Preostala sredstva", "220,00"],
            rows,
        )
        self.assertIn(
            ["2025-04", "Status", "Cilj ostvaren", ""], rows
        )

    def test_neprijavljen_korisnik(self):
        self.client.logout()
        response = self.client.get(self.url)

        expected = f"{reverse('login')}?next={self.url}"
        self.assertRedirects(
            response,
            expected,
            fetch_redirect_response=False,
        )

    def test_tudi_podaci_nisu_dostupni(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_nepostojeci_mjesec(self):
        url = reverse("export_csv", args=[999999])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_mjesec_bez_troskova(self):
        self.month.expenses.all().delete()
        rows = self.read_rows(self.client.get(self.url))

        self.assertIn(
            ["2025-04", "Sažetak", "Ukupni troškovi", "0,00"],
            rows,
        )
        self.assertIn(
            ["2025-04", "Sažetak", "Preostala sredstva", "1000,00"],
            rows,
        )

    def test_granica_ostvarenja_cilja(self):
        for goal, expected in [
            (Decimal("220.00"), "Cilj ostvaren"),
            (Decimal("220.01"), "Cilj nije ostvaren"),
        ]:
            with self.subTest(goal=goal):
                self.month.goal = goal
                self.month.save(update_fields=["goal"])
                rows = self.read_rows(self.client.get(self.url))

                self.assertIn(
                    ["2025-04", "Status", expected, ""], rows
                )

    def test_posebni_znakovi_i_tekst_formule(self):
        for category in ['Hrana; "ručak"', "=1+1"]:
            Expense.objects.create(
                monthly_data=self.month,
                category=category,
                amount=Decimal("1.00"),
            )

        rows = self.read_rows(self.client.get(self.url))

        self.assertIn(
            ["2025-04", "Trošak", 'Hrana; "ručak"', "1,00"], rows
        )
        self.assertIn(
            ["2025-04", "Trošak", "'=1+1", "1,00"], rows
        )

    def test_post_zahtjev_nije_dopusten(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)

    def test_gumb_csv_u_povijesti(self):
        response = self.client.get(reverse("history"))
        self.assertContains(response, f'href="{self.url}"')