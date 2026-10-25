import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class GamificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="ecoreto-tests-")
        self.env_keys = (
            "DATABASE_PATH",
            "DATABASE_URL",
            "SECRET_KEY",
            "ECO_ACTION_POINTS",
            "ECO_ACTION_EXPERIENCE",
        )
        self.previous_env = {key: os.environ.get(key) for key in self.env_keys}
        os.environ["DATABASE_PATH"] = str(Path(self.temp_dir.name) / "test.sqlite")
        os.environ["DATABASE_URL"] = ""
        os.environ["SECRET_KEY"] = "gamification-test-secret"
        os.environ["ECO_ACTION_POINTS"] = "100"
        os.environ["ECO_ACTION_EXPERIENCE"] = "125"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.client.post(
            "/registro",
            data={
                "username": "eco_test",
                "password": "test-password-123",
                "confirm_password": "test-password-123",
            },
            follow_redirects=True,
        )
        self.client.post(
            "/login",
            data={"username": "eco_test", "password": "test-password-123"},
            follow_redirects=True,
        )

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def create_action(self, title, token=None, category="Reciclaje"):
        if token is None:
            form = self.client.get("/acciones/nueva").get_data(as_text=True)
            token = re.search(
                r'name="submission_token" value="([^"]+)"', form
            ).group(1)
        response = self.client.post(
            "/acciones/nueva",
            data={
                "submission_token": token,
                "titulo": title,
                "categoria": category,
                "descripcion": f"Descripción de {title}",
                "fecha": "",
                "impacto": "",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True), token

    def query_one(self, sql, params=()):
        connection = sqlite3.connect(os.environ["DATABASE_PATH"])
        try:
            return connection.execute(sql, params).fetchone()
        finally:
            connection.close()

    def test_garden_and_shop_are_separate_pages_and_home_has_navigation_only(self):
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        dashboard_html = dashboard.get_data(as_text=True)
        self.assertIn('href="/jardin"', dashboard_html)
        self.assertIn('href="/tienda"', dashboard_html)
        self.assertNotIn("Mi jardín virtual", dashboard_html)
        self.assertNotIn("Tienda de recompensas", dashboard_html)
        self.assertNotIn("Elige tu próxima recompensa", dashboard_html)

        garden = self.client.get("/jardin")
        self.assertEqual(garden.status_code, 200)
        garden_html = garden.get_data(as_text=True)
        self.assertIn("Mi jardín virtual", garden_html)
        self.assertIn('href="/dashboard"', garden_html)
        self.assertIn("pulsa el lugar exacto", garden_html)
        self.assertIn("data-garden-placement", garden_html)

        shop = self.client.get("/tienda")
        self.assertEqual(shop.status_code, 200)
        shop_html = shop.get_data(as_text=True)
        self.assertIn("Tienda ecológica", shop_html)
        self.assertIn("Tu saldo disponible", shop_html)
        self.assertIn("Semilla de girasol", shop_html)

    def test_every_action_keeps_rewards_without_missions_and_replay_is_ignored(self):
        connection = sqlite3.connect(os.environ["DATABASE_PATH"])
        try:
            connection.execute("DELETE FROM eco_missions")
            connection.commit()
        finally:
            connection.close()

        first_response, replay_token = self.create_action("Acción 1")
        self.assertIn("+100 puntos y +125 XP", first_response)
        for number in range(2, 13):
            response, _ = self.create_action(f"Acción {number}")
            self.assertIn("+100 puntos y +125 XP", response)

        duplicate_response, _ = self.create_action("Acción duplicada", replay_token)
        self.assertIn("no se creó otra acción", duplicate_response)
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM acciones")[0], 12)
        self.assertEqual(
            self.query_one(
                "SELECT COUNT(*) FROM eco_point_ledger WHERE source_type = 'action'"
            )[0],
            12,
        )
        self.assertEqual(
            self.query_one("SELECT points, experience FROM eco_progress"),
            (1200, 1500),
        )

    def test_new_garden_grows_at_configured_thresholds_and_never_caps_actions(self):
        initial = re.sub(
            r"\s+", " ", self.client.get("/jardin").get_data(as_text=True)
        )
        self.assertIn("Nivel 1: Semilla", initial)
        self.assertIn("Acciones ecológicas: 0 de 3", initial)
        self.assertIn("aria-valuenow=\"0\"", initial)
        self.assertIn("¡Completa 3 acciones más", initial)

        growth_levels = (
            (3, 2, "Brote"),
            (7, 3, "Jardín en crecimiento"),
            (12, 4, "Jardín floreciente"),
            (20, 5, "Jardín ecológico"),
        )
        completed = 0
        for threshold, level, name in growth_levels:
            while completed < threshold:
                completed += 1
                action_response, _ = self.create_action(
                    f"Acción ecológica {completed}"
                )
            self.assertIn(
                f"¡Tu jardín creció al nivel {level}: {name}!",
                action_response,
            )
            garden = re.sub(
                r"\s+", " ", self.client.get("/jardin").get_data(as_text=True)
            )
            self.assertIn(f"Nivel {level}: {name}", garden)
            self.assertIn(f"Acciones ecológicas: {threshold}", garden)

        self.assertIn("aria-valuenow=\"100\"", garden)
        self.assertIn("alcanzó su máximo desarrollo", garden)
        self.create_action("Acción ecológica después del máximo")
        garden = re.sub(
            r"\s+", " ", self.client.get("/jardin").get_data(as_text=True)
        )
        self.assertIn("Nivel 5: Jardín ecológico", garden)
        self.assertIn("Acciones ecológicas: 21 · nivel máximo", garden)
        self.assertEqual(
            self.query_one(
                "SELECT COUNT(*) FROM eco_point_ledger WHERE source_type = 'action'"
            )[0],
            21,
        )

    def test_garden_progress_is_persistent_and_independent_per_user(self):
        for number in range(1, 8):
            self.create_action(f"Acción persistente {number}")
        self.assertIn(
            "Nivel 3: Jardín en crecimiento",
            self.client.get("/jardin").get_data(as_text=True),
        )

        other_client = self.app.test_client()
        other_client.post(
            "/registro",
            data={
                "username": "garden_progress_user",
                "password": "other-password-123",
                "confirm_password": "other-password-123",
            },
            follow_redirects=True,
        )
        other_client.post(
            "/login",
            data={
                "username": "garden_progress_user",
                "password": "other-password-123",
            },
            follow_redirects=True,
        )
        self.assertIn(
            "Nivel 1: Semilla",
            other_client.get("/jardin").get_data(as_text=True),
        )

        self.app = create_app()
        self.app.testing = True
        reloaded_client = self.app.test_client()
        reloaded_client.post(
            "/login",
            data={"username": "eco_test", "password": "test-password-123"},
            follow_redirects=True,
        )
        self.assertIn(
            "Nivel 3: Jardín en crecimiento",
            reloaded_client.get("/jardin").get_data(as_text=True),
        )
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM acciones")[0], 7)

    def test_garden_level_does_not_regress_when_action_is_removed(self):
        for number in range(1, 8):
            self.create_action(f"Acción que puede eliminarse {number}")
        action_id = self.query_one(
            "SELECT id FROM acciones ORDER BY id DESC LIMIT 1"
        )[0]
        connection = sqlite3.connect(os.environ["DATABASE_PATH"])
        try:
            connection.execute("DELETE FROM acciones WHERE id = ?", (action_id,))
            connection.commit()
        finally:
            connection.close()

        garden = re.sub(
            r"\s+", " ", self.client.get("/jardin").get_data(as_text=True)
        )
        self.assertIn("Nivel 3: Jardín en crecimiento", garden)
        self.assertIn("Acciones ecológicas: 7 de 12", garden)
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM acciones")[0], 6)
        self.assertEqual(
            self.query_one(
                """SELECT COUNT(*) FROM eco_point_ledger
                   WHERE source_type = 'action'"""
            )[0],
            7,
        )

    def test_garden_visual_growth_continues_past_maximum_level(self):
        for number in range(1, 32):
            self.create_action(f"Acción de crecimiento {number}")

        response = self.client.get("/jardin")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Nivel 5 · Jardín ecológico · 9 plantas", html)
        self.assertIn("--garden-scene-height: 380px", html)
        self.assertEqual(html.count('class="garden-plant '), 9)
        self.assertIn("plant-age-4", html)
        self.assertIn('images/garden-landscape.svg', html)

    def test_automatic_growth_preserves_manually_placed_decorations(self):
        user_id = self.query_one(
            "SELECT id FROM usuarios WHERE username = ?",
            ("eco_test",),
        )[0]
        connection = sqlite3.connect(os.environ["DATABASE_PATH"])
        try:
            cursor = connection.execute(
                """INSERT INTO eco_garden_items
                   (user_id, item_code, position_x, position_y)
                   VALUES (?, 'piedra', 37.5, 74.25)""",
                (user_id,),
            )
            garden_item_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        for number in range(1, 21):
            self.create_action(f"Acción con decoración {number}")

        self.assertEqual(
            self.query_one(
                """SELECT item_code, position_x, position_y
                   FROM eco_garden_items WHERE id = ?""",
                (garden_item_id,),
            ),
            ("piedra", 37.5, 74.25),
        )
        html = self.client.get("/jardin").get_data(as_text=True)
        self.assertIn(f'data-garden-item-id="{garden_item_id}"', html)
        self.assertIn("--placed-x: 37.5%; --placed-y: 74.25%;", html)

    def test_shop_purchase_is_atomic_idempotent_and_places_from_inventory(self):
        self.app.config["ACTION_REWARD_POINTS"] = 50
        self.create_action("Acción con recompensa")
        dashboard = self.client.get("/tienda").get_data(as_text=True)
        form = re.search(
            r'<form method="post" action="/tienda/comprar/girasol">(.*?)</form>',
            dashboard,
            re.DOTALL,
        ).group(1)
        token = re.search(
            r'name="purchase_token" value="([^"]+)"', form
        ).group(1)

        purchased = self.client.post(
            "/tienda/comprar/girasol",
            data={"purchase_token": token},
            follow_redirects=True,
        )
        self.assertIn("Compraste Semilla de girasol por 25 puntos", purchased.get_data(as_text=True))
        duplicate = self.client.post(
            "/tienda/comprar/girasol",
            data={"purchase_token": token},
            follow_redirects=True,
        )
        self.assertIn("no se descontaron puntos otra vez", duplicate.get_data(as_text=True))
        self.assertEqual(self.query_one("SELECT points FROM eco_progress")[0], 25)
        self.assertEqual(
            self.query_one(
                "SELECT quantity FROM eco_user_inventory WHERE item_code = 'girasol'"
            )[0],
            1,
        )

        placed = self.client.post(
            "/jardin/colocar/girasol",
            data={"position_x": "31.5", "position_y": "67.25"},
            follow_redirects=True,
        )
        self.assertIn("Colocaste Semilla de girasol", placed.get_data(as_text=True))
        self.assertEqual(
            self.query_one(
                "SELECT quantity FROM eco_user_inventory WHERE item_code = 'girasol'"
            )[0],
            0,
        )
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM eco_garden_items")[0], 1)
        self.assertEqual(
            self.query_one(
                "SELECT position_x, position_y FROM eco_garden_items"
            ),
            (31.5, 67.25),
        )
        garden_html = self.client.get("/jardin").get_data(as_text=True)
        self.assertIn("--placed-x: 31.5%; --placed-y: 67.25%;", garden_html)
        self.assertEqual(
            self.query_one(
                "SELECT COUNT(*) FROM eco_user_achievements WHERE achievement_code = 'garden_item'"
            )[0],
            1,
        )

        self.client.post(
            "/tienda/comprar/arbol",
            data={"purchase_token": "insufficient-balance-test"},
            follow_redirects=True,
        )
        self.assertEqual(self.query_one("SELECT points FROM eco_progress")[0], 25)
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM eco_shop_purchases")[0], 1)

        self.app = create_app()
        self.app.testing = True
        client = self.app.test_client()
        client.post(
            "/login",
            data={"username": "eco_test", "password": "test-password-123"},
            follow_redirects=True,
        )
        reloaded_dashboard = client.get("/dashboard").get_data(as_text=True)
        self.assertIn("Jardín con vida", reloaded_dashboard)
        self.assertIn("25", reloaded_dashboard)
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM eco_garden_items")[0], 1)
        self.assertEqual(
            self.query_one(
                "SELECT position_x, position_y FROM eco_garden_items"
            ),
            (31.5, 67.25),
        )
        self.assertEqual(
            self.query_one(
                "SELECT quantity FROM eco_user_inventory WHERE item_code = 'girasol'"
            )[0],
            0,
        )

    def test_invalid_garden_position_does_not_consume_inventory(self):
        self.app.config["ACTION_REWARD_POINTS"] = 50
        self.create_action("Acción para decoración")
        shop_html = self.client.get("/tienda").get_data(as_text=True)
        token = re.search(
            r'name="purchase_token" value="([^"]+)"',
            re.search(
                r'<form method="post" action="/tienda/comprar/girasol">(.*?)</form>',
                shop_html,
                re.DOTALL,
            ).group(1),
        ).group(1)
        self.client.post(
            "/tienda/comprar/girasol",
            data={"purchase_token": token},
            follow_redirects=True,
        )

        response = self.client.post(
            "/jardin/colocar/girasol",
            data={"position_x": "NaN", "position_y": "150"},
            follow_redirects=True,
        )
        self.assertIn("Elige un lugar válido", response.get_data(as_text=True))
        self.assertEqual(
            self.query_one(
                "SELECT quantity FROM eco_user_inventory WHERE item_code = 'girasol'"
            )[0],
            1,
        )
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM eco_garden_items")[0], 0)

    def test_moving_existing_garden_item_saves_position_without_consuming_inventory(self):
        self.create_action("Acción para mover decoración")
        user_id = self.query_one(
            "SELECT id FROM usuarios WHERE username = ?",
            ("eco_test",),
        )[0]
        connection = sqlite3.connect(os.environ["DATABASE_PATH"])
        try:
            cursor = connection.execute(
                """INSERT INTO eco_garden_items
                   (user_id, item_code, position_x, position_y)
                   VALUES (?, 'piedra', 25, 60)""",
                (user_id,),
            )
            garden_item_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        moved = self.client.post(
            f"/jardin/mover/{garden_item_id}",
            data={"position_x": "71.25", "position_y": "82.5"},
            follow_redirects=True,
        )
        self.assertEqual(moved.status_code, 200)
        self.assertIn("Moviste el objeto a su nueva posición", moved.get_data(as_text=True))
        self.assertEqual(
            self.query_one(
                "SELECT position_x, position_y FROM eco_garden_items WHERE id = ?",
                (garden_item_id,),
            ),
            (71.25, 82.5),
        )
        self.assertEqual(
            self.query_one("SELECT COUNT(*) FROM eco_garden_items")[0],
            1,
        )
        self.assertEqual(
            self.query_one(
                "SELECT COUNT(*) FROM eco_user_inventory WHERE user_id = ? AND item_code = 'piedra'",
                (user_id,),
            )[0],
            0,
        )
        self.assertEqual(self.query_one("SELECT points FROM eco_progress")[0], 100)

        garden_html = self.client.get("/jardin").get_data(as_text=True)
        self.assertIn(
            f'data-garden-item-id="{garden_item_id}"',
            garden_html,
        )
        self.assertIn("--placed-x: 71.25%; --placed-y: 82.5%;", garden_html)
        self.assertIn("Mover objeto a esta posición", garden_html)

        self.app = create_app()
        self.app.testing = True
        client = self.app.test_client()
        client.post(
            "/login",
            data={"username": "eco_test", "password": "test-password-123"},
            follow_redirects=True,
        )
        self.assertEqual(
            self.query_one(
                "SELECT position_x, position_y FROM eco_garden_items WHERE id = ?",
                (garden_item_id,),
            ),
            (71.25, 82.5),
        )

    def test_user_cannot_move_another_users_garden_item(self):
        other_client = self.app.test_client()
        registration = other_client.post(
            "/registro",
            data={
                "username": "other_garden_user",
                "password": "other-password-123",
                "confirm_password": "other-password-123",
            },
            follow_redirects=True,
        )
        self.assertEqual(registration.status_code, 200)
        other_client.post(
            "/login",
            data={"username": "other_garden_user", "password": "other-password-123"},
            follow_redirects=True,
        )
        other_user_id = self.query_one(
            "SELECT id FROM usuarios WHERE username = ?",
            ("other_garden_user",),
        )[0]
        connection = sqlite3.connect(os.environ["DATABASE_PATH"])
        try:
            cursor = connection.execute(
                """INSERT INTO eco_garden_items
                   (user_id, item_code, position_x, position_y)
                   VALUES (?, 'piedra', 34, 63)""",
                (other_user_id,),
            )
            other_item_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        response = self.client.post(
            f"/jardin/mover/{other_item_id}",
            data={"position_x": "80", "position_y": "80"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.query_one(
                "SELECT position_x, position_y FROM eco_garden_items WHERE id = ?",
                (other_item_id,),
            ),
            (34.0, 63.0),
        )

    def test_legacy_garden_rows_are_migrated_without_losing_items(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                """CREATE TABLE eco_garden_items (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    item_code TEXT NOT NULL,
                    placed_at TEXT
                )"""
            )
            connection.execute(
                "INSERT INTO eco_garden_items (id, user_id, item_code) VALUES (7, 3, 'girasol')"
            )
            connection.commit()
        finally:
            connection.close()

        original_path = os.environ["DATABASE_PATH"]
        os.environ["DATABASE_PATH"] = str(legacy_path)
        try:
            create_app()
        finally:
            os.environ["DATABASE_PATH"] = original_path

        migrated = sqlite3.connect(legacy_path)
        try:
            columns = {
                row[1] for row in migrated.execute("PRAGMA table_info(eco_garden_items)")
            }
            self.assertTrue({"position_x", "position_y"}.issubset(columns))
            self.assertEqual(
                migrated.execute(
                    "SELECT id, position_x, position_y FROM eco_garden_items"
                ).fetchone(),
                (7, 15, 61),
            )
        finally:
            migrated.close()

    def test_achievements_inventory_and_balances_survive_app_reinitialization(self):
        for number in range(1, 11):
            self.create_action(f"Acción {number}")

        dashboard = self.client.get("/dashboard").get_data(as_text=True)
        self.assertIn("Manos a la obra", dashboard)
        self.assertEqual(
            self.query_one(
                "SELECT COUNT(*) FROM eco_user_achievements "
                "WHERE achievement_code IN ('first_action', 'actions_10', 'level_5')"
            )[0],
            3,
        )

        self.app = create_app()
        self.app.testing = True
        client = self.app.test_client()
        client.post(
            "/login",
            data={"username": "eco_test", "password": "test-password-123"},
            follow_redirects=True,
        )
        reloaded_dashboard = client.get("/dashboard").get_data(as_text=True)
        self.assertIn("<strong>1000</strong>", reloaded_dashboard)
        self.assertIn("<strong>1250</strong>", reloaded_dashboard)
        self.assertIn("Manos a la obra", reloaded_dashboard)
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM acciones")[0], 10)
        self.assertEqual(
            self.query_one(
                "SELECT COUNT(*) FROM eco_user_achievements WHERE achievement_code = 'actions_10'"
            )[0],
            1,
        )


if __name__ == "__main__":
    unittest.main()
